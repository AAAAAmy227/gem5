# Sumcheck NoC Phase-04 experiment record

This file documents Phase-04 measured data and static calculations.  It is
not the Phase-05 final evaluation audit.

## Reproduction

Build and validate static assumptions:

```bash
scons build/NULL/gem5.debug -j16
PYTHONPATH=configs python3 scripts/sumcheck_phase04_oracle.py \
  --output m5out/sumcheck_phase04/static_oracle.json
python3 tests/pyunit/pyunit_sumcheck_phase04.py
```

Run the eight required causal smokes and the executed representative sweep:

```bash
bash scripts/run_sumcheck_smoke.sh m5out/sumcheck_phase04/smoke
bash scripts/run_sumcheck_sweep.sh m5out/sumcheck_phase04/sweep
python3 scripts/collect_sumcheck_results.py \
  m5out/sumcheck_phase04/smoke \
  --output-dir m5out/sumcheck_phase04/results/smoke
python3 scripts/collect_sumcheck_results.py \
  m5out/sumcheck_phase04/sweep \
  --output-dir m5out/sumcheck_phase04/results/representative_sweep
```

Each case directory contains `config.ini`, `stats.txt`, `trace.jsonl`,
`run.log`, and `workload_report.json`.  A valid report is the resumable marker;
the runner checks injected/received packet and flit equality before skipping.

## Common configuration and topology cost

Primary cases use 1 GHz Ruby clock, router/internal-link latency 1, 16-byte
flits, three vnets, four VCs/vnet, one slot/control VC, four slots/data VC,
and 69 real endpoint NIs/ExtLinks.  Gateway-entry and root-gateway links use
latency 1 in this executed matrix.  Every knob is repeated in each workload
report's `configuration` object.

The following comes from the actual generated `config.ini`, not the simplified
reference cost model:

| Variant | Routers | Undirected int links | ExtLinks/local ports | Buffer slots | Max radix | sum(radix^2) |
|---|---:|---:|---:|---:|---:|---:|
| Mesh 8x8 XY | 64 | 112 | 69 | 7032 | 7 | 1377 |
| Hierarchy p1 | 69 | 104 | 69 | 6648 | 6 | 1161 |
| Hierarchy p2 | 69 | 108 | 69 | 6840 | 5 | 1217 |
| Hierarchy p4 staggered | 69 | 116 | 69 | 7224 | 6 | 1369 |
| Hierarchy p4 corners | 69 | 116 | 69 | 7224 | 6 | 1337 |
| p4 lower buffer bracket | 69 | 116 | 69 | 6020 | 6 | 1369 |

With only a global integer data-VC depth, the p4 topology cannot equal Mesh's
7032 slots: data depth 3 gives 6020 and depth 4 gives 7224.  The named
`Hierarchy_p4_adaptive_buffer_matched` case is therefore explicitly the lower
bracket, not an exact match; the ordinary adaptive case is the upper bracket.

Mesh maps workers into the four specified quadrants and co-locates G0..G3 at
routers 18, 21, 42, 45 and R at router 18.  All five controllers remain real
NIs/ExtLinks/local ports, including G0/R competition at router 18.

## Static regression

The independently computed hierarchy full-trace values match the specification
for p1 `22448/1016`, p2 `18160/536`, p4 `11952/256`, and p4 no-aggregation
`26048/2368` (total flit-hops/peak undirected-link flits).

Strict conventional XY with the specified Mesh placement computes
`15824/624`, not the specification's `16208/632`.  The latter is reproduced
only by forcing A-to-B worker-state paths through hierarchy entry waypoints;
that is not strict XY.  The measured Mesh baseline keeps strict XY.  This
discrepancy is recorded in `static_oracle.json`; neither value is called a
gem5 measurement.  The reference bundle remains unavailable.

## Actually executed causal smokes

All eight variants completed with injected equal to received.  Seven
aggregated variants completed 2004 packets; no-aggregation completed 1856.
Selected single-seed measurements:

| Variant | Completion cycles | Mean / P95 / P99 packet latency (cycles) | Avg hops |
|---|---:|---:|---:|
| Mesh 8x8 XY | 2427 | 26.12 / 50 / 54 | 1.548 |
| Hierarchy p1 fixed | 3745 | 44.67 / 103 / 115 | 2.196 |
| Hierarchy p2 fixed | 2945 | 34.08 / 65 / 88 | 1.776 |
| Hierarchy p4 fixed | 2638 | 27.54 / 49 / 85 | 1.169 |
| Hierarchy p4 adaptive | 2638 | 27.70 / 49 / 84 | 1.233 |
| p4 adaptive lower buffer bracket | 2638 | 27.70 / 49 / 84 | 1.233 |
| Hierarchy p4 corners | 2596 | 27.97 / 50 / 81 | 1.401 |
| Hierarchy p4 no aggregation | 8988 | 162.58 / 405 / 433 | 2.750 |

These are smokes, not five-seed formal performance claims.  The workload
boundary correction keeps 64 individual A-to-B worker-state packets on the
entry-to-gateway cut, making all hierarchy static flit-hop oracles match.

## Actually executed five-seed offered-load subset

The representative matrix is 2 traffic cases x 2 loads x fixed/adaptive x 5
seeds = 40 completed runs, 23172 packets and 116172 flits total, with no failed
or accounting-mismatched case.  Aggregate accepted throughput below is packets
per network cycle across all 64 workers.

| Traffic/load | Fixed throughput / mean latency | Adaptive throughput / mean latency | Adaptive reroute rate |
|---|---:|---:|---:|
| uniform 0.01 | 0.4966 / 29.47 | 0.4966 / 29.60 | 0.1730 |
| uniform 0.08 | 0.6378 / 646.27 | 0.6309 / 648.71 | 0.2168 |
| skewed-bursty 0.01 | 0.2589 / 125.63 | 0.2585 / 125.89 | 0.2523 |
| skewed-bursty 0.08 | 0.2823 / 1451.80 | 0.2824 / 1451.94 | 0.2654 |

The bounded data do not demonstrate an adaptive win: fixed and adaptive are
effectively tied under skew, and fixed is slightly better under uniform 0.08.
This negative result is retained rather than cherry-picked away.  The large
latency increase and throughput plateau at 0.08 show near/over-saturation
behavior, but two load points do not locate a precise saturation threshold.

A repeated skewed-bursty load-0.08 adaptive seed-1 run is byte-identical in
both `trace.jsonl` (SHA-256
`d706a07b49c474c96826c594eda7adaa1e462de0312737e14820c8c0957373c1`)
and `workload_report.json`; evidence is under
`m5out/sumcheck_phase04/repro/cluster_skew_adaptive_seed1/`.

Source data are
`m5out/sumcheck_phase04/results/{smoke,representative_sweep}/results.{json,csv}`,
`summary.csv`, and `costs.json`.  The JSON also contains per-entry choices,
adaptive reroute rate, all-link maximum load, tracked root/gateway-entry link
load and utilization, topology cost, watchdog outcome, and raw-directory path.
Allocator stall counts are unavailable in this Garnet revision; raw endpoint
MessageBuffer stall-time stats are retained and the missing allocator metric
is explicitly `null` in collected JSON.

## Prepared but not executed

The following resumable full matrix was prepared but not run in Phase 04:

```bash
bash scripts/run_sumcheck_full_matrix.sh \
  m5out/sumcheck_phase04/full_matrix
```

It runs five causal seeds for all eight variants, then fixed/adaptive uniform
and skewed-bursty at nine loads from 0.005 through 0.16 for 2000 injection
cycles.  Phase 05 must not treat those unexecuted points as data.
