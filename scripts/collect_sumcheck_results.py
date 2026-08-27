#!/usr/bin/env python3
"""Collect completed Phase-04 runs and actual config.ini topology costs."""

import argparse
import configparser
import csv
import json
import math
from pathlib import Path
import re
import statistics


def stats_values(path):
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        fields = line.split()
        if len(fields) < 2 or not fields[0].startswith("system.ruby.network."):
            continue
        try:
            value = float(fields[1])
            values[fields[0]] = value if math.isfinite(value) else None
        except ValueError:
            pass
    return values


def topology_cost(path):
    config = configparser.ConfigParser(interpolation=None, strict=False)
    config.read(path, encoding="utf-8")
    network = config["system.ruby.network"]
    routers = network.get("routers", "").split()
    int_links = network.get("int_links", "").split()
    ext_links = network.get("ext_links", "").split()
    radix = {router: 0 for router in routers}
    for section in int_links:
        destination = config[section]["dst_node"]
        radix[destination] += 1
    for section in ext_links:
        router = config[section]["int_node"]
        radix[router] += 1

    vnets = int(config["system.ruby"].get("number_of_virtual_networks", 3))
    vcs = int(network["vcs_per_vnet"])
    data_depth = int(network["buffers_per_data_vc"])
    ctrl_depth = int(network["buffers_per_ctrl_vc"])
    flit_bytes = int(network["ni_flit_size"])
    input_ports = len(int_links) + len(ext_links)
    slots_per_input = vcs * (2 * ctrl_depth + data_depth)
    slots = input_ports * slots_per_input
    return {
        "routers": len(routers),
        "directed_internal_links": len(int_links),
        "undirected_internal_links": len(int_links) // 2,
        "external_links": len(ext_links),
        "local_ports": len(ext_links),
        "router_input_ports": input_ports,
        "router_output_ports": input_ports,
        "directed_router_port_ends": 2 * input_ports,
        "directed_ni_port_ends": 2 * len(ext_links),
        "vnets": vnets,
        "vcs_per_vnet": vcs,
        "actual_input_vcs": input_ports * vnets * vcs,
        "buffer_slots": slots,
        "buffer_bits": slots * flit_bytes * 8,
        "buffers_per_data_vc": data_depth,
        "buffers_per_ctrl_vc": ctrl_depth,
        "maximum_radix": max(radix.values()),
        "sum_radix_squared": sum(value * value for value in radix.values()),
        "gateway_entry_link_latency": int(network["gateway_entry_link_latency"])
            if "gateway_entry_link_latency" in network else None,
        "root_gateway_link_latency": int(network["root_gateway_link_latency"])
            if "root_gateway_link_latency" in network else None,
    }


