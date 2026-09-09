#!/bin/bash
set +e

GEM5="./build/NULL/gem5.opt"
SCRIPT="configs/example/sumcheck_causal_traffic.py"
RESULT="results_adaptive"
mkdir -p "$RESULT"

# ============================================================
# Common parameters
# ============================================================
COMMON="--simulate-rounds=5 --num-sumcheck-rounds=15 --vcs-per-vnet=4 \
  --buffers-per-data-vc=4 --buffers-per-ctrl-vc=1 --poly-degree=3 \
  --multiply-latency=3 --network=garnet --root-ni-lanes=4 --root-dir-lanes=4"

ALPHA_VALS=(16 8 4 2 1 0.5 0)
BETA_VALS=(16 8 4 2 1 0.5 0)
SMALL_SEEDS=(42 43 44)

HEADER="topology,mesh_rows,num_clusters,src_placement,routing_mode,alpha,beta,seed,queueing_latency,network_latency,latency,avg_hops,total_reroutes,total_choices,reroute_rate"

extract_stats() {
    local csv="$1"; local stats="$2"; shift; shift
    local ql=$(grep "average_packet_queueing_latency" "$stats" | awk '{print $2}')
    local nl=$(grep "average_packet_network_latency" "$stats" | awk '{print $2}')
    local la=$(grep "average_packet_latency" "$stats" | awk '{print $2}')
    local hp=$(grep "average_hops" "$stats" | awk '{print $2}')
    local rr=$(grep "total_reroutes" "$stats" | awk '{print $2}')
    local tc=$(grep "total_choices" "$stats" | awk '{print $2}')
    local rt=$(grep "reroute_rate" "$stats" | awk '{print $2}')
    echo "$@,${ql:-NA},${nl:-NA},${la:-NA},${hp:-NA},${rr:-NA},${tc:-NA},${rt:-NA}" >> "$csv"
}

run_one() {
    local name="$1"; local outdir="$RESULT/$name"; shift
    mkdir -p "$outdir"
    echo "=== $(date '+%H:%M:%S') $name ==="
    $GEM5 $SCRIPT "$@" > "$outdir/log.txt" 2>&1
    cp m5out/stats.txt "$outdir/stats.txt" 2>/dev/null
}

# ============================================================
# Large scale: Mesh 16x16 + SumcheckHierarchy 4x8x8
# ============================================================
CSV_LARGE="$RESULT/large_scale_reversed.csv"
echo "$HEADER" > "$CSV_LARGE"

# --- SumcheckHierarchy 4x8x8 ---
HIER_8="--topology=SumcheckHierarchy --mesh-rows=8 --num-clusters=4 \
  --num-dirs=512 --interleaving-bits=9 --routing-algorithm=3 --entries-per-cluster=4"

for alpha in "${ALPHA_VALS[@]}"; do
    for beta in "${BETA_VALS[@]}"; do
        name="hier_4x8x8_fixed_a${alpha}_b${beta}"
        run_one "$name" $COMMON $HIER_8 \
            --sumcheck-routing=fixed --alpha="$alpha" --beta="$beta"
        extract_stats "$CSV_LARGE" "$RESULT/$name/stats.txt" \
            SumcheckHierarchy,8,4,N/A,fixed,${alpha},${beta},N/A

        name="hier_4x8x8_adaptive_a${alpha}_b${beta}"
        run_one "$name" $COMMON $HIER_8 \
            --sumcheck-routing=adaptive --alpha="$alpha" --beta="$beta"
        extract_stats "$CSV_LARGE" "$RESULT/$name/stats.txt" \
            SumcheckHierarchy,8,4,N/A,adaptive,${alpha},${beta},42
    done
done

echo "=== $(date '+%H:%M:%S') All done ==="
wc -l "$CSV_SMALL" "$CSV_LARGE"