# Sumcheck NoC — Phase 05 Final Audit

## Final phase/status

- Phase 01 topology/fixed routing: **PASS**.
- Phase 02 adaptive routing/U-D VC/CDG: **PASS**.
- Phase 03 causal workload/endpoint aggregation: **PASS**.
- Phase 04 baselines/experiments: **PASS with bounded measured data and
  explicit full-matrix gaps**.
- Phase 05 final regression/specification/evidence audit: **PASS**.
- Final architecture version: **Phase-05 audited hierarchy v1**, gem5
  23.0.0.1 / Garnet 3.0, routing algorithm 3. This Phase-05 checkpoint contains
  the audit/test/documentation changes listed below and has parent/base
  `c6e06c33e3ce9eead75c9777bf596395da12f098`.
- Reference bundle remains unavailable. Values derived from
  `docs/sumcheck_spec.md` are labeled static, never measured gem5 results.
- The user authorized the Phase-05 checkpoint commit on 2026-08-28; no push
  was authorized or performed.

## Complete evidence table

| Step | Completed | Missing | Evidence |
|---|---|---|---|
| Repository/spec/API/reference review | Yes | Reference archive unavailable | Full spec/API/reference maps and all prior Sumcheck implementation/tests/scripts/docs inspected |
| 69-router hierarchy and placements | Yes | — | topology 8/8; p1/p2/p4/corners mappings and 104/108/116 links |
| Fixed deterministic relation | Yes | Exhaustive execution is mirrored Python plus focused gem5 smokes, not compiled-route extraction | all 4692 ordered pairs/config use physical links; fresh fixed synthetic and causal smokes |
| Live adaptive entry choice | Yes | — | C++/Python credit/tie tests; fresh smoke 328/896 non-nearest, 108 ties, reroute 0.366071 |
| Legal VC_D-only credit score | Yes | — | `RoutingUnit` reads `free_credits/credit_capacity(...Down)` offsets 2/3; candidate stats nonzero |
| Packet-stable outport | Yes | — | `InputUnit` computes once/head and persists outport; allocator never recomputes |
| Real U/D allocator enforcement | Yes | No deliberate wrong-VC corruption simulation | NI, `send_allowed`, and `vc_allocate` share subsets; live U/D allocations; fatal transition guards |
| Root-only U-to-D and no D-to-U | Yes | — | exact/superset route audit plus allocator guards |
| CDG matches C++ runtime relation | Yes | Offline model still requires human parity review | exact fixed 4692; exact adaptive 4692/8084/14868; all separated acyclic |
| Specification CDG acceptance counts | Yes | These are a conservative superset, not runtime counts | 4692/14548/52692, all separated acyclic; p2/p4 collapsed witnesses |
| Endpoint ejection/controller/reinjection | Yes | Controller compute is abstracted as one endpoint clock | VC-free credit precedes arrival callback; successor injects next clock |
| Causal trace and event counts | Yes | Reference JSONL unavailable | Phase03 10/10; aggregated 2004, no-aggregation 1856 |
| Exact 32/128-byte packets and accounting | Yes | — | fresh seven cases 2004/10224; no-aggregation 1856/9472; injected=received |
| Mesh/no-aggregation semantic baselines | Yes | Strict-XY static value differs from spec | same trace/bytes for Mesh; explicit negative-control trace; fresh smokes |
| Required eight variants | Yes | Formal five-seed causal comparison for each variant unrun | fresh Phase05 8/8 smoke |
| Actual topology/cost accounting | Yes | Exact slot match impossible with global integer VC depth | config.ini-derived cost; 6020 lower/7224 upper around Mesh 7032 |
| Uniform/skewed offered-load data | Yes, bounded | Nine-load 2000-cycle full matrix unrun | Phase04 40/40 cells, seeds 1..5, loads 0.01/0.08 |
| Long-link sensitivity | Parameterized | No Phase04 latency-2/4 performance matrix | CLI/topology code; prior single-packet checks only |
| Required metrics | Mostly | Allocator stall-reason counter absent; exact saturation point unmeasured | JSON/CSV includes completion, throughput, mean/P95/P99, hops, links, choices, reroutes; stalls `null` |
| Raw result provenance | Yes | Two development-preflight raw failure logs were overwritten and disclosed | Phase05 evidence audit: 8 smoke + 40 sweep, all raw files/config metadata/accounting present |
| Reproducibility | Yes | — | fresh byte-identical trace/report repeat and SHA-256 values below |
| Ring regression | Yes | — | fresh 1 packet injected/received, average hops 8 |
| Wormhole regression | Current-branch blocker accurately reproduced | Wormhole implementation remains only at separate commit `61eb8c1` | fresh parser exit 2, `unrecognized arguments: --wormhole` |
| Architecture/deadlock/evaluation/audit docs | Yes | — | `docs/sumcheck_{architecture,deadlock_proof,evaluation,requirements_audit}.md` |
| Final cleanliness review | Yes | Ignored evidence remains local | final `git status`, `git diff --check`, stale-name/path scan; ignored m5out retained locally |

