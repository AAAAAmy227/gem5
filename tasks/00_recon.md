# Phase 00 — Repository / API / Reference Reconnaissance

## Goal

Establish a trustworthy implementation map and regression baseline **before** writing Sumcheck topology/routing code.

This phase is reconnaissance, not feature implementation.

## Read first

1. `AGENTS.md`
2. `SUMCHECK_STATUS.md`
3. **all of** `docs/sumcheck_spec.md`
4. `docs/sumcheck_api_map.md`
5. `docs/sumcheck_reference_map.md`
6. If present, unpack and fully inspect `sumcheck_noc_reference_bundle.zip`, including the files named in the specification.

## Required work

### 1. Inspect repository state

Record, without destroying anything:

- `pwd`
- current branch
- HEAD commit
- `git status --short`
- relevant recent history if helpful
- existing Sumcheck-related files if any
- prior Lab3 Ring files/options/tests
- prior Lab3 Wormhole files/options/tests

Do not clean the worktree or discard user changes.

### 2. Establish actual build/run/test commands

Find the commands that really apply to this checkout. Prefer existing project scripts/history/docs over invented commands.

At minimum identify and, where locally feasible, execute:

- the relevant gem5 build command;
- an existing network smoke command;
- Ring regression/smoke;
- Wormhole regression/smoke;
- any relevant unit/Python tests.

Record exact commands and outcomes in `SUMCHECK_STATUS.md`.

### 3. Inspect actual gem5/Garnet APIs

Locate the real implementation points for:

- topology construction/registration;
- CLI options;
- router and port naming;
- routing computation;
- input VC / route state;
- downstream/output-unit credit/buffer state;
- switch/output VC allocation;
- VC indexing within vnets;
- NI injection/ejection;
- current tester/traffic-generator/controller facilities;
- packet-arrival observation;
- statistics and link-utilization hooks;
- build/SConscript/SimObject declarations if relevant.

Do **not** modify Garnet based on guessed APIs from another gem5 version.

Fill `docs/sumcheck_api_map.md` with exact files/classes/functions and any required semantic adaptations.

### 4. Inspect and index the reference bundle

If available:

- unpack it without overwriting unrelated repository files;
- read the design contract, README, reference implementation, deadlock proof, evaluation plan, and outputs;
- verify where the specification's static acceptance values come from;
- record any discrepancy between reference and the current spec;
- fill `docs/sumcheck_reference_map.md`.

Remember: reference/static output is not gem5 cycle-level evidence.

### 5. Decide the smallest Phase-1 implementation surface

Without implementing it yet, identify the likely files that Phase 1 must touch for:

- `SumcheckHierarchy` topology;
- command-line options;
- centralized mapping helper/table;
- deterministic Sumcheck routing;
- topology/path tests;
- deterministic smoke.

If the mapping cannot be shared directly between Python and C++, describe how consistency will be generated or regression-tested.

## Explicitly out of scope

Do **not** implement in Phase 00:

- the new topology;
- deterministic routing;
- adaptive routing;
- credit helpers;
- VC_U/VC_D allocator enforcement;
- CDG changes;
- Sumcheck causal traffic;
- baselines/experiments/plots.

A tiny temporary probe or non-functional diagnostic is acceptable only if needed to establish an API fact; do not leave accidental production changes behind.

## Acceptance gate

Phase 00 is PASS only if all of the following are true:

- repository branch/HEAD/status are recorded;
- prior Ring/Wormhole work is located and preserved;
- at least the relevant build command is identified and tested if the environment permits;
- existing Ring/Wormhole baseline outcome is recorded or an exact blocker is documented;
- `docs/sumcheck_api_map.md` contains concrete repository-specific API mapping;
- `docs/sumcheck_reference_map.md` indexes the available bundle and discrepancies;
- Phase 1's expected file surface and exact first implementation step are known;
- `SUMCHECK_STATUS.md` is updated with commands, evidence, blockers/risks, and next action.

Do not mark Phase 01 unblocked if critical topology/routing APIs are still guesses.
