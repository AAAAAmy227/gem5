# Phase 02 — Credit-Aware Adaptive Routing + VC Discipline + CDG Verification

## Goal

Add the project's only adaptive routing freedom, enforce the U/D VC discipline in the **actual Garnet allocation path**, and validate the resulting legal routing relation with CDG tests and a collapsed-single-VC negative control.

Correctness/deadlock safety takes priority over performance in this phase.

## Prerequisite

Phase 01 must be PASS with a working deterministic smoke baseline.

## Read first

1. `AGENTS.md`
2. `SUMCHECK_STATUS.md`
3. `docs/sumcheck_api_map.md`
4. `docs/sumcheck_reference_map.md`
5. `docs/sumcheck_spec.md`, especially Credit-aware adaptive routing, Deadlock-free VC discipline, CDG verification, tests, and execution-order sections
6. `DEADLOCK_PROOF.md` and other Phase-2 reference artifacts identified by the reference map
7. the actual current Garnet routing/output/allocator source files mapped during Phase 00

## Required implementation

### 1. Adaptive gateway→entry choice only

Adaptive freedom exists **only** when a gateway chooses an entry into the destination cluster mesh.

For every candidate legal entry use the specified score:

`ManhattanDistance(entry, destination) + lambda * (1 - freeCredits(entry) / capacity(entry))`

with default `lambda = 4.0` and repository-appropriate CLI equivalents of:

- `--entry-congestion-weight`
- `--sumcheck-routing=fixed|adaptive`

The credit term must reflect the candidate output port's downstream **legal VC_D subset**, not the sum of all VCs.

If the current API lacks the needed read-only quantity, add the smallest repository-correct helper rather than guessing a nonexistent API.

### 2. Choice stability and tie behavior

Implement:

- minimum-score selection;
- equal-score rotating per-gateway round-robin tie pointer;
- one entry/outport decision per head flit/packet route decision;
- persistence of the chosen output in appropriate input-VC/route state;
- waiting for a legal output VC if temporarily unavailable, rather than repeatedly changing entries or falling across VC classes.

The routing relation is non-deterministic/adaptive through credits/arbitration history; do not add irreproducible randomness.

### 3. Preserve fixed mesh routing

After choosing an entry:

- direct gateway→entry;
- then strict dim0→dim1 inside the mesh;
- no XY/YX adaptivity;
- no non-minimal wandering;
- no backtracking;
- no reselecting an entry after entering the mesh.

### 4. Enforce VC_U / VC_D in real allocation

Within **each protocol vnet** require at least 4 VCs and partition offsets:

- 0,1 → U
- 2,3 → D

Route-phase rules:

- worker→entry: U
- entry→gateway: U
- gateway→root: U
- root→gateway: D
- gateway→entry→worker: D
- same-cluster generic PE→PE fixed XY: U
- cross-cluster: U*D*
- U→D only at root
- D→U never

Enforce the partition where output VCs are actually enumerated/allocated. A D route may not use an idle/high-credit U VC as fallback, and vice versa.

If `vcs_per_vnet < 4`, fail clearly at startup.

Any representation/check for route class must agree with the actual allocator behavior, not exist only in the offline checker.

### 5. Instrumentation

Add enough instrumentation to recover at least:

- gateway×entry choice counts;
- fixed-nearest vs actual-choice mismatch count;
- candidate credit/occupancy state at selection (sampling/structured counters acceptable if full event logging is excessive);
- adaptive reroute rate;
- tie arbitration count;
- root/gateway-entry link flit/utilization counters or hooks required for Phase 4.

Avoid uncontrolled logging that makes experiments unusable; prefer counters/stats when appropriate.

### 6. CDG verification

Port/retain the independent checker so it enumerates the final legal routing relation, including all adaptive entry choices, over all 69 routers and ordered pairs.

Validate:

- ordered pairs = 4692;
- legal routes p=1: 4692;
- p=2: 14548;
- p=4: 52692;
- U/D-separated model acyclic for p=1/2/4;
- collapsed-single-VC model finds a concrete directed cycle witness for p=2 and p=4.

The checker must match the final C++ routing relation. If legal turns/choices/transitions change, update both together.

Do not overclaim: CDG verification does not automatically prove unrelated Ruby protocol/message-class dependencies.

## Required tests

At minimum automate:

- synthetic downstream credit state makes adaptive choose a non-nearest legal entry;
- equal-score consecutive packets rotate across multiple legal choices;
- adaptive never selects an entry from the wrong cluster;
- chosen entry persists while waiting;
- mesh suffix remains dim0→dim1;
- every legal route is U*, D*, or U*D*;
- all U→D transitions occur only at root;
- no D→U transition exists;
- output VC allocation never crosses U/D partition;
- p=1/2/4 separated CDG acyclic;
- p=2/4 collapsed VC cycle witness exists;
- fixed mode remains behaviorally available;
- deterministic/adaptive smoke completes as feasible;
- Ring/Wormhole regressions remain intact.

## Explicitly out of scope

Do not implement the full causal Sumcheck workload, Mesh baseline, large offered-load sweeps, plots, or final evaluation docs in this phase.

## Acceptance gate

Phase 02 is PASS only if adaptive-choice tests, allocator-partition tests, CDG positive/negative tests, build/smoke, and relevant regressions pass with evidence.

If CDG is cyclic or allocator enforcement cannot be demonstrated, this phase is **not** complete even if packets appear to flow in a smoke run.

Update `SUMCHECK_STATUS.md` with exact commands, cycle-witness paths, instrumentation locations, and any remaining correctness/deadlock/fairness risks.
