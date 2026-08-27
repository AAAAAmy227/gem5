# Sumcheck NoC — Phase 04 Handoff

## Current phase/status

- Phase 01 topology/fixed routing: **PASS**.
- Phase 02 adaptive VC/CDG: **PASS**.
- Phase 03 causal workload: **PASS**.
- Phase 04 baselines/experiments: **PASS with explicitly bounded data and
  remaining full-matrix gaps**.
- Do not begin the Phase-05 final audit implicitly; it remains the next phase.
- Reference bundle remains unavailable. Static values are derived from
  `docs/sumcheck_spec.md`, never labeled measured gem5 results.
- Wormhole remains branch-separated and unavailable on this branch.

## Repository state

- Worktree: `/root/gem5`, branch `sumcheck`.
- Phase-04 implementation commit: `02b09e0`
  (`sumcheck: complete phase 04 baselines and experiments`).
- The worktree is expected to be clean after this handoff-status correction
  is committed; ignored `m5out/sumcheck_phase04/` evidence remains local.
- The user explicitly authorized the Phase-04 commits after experiments
  completed. No push, merge, rebase, cherry-pick, amend, branch switch, reset,
  or clean was performed.

## Phase-04 implementation

- `SumcheckMesh` is a strict 8x8 XY baseline. Workers preserve quadrant
  placement; G0..G3 map to routers 18/21/42/45 and R to router 18. All 69
  roles retain real NIs, ExtLinks, and local-port competition.
- Required variants exist in `scripts/run_sumcheck_phase04_case.sh`; the
  smoke runner exercises all eight.
- A-to-B now keeps one terminal-state packet per worker routed through the
  assigned entry to the gateway cut. This preserved the 2004 event total and
  corrected hierarchy static full-trace values to the specification.
- Open-loop deterministic uniform-random and cluster-skewed/bursty traces have
  explicit release cycles and exact 32/128-byte packets. The causal workload
  scheduler respects both release time and dependencies, drains all traffic,
  and requires injected==received.
- Workload reports now include mean/P95/P99 packet latency, completion cycle,
  aggregate accepted throughput, and every experiment knob. Garnet exposes
  per-link flit counts for measured maximum-link load.
- `collect_sumcheck_results.py` parses actual `config.ini` topology objects,
  raw stats, costs, link utilization, entry choices, reroute rate, latency,
  hops, and accounting into JSON/CSV summaries.
- Global per-VC depths cannot exactly match Mesh's total buffer slots. The
  named buffer-matched sensitivity is explicitly a lower bracket (6020 slots,
  data depth 3); normal p4 is the upper bracket (7224); Mesh is 7032.

## Static acceptance evidence

Command:

```bash
PYTHONPATH=configs python3 scripts/sumcheck_phase04_oracle.py \
  --output m5out/sumcheck_phase04/static_oracle.json
```

Result: hierarchy p1 `22448/1016`, p2 `18160/536`, p4 `11952/256`, and
p4 no-aggregation `26048/2368` total flit-hops/peak undirected-link flits all
match the specification.

Strict Mesh XY calculates `15824/624`, while the spec says `16208/632`. The
spec value requires forcing A-to-B packets through hierarchy entry waypoints,
which is not conventional XY. The implemented/measured Mesh stays strict XY;
the discrepancy is recorded in the oracle and evaluation record.

## Build and regression evidence

```bash
scons build/NULL/gem5.debug -j16 \
  > m5out/sumcheck_phase04/build.log 2>&1
python3 tests/pyunit/pyunit_sumcheck_topology.py
python3 tests/pyunit/pyunit_sumcheck_phase02.py
python3 tests/pyunit/pyunit_sumcheck_phase03.py
python3 tests/pyunit/pyunit_sumcheck_phase04.py
python3 tests/pyunit/sumcheck_cdg.py \
  --output m5out/sumcheck_phase04/regressions/cdg_report.json
g++ -std=c++17 -Isrc tests/pyunit/sumcheck_adaptive_cpp_test.cc \
  -o m5out/sumcheck_phase04/regressions/sumcheck_adaptive_cpp_test
m5out/sumcheck_phase04/regressions/sumcheck_adaptive_cpp_test
```

Results: build PASS (only optional PNG/HDF5 warnings); topology 8/8; Phase 02
12/12; Phase 03 10/10; Phase 04 5/5; adaptive C++ selector PASS. CDG remains
4692/14548/52692 routes for p1/p2/p4, U/D separated acyclic, p2/p4 collapsed
witnesses present. Logs are under `m5out/sumcheck_phase04/regressions/`.

