# Phase 01 — SumcheckHierarchy Topology + Deterministic Routing

## Goal

Implement and validate the new hierarchical topology and the fixed deterministic routing baseline. End with a deterministic gem5 smoke test and preserved prior regressions.

## Prerequisite

`SUMCHECK_STATUS.md` must show Phase 00 PASS (or explicitly document why a missing non-critical item does not block Phase 1).

## Read first

1. `AGENTS.md`
2. `SUMCHECK_STATUS.md`
3. `docs/sumcheck_api_map.md`
4. `docs/sumcheck_reference_map.md`
5. `docs/sumcheck_spec.md`, especially Architecture, Deterministic routing, implementation-location, tests, and execution-order sections
6. Phase-1 reference files identified in `docs/sumcheck_reference_map.md`

## Required implementation

### 1. Centralized topology/mapping model

Implement the spec's logical mapping without scattering magic numbers:

- 64 worker routers, IDs 0..63;
- G0..G3, IDs 64..67;
- root R, ID 68;
- 4 clusters, 4x4 worker mesh each;
- worker ID mapping `cluster * 16 + row * 4 + col`;
- entry placements for p=1,2,4 and p=4 corners ablation;
- stable port naming independent of Python dictionary traversal order.

If Python/C++ cannot share one mapping directly, provide an explicit consistency test/generation path.

### 2. `SumcheckHierarchy` topology

Support the actual repository equivalents of:

- `--entries-per-cluster=1|2|4`
- `--entry-placement=staggered|corners`
- gateway-entry link latency sensitivity
- root-gateway link latency sensitivity

Build:

- all 4x4 cluster mesh links;
- p entry↔gateway direct links per cluster;
- one gateway↔root link per cluster;
- worker endpoints plus controller/root logical endpoint mapping as far as the current framework permits.

Do not silently ignore endpoint co-location or port competition if a workaround is required; document it in the API map/status.

### 3. Deterministic routing

Implement the complete fixed routing relation for all legal source/destination roles:

- same-cluster worker→worker: dim0 then dim1;
- worker→assigned entry: dim0 then dim1;
- entry→gateway: direct;
- gateway→root: direct;
- root→gateway: direct;
- gateway→worker: choose nearest legal entry, fixed smaller-entry-index tie-break, then direct gateway→entry and fixed dim0→dim1 inside mesh;
- cross-cluster generic traffic: source side→gateway→root→destination gateway→destination mesh;
- unsupported/illegal cases must assert/fatal rather than silently selecting an arbitrary port.

Do not implement adaptive entry selection yet.

### 4. Tests

Add automated tests for at least:

- p=1/2/4 router counts and undirected internal-link counts: 104/108/116 with 69 routers;
- exact entry coordinates for all supported placements;
- every generated route uses real physical links;
- deterministic nearest-entry selection and smaller-index tie-break;
- entering a mesh produces strict dim0→dim1 routing;
- mapping consistency between topology construction and C++ routing assumptions if they are separate.

Where useful, validate static path construction against the reference oracles before injecting traffic into gem5.

### 5. Deterministic smoke

Build and run the smallest meaningful gem5 smoke that exercises the topology and fixed routing. Verify injected/received equality if the test exposes those counters.

Also rerun the relevant existing Ring/Wormhole regression commands established in Phase 00.

## Explicitly out of scope

Do not start:

- credit-aware entry choice;
- round-robin adaptive tie arbitration;
- VC_U/VC_D allocator enforcement;
- CDG proof implementation changes beyond any Phase-1-independent checker scaffolding already present;
- causal Sumcheck endpoint workload;
- Mesh baseline or performance sweeps.

## Acceptance gate

Phase 01 is PASS only when:

- topology count tests pass for p=1/2/4;
- all entry placement tests pass;
- route-physical-link validation passes;
- deterministic nearest-entry/tie-break tests pass;
- deterministic route suffix is strict dim0→dim1;
- the relevant gem5 binary builds;
- deterministic smoke completes successfully;
- prior Ring/Wormhole regressions are still passing, or any pre-existing unrelated failure is demonstrated and documented;
- `SUMCHECK_STATUS.md` contains exact commands, outputs, changed files, unresolved risks, and the Phase-2 next action.