def collect(run_dir):
    report = json.loads((run_dir / "workload_report.json").read_text())
    if "configuration" in report:
        report["endpoint_mapping"] = report["configuration"]["endpoint_mapping"]
    stats = stats_values(run_dir / "stats.txt")
    cost = topology_cost(run_dir / "config.ini")
    prefix = "system.ruby.network."
    all_links = [
        value for name, value in stats.items()
        if name.startswith(prefix + "sumcheck_all_link_flits::")
    ]
    tracked = {
        name.rsplit("::", 1)[-1]: value for name, value in stats.items()
        if name.startswith(prefix + "sumcheck_tracked_link_flits::")
    }
    choices = {
        name.rsplit("::", 1)[-1]: value for name, value in stats.items()
        if name.startswith(prefix + "sumcheck_gateway_entry_choices::")
    }
    completion_cycles = max(1, report["completion_cycle"])
    tracked_utilization = {
        name: value / completion_cycles for name, value in tracked.items()
    }
    root_cut = {
        name: value for name, value in tracked_utilization.items()
        if "r68" in name
    }
    gateway_entry = {
        name: value for name, value in tracked_utilization.items()
        if "r68" not in name
    }
    report["gem5_metrics"] = {
        "average_packet_latency_ticks": stats.get(
            prefix + "average_packet_latency"
        ),
        "average_hops": stats.get(prefix + "average_hops"),
        "adaptive_reroute_rate": stats.get(
            prefix + "sumcheck_adaptive_reroute_rate"
        ),
        "maximum_link_load_flits": max(all_links, default=None),
        "maximum_link_utilization_flits_per_cycle": (
            max(all_links) / completion_cycles if all_links else None
        ),
        "tracked_root_gateway_entry_link_flits": tracked,
        "tracked_link_utilization_flits_per_cycle": tracked_utilization,
        "maximum_root_cut_utilization_flits_per_cycle": max(
            root_cut.values(), default=None
        ),
        "maximum_gateway_entry_utilization_flits_per_cycle": max(
            gateway_entry.values(), default=None
        ),
        "per_entry_choice_distribution": choices,
        "buffer_vc_stalls": None,
        "buffer_vc_stalls_note": (
            "This Garnet revision has no allocator-stall counter; endpoint "
            "MessageBuffer stall-time stats remain in raw stats.txt."
        ),
    }
    report["actual_topology_cost"] = cost
    report["raw_directory"] = str(run_dir)
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("results_root")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    root = Path(args.results_root)
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    reports = []
    failures = []
    for run_log in root.rglob("run.log"):
        run_dir = run_log.parent
        if not (run_dir / "workload_report.json").exists():
            failures.append({"directory": str(run_dir), "status": "failed_or_timeout"})
            continue
        report = collect(run_dir)
        if report["packets_injected"] != report["packets_received"]:
            failures.append({"directory": str(run_dir), "status": "accounting_mismatch"})
            continue
        reports.append(report)

    (output / "results.json").write_text(
        json.dumps({"completed": reports, "failed": failures}, indent=2) + "\n"
    )
    rows = []
    for report in reports:
        config = report["configuration"]
        metrics = report["gem5_metrics"]
        rows.append({
            "variant": report.get("variant", ""),
            "traffic_case": config["traffic_case"],
            "seed": config["seed"],
            "offered_load": config["offered_load_packets_per_cycle_per_worker"],
            "packets": report["packets_received"],
            "flits": report["flits_received"],
            "completion_cycle": report["completion_cycle"],
            "accepted_throughput": report["accepted_throughput_packets_per_cycle"],
            "mean_latency_cycles": report["mean_packet_latency_cycles"],
            "p95_latency_cycles": report["p95_packet_latency_cycles"],
            "p99_latency_cycles": report["p99_packet_latency_cycles"],
            "average_hops": metrics["average_hops"],
            "adaptive_reroute_rate": metrics["adaptive_reroute_rate"],
            "maximum_link_load_flits": metrics["maximum_link_load_flits"],
            "buffer_slots": report["actual_topology_cost"]["buffer_slots"],
            "cost_match_label": report.get("cost_match_label", ""),
            "raw_directory": report["raw_directory"],
        })
    with (output / "results.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]) if rows else ["variant"])
        writer.writeheader(); writer.writerows(rows)
    grouped = {}
    for row in rows:
        key = (row["variant"], row["traffic_case"], row["offered_load"])
        grouped.setdefault(key, []).append(row)
    summary_rows = []
    for (variant, traffic, load), group in sorted(grouped.items()):
        summary_rows.append({
            "variant": variant,
            "traffic_case": traffic,
            "offered_load": load,
            "seeds": len(group),
            "mean_accepted_throughput": statistics.fmean(
                row["accepted_throughput"] for row in group
            ),
            "mean_packet_latency_cycles": statistics.fmean(
                row["mean_latency_cycles"] for row in group
            ),
            "mean_p95_latency_cycles": statistics.fmean(
                row["p95_latency_cycles"] for row in group
            ),
            "mean_p99_latency_cycles": statistics.fmean(
                row["p99_latency_cycles"] for row in group
            ),
            "mean_average_hops": statistics.fmean(
                row["average_hops"] for row in group
            ),
            "mean_adaptive_reroute_rate": statistics.fmean(
                row["adaptive_reroute_rate"] or 0.0 for row in group
            ),
        })
    with (output / "summary.csv").open("w", newline="", encoding="utf-8") as stream:
        fields = list(summary_rows[0]) if summary_rows else ["variant"]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader(); writer.writerows(summary_rows)
    costs = {}
    for report in reports:
        costs.setdefault(report.get("variant", ""), report["actual_topology_cost"])
    (output / "costs.json").write_text(json.dumps(costs, indent=2) + "\n")
    print(f"COLLECT_PASS completed={len(reports)} failed={len(failures)}")


if __name__ == "__main__":
    main()