Prior fixed/adaptive two-case smokes PASS at 1/1 each. Ring single-packet PASS
at 1/1 and average hops 8. The Wormhole probe is retained under
`regressions/wormhole_probe/` and still exits on `unrecognized arguments:
--wormhole`; no Wormhole pass or integration is claimed.

## Required causal variant smokes

Command:

```bash
bash scripts/run_sumcheck_smoke.sh m5out/sumcheck_phase04/smoke
```

All eight variants PASS. Seven aggregated cases have 2004 injected/received;
no-aggregation has 1856/1856. Total across smokes: 15884 packets and 81040
flits, with zero failed/timeout/accounting-mismatch runs.

| Variant | Completion cycles | Mean/P95/P99 latency cycles | Avg hops |
|---|---:|---:|---:|
| Mesh_8x8_XY | 2427 | 26.12/50/54 | 1.548 |
| Hierarchy_p1_fixed | 3745 | 44.67/103/115 | 2.196 |
| Hierarchy_p2_fixed | 2945 | 34.08/65/88 | 1.776 |
| Hierarchy_p4_fixed | 2638 | 27.54/49/85 | 1.169 |
| Hierarchy_p4_adaptive | 2638 | 27.70/49/84 | 1.233 |
| p4 adaptive lower buffer bracket | 2638 | 27.70/49/84 | 1.233 |
| Hierarchy_p4_corners | 2596 | 27.97/50/81 | 1.401 |
| Hierarchy_p4_no_aggregation | 8988 | 162.58/405/433 | 2.750 |

These are one-seed smokes, not formal multi-seed performance conclusions.

## Actually executed representative sweep

```bash
bash scripts/run_sumcheck_sweep.sh m5out/sumcheck_phase04/sweep
python3 scripts/collect_sumcheck_results.py \
  m5out/sumcheck_phase04/sweep \
  --output-dir m5out/sumcheck_phase04/results/representative_sweep
```

Executed 40/40 points: uniform/skewed-bursty x load 0.01/0.08 x
fixed/adaptive x seeds 1..5, 200 release cycles. All 23172 packets and 116172
flits were received; failures/timeouts/accounting mismatches: zero.

Five-seed means (accepted packets/network-cycle; latency cycles):

| Traffic/load | Fixed throughput/latency | Adaptive throughput/latency |
|---|---:|---:|
| uniform 0.01 | 0.4966/29.47 | 0.4966/29.60 |
| uniform 0.08 | 0.6378/646.27 | 0.6309/648.71 |
| skewed-bursty 0.01 | 0.2589/125.63 | 0.2585/125.89 |
| skewed-bursty 0.08 | 0.2823/1451.80 | 0.2824/1451.94 |

The bounded results show no adaptive performance benefit; they are retained
as a negative result. Load 0.08 shows a throughput plateau and sharply higher
latency, but the precise saturation threshold is not located by two points.
An exact repeat of skewed-bursty load 0.08/adaptive/seed 1 produced a
byte-identical trace (SHA-256 `d706a07b49c474c96826c594eda7adaa1e462de0312737e14820c8c0957373c1`)
and report under `m5out/sumcheck_phase04/repro/`.

Raw/summarized evidence:

- `m5out/sumcheck_phase04/{smoke,sweep}/...` per-run artifacts;
- `m5out/sumcheck_phase04/results/smoke/{results.json,results.csv,summary.csv,costs.json}`;
- `m5out/sumcheck_phase04/results/representative_sweep/{results.json,results.csv,summary.csv,costs.json}`;
- `docs/sumcheck_phase04_experiments.md` interpretation and reproduction;
- `m5out/sumcheck_phase04/failures.json` discloses two overwritten development
  preflight failures; accepted smoke/sweep failure lists are empty.

## Remaining experiment gaps / exact next action

1. The prepared full matrix was **not executed**:

   ```bash
   bash scripts/run_sumcheck_full_matrix.sh \
     m5out/sumcheck_phase04/full_matrix
   ```

   It is resumable and includes five causal seeds for all variants plus nine
   loads (0.005..0.16), two traffic cases, two routing policies, and 2000
   release cycles.
2. Therefore precise saturation points and formal five-seed causal comparisons
   for every ablation remain unmeasured; no values were invented.
3. Allocator buffer/VC stall counters are unavailable in this Garnet revision.
   Endpoint MessageBuffer stall-time remains in raw stats; collected JSON marks
   allocator stalls `null`.
4. Long-link latency 2/4 sensitivities are parameterized but not executed in
   the bounded subset.
5. Reference bundle and Wormhole integration remain unavailable.

Proceed next only to the Phase-05 final evidence/documentation audit, or run
the prepared full matrix first if more experiment time is authorized.
