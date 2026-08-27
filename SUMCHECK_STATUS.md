# Sumcheck NoC — Phase 02 Handoff

## Current phase/status

- Phase 01 (`01_topology_fixed`): **PASS / complete**.
- Phase 02 (`02_adaptive_vc_cdg`): **PASS / complete** for the current
  `sumcheck` branch: adaptive-choice tests, real allocator partitioning,
  separated/collapsed CDG controls, build, fixed/adaptive smokes, and the
  executable Ring regression pass.
- Wormhole remains an inherited branch-integration limitation, not a measured
  current-branch regression pass: this branch still has no `--wormhole` CLI;
  the implementation remains at `61eb8c18beeb013d5d3c320cfa0014bed2809d19`.
- Worktree: `/root/gem5` (WSL Ubuntu). No commit, push, merge, rebase,
  cherry-pick, amend, branch switch, reset, or clean was performed in Phase 02.

## Repository state

- Branch: `sumcheck`.
- HEAD: `19f85604d90a8bbb1fc84a281d0ab3523e5ba52c`
  (`sumcheck: complete phase 01 topology and fixed routing`).
- Phase-02 implementation and tests are unstaged and uncommitted.
- The pre-existing `AGENTS.md` modification was preserved and not edited by
  Phase 02.

## Implemented behavior

### Adaptive entry choice

- CLI: `--sumcheck-routing=fixed|adaptive` (default `fixed`) and
  `--entry-congestion-weight=<float>` (default `4.0`, non-negative).
- Adaptive freedom remains only at a gateway entering the destination mesh.
- The selector is
  `distance + lambda * (1 - D_free / D_capacity)` and reads only VC_D offsets
  2 and 3 on each candidate output.
- Equal minima use a rotating pointer owned by each gateway `RoutingUnit`; no
  random routing was added.
- Generated `SumcheckConfig.hh` contains the pure C++ selector actually called
  by `RoutingUnit`; its standalone test covers non-nearest and rotating-tie
  synthetic credit states.
- Garnet computes a HEAD/HEAD_TAIL route once and stores the outport in the
  input VC. Waiting does not recompute or switch entries/classes.
- After gateway→entry, the unchanged mesh suffix is strict dim0-then-dim1.

### VC_U / VC_D enforcement

- Per vnet: offsets 0,1 are U; offsets 2,3 are D; offsets >=4 are unused by
  Sumcheck. Both Python and C++ reject `vcs_per_vnet < 4` for algorithm 3.
- `NetworkInterface::calculateVC()` selects the first router input VC from the
  required subset.
- `SwitchAllocator::send_allowed()` validates the input class and checks only
  the required output subset.
- `SwitchAllocator::vc_allocate()` passes that same class to
  `OutputUnit::select_free_vc()`; there is no fallback across partitions.
- D→U is fatal. U→D is fatal outside router 68; the root transition is allowed.
- Runtime counters show U=3/D=2 allocations on a cross-cluster route and D=4
  on root→worker.

## Instrumentation

Locations:

- `RoutingUnit.cc`: candidate D state, choice, mismatch, and tie pointer.
- `OutputUnit.cc/.hh`: subset-bounded scans and credit/capacity helpers.
- `SwitchAllocator.cc`: transition assertions and actual allocation class.
- `NetworkInterface.cc/.hh`: matching first-hop subset.
- `GarnetNetwork.cc/.hh`: stats registration/collection.

Published stats:

- `sumcheck_gateway_entry_choices`, `sumcheck_gateway_entry_selections`;
- `sumcheck_fixed_choice_mismatches`, `sumcheck_adaptive_reroute_rate`;
- `sumcheck_tie_arbitrations`;
- `sumcheck_candidate_evaluations`, `sumcheck_candidate_credit_sum`;
- `sumcheck_candidate_occupancy_sum`, `sumcheck_candidate_capacity_sum`;
- `sumcheck_vc_allocations`;
- `sumcheck_tracked_link_flits` for every directed gateway-entry and
  root-gateway link. Divide by elapsed cycles for utilization.

## CDG verification

Checker: `tests/pyunit/sumcheck_cdg.py`.

The specified totals enumerate every legal static source-entry assignment and
every legal adaptive destination-entry choice. Runtime source routing remains
fixed nearest; source-side adaptivity was not added. This conservative relation
produces the required p-squared cross-cluster set.

| p | Ordered pairs | Legal routes | U/D-separated | Collapsed VC |
|---:|---:|---:|---|---|
| 1 | 4692 | 4692 | acyclic | no cycle required/found |
| 2 | 4692 | 14548 | acyclic | cycle found |
| 4 | 4692 | 52692 | acyclic | cycle found |

Collapsed witnesses (first channel repeats at the end):

- p=2: `64->68 -> 68->65 -> 65->17 -> 17->21 -> 21->25 -> 25->29 -> 29->30 -> 30->65 -> 65->68 -> 68->64 -> 64->1 -> 1->5 -> 5->9 -> 9->13 -> 13->14 -> 14->64 -> 64->68`.
- p=4: `64->68 -> 68->65 -> 65->17 -> 17->21 -> 21->22 -> 22->23 -> 23->65 -> 65->68 -> 68->64 -> 64->1 -> 1->5 -> 5->6 -> 6->7 -> 7->64 -> 64->68`.

Structured evidence: `m5out/sumcheck_phase02/cdg_report.json`.

## Acceptance evidence

### Static/unit tests

