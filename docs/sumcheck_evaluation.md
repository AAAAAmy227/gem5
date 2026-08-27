# Sumcheck NoC evaluation

## Evidence policy

Cycle, latency, throughput, hop, choice, and link-load values in the measured
sections come from completed gem5 runs with packet and flit injection equal to
reception. Static path/flit-hop calculations appear in a separate section and
are never presented as gem5 measurements. The named reference bundle is
unavailable.

Phase-05 raw-evidence validation is automated by
`scripts/audit_sumcheck_phase05_evidence.py`; its output is
`m5out/sumcheck_phase05/evidence/phase04_audit.json`.

## Baselines and fairness

The eight causal variants are:

| Variant | Purpose |
|---|---|
| Mesh_8x8_XY | conventional 64-router strict-XY baseline |
| Hierarchy_p1_fixed | one-entry topology ablation |
| Hierarchy_p2_fixed | two-entry topology ablation |
| Hierarchy_p4_fixed | topology-only p4 result |
| Hierarchy_p4_adaptive | adaptive increment over p4 fixed |
| Hierarchy_p4_adaptive_buffer_matched | lower buffer-cost bracket |
| Hierarchy_p4_corners | placement ablation |
| Hierarchy_p4_no_aggregation | aggregation semantic negative control |

Primary cases share a 1 GHz Ruby clock, one-cycle routers and internal links,
16-byte flits, three vnets, four VCs/vnet, one slot/control VC, four slots/data
VC, and the same offered logical traffic. Mesh carries the same 64 worker and
five controller roles with real NIs/ExtLinks/local ports. No-aggregation is an
intentional semantic control: packet sizes and rounds are comparable, but it
removes controller aggregation to expose root-cut amplification.

## Workload semantics

The causal trace uses exact 128-byte partials and 32-byte challenges, 14
worker-distributed rounds, an A-to-B terminal-state boundary, four gateway
rounds, a B-to-C boundary, and two root-local rounds. Successors wait for actual
predecessor destination arrival. Aggregated p1/p2/p4 traces contain 2004
network events; no aggregation contains 1856.

Uniform-random and cluster-skewed/bursty traffic are deterministic open-loop
64-worker traces with explicit release cycles. The representative sweep uses
loads 0.01 and 0.08, seeds 1..5, and 200 release cycles. This is a bounded
subset, not the prepared nine-load, 2000-cycle full matrix.

## Actual topology cost

These values are parsed from each run's `config.ini`. Buffer slots count every
real router input port, vnet, VC, and configured data/control depth.

| Variant | Routers | Undirected int links | ExtLinks/local ports | Buffer slots | Max radix | sum(radix^2) |
|---|---:|---:|---:|---:|---:|---:|
| Mesh 8x8 XY | 64 | 112 | 69 | 7032 | 7 | 1377 |
| Hierarchy p1 | 69 | 104 | 69 | 6648 | 6 | 1161 |
| Hierarchy p2 | 69 | 108 | 69 | 6840 | 5 | 1217 |
| Hierarchy p4 staggered | 69 | 116 | 69 | 7224 | 6 | 1369 |
| Hierarchy p4 corners | 69 | 116 | 69 | 7224 | 6 | 1337 |
| p4 data-depth-3 lower bracket | 69 | 116 | 69 | 6020 | 6 | 1369 |

Global integer VC depth cannot make p4 equal Mesh's 7032 slots: depth 3 gives
6020 and depth 4 gives 7224. The historical variant name contains
`buffer_matched`, but every report labels it
`lower_buffer_bracket_not_exact`; the normal p4 case is the upper bracket.

## Phase-05 measured causal regression

The fresh command was:

```bash
bash scripts/run_sumcheck_smoke.sh m5out/sumcheck_phase05/smoke
python3 scripts/collect_sumcheck_results.py \
  m5out/sumcheck_phase05/smoke \
  --output-dir m5out/sumcheck_phase05/results/smoke
```

All eight variants passed; seven aggregated cases received 2004 packets and
10224 flits, and no aggregation received 1856 packets and 9472 flits.

| Variant | Completion cycles | Mean/P95/P99 latency cycles | Avg hops | Adaptive reroute |
|---|---:|---:|---:|---:|
| Mesh 8x8 XY | 2427 | 26.12/50/54 | 1.548 | N/A |
| Hierarchy p1 fixed | 3745 | 44.67/103/115 | 2.196 | 0 |
| Hierarchy p2 fixed | 2945 | 34.08/65/88 | 1.776 | 0 |
| Hierarchy p4 fixed | 2638 | 27.54/49/85 | 1.169 | 0 |
| Hierarchy p4 adaptive | 2638 | 27.70/49/84 | 1.233 | 0.366071 |
| p4 adaptive lower buffer bracket | 2638 | 27.70/49/84 | 1.233 | 0.366071 |
| Hierarchy p4 corners | 2596 | 27.97/50/81 | 1.401 | 0 |
| Hierarchy p4 no aggregation | 8988 | 162.58/405/433 | 2.750 | 0 |