## Architecture and key decisions

- Workers 0..63 form four 4x4 meshes; G0..G3 are routers 64..67 and R is 68.
  The causal hierarchy has exactly 69 controller queues, NIs, ExtLinks, local
  ports, and routers with logical/NI/router identity.
- Mesh uses 64 routers but preserves 69 endpoint roles: workers occupy the
  specified quadrants, G0..G3 map to 18/21/42/45, and R maps to 18. Co-location
  is real contention and cost.
- Fixed non-local worker routing uses the source's nearest entry. Adaptive
  freedom exists only at a destination gateway choosing among local entries
  using legal VC_D credits and a per-gateway rotating tie pointer.
- NI injection, switch eligibility, and output-VC allocation enforce offsets
  0/1=U and 2/3=D within every vnet. U-to-D is allowed only at root; D-to-U is
  fatal.
- Aggregation is ejection followed by endpoint dependency wait and fresh
  reinjection; no router performs computation while holding an input VC.
- The CDG now reports the exact C++ relation separately from the stronger
  specification-counted source/destination-entry superset. This fixes the prior
  evidence-label ambiguity without adding forbidden source-side adaptivity.
- The named buffer-matched variant is an explicitly labeled lower bracket,
  never an exact match.

## Files changed/added across the Sumcheck project

Topology/configuration and runners:

- `configs/topologies/SumcheckConfig.py`
- `configs/topologies/SumcheckHierarchy.py`
- `configs/topologies/SumcheckMesh.py`
- `configs/topologies/SumcheckWorkload.py`
- `configs/example/sumcheck_causal_traffic.py`
- `configs/network/Network.py`
- `configs/ruby/Garnet_standalone.py`
- `configs/ruby/Ruby.py`

Garnet/protocol implementation:

- `src/mem/ruby/network/garnet/CommonTypes.hh`
- `src/mem/ruby/network/garnet/SumcheckConfig.hh`
- `src/mem/ruby/network/garnet/RoutingUnit.hh/.cc`
- `src/mem/ruby/network/garnet/OutputUnit.hh/.cc`
- `src/mem/ruby/network/garnet/SwitchAllocator.cc`
- `src/mem/ruby/network/garnet/NetworkInterface.hh/.cc`
- `src/mem/ruby/network/garnet/GarnetNetwork.py/.hh/.cc`
- `src/mem/ruby/network/garnet/SumcheckWorkload.py/.hh/.cc`
- `src/mem/ruby/network/garnet/SConscript`
- `src/mem/ruby/protocol/Garnet_standalone-cache.sm`
- `src/mem/ruby/protocol/Garnet_standalone-dir.sm`
- `src/mem/ruby/slicc_interface/Message.hh`

Tests/scripts:

- `tests/pyunit/pyunit_sumcheck_topology.py`
- `tests/pyunit/pyunit_sumcheck_phase02.py`
- `tests/pyunit/pyunit_sumcheck_phase03.py`
- `tests/pyunit/pyunit_sumcheck_phase04.py`
- `tests/pyunit/sumcheck_adaptive_cpp_test.cc`
- `tests/pyunit/sumcheck_cdg.py`
- `scripts/run_sumcheck_causal_smoke.sh`
- `scripts/run_sumcheck_phase04_case.sh`
- `scripts/run_sumcheck_smoke.sh`
- `scripts/run_sumcheck_sweep.sh`
- `scripts/run_sumcheck_full_matrix.sh`
- `scripts/sumcheck_workload_oracle.py`
- `scripts/sumcheck_phase04_oracle.py`
- `scripts/collect_sumcheck_results.py`
- `scripts/audit_sumcheck_phase05_evidence.py` (Phase05 new)

