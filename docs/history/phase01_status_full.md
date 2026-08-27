# Sumcheck NoC — Persistent Project Status

> Cross-session external memory. Read this file before acting.

## Current state

- **Current phase:** `01_topology_fixed`
- **Phase status:** **PASS**
- **Current branch:** `sumcheck`
- **Current HEAD:** `c644910f321ec672151058db663e026de68afd9d`
  (`sumcheck: record phase 00 checkpoint`).
- **Last known-good committed network baseline:**
  `86686aa3b4e015fc961c9f41e27af4e2dfef8096`.
- **Latest committed Sumcheck documentation checkpoint:**
  `c644910f321ec672151058db663e026de68afd9d` (local only).
- **Phase-1 checkpoint:** **UNCOMMITTED; NOT PUSHED**. The user explicitly
  prohibited commit/push without later authorization.
- **Upstream:** `origin/sumcheck` at `86686aa`; current HEAD is two local
  documentation commits ahead and Phase-1 changes remain in the worktree.
- **Worktree:** `/root/gem5` in WSL Ubuntu.
- **Build:** gem5 `23.0.0.1`, Garnet `3.0`,
  `build/NULL/gem5.debug`, `PROTOCOL='Garnet_standalone'`.
- **Reference bundle:** still unavailable. Phase-1 static checks use the
  canonical specification and local implementation model, not bundle output.

Phase 1 implements only the hierarchical topology and fixed deterministic
routing. Credit-aware selection, VC_U/VC_D enforcement, CDG verification,
causal workload, aggregation, baselines, and experiments were not started.

## Phase tracker

| Phase | Scope | Status | Checkpoint | Evidence |
|---|---|---|---|---|
| 00 | Repository/API/reference reconnaissance | **PASS** | `9804d7f`, then status-only `c644910` (local only) | API/reference maps and `m5out/sumcheck_recon/` |
| 01 | Topology + deterministic routing | **PASS** | Uncommitted | 8 static tests, build, five Sumcheck single-packet runs, Ring regression |
| 02 | Adaptive routing + VC discipline + CDG | READY, NOT STARTED | — | Credit/allocator API map exists; Wormhole overlap must be reviewed first |
| 03 | Causal workload + aggregation | BLOCKED ON 02 | — | — |
| 04 | Baselines + experiments | BLOCKED ON 03 | — | — |
| 05 | Final regression + evidence audit | BLOCKED ON 04 | — | — |

## Phase-1 acceptance table

| Gate | Completed | Missing / limitation | Evidence |
|---|---|---|---|
| Centralized 69-router mapping | Yes | Python and C++ cannot import one another directly | `SumcheckConfig.py`; generated `SumcheckConfig.hh`; byte-for-byte generation test |
| p=1/2/4 router/link counts | Yes | 72 ExtLinks are a documented smoke-harness deviation | Static 69/104, 69/108, 69/116; gem5 config.ini shows 69 routers and 208/216/232 directed IntLinks |
| Exact entry placements | Yes | Reference archive unavailable | p1, p2, p4 staggered, and p4 corners tested exactly |
| Stable, unique port names | Yes | — | Unit test covers every router endpoint port in all four configurations |
| Generated routes use physical links | Yes | Static model, not a C++ exhaustive unit harness | All 18,768 ordered routes (4 configurations × 4,692 pairs) validated against topology adjacency |
| Deterministic nearest entry and smaller-index tie-break | Yes | — | Exhaustive gateway→worker tests; multiple ties required and observed |
| Strict dim0→dim1 mesh suffix | Yes | — | Every worker-only segment of all 18,768 routes checked; root→worker gem5 smoke exercises downward suffix |
| Complete fixed C++ relation | Yes | C++ is smoke-tested, while exhaustive enumeration is in the shared Python logical model | Algorithm 3 in `RoutingUnit::outportComputeSumcheck`; illegal/missing roles and ports fatal |
| CLI and long-link sensitivity | Yes | Sensitivity runs are correctness smokes, not performance experiments | p1 with gateway-entry=2/root-gateway=4 and p2 with 4/2 both run; config.ini contains latencies 1/2/4 |
| Relevant binary builds | Yes | Optional PNG/HDF5 dependencies absent, unrelated | `scons build/NULL/gem5.debug -j16`, exit 0 |
| Deterministic smoke | Yes | Garnet standalone is asymmetric and needs a temporary endpoint mapping | Two cases, each 1 packet injected = 1 received; average hops 4 and 3 |
| p1/p2/p4-corners gem5 variants | Yes | Single packet only | Each exits 0 with 1 injected = 1 received and correct config counts |
| Ring preserved | Yes | — | Algorithm 2 regression exits 0, 1=1, average hops 8 |
| Wormhole regression | Pre-existing blocker reproduced | Implementation remains only on separate `wormhole` branch/commit `61eb8c1` | Current branch still rejects `--wormhole`, parser exit 2; no Phase-1 allocator/NI files were changed |
| Status/API map updated | Yes | — | This file and `docs/sumcheck_api_map.md` |

