# Sumcheck NoC — Phase 03 Handoff

## Current phase/status

- Phase 01 (`01_topology_fixed`): **PASS / complete**.
- Phase 02 (`02_adaptive_vc_cdg`): **PASS / complete**.
- Phase 03 (`03_causal_workload`): **PASS / complete**. Aggregated and
  no-aggregation graphs are validated before simulation, successor injection
  is driven only by destination-NI ejection, exact 32/128-byte packets traverse
  Garnet, two root-local Phase-C rounds run without network messages, and
  fixed/adaptive full-workload smokes complete with injected == received.
- The reference bundle remains unavailable. Phase-03 graphs and static oracles
  are derived from `docs/sumcheck_spec.md`, not claimed as bundle-verified.
- Wormhole remains an inherited branch-integration limitation: this branch has
  no `--wormhole` CLI. Its implementation remains at
  `61eb8c18beeb013d5d3c320cfa0014bed2809d19`.
- Worktree: `/root/gem5` (WSL Ubuntu). No commit, push, merge, rebase,
  cherry-pick, amend, branch switch, reset, or clean was performed in Phase 03.

## Repository state

- Branch: `sumcheck`.
- HEAD: `212b1f83fde841e3b18a32d390797fcf904beaba`
  (`sumcheck: complete phase 02 adaptive VC routing and CDG checks`).
- All Phase-03 implementation, tests, scripts, and this handoff are unstaged
  and uncommitted.

## Implemented behavior

### Logical traces and dependency validation

- `configs/topologies/SumcheckWorkload.py` builds stable deterministic graphs
  directly from the canonical specification.
- Aggregated p=1, p=2, and p=4 each contain exactly **2004** events: 14 Phase-A
  rounds, A→B, four Phase-B rounds, and B→C. Phase C is two root-local rounds
  with no messages.
- The pure-router/no-cluster-aggregation control contains exactly **1856**
  events: 14 rounds of 64 worker→root partials and 64 individual root→worker
  challenges, followed by 64 worker terminal states.
- Python and C++ validators reject duplicate IDs, missing/repeated dependencies,
  and self/forward dependencies before simulation.
- Readiness is an actual arrived-event set plus remaining-dependency count. No
  expected latency or precomputed injection timestamp is used.
- Fixed seed/config generation is byte-stable. Completion reports record trace
  and realized injection-order FNV-64 digests.

### Real Garnet causal replay

- `SumcheckWorkload` is a central endpoint/controller scheduler connected to
  one outgoing protocol `MessageBuffer` per logical endpoint.
- Every `RequestMsg` carries a stable event ID and optional exact byte count in
  the base Ruby `Message`. `NetworkInterface` uses it when present; all other
  traffic retains normal `MessageSizeType` conversion.
- On tail arrival, the NI enqueues at the destination endpoint, sends the
  VC-free credit, updates Garnet stats, and only then reports that event ID.
- A dependent output enters a fresh source endpoint queue no earlier than the
  next endpoint clock after all required arrival callbacks:

  ```text
  packet eject -> VC-free credit -> controller dependency wait
  -> one controller cycle -> fresh packet injection
  ```

  No router input VC is retained for aggregation.
- Partials/state are 128 B and challenges are 32 B. At the tested
  128-bit/16-byte link width these are 8 and 2 flits.
- After all B→C arrivals, two network-silent Phase-C root rounds execute before
  total completion.
- The watchdog reports injected/received/outstanding counts and up to eight
  pending IDs, endpoints, kinds, injection states, and unmet dependencies.

### Endpoint / NI / ExtLink / router mapping

The causal harness uses exactly 69 physical endpoints with no co-located extras:

| Logical roles | Ruby controller identity | Global node / NI | ExtLink | Router |
|---|---|---:|---:|---:|
| workers 0..63 | `L1Cache` version 0..63 | 0..63 | 0..63 | 0..63 |
| G0..G3 | `Directory` version 0..3 | 64..67 | 64..67 | 64..67 |
| root R | `Directory` version 4 | 68 | 68 | 68 |

`config.ini` confirms 69 routers, NIs, and ExtLinks. Each role has one real
injection queue, NI, ExtLink, and local router port; its messages contend there.

Repository/API adaptation and consequence:

- Garnet_standalone is asymmetric by default. Phase 03 adds a vnet-0 receive
  queue to L1 and transmit queue to Directory while preserving existing paths.
- A shared `SumcheckWorkload` manager holds logical dependency/aggregation
  state instead of duplicating the graph in 69 SLICC machines. It injects and
  observes only through endpoint queues and destination NI ejection, so network
  causality and contention are real.
- Aggregation compute latency is one endpoint clock, not calibrated arithmetic
  latency; the shared manager itself is not a modeled hardware cost. NoC
  endpoint cost is exact. Sixty-four unused sequencer/cache objects remain
  because generated L1 controllers require them, but add no NIs, ExtLinks,
  router ports, or traffic.

### No-aggregation root-cut accounting

At actual 16 B/flit, logical/static per-cluster, per-Phase-A-round root cut is:

| Variant | Upward | Downward | Relationship |
|---|---:|---:|---:|
| aggregated | 8 flits | 2 flits | 1x |
| no aggregation | 128 flits | 32 flits | 16x each direction |

The helper recalculates by ceiling division for other flit sizes. Evidence:
`m5out/sumcheck_phase03/logical_oracle.json`.

## Acceptance evidence

### Build and static/unit tests

```bash
scons build/NULL/gem5.debug -j16 \
  > m5out/sumcheck_phase03/build.log 2>&1
```

**PASS**; only known optional PNG/HDF5 warnings.

