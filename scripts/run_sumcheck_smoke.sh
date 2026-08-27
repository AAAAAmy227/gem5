#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_root"

if [[ ${2:-} == fixed || ${2:-} == adaptive ]]; then
    outdir=$1
    routing_mode=$2
    run_case() {
        local name=$1 sender=$2 destination=$3 case_outdir="$outdir/$1"
        mkdir -p "$case_outdir"
        ./build/NULL/gem5.debug --outdir="$case_outdir" \
            configs/example/garnet_synth_traffic.py --network=garnet \
            --num-cpus=64 --num-dirs=8 --topology=SumcheckHierarchy \
            --mesh-rows=0 --routing-algorithm=3 \
            --sumcheck-routing="$routing_mode" --entries-per-cluster=4 \
            --entry-placement=staggered --inj-vnet=0 \
            --synthetic=uniform_random --sim-cycles=1000 \
            --injectionrate=1.0 --num-packets-max=1 \
            --single-sender-id="$sender" --single-dest-id="$destination" \
            >"$case_outdir/run.log" 2>&1
        local injected received
        injected=$(awk '$1=="system.ruby.network.packets_injected::total"{print $2}' "$case_outdir/stats.txt")
        received=$(awk '$1=="system.ruby.network.packets_received::total"{print $2}' "$case_outdir/stats.txt")
        [[ -n $injected && $injected == "$received" ]]
        echo "Sumcheck $routing_mode smoke $name PASS: injected=$injected received=$received"
    }
    run_case worker_to_remote_gateway 0 4
    run_case root_to_worker 63 0
    exit 0
fi

root=${1:-m5out/sumcheck_phase04/smoke}
variants=(
    Mesh_8x8_XY Hierarchy_p1_fixed Hierarchy_p2_fixed
    Hierarchy_p4_fixed Hierarchy_p4_adaptive
    Hierarchy_p4_adaptive_buffer_matched Hierarchy_p4_corners
    Hierarchy_p4_no_aggregation
)
for variant in "${variants[@]}"; do
    bash scripts/run_sumcheck_phase04_case.sh \
        "$root/$variant/seed7" "$variant" 7 causal
done