## Implemented architecture and routing

- Router IDs are fixed: workers 0..63, gateways 64..67, root 68.
- Each cluster has a 4x4 worker mesh with row/dim0 before col/dim1.
- Supported entry tables:
  - p1 staggered: `(1,1)`;
  - p2 staggered: `(0,1),(3,2)`;
  - p4 staggered: `(0,1),(1,3),(2,0),(3,2)`;
  - p4 corners: `(0,0),(0,3),(3,0),(3,3)`.
- Every undirected edge is emitted as two Garnet IntLinks with stable names:
  `Dim0Pos/Neg`, `Dim1Pos/Neg`, `Gateway`, `Entry0..3`, `RootUp`, and
  `RootToG0..3`.
- `--gateway-entry-link-latency` and `--root-gateway-link-latency` accept
  1, 2, or 4 cycles and are applied only to their respective link classes.
- Routing algorithm 3 is Sumcheck fixed routing; algorithm 2 remains the Lab3
  Ring implementation.
- Same-cluster worker traffic is strict dim0→dim1. Non-local worker traffic
  uses the source worker's nearest legal entry with smaller-index tie-break,
  then gateway→root as needed. Root selects the destination gateway. A
  destination gateway selects the destination worker's nearest legal entry,
  after which routing is strict dim0→dim1.
- Unsupported IDs, roles, configurations, or absent port directions terminate
  with fatal errors rather than using a routing-table fallback.

## Phase-1 endpoint/ExtLink adaptation

The desired 65-L1 + 4-Directory Garnet-standalone harness failed before
simulation because this build's MachineID set supports only 64 same-type L1
controllers. Directory count must remain a power of two. The working harness
therefore uses 64 L1s plus 8 Directories:

| Controller | Router role |
|---|---|
| L1 0..62 | workers 0..62 |
| L1 63 | root 68 |
| Directory 0 | worker 63 |
| Directory 1..4 | gateways 64..67 |
| Directory 5..7 | explicitly co-located on root 68 |

This provides one endpoint for every logical role and lets the asymmetric
tester inject both an upward worker route and a downward root route. The three
extra Directory endpoints are not ignored: the realized configuration has 72
ExtLinks/NIs, four local ports at root, and the corresponding buffers and
arbitration cost. Phase 3 still needs the final symmetric causal controller
path; these endpoint types are only a Phase-1 smoke harness.

## Files changed in Phase 1

New implementation/test files:

- `configs/topologies/SumcheckConfig.py`
- `configs/topologies/SumcheckHierarchy.py`
- `src/mem/ruby/network/garnet/SumcheckConfig.hh`
- `tests/pyunit/pyunit_sumcheck_topology.py`
- `scripts/run_sumcheck_smoke.sh`

Modified implementation/documentation files:

- `configs/network/Network.py`
- `src/mem/ruby/network/garnet/CommonTypes.hh`
- `src/mem/ruby/network/garnet/GarnetNetwork.py`
- `src/mem/ruby/network/garnet/GarnetNetwork.hh`
- `src/mem/ruby/network/garnet/GarnetNetwork.cc`
- `src/mem/ruby/network/garnet/RoutingUnit.hh`
- `src/mem/ruby/network/garnet/RoutingUnit.cc`
- `docs/sumcheck_api_map.md`
- `SUMCHECK_STATUS.md`

No Phase-1 edits were made to `InputUnit`, `OutputUnit`, `SwitchAllocator`,
`NetworkInterface`, workload/controller code, or the existing `Ring.py`.

## Exact validation commands and results

### Syntax and static unit tests

```bash
cd /root/gem5
python3 -m py_compile \
  configs/topologies/SumcheckConfig.py \
  configs/topologies/SumcheckHierarchy.py \
  configs/network/Network.py \
  tests/pyunit/pyunit_sumcheck_topology.py
python3 tests/pyunit/pyunit_sumcheck_topology.py
```

Result: **PASS**, 8 tests. The suite covers 69 ID classifications and
round-trips, the 72-controller harness map, all entry tables, generated-header
consistency, topology/link/latency-class counts, stable port uniqueness, all
18,768 physical routes, nearest-entry tie-break, and dim0→dim1 ordering.

### Build

```bash
scons build/NULL/gem5.debug -j16
```

Result: **PASS**, exit 0. Only pre-existing optional PNG/HDF5 warnings.

### Main deterministic smoke

