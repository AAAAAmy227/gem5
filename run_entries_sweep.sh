#!/bin/bash
set +e

GEM5="./build/NULL/gem5.opt"
SCRIPT="configs/example/sumcheck_causal_traffic.py"
RESULT="results_entries"
mkdir -p "$RESULT"

# ============================================================
# Common parameters
# ============================================================
COMMON="--simulate-rounds=5 --num-sumcheck-rounds=15 --vcs-per-vnet=4 \
  --buffers-per-data-vc=4 --buffers-per-ctrl-vc=1 --poly-degree=3 \
  --multiply-latency=3 --network=garnet --root-ni-lanes=4 --root-dir-lanes=4 \
  --sumcheck-routing=fixed"

ENTRIES_VALS=(1 2 4)

HEADER="topology,mesh_rows,num_clusters,entries_per_cluster,src_placement,queueing_latency,network_latency,latency,avg_hops"

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

# --- Mesh 8x8 baseline (src-center) ---
MESH_8="--topology=MeshSumcheck --mesh-rows=8 --num-dirs=128 \
  --routing-algorithm=0 --src-center"

run_one "mesh_8x8" $COMMON $MESH_8
extract_stats "$CSV_SMALL" "$RESULT/mesh_8x8/stats.txt" \
    MeshSumcheck,8,0,N/A,center

# --- SumcheckHierarchy 4x4x4, entries=1,2,4 ---
HIER_4="--topology=SumcheckHierarchy --mesh-rows=4 --num-clusters=4 \
  --num-dirs=128 --interleaving-bits=7 --routing-algorithm=3"

for entries in "${ENTRIES_VALS[@]}"; do
    name="hier_4x4x4_entries${entries}"
    run_one "$name" $COMMON $HIER_4 --entries-per-cluster="$entries"
    extract_stats "$CSV_SMALL" "$RESULT/$name/stats.txt" \
        SumcheckHierarchy,4,4,${entries},N/A
done

# ============================================================
# Large scale: Mesh 16x16 + SumcheckHierarchy 4x8x8
# ============================================================
CSV_LARGE="$RESULT/large_scale.csv"
echo "$HEADER" > "$CSV_LARGE"

# --- Mesh 16x16 baseline (src-center) ---
MESH_16="--topology=MeshSumcheck --mesh-rows=16 --num-dirs=512 \
  --routing-algorithm=0 --src-center"

run_one "mesh_16x16" $COMMON $MESH_16
extract_stats "$CSV_LARGE" "$RESULT/mesh_16x16/stats.txt" \
    MeshSumcheck,16,0,N/A,center

# --- SumcheckHierarchy 4x8x8, entries=1,2,4 ---
HIER_8="--topology=SumcheckHierarchy --mesh-rows=8 --num-clusters=4 \
  --num-dirs=512 --interleaving-bits=9 --routing-algorithm=3"

for entries in "${ENTRIES_VALS[@]}"; do
    name="hier_4x8x8_entries${entries}"
    run_one "$name" $COMMON $HIER_8 --entries-per-cluster="$entries"
    extract_stats "$CSV_LARGE" "$RESULT/$name/stats.txt" \
        SumcheckHierarchy,8,4,${entries},N/A
done

echo "=== $(date '+%H:%M:%S') All done ==="
wc -l "$CSV_SMALL" "$CSV_LARGE"