Documentation/state:

- `docs/sumcheck_spec.md`, `docs/sumcheck_api_map.md`,
  `docs/sumcheck_reference_map.md`, `docs/sumcheck_phase04_experiments.md`
- `docs/sumcheck_architecture.md` (Phase05 new)
- `docs/sumcheck_deadlock_proof.md` (Phase05 new)
- `docs/sumcheck_evaluation.md` (Phase05 new)
- `docs/sumcheck_requirements_audit.md` (Phase05 new)
- `SUMCHECK_STATUS.md`

Phase05 also modifies `tests/pyunit/sumcheck_cdg.py` and
`pyunit_sumcheck_phase02.py` to separate exact-runtime and conservative CDG
relations. Existing `Ring.py` and unrelated Lab work were not modified.

## Build and regression commands/outcomes

Build:

```bash
scons build/NULL/gem5.debug -j16 \
  > m5out/sumcheck_phase05/build.log 2>&1
```

Result: **PASS**, exit 0; target up to date. Optional PNG/HDF5 warnings and
pre-existing Python invalid-escape syntax warnings only.

Static/unit/CDG/C++ commands:

```bash
python3 tests/pyunit/pyunit_sumcheck_topology.py
python3 tests/pyunit/pyunit_sumcheck_phase02.py
python3 tests/pyunit/pyunit_sumcheck_phase03.py
python3 tests/pyunit/pyunit_sumcheck_phase04.py
python3 tests/pyunit/sumcheck_cdg.py \
  --output m5out/sumcheck_phase05/regressions/cdg_report.json
g++ -std=c++17 -Isrc tests/pyunit/sumcheck_adaptive_cpp_test.cc \
  -o m5out/sumcheck_phase05/regressions/sumcheck_adaptive_cpp_test
m5out/sumcheck_phase05/regressions/sumcheck_adaptive_cpp_test
PYTHONPATH=configs python3 scripts/sumcheck_workload_oracle.py \
  --output m5out/sumcheck_phase05/evidence/workload_oracle.json
PYTHONPATH=configs python3 scripts/sumcheck_phase04_oracle.py \
  --output m5out/sumcheck_phase05/evidence/static_oracle.json
python3 scripts/audit_sumcheck_phase05_evidence.py \
  --output m5out/sumcheck_phase05/evidence/phase04_audit.json
```

Outcomes:

| Test | Outcome |
|---|---|
| Topology/count/placement/path/fixed routing | **8/8 PASS** |
| Adaptive/VC/exact+superset CDG tests | **13/13 PASS** |
| Trace/dependency/aggregation tests | **10/10 PASS** |
| Mesh/static/synthetic/cost tests | **5/5 PASS** |
| C++ adaptive credit/tie/class selector | **PASS**, exit 0 |
| Syntax compilation of Sumcheck Python/scripts | **PASS** |
| Static workload/oracle generation | **PASS** |
| Phase04 raw evidence audit | **PASS**, smoke 8, sweep 40, full matrix unrun |

CDG results:

| p | Exact fixed/adaptive routes | Conservative spec routes | U/D separated | Collapsed single VC |
|---:|---:|---:|---|---|
| 1 | 4692/4692 | 4692 | acyclic | acyclic allowed |
| 2 | 4692/8084 | 14548 | both acyclic | concrete cycle |
| 4 | 4692/14868 | 52692 | both acyclic | concrete cycle |

Fresh simulation/regression commands:

```bash
bash scripts/run_sumcheck_smoke.sh m5out/sumcheck_phase05/smoke
bash scripts/run_sumcheck_smoke.sh \
  m5out/sumcheck_phase05/prior_fixed fixed
bash scripts/run_sumcheck_smoke.sh \
  m5out/sumcheck_phase05/prior_adaptive adaptive
```

Results: eight causal variants **8/8 PASS**; fixed and adaptive synthetic
two-case smokes **2/2 each**, every case injected=received.

Ring regression:

```bash
./build/NULL/gem5.debug \
  --outdir=m5out/sumcheck_phase05/ring_single_packet \
  configs/example/garnet_synth_traffic.py \
  --network=garnet --num-cpus=16 --num-dirs=16 --topology=Ring \
  --mesh-rows=1 --routing-algorithm=2 --inj-vnet=0 \
  --synthetic=uniform_random --sim-cycles=500 --injectionrate=1.0 \
  --num-packets-max=1 --single-sender-id=0 --single-dest-id=8
```

