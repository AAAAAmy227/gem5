#!/bin/bash
set +e

GEM5="./build/NULL/gem5.opt"
SCRIPT="configs/example/sumcheck_causal_traffic.py"
RESULT="results_speedup"
mkdir -p "$RESULT"

# ============================================================
# Common parameters for Experiments 1.1 and 1.2
# ============================================================
COMMON="--simulate-rounds=5 --buffers-per-data-vc=4 \
  --buffers-per-ctrl-vc=1 --poly-degree=3 --multiply-latency=3 \
  --network=garnet --root-ni-lanes=4 --root-dir-lanes=4"

VCS_VALS=(1 2 4)
SUMCHECK_ROUNDS=(14 15 16 17 18)

SPEEDUP_HEADER="scale,topology,mesh_rows,num_clusters,src_placement,vcs_per_vnet,num_sumcheck_rounds,sim_ticks,queueing_latency,network_latency,latency,avg_hops"
METRIC_HEADER="scale,topology,mesh_rows,num_clusters,src_placement,vcs_per_vnet,num_sumcheck_rounds,queueing_latency,network_latency,latency,avg_hops"

CSV_SPEEDUP="$RESULT/speed_up.csv"
CSV_METRIC="$RESULT/metric.csv"
echo "$SPEEDUP_HEADER" > "$CSV_SPEEDUP"
echo "$METRIC_HEADER" > "$CSV_METRIC"

extract_stats() {
    local csv="$1"; local stats="$2"; shift; shift
    local ticks=$(grep '^simTicks ' "$stats" | awk '{print $2}')
    local ql=$(grep 'average_packet_queueing_latency' "$stats" | awk '{print $2}')
    local nl=$(grep 'average_packet_network_latency' "$stats" | awk '{print $2}')
    local la=$(grep 'average_packet_latency' "$stats" | awk '{print $2}')
    local hp=$(grep 'average_hops' "$stats" | awk '{print $2}')
    echo "$@,${ticks:-NA},${ql:-NA},${nl:-NA},${la:-NA},${hp:-NA}" >> "$csv"
}

extract_metric_stats() {
    local csv="$1"; local stats="$2"; shift; shift
    local ql=$(grep 'average_packet_queueing_latency' "$stats" | awk '{print $2}')
    local nl=$(grep 'average_packet_network_latency' "$stats" | awk '{print $2}')
    local la=$(grep 'average_packet_latency' "$stats" | awk '{print $2}')
    local hp=$(grep 'average_hops' "$stats" | awk '{print $2}')
    echo "$@,${ql:-NA},${nl:-NA},${la:-NA},${hp:-NA}" >> "$csv"
}

run_one() {
    local name="$1"; local outdir="$RESULT/$name"; shift
    mkdir -p "$outdir"
    echo "=== $(date '+%H:%M:%S') $name ==="
    $GEM5 $SCRIPT "$@" > "$outdir/log.txt" 2>&1
    cp m5out/stats.txt "$outdir/stats.txt" 2>/dev/null
}

run_scale() {
    local scale="$1"
    local mesh_rows="$2"
    local num_dirs="$3"
    local interleaving_bits="$4"

    local mesh="--topology=MeshSumcheck --mesh-rows=$mesh_rows \
      --num-dirs=$num_dirs --routing-algorithm=0"
    local hierarchy="--topology=SumcheckHierarchy --mesh-rows=$((mesh_rows / 2)) \
      --num-clusters=4 --num-dirs=$num_dirs --interleaving-bits=$interleaving_bits \
      --routing-algorithm=3 --entries-per-cluster=4 --sumcheck-routing=fixed"

    for vcs in "${VCS_VALS[@]}"; do
        for rounds in "${SUMCHECK_ROUNDS[@]}"; do
            # SumcheckHierarchy: 4x4x4 or 4x8x8, fixed routing.
            local hier_rows=$((mesh_rows / 2))
            local name="exp1_1_${scale}_hier_4x${hier_rows}x${hier_rows}_vcs${vcs}_r${rounds}"
            run_one "$name" $COMMON $hierarchy \
                --vcs-per-vnet="$vcs" --num-sumcheck-rounds="$rounds"
            extract_stats "$CSV_SPEEDUP" "$RESULT/$name/stats.txt" \
                "$scale,SumcheckHierarchy,$hier_rows,4,N/A,$vcs,$rounds"

            if [ "$vcs" -eq 4 ] && [ "$rounds" -eq 15 ]; then
                extract_metric_stats "$CSV_METRIC" "$RESULT/$name/stats.txt" \
                    "$scale,SumcheckHierarchy,$hier_rows,4,N/A,$vcs,$rounds"
            fi

            # Matching Mesh baseline with the source at center and corner.
            for place in center corner; do
                name="exp1_1_${scale}_mesh_${mesh_rows}x${mesh_rows}_${place}_vcs${vcs}_r${rounds}"
                run_one "$name" $COMMON $mesh --src-${place} \
                    --vcs-per-vnet="$vcs" --num-sumcheck-rounds="$rounds"
                extract_stats "$CSV_SPEEDUP" "$RESULT/$name/stats.txt" \
                    "$scale,MeshSumcheck,$mesh_rows,0,$place,$vcs,$rounds"

                if [ "$vcs" -eq 4 ] && [ "$rounds" -eq 15 ]; then
                    extract_metric_stats "$CSV_METRIC" "$RESULT/$name/stats.txt" \
                        "$scale,MeshSumcheck,$mesh_rows,0,$place,$vcs,$rounds"
                fi
            done
        done
    done
}

# Experiment 1.1: two topology scales, three VC settings, five workloads.
# Experiment 1.2 is collected from the vcs=4, rounds=15 cases above.
run_scale small 8 128 7
run_scale large 16 512 9

echo "=== $(date '+%H:%M:%S') All done ==="
wc -l "$CSV_SPEEDUP" "$CSV_METRIC"
