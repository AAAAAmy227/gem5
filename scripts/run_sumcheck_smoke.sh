#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
outdir=${1:-"${repo_root}/m5out/sumcheck_phase01/deterministic_smoke"}

cd "${repo_root}"

run_case() {
    local name=$1
    local sender=$2
    local destination=$3
    local case_outdir="${outdir}/${name}"

    ./build/NULL/gem5.debug --outdir="${case_outdir}" \
        configs/example/garnet_synth_traffic.py \
        --network=garnet \
        --num-cpus=64 \
        --num-dirs=8 \
        --topology=SumcheckHierarchy \
        --mesh-rows=0 \
        --routing-algorithm=3 \
        --entries-per-cluster=4 \
        --entry-placement=staggered \
        --gateway-entry-link-latency=1 \
        --root-gateway-link-latency=1 \
        --inj-vnet=0 \
        --synthetic=uniform_random \
        --sim-cycles=1000 \
        --injectionrate=1.0 \
        --num-packets-max=1 \
        --single-sender-id="${sender}" \
        --single-dest-id="${destination}"

    local stats="${case_outdir}/stats.txt"
    local injected
    local received
    injected=$(awk '$1 == "system.ruby.network.packets_injected::total" {print $2}' "${stats}")
    received=$(awk '$1 == "system.ruby.network.packets_received::total" {print $2}' "${stats}")

    if [[ -z "${injected}" || -z "${received}" || "${injected}" != "${received}" ]]; then
        echo "Sumcheck smoke ${name} mismatch: injected=${injected:-missing} received=${received:-missing}" >&2
        exit 1
    fi
    echo "Sumcheck smoke ${name} PASS: injected=${injected} received=${received}"
}

# Worker 0 to Directory 4/G3 exercises source mesh, both hierarchy levels,
# and a cross-cluster destination gateway.
run_case worker_to_remote_gateway 0 4

# L1 63/root to Directory 0/worker 63 exercises root-to-gateway, deterministic
# nearest-entry selection, and the strict dim0-then-dim1 destination suffix.
run_case root_to_worker 63 0
