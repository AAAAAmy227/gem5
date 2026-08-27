"""Run an arrival-triggered Sumcheck event graph on Garnet."""

import argparse
import json
import os
from pathlib import Path
import sys

import m5
from m5.objects import *
from m5.util import addToPath


addToPath("../")
from common import Options  # noqa: E402
from ruby import Ruby  # noqa: E402
from topologies.SumcheckWorkload import (  # noqa: E402
    build_aggregated_trace,
    build_no_aggregation_trace,
    trace_digest,
    write_jsonl,
)


parser = argparse.ArgumentParser()
Options.addNoISAOptions(parser)
parser.add_argument(
    "--sumcheck-mode",
    choices=("aggregated", "no-aggregation"),
    default="aggregated",
)
parser.add_argument("--sumcheck-seed", type=int, default=1)
parser.add_argument("--sumcheck-watchdog-cycles", type=int, default=50000)
parser.add_argument("--sumcheck-trace-file", default="")
parser.add_argument("--sumcheck-report-file", default="")
Ruby.define_options(parser)
parser.set_defaults(
    network="garnet",
    topology="SumcheckHierarchy",
    mesh_rows=0,
    routing_algorithm=3,
    num_cpus=64,
    num_dirs=5,
    vcs_per_vnet=4,
)
args = parser.parse_args()

if args.link_width_bits % 8 != 0:
    raise ValueError("--link-width-bits must be byte aligned")
if args.num_cpus != 64 or args.num_dirs != 5:
    raise ValueError("causal Sumcheck fixes --num-cpus=64 --num-dirs=5")
if args.sumcheck_seed < 0:
    raise ValueError("--sumcheck-seed must be non-negative")

if args.sumcheck_mode == "aggregated":
    events = build_aggregated_trace(
        args.entries_per_cluster, args.entry_placement
    )
else:
    events = build_no_aggregation_trace()

outdir = Path(m5.options.outdir).resolve()
outdir.mkdir(parents=True, exist_ok=True)
trace_file = Path(args.sumcheck_trace_file) if args.sumcheck_trace_file else (
    outdir / "trace.jsonl"
)
report_file = Path(args.sumcheck_report_file) if args.sumcheck_report_file else (
    outdir / "workload_report.json"
)
write_jsonl(events, trace_file)

system = System(mem_ranges=[AddrRange(args.mem_size)])
system.voltage_domain = VoltageDomain(voltage=args.sys_voltage)
system.clk_domain = SrcClockDomain(
    clock=args.sys_clock, voltage_domain=system.voltage_domain
)
system.sumcheck_workload = SumcheckWorkload(
    events=[event.wire_record() for event in events],
    mode=args.sumcheck_mode,
    report_file=str(report_file.resolve()),
    seed=args.sumcheck_seed,
    flit_bytes=args.link_width_bits // 8,
    watchdog_cycles=args.sumcheck_watchdog_cycles,
)

args.sumcheck_causal = True
Ruby.create_system(args, False, system, cpus=[])
system.ruby.clk_domain = SrcClockDomain(
    clock=args.ruby_clock, voltage_domain=system.voltage_domain
)

root = Root(full_system=False, system=system)
root.system.mem_mode = "timing"
m5.ticks.setGlobalFrequency("500ps")
m5.instantiate()
exit_event = m5.simulate(args.abs_max_tick)
m5.stats.dump()

if not report_file.exists():
    raise RuntimeError(
        f"Sumcheck workload did not produce {report_file}: "
        f"{exit_event.getCause()}"
    )
report = json.loads(report_file.read_text(encoding="utf-8"))
if report["packets_injected"] != report["packets_received"]:
    raise RuntimeError("Sumcheck packet accounting mismatch")
if report["flits_injected"] != report["flits_received"]:
    raise RuntimeError("Sumcheck flit accounting mismatch")

print(
    "SUMCHECK_CAUSAL_PASS",
    f"mode={args.sumcheck_mode}",
    f"routing={args.sumcheck_routing}",
    f"events={len(events)}",
    f"packets={report['packets_received']}",
    f"flits={report['flits_received']}",
    f"trace_sha256={trace_digest(events)}",
    f"completion_tick={report['completion_tick']}",
)
print("Exiting @ tick", m5.curTick(), "because", exit_event.getCause())
