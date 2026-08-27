#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 3 || $# -gt 6 ]]; then
    echo "usage: $0 OUTDIR VARIANT SEED [TRAFFIC [LOAD [CYCLES]]]" >&2
    exit 2
fi

outdir=$1
variant=$2
seed=$3
traffic=${4:-causal}
load=${5:-0.02}
cycles=${6:-200}
topology=SumcheckHierarchy
mesh_rows=0
routing_algorithm=3
routing=fixed
mode=aggregated
entries=4
placement=staggered
data_buffers=4
cost_label=primary_equal_per_vc

case "$variant" in
    Mesh_8x8_XY)
        topology=SumcheckMesh; mesh_rows=8; routing_algorithm=1 ;;
    Hierarchy_p1_fixed) entries=1 ;;
    Hierarchy_p2_fixed) entries=2 ;;
    Hierarchy_p4_fixed) ;;
    Hierarchy_p4_adaptive) routing=adaptive ;;
    Hierarchy_p4_adaptive_buffer_matched)
        routing=adaptive; data_buffers=3
        cost_label=lower_buffer_bracket_not_exact ;;
    Hierarchy_p4_corners) placement=corners ;;
    Hierarchy_p4_no_aggregation) mode=no-aggregation ;;
    *) echo "unknown Phase-04 variant: $variant" >&2; exit 2 ;;
esac

mkdir -p "$outdir"
if [[ -f "$outdir/workload_report.json" ]]; then
    python3 - "$outdir/workload_report.json" <<'PY'
import json, sys
r=json.load(open(sys.argv[1], encoding="utf-8"))
assert r["packets_injected"] == r["packets_received"]
assert r["flits_injected"] == r["flits_received"]
print("RESUME_SKIP", sys.argv[1])
PY
    exit 0
fi

./build/NULL/gem5.debug --outdir="$outdir" \
    configs/example/sumcheck_causal_traffic.py \
    --network=garnet --topology="$topology" --mesh-rows="$mesh_rows" \
    --routing-algorithm="$routing_algorithm" --sumcheck-routing="$routing" \
    --sumcheck-mode="$mode" --entries-per-cluster="$entries" \
    --entry-placement="$placement" --vcs-per-vnet=4 \
    --buffers-per-data-vc="$data_buffers" --buffers-per-ctrl-vc=1 \
    --link-width-bits=128 --link-latency=1 --router-latency=1 \
    --gateway-entry-link-latency=1 --root-gateway-link-latency=1 \
    --sumcheck-seed="$seed" --traffic-case="$traffic" \
    --offered-load="$load" --traffic-cycles="$cycles" \
    --sumcheck-watchdog-cycles=100000 >"$outdir/run.log" 2>&1

python3 - "$outdir/workload_report.json" "$variant" "$cost_label" <<'PY'
import json, pathlib, sys
path=pathlib.Path(sys.argv[1]); r=json.loads(path.read_text())
assert r["packets_injected"] == r["packets_received"]
assert r["flits_injected"] == r["flits_received"]
r["variant"] = sys.argv[2]
r["cost_match_label"] = sys.argv[3]
path.write_text(json.dumps(r, indent=2, sort_keys=True)+"\n")
print("PHASE04_CASE_PASS", sys.argv[2], r["packets_received"], "packets")
PY
