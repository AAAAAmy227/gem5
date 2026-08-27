#!/usr/bin/env bash
set -euo pipefail
root=${1:-m5out/sumcheck_phase04/sweep}
seeds=${SUMCHECK_SEEDS:-"1 2 3 4 5"}
loads=${SUMCHECK_LOADS:-"0.01 0.08"}
cycles=${SUMCHECK_TRAFFIC_CYCLES:-200}
for traffic in uniform-random cluster-skewed-bursty; do
  for load in $loads; do
    for seed in $seeds; do
      for pair in "Hierarchy_p4_fixed fixed" "Hierarchy_p4_adaptive adaptive"; do
        read -r variant routing <<<"$pair"
        out="$root/$traffic/load_$load/$routing/seed$seed"
        bash scripts/run_sumcheck_phase04_case.sh \
            "$out" "$variant" "$seed" "$traffic" "$load" "$cycles"
      done
    done
  done
done