```bash
python3 -m py_compile configs/network/Network.py configs/ruby/Ruby.py \
  configs/ruby/Garnet_standalone.py \
  configs/topologies/SumcheckConfig.py \
  configs/topologies/SumcheckHierarchy.py \
  configs/topologies/SumcheckWorkload.py \
  configs/example/sumcheck_causal_traffic.py \
  scripts/sumcheck_workload_oracle.py tests/pyunit/sumcheck_cdg.py \
  tests/pyunit/pyunit_sumcheck_phase03.py
python3 tests/pyunit/pyunit_sumcheck_topology.py
python3 tests/pyunit/pyunit_sumcheck_phase02.py
python3 tests/pyunit/pyunit_sumcheck_phase03.py
```

Syntax **PASS**; topology **8/8**; Phase 02 **12/12**; Phase 03
dependency/boundary/root-cut tests **10/10**. Logs:
`m5out/sumcheck_phase03/regressions/{syntax.log,topology.log,phase02.log,phase03.log}`.

```bash
python3 scripts/sumcheck_workload_oracle.py \
  --output m5out/sumcheck_phase03/logical_oracle.json --flit-bytes=16
```

**PASS**: aggregated p=1/2/4 are 2004 events; no aggregation is 1856;
root-cut values are 8/2 versus 128/32 flits.

### Full causal gem5 workloads

```bash
bash scripts/run_sumcheck_causal_smoke.sh \
  m5out/sumcheck_phase03/fixed_aggregated fixed aggregated 4
bash scripts/run_sumcheck_causal_smoke.sh \
  m5out/sumcheck_phase03/adaptive_aggregated adaptive aggregated 4
bash scripts/run_sumcheck_causal_smoke.sh \
  m5out/sumcheck_phase03/fixed_no_aggregation fixed no-aggregation 4
```

Measured Garnet results at 16 B/flit, seed 7:

| Case | Events / packets injected / received | Flits injected / received | Completion tick | Result |
|---|---:|---:|---:|---|
| p=4 aggregated fixed | 2004 / 2004 / 2004 | 10224 / 10224 | 5160 | PASS |
| p=4 aggregated adaptive | 2004 / 2004 / 2004 | 10224 / 10224 | 5160 | PASS |
| p=4 no aggregation fixed | 1856 / 1856 / 1856 | 9472 / 9472 | 17976 | PASS |

Each directory contains `trace.jsonl`, `config.ini`, `stats.txt`, `run.log`, and
`workload_report.json`. Reports contain per-round ticks, zero outstanding,
ejection count, two Phase-C rounds, seed, and digests. Garnet stats independently
match packet/flit totals. Equal fixed/adaptive completion is only a low-load
smoke result, not a performance conclusion.

### Reproducibility

```bash
bash scripts/run_sumcheck_causal_smoke.sh \
  m5out/sumcheck_phase03/fixed_aggregated_repeat fixed aggregated 4
```

**PASS**: trace digest `6bef6b51aa1d2a2`, injection digest
`612f3eda132ec9cf`, 2004 packets, 10224 flits, and completion tick 5160 all
match the first fixed run.

### Prior routing/CDG regressions

```bash
python3 tests/pyunit/sumcheck_cdg.py \
  --output m5out/sumcheck_phase03/regressions/cdg_report.json
g++ -std=c++17 -Isrc tests/pyunit/sumcheck_adaptive_cpp_test.cc \
  -o m5out/sumcheck_phase03/regressions/sumcheck_adaptive_cpp_test
m5out/sumcheck_phase03/regressions/sumcheck_adaptive_cpp_test
bash scripts/run_sumcheck_smoke.sh \
  m5out/sumcheck_phase03/prior_fixed_smoke fixed
bash scripts/run_sumcheck_smoke.sh \
  m5out/sumcheck_phase03/prior_adaptive_smoke adaptive
```

**PASS**. CDG counts remain 4692/14548/52692 for p=1/2/4; separated U/D is
acyclic and p=2/4 retain collapsed witnesses. The selector passes. All four
prior fixed/adaptive gem5 cases report 1/1 packets.

### Ring and Wormhole

```bash
./build/NULL/gem5.debug \
  --outdir=m5out/sumcheck_phase03/ring_single_packet \
  configs/example/garnet_synth_traffic.py \
  --network=garnet --num-cpus=16 --num-dirs=16 --topology=Ring \
  --mesh-rows=1 --routing-algorithm=2 --inj-vnet=0 \
  --synthetic=uniform_random --sim-cycles=500 --injectionrate=1.0 \
  --num-packets-max=1 --single-sender-id=0 --single-dest-id=8
```

Ring **PASS**: 1/1 packets and flits, average hops 8.

The `--vcs-per-vnet=16 --wormhole` probe under
`m5out/sumcheck_phase03/wormhole_probe/` reproduces the inherited parser exit
`unrecognized arguments: --wormhole`. No Wormhole pass is claimed and no branch
integration was attempted.

## Remaining risks/limits

1. The reference bundle is unavailable, so JSONL cannot be byte-compared with
   its intended generator; counts/dependencies/sizes are independently derived.
2. Aggregation compute is one endpoint cycle and the manager is not modeled as
   hardware area; later work may need calibrated/configurable compute latency.
3. Generated worker sequencer/cache objects are idle framework overhead.
4. Percentiles, multi-seed sweeps, saturation, cost comparison, and plots are
   intentionally deferred to Phase 04.
5. The watchdog identifies pending events/endpoints/dependencies but does not
   dump every router input VC and waited allocator resource.
6. Wormhole remains branch-separated and needs separately authorized,
   conflict-aware integration/testing.

## Exact next action

Proceed only to `tasks/04_baselines_experiments.md`: use the causal workload for
Mesh/placement/aggregation baselines and bounded experiment automation. Do not
begin Phase 05 final review yet.
