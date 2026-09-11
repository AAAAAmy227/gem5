#!/bin/bash
set +e

GEM5="./build/NULL/gem5.opt"
SCRIPT="configs/example/sumcheck_causal_traffic.py"
RESULT="results_multini"
mkdir -p "$RESULT"

# ============================================================
# Common parameters
# ============================================================
COMMON="--simulate-rounds=5 --num-sumcheck-rounds=15 --vcs-per-vnet=4 \
  --buffers-per-data-vc=4 --buffers-per-ctrl-vc=1 --poly-degree=3 \
  --multiply-latency=3 --network=garnet"

HEADER="topology,mesh_rows,num_clusters,ni_lanes,dir_lanes,sim_ticks,queueing_latency,network_latency,latency,avg_hops"

extract_stats() {
    local csv="$1"; local stats="$2"; local log="$3"; shift; shift; shift
    local tick=$(grep -oP 'Exiting @ tick \K\d+' "$log")
    local ql=$(grep "average_packet_queueing_latency" "$stats" | awk '{print $2}')
    local nl=$(grep "average_packet_network_latency" "$stats" | awk '{print $2}')
    local la=$(grep "average_packet_latency" "$stats" | awk '{print $2}')
    local hp=$(grep "average_hops" "$stats" | awk '{print $2}')
    echo "$@,${tick:-NA},${ql:-NA},${nl:-NA},${la:-NA},${hp:-NA}" >> "$csv"
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

MESH_8="--topology=MeshSumcheck --mesh-rows=8 --num-dirs=128 \
  --routing-algorithm=0 --src-center"

for lanes in "1 1" "4 1" "4 4"; do
    read ni dir <<< "$lanes"
    name="mesh_8x8_NI${ni}_DIR${dir}"
    run_one "$name" $COMMON $MESH_8 --root-ni-lanes="$ni" --root-dir-lanes="$dir"
    extract_stats "$CSV_SMALL" "$RESULT/$name/stats.txt" "$RESULT/$name/log.txt" \
        MeshSumcheck,8,0,${ni},${dir}
done

HIER_4="--topology=SumcheckHierarchy --mesh-rows=4 --num-clusters=4 \
  --num-dirs=128 --interleaving-bits=7 --routing-algorithm=3 \
  --sumcheck-routing=fixed --entries-per-cluster=4"

for lanes in "1 1" "4 1" "4 4"; do
    read ni dir <<< "$lanes"
    name="hier_4x4x4_NI${ni}_DIR${dir}"
    run_one "$name" $COMMON $HIER_4 --root-ni-lanes="$ni" --root-dir-lanes="$dir"
    extract_stats "$CSV_SMALL" "$RESULT/$name/stats.txt" "$RESULT/$name/log.txt" \
        SumcheckHierarchy,4,4,${ni},${dir}
done

# ============================================================
# Large scale: Mesh 16x16 + SumcheckHierarchy 4x8x8
# ============================================================
CSV_LARGE="$RESULT/large_scale.csv"
echo "$HEADER" > "$CSV_LARGE"

MESH_16="--topology=MeshSumcheck --mesh-rows=16 --num-dirs=512 \
  --routing-algorithm=0 --src-center"

for lanes in "1 1" "4 1" "4 4"; do
    read ni dir <<< "$lanes"
    name="mesh_16x16_NI${ni}_DIR${dir}"
    run_one "$name" $COMMON $MESH_16 --root-ni-lanes="$ni" --root-dir-lanes="$dir"
    extract_stats "$CSV_LARGE" "$RESULT/$name/stats.txt" "$RESULT/$name/log.txt" \
        MeshSumcheck,16,0,${ni},${dir}
done

HIER_8="--topology=SumcheckHierarchy --mesh-rows=8 --num-clusters=4 \
  --num-dirs=512 --interleaving-bits=9 --routing-algorithm=3 \
  --sumcheck-routing=fixed --entries-per-cluster=4"

for lanes in "1 1" "4 1" "4 4"; do
    read ni dir <<< "$lanes"
    name="hier_4x8x8_NI${ni}_DIR${dir}"
    run_one "$name" $COMMON $HIER_8 --root-ni-lanes="$ni" --root-dir-lanes="$dir"
    extract_stats "$CSV_LARGE" "$RESULT/$name/stats.txt" "$RESULT/$name/log.txt" \
        SumcheckHierarchy,8,4,${ni},${dir}
done

# ============================================================
echo "=== $(date '+%H:%M:%S') All done ==="
wc -l "$CSV_SMALL" "$CSV_LARGE"