```bash
python3 -m py_compile configs/network/Network.py \
  configs/topologies/SumcheckConfig.py \
  configs/topologies/SumcheckHierarchy.py \
  tests/pyunit/sumcheck_cdg.py \
  tests/pyunit/pyunit_sumcheck_phase02.py
python3 tests/pyunit/pyunit_sumcheck_topology.py
python3 tests/pyunit/pyunit_sumcheck_phase02.py
```

Results: syntax **PASS**; topology **8/8 PASS**; Phase-02 adaptive/VC/CDG
**12/12 PASS**. Logs:
`m5out/sumcheck_phase02/{topology_pyunit.log,phase02_pyunit.log}`.

```bash
g++ -std=c++17 -Isrc tests/pyunit/sumcheck_adaptive_cpp_test.cc \
  -o m5out/sumcheck_phase02/sumcheck_adaptive_cpp_test
m5out/sumcheck_phase02/sumcheck_adaptive_cpp_test
```

Result: **PASS**. Synthetic D-credit congestion chooses non-nearest entry 1;
equal scores rotate 0,1; exact VC offsets/root phases also pass.

```bash
python3 tests/pyunit/sumcheck_cdg.py \
  --output m5out/sumcheck_phase02/cdg_report.json
```

Result: **PASS** with the counts/witnesses above.

### Build and startup negative control

```bash
scons build/NULL/gem5.debug -j16 \
  > m5out/sumcheck_phase02/build.log 2>&1
```

Result: **PASS**, exit 0; known optional PNG/HDF5 warnings only.

```bash
./build/NULL/gem5.debug \
  --outdir=m5out/sumcheck_phase02/vcs3_negative \
  configs/example/garnet_synth_traffic.py \
  --network=garnet --num-cpus=64 --num-dirs=8 \
  --topology=SumcheckHierarchy --mesh-rows=0 --routing-algorithm=3 \
  --vcs-per-vnet=3 --inj-vnet=0 --sim-cycles=10
```

Result: **PASS negative control**, exit 1 with
`Sumcheck routing requires --vcs-per-vnet >= 4`. Evidence:
`m5out/sumcheck_phase02/vcs3_negative/run.log`.

### Fixed/adaptive gem5 smokes

```bash
bash scripts/run_sumcheck_smoke.sh m5out/sumcheck_phase02/fixed_smoke fixed
bash scripts/run_sumcheck_smoke.sh m5out/sumcheck_phase02/adaptive_smoke adaptive
```

Result: **PASS**. Each mode ran worker→remote-gateway and root→worker; all four
cases reported 1 injected / 1 received. Evidence:
`m5out/sumcheck_phase02/{fixed_smoke,adaptive_smoke}/`.

### Ring regression

```bash
./build/NULL/gem5.debug \
  --outdir=m5out/sumcheck_phase02/ring_single_packet \
  configs/example/garnet_synth_traffic.py \
  --network=garnet --num-cpus=16 --num-dirs=16 --topology=Ring \
  --mesh-rows=1 --routing-algorithm=2 --inj-vnet=0 \
  --synthetic=uniform_random --sim-cycles=500 --injectionrate=1.0 \
  --num-packets-max=1 --single-sender-id=0 --single-dest-id=8
```

Result: **PASS**, 1/1 packets, average hops 8. Evidence:
`m5out/sumcheck_phase02/ring_single_packet/`.

### Wormhole overlap/probe

Commit `61eb8c1` was diffed before allocator/NI edits. Phase-02 subset logic is
gated on routing algorithm 3, so algorithm 1/2 behavior is unchanged. The
current branch still cannot execute Wormhole:

```bash
./build/NULL/gem5.debug \
  --outdir=m5out/sumcheck_phase02/wormhole_probe \
  configs/example/garnet_synth_traffic.py \
  --network=garnet --num-cpus=16 --num-dirs=16 --topology=Mesh_XY \
  --mesh-rows=4 --routing-algorithm=1 --inj-vnet=0 \
  --synthetic=uniform_random --sim-cycles=500 --injectionrate=1.0 \
  --num-packets-max=1 --single-sender-id=0 --single-dest-id=15 \
  --vcs-per-vnet=16 --wormhole
```

Result: inherited blocker reproduced, parser exit 2,
`unrecognized arguments: --wormhole`. Evidence:
`m5out/sumcheck_phase02/wormhole_probe/run.log`. No Wormhole pass is claimed.

### Hygiene

```bash
git diff --check
git status --branch --short --untracked-files=all
```

`git diff --check`: **PASS / empty**. Nothing is staged or committed.

## Remaining risks/limits

1. The reference bundle remains unavailable, so its `DEADLOCK_PROOF.md` and
   reference implementation/output provenance cannot be checked.
2. CDG verifies the enumerated physical-channel U/D relation, not unrelated
   Ruby protocol/message-class dependencies.
3. The required CDG totals conservatively enumerate source assignments;
   runtime source routing remains fixed nearest while destination choices are
   exactly the adaptive C++ relation.
4. Equal-score rotation is fair among current minima, but there is no global
   starvation proof under continuously changing scores.
5. Credit scoring observes completed prior-cycle state, consistent with this
   Garnet wakeup order; same-cycle returning credits are not yet visible.
6. Wormhole remains branch-separated and needs separately authorized,
   conflict-aware integration/testing before it can run on `sumcheck`.
7. The 64-L1 + 8-Directory fixed-cycle harness remains smoke-only; Phase 03
   still needs causal destination consumption and controller reinjection.

## Exact next action

Proceed only to `tasks/03_causal_workload.md`: implement causal destination
consumption/ejection, controller wait/aggregation, and reinjection without
holding a network channel. Do not begin Phase 04 experiments.
