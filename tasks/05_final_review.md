# Phase 05 — Final Regression, Specification Audit, and Delivery Review

## Goal

Turn the working implementation into an auditable course-project deliverable. Recheck every major requirement against code/tests/data and report gaps precisely.

This phase may fix bugs found by the audit, but it should not casually introduce new architecture or experiment semantics.

## Prerequisite

Phases 00–04 should be PASS or have explicitly documented residual gaps that can now be resolved/audited.

## Read first

1. `AGENTS.md`
2. the entire current `SUMCHECK_STATUS.md`
3. the entire `docs/sumcheck_spec.md`
4. `docs/sumcheck_api_map.md`
5. `docs/sumcheck_reference_map.md`
6. all Sumcheck implementation/tests/scripts/docs changed during prior phases
7. raw experiment/result metadata actually produced in Phase 04

## 1. Full requirement audit

Walk through the specification and classify every substantive requirement as one of:

- IMPLEMENTED + TESTED
- IMPLEMENTED + NOT FULLY TESTED
- PARTIAL
- NOT IMPLEMENTED
- NOT APPLICABLE due to an explicitly documented repository/API constraint

Do not infer completion from comments or filenames. Trace the real execution path for critical features.

Pay special attention to these high-risk claims:

- adaptive routing is truly non-deterministic with respect to credit/arbitration state;
- credit score uses only legal downstream VC_D state;
- chosen entry/outport is stable for the packet while blocked;
- allocator enforces U/D partition in the real output-VC path;
- U→D occurs only at root and D→U never occurs;
- CDG checker enumerates exactly the same legal routing relation as C++;
- aggregation ejects/reinjects and does not hold a wormhole channel;
- causal successors wait for actual predecessor destination arrival;
- Mesh and no-aggregation baselines preserve comparable logical semantics;
- buffer/cost matching is labeled accurately;
- static/reference results are never presented as measured gem5 results.

## 2. Rerun regression suite

Rerun, as locally feasible:

- build;
- topology/count/placement/path tests;
- deterministic routing tests;
- adaptive synthetic-credit and tie tests;
- U/D allocator tests;
- CDG separated and collapsed-negative tests;
- trace dependency/event-count tests;
- fixed/adaptive causal smoke;
- no-aggregation smoke;
- reproducibility test;
- Ring regression;
- Wormhole regression.

Record exact commands, test counts, pass/fail, and output paths.

## 3. Recheck experiments

For each result/plot/table intended for the report:

- verify its source raw file exists;
- verify variant/config/seed/load metadata;
- verify injected==received for completed network runs;
- mark failed/timeout/incomplete runs explicitly;
- confirm that reported numbers are actually measured or clearly labeled static/reference calculations.

Do not fill missing experiment cells by interpolation or reference numbers.

## 4. Required project documentation

Create/update the repository-appropriate versions of:

- `docs/sumcheck_architecture.md`
- `docs/sumcheck_deadlock_proof.md`
- `docs/sumcheck_evaluation.md`
- `SUMCHECK_STATUS.md`

### Architecture doc must cover

- router/endpoint mapping;
- topology/link/entry placement;
- deterministic and adaptive routing relation;
- controller aggregation boundary;
- CLI/config knobs;
- any deviation forced by actual gem5 APIs.

### Deadlock doc must cover

- physical channel classes;
- VC_U/VC_D partition;
- allocator enforcement point;
- allowed U*/D*/U*D* transitions;
- root-only U→D;
- CDG construction/enumeration;
- p=1/2/4 acyclic results;
- p=2/4 collapsed-single-VC concrete cycle witness;
- limitation regarding higher-level Ruby protocol/message-class dependencies;
- endpoint ejection/reinjection assumption.

### Evaluation doc must cover

- baselines and why they are fair;
- workload semantics;
- cost accounting;
- seeds/load sweeps;
- actual measured metrics/results;
- static/reference regression values in a separately labeled role;
- unrun/partial experiments and exact reason;
- correctness/deadlock/fairness threats to validity.

## 5. Final `SUMCHECK_STATUS.md`

The final status must contain a complete evidence table with at least:

| Step | Completed | Missing | Evidence |
|---|---|---|---|

and clearly list:

- final architecture version;
- changed/added files;
- key implementation decisions;
- build command;
- test commands + per-test outcomes;
- experiment commands;
- actually measured data paths/results;
- static-only results;
- incomplete items and exact blockers;
- remaining correctness/deadlock/fairness risks;
- concrete files/functions recommended for human review.

## 6. Final cleanliness review

Before finishing:

- inspect `git status` and `git diff`;
- ensure no unrelated Lab3/user work was lost;
- ensure generated giant build/cache/result artifacts are not accidentally added where inappropriate;
- ensure scripts/docs refer to current filenames/options rather than stale names;
- ensure experiment outputs can be reproduced from recorded commands.

## Acceptance gate

Phase 05 is PASS only when the final claims are evidence-backed and the remaining gaps, if any, are explicit.

A partially complete but accurately audited implementation is preferable to an unsupported claim of full completion.