These are one-seed correctness/performance smokes, not formal multi-seed
conclusions. The p4 adaptive smoke recorded 328 non-nearest choices out of 896
destination-entry decisions and 108 tie arbitrations, demonstrating exercised
credit/tie adaptivity while retaining deterministic replay.

## Actually measured five-seed offered-load subset

Phase 04 executed:

```bash
bash scripts/run_sumcheck_sweep.sh m5out/sumcheck_phase04/sweep
python3 scripts/collect_sumcheck_results.py \
  m5out/sumcheck_phase04/sweep \
  --output-dir m5out/sumcheck_phase04/results/representative_sweep
```

All 40 cells completed: 23172 packets and 116172 flits, with zero failures,
timeouts, or accounting mismatches.

| Traffic/load | Fixed throughput/latency | Adaptive throughput/latency | Adaptive reroute rate |
|---|---:|---:|---:|
| uniform 0.01 | 0.4966 / 29.47 | 0.4966 / 29.60 | 0.1730 |
| uniform 0.08 | 0.6378 / 646.27 | 0.6309 / 648.71 | 0.2168 |
| skewed-bursty 0.01 | 0.2589 / 125.63 | 0.2585 / 125.89 | 0.2523 |
| skewed-bursty 0.08 | 0.2823 / 1451.80 | 0.2824 / 1451.94 | 0.2654 |

Throughput is accepted packets per network cycle; latency is mean packet
latency in cycles. This subset does not show an adaptive performance benefit.
Fixed/adaptive are effectively tied under skew, and fixed is slightly better
for uniform load 0.08. The negative result is retained. The latency growth and
throughput plateau at 0.08 suggest near/over-saturation behavior, but two loads
cannot locate a saturation threshold.

Source data are under
`m5out/sumcheck_phase04/results/representative_sweep/`, with every row linked to
its raw `config.ini`, `stats.txt`, `trace.jsonl`, `run.log`, and
`workload_report.json` directory.

## Reproducibility

Phase 05 reran cluster-skewed/bursty, load 0.08, adaptive, seed 1 into
`m5out/sumcheck_phase05/repro/cluster_skew_adaptive_seed1/`. It is byte-identical
to the Phase-04 source run:

| File | SHA-256 |
|---|---|
| `trace.jsonl` | `d706a07b49c474c96826c594eda7adaa1e462de0312737e14820c8c0957373c1` |
| `workload_report.json` | `5bb768970d47cced1a8aaa6f2de8220dffa10b46dc9306023ca6bcbbe67ea2cd` |

## Static/reference-role results — not gem5 measurements

`scripts/sumcheck_phase04_oracle.py` calculates strict routes with the
reference 16-byte flit assumption:

| Variant | Static total flit-hops / peak undirected-link flits | Status |
|---|---:|---|
| Hierarchy p1 fixed | 22448 / 1016 | matches specification |
| Hierarchy p2 fixed | 18160 / 536 | matches specification |
| Hierarchy p4 fixed | 11952 / 256 | matches specification |
| Hierarchy p4 no aggregation | 26048 / 2368 | matches specification |
| Strict Mesh XY | 15824 / 624 | differs from spec 16208 / 632 |

The Mesh discrepancy is explicit: 16208/632 requires forcing A-to-B worker
states through hierarchy entry waypoints, which is not conventional strict XY.
The implemented/measured Mesh remains strict XY.

The workload static oracle also confirms p1/p2/p4 2004 events, no aggregation
1856 events, and at 16-byte flits per-cluster/per-round root cuts of 8 up/2 down
with aggregation versus 128 up/32 down without it.

## Unrun or unavailable evidence

- `scripts/run_sumcheck_full_matrix.sh` is prepared and resumable but has not
  been executed. Therefore there are no formal five-seed causal comparisons
  for every ablation and no nine-load saturation curves.
- Long-link latency 2/4 sensitivities are parameterized but absent from the
  Phase-04 measured matrix.
- Allocator buffer/VC stall-reason counters are unavailable in this Garnet
  revision. Collected JSON uses `null`; raw endpoint MessageBuffer stall-time
  stats are retained.
- The reference bundle is unavailable, so specification/static values cannot
  be attributed to bundle outputs.
- Wormhole integration is unavailable on this branch; the Phase-05 probe exits
  2 on unrecognized `--wormhole`.

## Threats to validity

- **Correctness:** the centralized workload manager models controller compute
  and aggregation timing as a one-clock ejection/reinjection boundary rather
  than a detailed accelerator pipeline.
- **Deadlock:** the CDG proves internal channel resources for this routing
  relation, not arbitrary higher-level Ruby message-class/controller cycles.
- **Fairness/cost:** Mesh and hierarchy differ in router count, radix, link
  count, and total slots; both equal-per-VC and explicitly labeled slot
  brackets are reported, but no exact cost match exists.
- **Performance:** causal ablations are one-seed smokes and the five-seed sweep
  covers only p4 fixed/adaptive at two loads and 200 release cycles.
- **Saturation:** accepted throughput is total packets divided by workload
  completion cycles, so drain time is included; the limited loads do not
  identify a precise injection threshold.
- **Generality:** all measured long links have latency one, allocator stalls
  are missing, and results apply to Garnet standalone rather than a full
  coherence workload.
