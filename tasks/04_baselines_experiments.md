# Phase 04 — Baselines, Cost Accounting, Traffic Sweeps, and Results

## Goal

Run a fair, reproducible evaluation of the validated Sumcheck hierarchy against required baselines/ablations, collect raw results, and create scripts/data needed for the final report.

Do not trade away correctness for experiment throughput.

## Prerequisite

Phase 03 must be PASS with causal workload smoke tests and injected==received accounting.

## Read first

1. `AGENTS.md`
2. `SUMCHECK_STATUS.md`
3. `docs/sumcheck_api_map.md`
4. `docs/sumcheck_reference_map.md`
5. `docs/sumcheck_spec.md`, especially Baselines/experiments, cost matching, traffic cases/metrics, static regression oracles, and final delivery requirements
6. Phase-4 evaluation/reference artifacts identified by the reference map

## Required variants

Implement/run, at minimum:

- `Mesh_8x8_XY`
- `Hierarchy_p1_fixed`
- `Hierarchy_p2_fixed`
- `Hierarchy_p4_fixed`
- `Hierarchy_p4_adaptive`
- `Hierarchy_p4_adaptive_buffer_matched`
- `Hierarchy_p4_corners`
- `Hierarchy_p4_no_aggregation`

Use the same logical workload and packet sizes where the comparison requires it.

For Mesh, preserve the worker quadrant mapping and implement the logical gateway/root controller placement semantics described in the specification. If controller endpoint co-location introduces extra ExtLinks/local-port/NI competition, count it; do not model controllers as cost-free metadata.

## 1. Pre-experiment static regression

Before large runs, independently recompute/validate the routing/path assumptions against the specification/reference static oracles.

Do not require actual Garnet latency/throughput to equal static flit-hop/path numbers.

## 2. Primary fair-comparison configuration

Keep consistent across primary comparisons:

- clock;
- internal-link latency assumption;
- flit size;
- vnets;
- 4 VCs per vnet;
- per-VC buffer depth;
- offered application traffic.

Record every configuration knob in machine-readable output so variants are reproducible.

## 3. Cost accounting

Compute cost from the **actual constructed gem5 topologies**, not simplified reference estimates.

Report at least:

- routers;
- internal links;
- external links;
- directed port ends;
- local ports;
- VC counts;
- actual input buffers;
- buffer slots/bits;
- maximum radix;
- `sum(radix^2)` crossbar proxy;
- gateway-entry and root-gateway long-link latency assumptions.

### Buffer-matched sensitivity

Attempt total-buffer-slot matching using the actual repository capability.

If exact per-port/per-VC matching is unsupported:

- either implement the smallest local override justified by the spec; or
- run clearly labeled bracketing sensitivity.

Never label an approximation as “exact cost matched.”

## 4. Traffic cases

Run at least:

1. causal Sumcheck trace;
2. uniform-random offered-load sweep;
3. cluster-skewed/bursty sweep.

Adaptive benefit must not be demonstrated using only a cherry-picked favorable load. Include low load and near-saturation behavior where feasible.

## 5. Seeds / runtime policy

Formal experiments target at least 5 seeds per required point.

If full sweeps are too expensive in the available environment:

- complete smoke + a smaller representative sweep now;
- provide a resumable batch script for the full matrix;
- clearly distinguish **actually executed data** from commands prepared but not run.

Never invent missing measurements.

## 6. Metrics

Collect as many specified metrics as the current implementation supports, adding minimal instrumentation where necessary:

- per-round completion cycles;
- total Sumcheck completion cycles;
- packets/flits injected and received;
- accepted throughput;
- saturation point;
- mean/P95/P99 latency;
- average hops;
- root-cut utilization;
- gateway-entry utilization;
- maximum-link load;
- per-entry choice distribution;
- adaptive reroute rate;
- buffer/VC stalls;
- watchdog/deadlock/livelock information;
- topology/cost counters.

For every completed variant verify `packets_injected == packets_received`.

## 7. Reproducible scripts and raw data

Leave repository-appropriate equivalents of:

- `scripts/run_sumcheck_smoke.sh`
- `scripts/run_sumcheck_sweep.sh`
- `scripts/collect_sumcheck_results.py`

and store raw stats/CSV/JSON in a clearly documented results directory.

Scripts should be restartable/resumable where feasible and include enough configuration metadata to identify the exact variant/seed/load.

## 8. Plots / result summaries

Generate only plots that are backed by actually collected data. Keep source CSV/JSON next to or referenced from plots.

At minimum prepare the data needed to compare:

- Mesh vs hierarchy;
- p=1/2/4 fixed;
- p=4 fixed vs adaptive;
- staggered vs corners;
- aggregation vs no aggregation;
- primary vs buffer-matched/bracketed sensitivity;
- fixed/adaptive across offered load and skew/burstiness.

## Required validation during experiments

- no variant silently changes workload semantics;
- no variant violates VC discipline just to complete;
- same seed/config is reproducible;
- reference/static numbers remain labeled as such;
- failed/time-out runs are retained/marked, not silently omitted;
- Ring/Wormhole and core Sumcheck regression tests are rerun after experiment-related code changes.

## Explicitly out of scope

Do not declare the whole project complete yet. Final evidence audit, documentation consistency check, and full regression belong to Phase 05.

## Acceptance gate

Phase 04 is PASS when:

- all required variants exist;
- smoke experiments pass;
- a meaningful subset of the requested sweeps has actually run, with 5 seeds for formal points where feasible;
- any unrun full matrix has a reproducible/resumable batch command and is labeled unexecuted;
- raw machine-readable results and cost accounting exist;
- injected==received is checked for completed runs;
- measured results are clearly separated from reference/static calculations;
- `SUMCHECK_STATUS.md` records exact commands, data paths, failures, and remaining experiment gaps.