```bash
bash scripts/run_sumcheck_smoke.sh
```

The script executes two exact single-packet commands under the common p4
staggered topology:

- worker 0 → Directory 4 / G3:
  `m5out/sumcheck_phase01/deterministic_smoke/worker_to_remote_gateway/`;
- L1 63 / root → Directory 0 / worker 63:
  `m5out/sumcheck_phase01/deterministic_smoke/root_to_worker/`.

Both use `--num-cpus=64 --num-dirs=8 --topology=SumcheckHierarchy
--mesh-rows=0 --routing-algorithm=3 --entries-per-cluster=4
--entry-placement=staggered --gateway-entry-link-latency=1
--root-gateway-link-latency=1 --sim-cycles=1000 --injectionrate=1.0
--num-packets-max=1`. Results:

| Case | Routers | Directed/undirected IntLinks | ExtLinks | Packets injected/received | Average hops |
|---|---:|---:|---:|---:|---:|
| worker→remote gateway | 69 | 232/116 | 72 | 1/1 | 4 |
| root→worker | 69 | 232/116 | 72 | 1/1 | 3 |

### Entry/placement/latency gem5 variants

Each command uses the same common options as the root→worker case above and
changes only the listed parameters:

```bash
./build/NULL/gem5.debug --outdir=m5out/sumcheck_phase01/p1_sensitivity \
  configs/example/garnet_synth_traffic.py [common options] \
  --entries-per-cluster=1 --entry-placement=staggered \
  --gateway-entry-link-latency=2 --root-gateway-link-latency=4

./build/NULL/gem5.debug --outdir=m5out/sumcheck_phase01/p2_sensitivity \
  configs/example/garnet_synth_traffic.py [common options] \
  --entries-per-cluster=2 --entry-placement=staggered \
  --gateway-entry-link-latency=4 --root-gateway-link-latency=2

./build/NULL/gem5.debug --outdir=m5out/sumcheck_phase01/p4_corners \
  configs/example/garnet_synth_traffic.py [common options] \
  --entries-per-cluster=4 --entry-placement=corners \
  --gateway-entry-link-latency=1 --root-gateway-link-latency=1
```

`[common options]` were exactly:
`--network=garnet --num-cpus=64 --num-dirs=8
--topology=SumcheckHierarchy --mesh-rows=0 --routing-algorithm=3
--inj-vnet=0 --synthetic=uniform_random --sim-cycles=1000
--injectionrate=1.0 --num-packets-max=1 --single-sender-id=63
--single-dest-id=0`.

| Variant | Routers | Directed/undirected IntLinks | ExtLinks | Packets injected/received | Result |
|---|---:|---:|---:|---:|---|
| p1 staggered, latency 2/4 | 69 | 208/104 | 72 | 1/1 | PASS |
| p2 staggered, latency 4/2 | 69 | 216/108 | 72 | 1/1 | PASS |
| p4 corners, latency 1/1 | 69 | 232/116 | 72 | 1/1 | PASS |

### Ring regression

```bash
./build/NULL/gem5.debug \
  --outdir=m5out/sumcheck_phase01/ring_single_packet \
  configs/example/garnet_synth_traffic.py \
  --network=garnet --num-cpus=16 --num-dirs=16 --topology=Ring \
  --mesh-rows=1 --routing-algorithm=2 --inj-vnet=0 \
  --synthetic=uniform_random --sim-cycles=500 --injectionrate=1.0 \
  --num-packets-max=1 --single-sender-id=0 --single-dest-id=8
```

Result: **PASS**, exit 0, packets 1/1, average hops 8.

### Wormhole current-branch probe

```bash
./build/NULL/gem5.debug \
  --outdir=m5out/sumcheck_phase01/wormhole_probe \
  configs/example/garnet_synth_traffic.py \
  --network=garnet --num-cpus=16 --num-dirs=16 --topology=Mesh_XY \
  --mesh-rows=4 --routing-algorithm=1 --inj-vnet=0 \
  --synthetic=uniform_random --sim-cycles=500 --injectionrate=1.0 \
  --num-packets-max=1 --single-sender-id=0 --single-dest-id=15 \
  --vcs-per-vnet=16 --wormhole
```

Result: **PRE-EXISTING BLOCKER REPRODUCED**, parser exit 2,
`unrecognized arguments: --wormhole`. The implementation remains on branch
`wormhole`, commit `61eb8c18beeb013d5d3c320cfa0014bed2809d19`.

### Failed diagnostic that established the endpoint constraint

The initial main smoke used `--num-cpus=65 --num-dirs=4` and failed before
network simulation with:

```text
fatal: Number of bits(64) < size specified(65). Increase the number of bits and recompile.
```

It is not acceptance evidence. The documented 64+8 harness resolved the
framework limit without changing protocol bit widths.

