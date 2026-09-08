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

ALPHA_VALS=(0 0.5 1 2 4 8 16)
BETA_VALS=(0 0.5 1 2 4 8 16)
SMALL_SEEDS=(42 43 44)

HEADER="topology,mesh_rows,num_clusters,src_placement,routing_mode,alpha,beta,seed,queueing_latency,network_latency,latency,avg_hops"

extract_stats() {
    local csv="$1"; local stats="$2"; shift; shift
    local ql=$(grep "average_packet_queueing_latency" "$stats" | awk '{print $2}')
    local nl=$(grep "average_packet_network_latency" "$stats" | awk '{print $2}')
    local la=$(grep "average_packet_latency" "$stats" | awk '{print $2}')
    local hp=$(grep "average_hops" "$stats" | awk '{print $2}')
    echo "$@,${ql:-NA},${nl:-NA},${la:-NA},${hp:-NA}" >> "$csv"
}

run_one() {
    local name="$1"; local outdir="$RESULT/$name"; shift
    mkdir -p "$outdir"
    echo "=== $(date '+%H:%M:%S') $name ==="
    $GEM5 $SCRIPT "$@" > "$outdir/log.txt" 2>&1
    cp m5out/stats.txt "$outdir/stats.txt" 2>/dev/null
}

# ============================================================
# Small scale: Mesh 8x8 + SumcheckHierarchy 4x4x4
# ============================================================
CSV_SMALL="$RESULT/small_scale.csv"
echo "$HEADER" > "$CSV_SMALL"

# --- Mesh 8x8 baselines ---
MESH_8="--topology=MeshSumcheck --mesh-rows=8 --num-dirs=128 --routing-algorithm=0"

for place in corner center; do
    name="mesh_8x8_${place}"
    run_one "$name" $COMMON $MESH_8 --src-${place}
    extract_stats "$CSV_SMALL" "$RESULT/$name/stats.txt" \
        MeshSumcheck,8,0,${place},N/A,N/A,N/A,N/A
done

# --- SumcheckHierarchy 4x4x4 ---
HIER_4="--topology=SumcheckHierarchy --mesh-rows=4 --num-clusters=4 \
  --num-dirs=128 --interleaving-bits=7 --routing-algorithm=3 --entries-per-cluster=4"

for alpha in "${ALPHA_VALS[@]}"; do
    for beta in "${BETA_VALS[@]}"; do
        # fixed
        name="hier_4x4x4_fixed_a${alpha}_b${beta}"
        run_one "$name" $COMMON $HIER_4 \
            --sumcheck-routing=fixed --alpha="$alpha" --beta="$beta"
        extract_stats "$CSV_SMALL" "$RESULT/$name/stats.txt" \
            SumcheckHierarchy,4,4,N/A,fixed,${alpha},${beta},N/A

        # adaptive (3 seeds)
        for seed in "${SMALL_SEEDS[@]}"; do
            name="hier_4x4x4_adaptive_a${alpha}_b${beta}_s${seed}"
            run_one "$name" $COMMON $HIER_4 \
                --sumcheck-routing=adaptive --alpha="$alpha" --beta="$beta" \
                --sumcheck-seed="$seed"
            extract_stats "$CSV_SMALL" "$RESULT/$name/stats.txt" \
                SumcheckHierarchy,4,4,N/A,adaptive,${alpha},${beta},${seed}
        done
    done
done

# ============================================================
# Large scale: Mesh 16x16 + SumcheckHierarchy 4x8x8
# ============================================================
CSV_LARGE="$RESULT/large_scale.csv"
echo "$HEADER" > "$CSV_LARGE"

# --- Mesh 16x16 baselines ---
MESH_16="--topology=MeshSumcheck --mesh-rows=16 --num-dirs=512 --routing-algorithm=0"

for place in corner center; do
    name="mesh_16x16_${place}"
    run_one "$name" $COMMON $MESH_16 --src-${place}
    extract_stats "$CSV_LARGE" "$RESULT/$name/stats.txt" \
        MeshSumcheck,16,0,${place},N/A,N/A,N/A,N/A
done

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