Result: **PASS**, packets 1/1, average hops 8.

Wormhole current-branch probe:

```bash
./build/NULL/gem5.debug \
  --outdir=m5out/sumcheck_phase05/wormhole_probe \
  configs/example/garnet_synth_traffic.py \
  --network=garnet --num-cpus=16 --num-dirs=16 --topology=Mesh_XY \
  --mesh-rows=4 --routing-algorithm=1 --inj-vnet=0 \
  --synthetic=uniform_random --sim-cycles=500 --injectionrate=1.0 \
  --num-packets-max=1 --single-sender-id=0 --single-dest-id=15 \
  --vcs-per-vnet=16 --wormhole
```

The probe wrote `m5out/sumcheck_phase05/regressions/wormhole_probe.log`:
expected current-branch blocker, parser exit 2 on unrecognized `--wormhole`;
no Wormhole pass claimed.

## Experiment commands and actually measured results

Fresh Phase05 causal smoke:

```bash
bash scripts/run_sumcheck_smoke.sh m5out/sumcheck_phase05/smoke
python3 scripts/collect_sumcheck_results.py \
  m5out/sumcheck_phase05/smoke \
  --output-dir m5out/sumcheck_phase05/results/smoke
```

All eight runs completed; total 15884 packets and 81040 flits, zero failures
or accounting mismatches. Measured single-seed results:

| Variant | Completion cycles | Mean/P95/P99 latency | Avg hops |
|---|---:|---:|---:|
| Mesh_8x8_XY | 2427 | 26.12/50/54 | 1.548 |
| Hierarchy_p1_fixed | 3745 | 44.67/103/115 | 2.196 |
| Hierarchy_p2_fixed | 2945 | 34.08/65/88 | 1.776 |
| Hierarchy_p4_fixed | 2638 | 27.54/49/85 | 1.169 |
| Hierarchy_p4_adaptive | 2638 | 27.70/49/84 | 1.233 |
| p4 adaptive lower buffer bracket | 2638 | 27.70/49/84 | 1.233 |
| Hierarchy_p4_corners | 2596 | 27.97/50/81 | 1.401 |
| Hierarchy_p4_no_aggregation | 8988 | 162.58/405/433 | 2.750 |

Phase04 representative sweep command:

```bash
bash scripts/run_sumcheck_sweep.sh m5out/sumcheck_phase04/sweep
python3 scripts/collect_sumcheck_results.py \
  m5out/sumcheck_phase04/sweep \
  --output-dir m5out/sumcheck_phase04/results/representative_sweep
```

Actually executed: 40/40 fixed/adaptive p4 points, two traffic cases, loads
0.01/0.08, seeds 1..5, 200 release cycles; 23172 packets and 116172 flits,
zero failures/timeouts/mismatches. Five-seed throughput/mean-latency means:

| Traffic/load | Fixed | Adaptive |
|---|---:|---:|
| uniform 0.01 | 0.4966 / 29.47 | 0.4966 / 29.60 |
| uniform 0.08 | 0.6378 / 646.27 | 0.6309 / 648.71 |
| skewed-bursty 0.01 | 0.2589 / 125.63 | 0.2585 / 125.89 |
| skewed-bursty 0.08 | 0.2823 / 1451.80 | 0.2824 / 1451.94 |

The bounded sweep shows no adaptive performance benefit. It suggests a
throughput plateau/high-latency region at 0.08 but cannot identify a precise
saturation point.

Raw/measured data paths:

- `m5out/sumcheck_phase05/{smoke,results/smoke}/`
- `m5out/sumcheck_phase04/{smoke,sweep}/`
- `m5out/sumcheck_phase04/results/{smoke,representative_sweep}/`
- `m5out/sumcheck_phase05/evidence/phase04_audit.json`

Fresh reproducibility command:

```bash
bash scripts/run_sumcheck_phase04_case.sh \
  m5out/sumcheck_phase05/repro/cluster_skew_adaptive_seed1 \
  Hierarchy_p4_adaptive 1 cluster-skewed-bursty 0.08 200
```

This reruns the cluster-skewed/bursty load-0.08 adaptive seed-1 case and
matches the original byte-for-byte:

