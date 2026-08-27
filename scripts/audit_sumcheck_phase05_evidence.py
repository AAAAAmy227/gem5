#!/usr/bin/env python3
"""Audit the raw Phase-04 evidence consumed by the final evaluation."""

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics


SMOKE_VARIANTS = {
    "Mesh_8x8_XY",
    "Hierarchy_p1_fixed",
    "Hierarchy_p2_fixed",
    "Hierarchy_p4_fixed",
    "Hierarchy_p4_adaptive",
    "Hierarchy_p4_adaptive_buffer_matched",
    "Hierarchy_p4_corners",
    "Hierarchy_p4_no_aggregation",
}
RAW_FILES = {
    "config.ini",
    "stats.txt",
    "trace.jsonl",
    "run.log",
    "workload_report.json",
}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_results(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if data["failed"]:
        raise AssertionError(f"accepted result set contains failures: {path}")
    return data["completed"]


def check_report(report):
    raw = Path(report["raw_directory"])
    missing = sorted(name for name in RAW_FILES if not (raw / name).is_file())
    if missing:
        raise AssertionError(f"{raw} lacks raw files: {missing}")
    if report["packets_injected"] != report["packets_received"]:
        raise AssertionError(f"packet mismatch in {raw}")
    if report["flits_injected"] != report["flits_received"]:
        raise AssertionError(f"flit mismatch in {raw}")
    trace_lines = sum(1 for line in (raw / "trace.jsonl").open(
        encoding="utf-8"
    ) if line.strip())
    if trace_lines != report["trace_events"]:
        raise AssertionError(f"trace/report event mismatch in {raw}")
    config = report["configuration"]
    for key in (
        "topology",
        "routing_algorithm",
        "sumcheck_routing",
        "traffic_case",
        "offered_load_packets_per_cycle_per_worker",
        "entries_per_cluster",
        "entry_placement",
        "seed",
        "vcs_per_vnet",
        "buffers_per_data_vc",
        "flit_bytes",
    ):
        if key not in config:
            raise AssertionError(f"{raw} lacks configuration key {key}")
    return raw


def check_summary(summary_path, reports):
    expected = {}
    groups = {}
    for report in reports:
        config = report["configuration"]
        key = (
            report["variant"],
            config["traffic_case"],
            float(config["offered_load_packets_per_cycle_per_worker"]),
        )
        groups.setdefault(key, []).append(report)
    for key, group in groups.items():
        expected[key] = {
            "seeds": len(group),
            "mean_accepted_throughput": statistics.fmean(
                item["accepted_throughput_packets_per_cycle"] for item in group
            ),
            "mean_packet_latency_cycles": statistics.fmean(
                item["mean_packet_latency_cycles"] for item in group
            ),
            "mean_p95_latency_cycles": statistics.fmean(
                item["p95_packet_latency_cycles"] for item in group
            ),
            "mean_p99_latency_cycles": statistics.fmean(
                item["p99_packet_latency_cycles"] for item in group
            ),
            "mean_average_hops": statistics.fmean(
                item["gem5_metrics"]["average_hops"] for item in group
            ),
            "mean_adaptive_reroute_rate": statistics.fmean(
                item["gem5_metrics"]["adaptive_reroute_rate"] or 0.0
                for item in group
            ),
        }
    with summary_path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != len(expected):
        raise AssertionError("summary row count mismatch")
    for row in rows:
        key = (
            row["variant"],
            row["traffic_case"],
            float(row["offered_load"]),
        )
        values = expected.pop(key)
        if int(row["seeds"]) != values["seeds"]:
            raise AssertionError(f"seed count mismatch for {key}")
        for name, value in values.items():
            if name == "seeds":
                continue
            if not math.isclose(float(row[name]), value, rel_tol=1e-12):
                raise AssertionError(f"summary mismatch for {key} {name}")
    if expected:
        raise AssertionError(f"summary lacks groups: {sorted(expected)}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root", type=Path, default=Path("m5out/sumcheck_phase04")
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root

    smoke_path = root / "results/smoke/results.json"
    sweep_path = root / "results/representative_sweep/results.json"
    smoke = load_results(smoke_path)
    sweep = load_results(sweep_path)
    for report in smoke + sweep:
        check_report(report)

    if len(smoke) != 8 or {item["variant"] for item in smoke} != SMOKE_VARIANTS:
        raise AssertionError("smoke variant coverage mismatch")
    if any(item["configuration"]["seed"] != 7 for item in smoke):
        raise AssertionError("smoke seed metadata mismatch")
    no_aggregation = next(
        item for item in smoke
        if item["variant"] == "Hierarchy_p4_no_aggregation"
    )
    if no_aggregation["trace_events"] != 1856:
        raise AssertionError("no-aggregation event count mismatch")
    if any(
        item["trace_events"] != 2004
        for item in smoke if item is not no_aggregation
    ):
        raise AssertionError("aggregated event count mismatch")

    expected_sweep = {
        (traffic, load, routing, seed)
        for traffic in ("uniform-random", "cluster-skewed-bursty")
        for load in (0.01, 0.08)
        for routing in ("fixed", "adaptive")
        for seed in range(1, 6)
    }
    actual_sweep = {
        (
            item["configuration"]["traffic_case"],
            float(item["configuration"][
                "offered_load_packets_per_cycle_per_worker"
            ]),
            item["configuration"]["sumcheck_routing"],
            item["configuration"]["seed"],
        )
        for item in sweep
    }
    if actual_sweep != expected_sweep:
        raise AssertionError("representative sweep cell coverage mismatch")
    check_summary(
        root / "results/representative_sweep/summary.csv", sweep
    )

    static = json.loads((root / "static_oracle.json").read_text())
    if static["measurement_kind"] != "static_not_gem5":
        raise AssertionError("static oracle measurement label is unsafe")
    if not all(
        case["matches_spec"]
        for name, case in static["cases"].items()
        if name != "Mesh_8x8_XY"
    ):
        raise AssertionError("hierarchy static oracle mismatch")
    if static["cases"]["Mesh_8x8_XY"]["matches_spec"]:
        raise AssertionError("known strict-XY discrepancy disappeared")

    original = root / "sweep/cluster-skewed-bursty/load_0.08/adaptive/seed1"
    repeated = root / "repro/cluster_skew_adaptive_seed1"
    reproducible = {
        name: {
            "original_sha256": sha256(original / name),
            "repeat_sha256": sha256(repeated / name),
            "byte_identical": (original / name).read_bytes()
            == (repeated / name).read_bytes(),
        }
        for name in ("trace.jsonl", "workload_report.json")
    }
    if not all(item["byte_identical"] for item in reproducible.values()):
        raise AssertionError("saved reproducibility evidence differs")

    failures = json.loads((root / "failures.json").read_text())
    if failures["accepted_smoke_failures"] or failures[
        "representative_sweep_failures"
    ] or failures["timeouts"]:
        raise AssertionError("accepted Phase-04 failures are non-empty")
    full_matrix_reports = list(
        (root / "full_matrix").rglob("workload_report.json")
    ) if (root / "full_matrix").exists() else []
    if full_matrix_reports:
        raise AssertionError(
            "full matrix now has data; evaluation/status must be re-audited"
        )

    output = {
        "status": "PASS",
        "phase04_smoke": {
            "completed": len(smoke),
            "failed": 0,
            "packets": sum(item["packets_received"] for item in smoke),
            "flits": sum(item["flits_received"] for item in smoke),
        },
        "phase04_representative_sweep": {
            "completed": len(sweep),
            "failed": 0,
            "packets": sum(item["packets_received"] for item in sweep),
            "flits": sum(item["flits_received"] for item in sweep),
            "cells": len(actual_sweep),
        },
        "raw_files_per_run": sorted(RAW_FILES),
        "static_measurement_kind": static["measurement_kind"],
        "saved_reproducibility": reproducible,
        "full_matrix_reports": 0,
        "disclosed_development_preflight_failures": len(
            failures["development_preflight_failures"]
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(
        "PHASE05_EVIDENCE_AUDIT_PASS",
        f"smoke={len(smoke)}",
        f"sweep={len(sweep)}",
        "full_matrix=unrun",
    )


if __name__ == "__main__":
    main()
