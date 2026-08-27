#!/usr/bin/env bash
set -euo pipefail

# Prepared Phase-04 full matrix.  This script is resumable because each case
# validates and skips an existing workload_report.json.  The Phase-04 handoff
# explicitly records whether this larger matrix was actually executed.
root=${1:-m5out/sumcheck_phase04/full_matrix}
variants=(
    Mesh_8x8_XY Hierarchy_p1_fixed Hierarchy_p2_fixed
    Hierarchy_p4_fixed Hierarchy_p4_adaptive
    Hierarchy_p4_adaptive_buffer_matched Hierarchy_p4_corners
    Hierarchy_p4_no_aggregation
)
for seed in 1 2 3 4 5; do
    for variant in "${variants[@]}"; do
        bash scripts/run_sumcheck_phase04_case.sh \
            "$root/causal/$variant/seed$seed" "$variant" "$seed" causal
    done
done

SUMCHECK_SEEDS="1 2 3 4 5" \
SUMCHECK_LOADS="0.005 0.01 0.02 0.04 0.06 0.08 0.10 0.12 0.16" \
SUMCHECK_TRAFFIC_CYCLES=2000 \
    bash scripts/run_sumcheck_sweep.sh "$root/offered_load"