## Static checks vs measured gem5 results

Static implementation checks:

- router/internal-link counts and entry tables;
- exhaustive physical path validity;
- deterministic nearest-entry/tie-break behavior;
- strict dim0→dim1 ordering;
- Python/generated-C++ mapping consistency.

Measured gem5 smoke results:

- the five Sumcheck cases listed above, each 1 packet injected = 1 received;
- main p4 average hops 4 (worker→remote gateway) and 3 (root→worker);
- Ring regression 1/1 with average hops 8.

No causal Sumcheck workload, application completion cycles, adaptive behavior,
latency distribution, throughput, utilization sweep, or performance comparison
was measured. Reference trace/CDG/flit-hop numbers remain static specification
oracles and were not presented as gem5 results.

## Git / worktree state

At Phase-1 entry, tracked files were clean. Existing untracked project-control
files were `AGENTS.md`, `CODEX_START_HERE.md`, `docs/sumcheck_spec.md`, and
`tasks/00_recon.md` through `tasks/05_final_review.md`; they were preserved.

Phase-1 files are unstaged and uncommitted. No commit, push, branch switch,
merge, cherry-pick, reset, restore, or clean was performed. Generated build
and `m5out/sumcheck_phase01/` evidence is ignored and unstaged.

Final `git status --branch --short --untracked-files=all`:

```text
## sumcheck...origin/sumcheck [ahead 2]
 M SUMCHECK_STATUS.md
 M configs/network/Network.py
 M docs/sumcheck_api_map.md
 M src/mem/ruby/network/garnet/CommonTypes.hh
 M src/mem/ruby/network/garnet/GarnetNetwork.cc
 M src/mem/ruby/network/garnet/GarnetNetwork.hh
 M src/mem/ruby/network/garnet/GarnetNetwork.py
 M src/mem/ruby/network/garnet/RoutingUnit.cc
 M src/mem/ruby/network/garnet/RoutingUnit.hh
?? AGENTS.md
?? CODEX_START_HERE.md
?? configs/topologies/SumcheckConfig.py
?? configs/topologies/SumcheckHierarchy.py
?? docs/sumcheck_spec.md
?? scripts/run_sumcheck_smoke.sh
?? src/mem/ruby/network/garnet/SumcheckConfig.hh
?? tasks/00_recon.md
?? tasks/01_topology_fixed.md
?? tasks/02_adaptive_vc_cdg.md
?? tasks/03_causal_workload.md
?? tasks/04_baselines_experiments.md
?? tasks/05_final_review.md
?? tests/pyunit/pyunit_sumcheck_topology.py
```

`git diff --check` is empty. The tracked diff contains the nine modified files
shown above; the five new Phase-1 files are untracked and therefore are not
included in `git diff --stat`. Nothing is staged.

## Unresolved risks / blockers

1. **Deadlock freedom is not yet established.** Phase 1 intentionally has no
   VC_U/VC_D allocator enforcement or CDG proof. Fixed routing passing small
   smokes is not a deadlock proof.
2. **Python/C++ exhaustive relation parity needs continued discipline.** The
   mapping header is generated and checked exactly; the exhaustive route model
   and C++ decision code are still separate implementations. Phase 2 must keep
   the legal routing relation/checker synchronized with C++.
3. **Endpoint harness is temporary.** Three extra Directory endpoints are
   co-located at root and materially affect local ports/NIs/buffers. Phase 3
   needs final causal symmetric controllers and must recompute actual costs.
4. **Wormhole is still branch-separated.** Phase 2 overlaps its allocator/NI
   files. Review or explicitly integrate its semantics before editing those
   files; do not overwrite it accidentally.
5. **Reference archive is absent.** Bundle-provenance path/CDG/trace oracles
   remain unavailable.
6. **Synthetic termination is fixed-cycle.** Acceptance uses bounded one-packet
   injection and verifies equality; the final causal workload needs
   workload-driven drain/termination.

## Exact next action

First review the uncommitted Phase-1 diff, especially:

- `configs/topologies/SumcheckConfig.py` and `SumcheckHierarchy.py`;
- `RoutingUnit::outportComputeSumcheck()`;
- the generated `SumcheckConfig.hh` consistency path;
- the documented 64+8 endpoint mapping.

If a Phase-1 checkpoint commit/push is desired, obtain explicit user
authorization first. Otherwise start a new run with
`tasks/02_adaptive_vc_cdg.md`: begin by reviewing the separate Wormhole commit
against the current `OutputUnit`/`SwitchAllocator`/`NetworkInterface` surface,
then add real credit-aware fixed-vs-adaptive entry choice and enforce VC_U/VC_D
allocation before claiming any deadlock result.