- trace SHA-256 `d706a07b49c474c96826c594eda7adaa1e462de0312737e14820c8c0957373c1`;
- report SHA-256 `5bb768970d47cced1a8aaa6f2de8220dffa10b46dc9306023ca6bcbbe67ea2cd`.

## Static-only results

These are 16-byte-flit path/trace calculations, **not measured gem5 data**:

- hierarchy p1 `22448/1016`, p2 `18160/536`, p4 `11952/256`, and p4
  no-aggregation `26048/2368` total flit-hops/peak undirected-link flits;
- strict Mesh XY `15824/624`, versus specification `16208/632`; the latter
  requires non-conventional A-to-B entry waypoints and is not implemented;
- aggregated p1/p2/p4 2004 events, no-aggregation 1856 events;
- reference-flit root cut 8 up/2 down aggregated and 128 up/32 down without
  aggregation per cluster per Phase-A round.

## Incomplete items and exact blockers

1. The prepared resumable full matrix was not executed:

   ```bash
   bash scripts/run_sumcheck_full_matrix.sh \
     m5out/sumcheck_phase04/full_matrix
   ```

   Therefore formal five-seed causal comparisons for all ablations, nine-load
   curves, and precise saturation thresholds are absent.
2. Gateway-entry/root-gateway latency 2/4 performance sensitivities are unrun;
   only configuration/single-packet coverage exists.
3. This Garnet revision has no allocator stall-reason counters. Collected JSON
   uses `null`; endpoint MessageBuffer stall time remains in raw stats.
4. The logical watchdog reports pending events but cannot identify the exact
   router/input VC/waited output resource without broader router diagnostics.
5. Two overwritten development-preflight failures are disclosed in
   `m5out/sumcheck_phase04/failures.json`; their raw failing logs were not
   retained. Accepted smoke/sweep failure lists are empty.
6. Reference bundle files are unavailable.
7. Wormhole support is branch-separated and cannot be regressed on this branch
   without an explicitly authorized integration/branch operation.

## Remaining correctness/deadlock/fairness risks

- Python/CDG and C++ route relation parity is strongly checked but not formally
  extracted from the compiled binary; human review remains warranted.
- The internal-channel CDG does not prove arbitrary higher-level Ruby
  protocol/message-class/controller dependency freedom.
- No negative live simulation deliberately corrupts an out-VC to hit every
  wrong-class assertion, although both normal U/D paths execute.
- Controller aggregation timing is abstract, and future in-router aggregation
  or hardware multicast would invalidate the current ejection/CDG assumptions.
- Exact buffer-slot matching is unavailable; comparisons use equal per-VC
  depth plus explicit lower/upper brackets.
- Causal ablations are one-seed smokes; the bounded two-load sweep is not a
  complete performance characterization.

## Recommended human review

- `configs/topologies/SumcheckConfig.py`: `deterministic_next_hop()`,
  `choose_adaptive_entry()`, `route_vc_class()`, `render_cpp_header()`.
- `src/mem/ruby/network/garnet/RoutingUnit.cc`:
  `outportComputeSumcheck()`.
- `src/mem/ruby/network/garnet/SwitchAllocator.cc`:
  `requiredVcClass()`, `send_allowed()`, `vc_allocate()`.
- `src/mem/ruby/network/garnet/OutputUnit.cc`:
  `has_free_vc()`, `select_free_vc()`, `free_credits()`.
- `src/mem/ruby/network/garnet/NetworkInterface.cc`:
  tail ejection callback, `flitisizeMessage()`, `calculateVC()`.
- `src/mem/ruby/network/garnet/SumcheckWorkload.cc`:
  `inject()`, `notifyArrival()`, `watchdog()`, `finish()`.
- `tests/pyunit/sumcheck_cdg.py`: exact-runtime vs conservative relation and
  resource-dependency construction.
- `scripts/collect_sumcheck_results.py` and
  `audit_sumcheck_phase05_evidence.py`: cost/metric/provenance derivation.

## Git/checkpoint state

- Worktree: `/root/gem5`, branch `sumcheck`; this Phase-05 checkpoint has
  parent/base `c6e06c3`.
- The user authorized this checkpoint commit; ignored
  `m5out/sumcheck_phase05/` evidence stays local.
- No push, merge, rebase, amend, reset, restore, clean, branch switch, or
  destructive operation was performed.
