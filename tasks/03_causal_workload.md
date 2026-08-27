# Phase 03 — Causal Sumcheck Workload + Aggregation Endpoints

## Goal

Implement/replay the specified Sumcheck communication as a **causal** workload on the validated NoC, with aggregation occurring at endpoints/controllers through packet termination and reinjection.

Also implement the pure-router/no-aggregation negative control.

## Prerequisite

Phase 02 must be PASS: adaptive routing, VC enforcement, and CDG checks are already validated.

## Read first

1. `AGENTS.md`
2. `SUMCHECK_STATUS.md`
3. `docs/sumcheck_api_map.md`
4. `docs/sumcheck_reference_map.md`
5. `docs/sumcheck_spec.md`, especially Sumcheck workload, phase boundary, causal replay, aggregation semantics, tests, and execution order
6. Phase-3 reference trace/README/reference-implementation files identified by the reference map

## Required semantics

Use the specified logical roles:

- 64 workers;
- 4 gateway/controller roles;
- 1 root controller role.

If the actual tester/controller framework cannot expose 69 independent endpoints exactly, implement the closest semantics allowed by the spec and document the logical endpoint→NI→ExtLink→router mapping and any port/injection contention it creates.

### Packet sizes / phases

Preserve the spec's logical packet sizes and phase structure:

- field element 32 B;
- partial polynomial 128 B;
- Phase A: 14 worker-distributed rounds;
- boundary to cluster controllers;
- Phase B: 4 cluster-controller rounds;
- boundary to root;
- Phase C: 2 root-local rounds with no network messages.

Use the actual configured Garnet flit size for simulation conversion; do not silently assume the reference's 16 B/flit if the gem5 configuration differs.

## 1. Aggregation endpoint semantics

Aggregation must be:

`packet eject → controller waits for all required inputs → aggregation compute/simulate → inject one new packet`

A router must not retain an input VC during aggregation.

Implement the Phase-A sequence and later phase boundaries according to the specification, including separate unicast challenge packets when hardware multicast is not explicitly implemented.

## 2. Causal dependency replay

Prefer the reference JSONL traces if available and compatible.

A successor event may inject **only after every event in its `depends_on` set has actually arrived at its destination**.

Do not approximate this with precomputed timestamps or expected latencies.

Implement/verify:

- stable event IDs;
- dependency graph validation before simulation;
- missing dependency detection;
- forward/invalid dependency detection;
- arrival notification/accounting;
- readiness tracking;
- deterministic scheduling under a fixed seed/config.

## 3. Reference event-count regression

Validate the logical/reference trace counts before relying on gem5 performance:

- aggregated p=1: 2004 events;
- aggregated p=2: 2004 events;
- aggregated p=4: 2004 events;
- no-aggregation: 1856 events.

These are logical/static regression values, not gem5 cycle counts.

## 4. No-aggregation negative control

Implement the specified control in which Phase-A workers send partials directly to root and root returns individual worker challenges.

Validate the specified per-cluster/per-round root-cut traffic relationship in flits under the reference 16 B/flit assumption, or recalculate/report the corresponding actual-flit-size values if the gem5 flit size differs. Do not mix the two without labeling them.

## 5. Completion/accounting

Add or use robust accounting for:

- per-round completion;
- total workload completion;
- packet/flit injected and received counts;
- outstanding events/packets;
- reproducible seed/config;
- a watchdog that reports useful stuck state rather than only “simulation hung,” as far as the current API permits.

Every completed smoke must verify `packets_injected == packets_received`.

## Required tests

At minimum:

- dependency graph has no missing/forward dependencies;
- aggregated event counts match 2004 for p=1/2/4;
- no-aggregation event count matches 1856;
- aggregation waits for required input arrivals;
- successor injection cannot occur before dependency arrival;
- controller aggregation releases/reinjects rather than holding a wormhole channel;
- no-aggregation root-cut accounting matches the configured packet/flit assumptions;
- small fixed-routing workload smoke completes;
- small adaptive workload smoke completes if Phase-2 infrastructure supports it;
- injected == received;
- identical seed/config is reproducible at least at the logical event/choice level required by the spec;
- prior topology/routing/CDG and Ring/Wormhole regressions remain passing.

## Explicitly out of scope

Do not launch the complete multi-seed performance matrix or final plots/docs yet. A minimal smoke dataset is expected; broad experiments belong to Phase 04.

## Acceptance gate

Phase 03 is PASS only when the causal arrival-triggered workload semantics, event-count regressions, aggregation boundary, no-aggregation control, and smoke accounting are demonstrated with exact commands/output paths.

Update `SUMCHECK_STATUS.md`, especially any endpoint-mapping compromise and its cost/correctness consequence.
