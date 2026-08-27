#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 3 || $# -gt 4 ]]; then
    echo "usage: $0 OUTDIR fixed|adaptive aggregated|no-aggregation [p]" >&2
    exit 2
fi

outdir=$1
routing=$2
mode=$3
entries=${4:-4}

case "$routing" in
    fixed|adaptive) ;;
    *) echo "invalid routing: $routing" >&2; exit 2 ;;
esac
case "$mode" in
    aggregated|no-aggregation) ;;
    *) echo "invalid workload mode: $mode" >&2; exit 2 ;;
esac

mkdir -p "$outdir"
./build/NULL/gem5.debug \
    --outdir="$outdir" \
    configs/example/sumcheck_causal_traffic.py \
    --network=garnet \
    --topology=SumcheckHierarchy \
    --mesh-rows=0 \
    --routing-algorithm=3 \
    --sumcheck-routing="$routing" \
    --sumcheck-mode="$mode" \
    --entries-per-cluster="$entries" \
    --entry-placement=staggered \
    --vcs-per-vnet=4 \
    --link-width-bits=128 \
    --sumcheck-seed=7 \
    --sumcheck-watchdog-cycles=50000 \
    >"$outdir/run.log" 2>&1

grep 'SUMCHECK_CAUSAL_PASS' "$outdir/run.log"
python3 - "$outdir/workload_report.json" <<'PY'
import json
import sys

report = json.load(open(sys.argv[1], encoding="utf-8"))
assert report["packets_injected"] == report["packets_received"]
assert report["flits_injected"] == report["flits_received"]
assert report["outstanding_packets"] == 0
assert report["eject_then_reinject"] is True
print(
    "accounting PASS",
    report["packets_received"],
    "packets",
    report["flits_received"],
    "flits",
)
PY
