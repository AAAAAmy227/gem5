# Sumcheck NoC — Reference Bundle Map

> Phase 0 result: the named reference archive is not present in the WSL
> repository or the supplied Windows task-material directory. Values copied
> from `docs/sumcheck_spec.md` remain specification/static oracles only; they
> are not bundle-verified and are not measured gem5 results.

## Precedence

The active phase task controls local scope, then `docs/sumcheck_spec.md`, then
the actual APIs/behavior of this gem5 checkout. If a reference bundle is later
provided, it remains a design/logical/static oracle and does not override the
specification or current gem5 behavior.

## Bundle discovery

| Item | Value |
|---|---|
| `sumcheck_noc_reference_bundle.zip` found? | **NO** |
| Paths searched | Full `/root/gem5`; exact-name search under `/mnt/d/faq/清华/大二下暑/lab1作业材料` to depth 4 |
| Extracted to | N/A — nothing extracted and no repository files overwritten |
| Bundle hash | N/A |
| Fully inspected during Phase 0? | **NO — archive unavailable**, not skipped while present |

Exact discovery commands:

```bash
find /root/gem5 -type f -name "sumcheck_noc_reference_bundle.zip" -print
find "/mnt/d/faq/清华/大二下暑/lab1作业材料" -maxdepth 4 -type f   -name "sumcheck_noc_reference_bundle.zip" -print
```

Both produced no matching path.

## Expected reference files

These are the paths required by the project specification. Their intended use
is indexed now so a later phase can ingest only the relevant material if the
archive appears.

| Reference file | Role in project | Relevant phases | Phase-0 result |
|---|---|---|---|
| `sumcheck_noc_design_contract_v0.1.md` | Architecture, IDs, endpoint/aggregation boundary, routing/VC semantic contract | 01, 02, 03, 04 | UNAVAILABLE; specification is the only current source |
| `sumcheck_noc_reference/README.md` | Reference model usage, assumptions, commands, and interpretation | 00–04 | UNAVAILABLE |
| `sumcheck_noc_reference/sumcheck_noc.py` | Logical topology, deterministic/adaptive route enumeration, traces, and static calculations | 01, 02, 03 | UNAVAILABLE |
| `sumcheck_noc_reference/DEADLOCK_PROOF.md` | U/D CDG reasoning and collapsed-single-VC negative control | 02 | UNAVAILABLE |
| `sumcheck_noc_reference/EVALUATION_PLAN.md` | Baselines, placement/cost assumptions, metrics, and experiment intent | 04 | UNAVAILABLE |
| `sumcheck_noc_reference/outputs/` | Expected static JSON/JSONL/text oracles and cycle witnesses | 01–04 | UNAVAILABLE; no output filename can yet be cited |

## Static acceptance oracles currently available

Every value in this section comes from `docs/sumcheck_spec.md`, not from a
bundle file and not from a gem5 run.

### Topology size

| entries/cluster `p` | Routers | Undirected internal links | Phase-0 arithmetic check |
|---:|---:|---:|---|
| 1 | 69 | 104 | PASS: `4 * (24 + 1 + 1)` |
| 2 | 69 | 108 | PASS: `4 * (24 + 2 + 1)` |
| 4 | 69 | 116 | PASS: `4 * (24 + 4 + 1)` |

### Entry tables

| Case | Coordinates |
|---|---|
| p=1 | `(1,1)` |
| p=2 | `(0,1), (3,2)` |
| p=4 staggered | `(0,1), (1,3), (2,0), (3,2)` |
| p=4 corners | `(0,0), (0,3), (3,0), (3,3)` |

### Reference trace event counts

| Trace | Expected events | Phase-0 status |
|---|---:|---|
| Aggregated, p=1 | 2004 | NOT VERIFIED — trace unavailable |
| Aggregated, p=2 | 2004 | NOT VERIFIED — trace unavailable |
| Aggregated, p=4 | 2004 | NOT VERIFIED — trace unavailable |
| No aggregation | 1856 | NOT VERIFIED — trace unavailable |

### CDG enumeration

- Ordered source/destination pairs: `69 * 68 = 4692`.

| p | Expected legal routes | U/D separated | Collapsed single VC |
|---:|---:|---|---|
| 1 | 4692 | acyclic | may remain acyclic |
| 2 | 14548 | acyclic | must find a cycle |
| 4 | 52692 | acyclic | must find a cycle |

No CDG script or cycle witness is available in Phase 0. These rows are
unverified specification targets.

### Placement/path static oracle

| Variant | Mean PE→entry | Max distance | Max mesh-edge paths | Weighted flit-hop/cluster/round |
|---|---:|---:|---:|---:|
| p=1 | 2.00 | 4 | 8 | 370 |
| p=2 | 1.50 | 3 | 4 | 298 |
| p=4 staggered | 0.75 | 1 | 1 | 194 |
| p=4 corners | 1.00 | 2 | 2 | 234 |

Phase 0 independently recomputed the first three path columns from the
coordinate tables, deterministic smaller-index assignment, and strict
dim0-then-dim1 paths. All matched. Weighted flit-hop totals were not
recomputed because the reference implementation/output is absent.

### Full reference-trace static oracle

| Variant | Total flit-hops | Peak undirected-link flits |
|---|---:|---:|
| Mesh 8x8 best controller placement | 16208 | 632 |
| Hierarchy p=1 fixed | 22448 | 1016 |
| Hierarchy p=2 fixed | 18160 | 536 |
| Hierarchy p=4 fixed | 11952 | 256 |
| Hierarchy p=4 no aggregation | 26048 | 2368 |

These totals were not independently verified in Phase 0 because the trace and
reference path calculator are unavailable.

## Phase-specific reread map

If the archive is later added, first record its path/hash and inspect all
required files once. Later phases should then reopen only:

### Phase 01 — topology + fixed routing

- design-contract architecture/ID/entry/latency sections;
- deterministic route/path construction in `sumcheck_noc.py`;
- topology/path outputs.

Validate router/links, exact entries, real-link paths, nearest-entry
smaller-index tie-break, dim0→dim1 suffix, and static path/hop oracles.

### Phase 02 — adaptive + VC + CDG

- `DEADLOCK_PROOF.md`;
- legal-route/CDG enumeration in `sumcheck_noc.py`;
- legal-route counts and concrete collapsed-VC cycle witnesses in outputs.

The final checker must match the actual C++ routing relation and enforce the
same U/D VC allocator subsets.

### Phase 03 — causal workload

- trace generation/replay semantics in README and `sumcheck_noc.py`;
- every aggregated/no-aggregation JSONL trace/output.

Validate dependency IDs/order, exact 32/128-byte messages, arrival-triggered
successors, event counts, aggregation ejection/reinjection, and root-cut
traffic.

### Phase 04 — baselines + experiments

- `EVALUATION_PLAN.md`;
- cost, placement, and full-trace static outputs.

Use them for intent/static regressions only. Recompute actual gem5 ports, NIs,
ExtLinks, VCs, buffers, latency, and performance.

## Reference vs implementation discrepancy log

| Topic | Reference/spec assumption | Actual gem5/repo behavior | Resolution | Consequence |
|---|---|---|---|---|
| Bundle availability | Named archive and six artifact groups may be present | Archive is absent from both searched workspace locations | Keep all bundle-derived checks explicitly unverified; ingest if later supplied | Does not block Phase 1 API work, but blocks direct provenance of trace/CDG/full-hop oracles |
| 69 logical endpoints | 64 worker + 4 gateway controller + 1 root controller, normally one endpoint/NI/ExtLink each | Garnet standalone creates L1 plus Directory controllers and sends only L1→Directory traffic | Phase-1 smoke may use a documented 65-L1+4-directory mapping; Phase 3 needs a custom symmetric controller path | Smoke endpoint types are not aggregation semantics |
| Packet sizes | Reference uses exact 32 B and 128 B messages with 16 B flits | Current `MessageSizeType_to_int` produces 8 B control or normally 72 B data | Add scoped exact-byte message support before workload replay | Current synthetic traffic cannot validate reference flit counts |
| Packet-arrival dependency | Successor injects after predecessor arrives | Synthetic tester receives an immediate Ruby callback before network delivery | Complete dependencies at destination NI enqueue/custom controller consumption | Existing tester callback cannot be used for causal replay |
| Link/cost outputs | Reference may contain simplified static hardware counts | Current gem5 materializes directed links, ExtLinks, one NI per ExtLink, local ports, VCs and buffers | Recompute from `config.ini`/constructed objects | Never reuse simplified “288 input ports” as measured cost |
| p=2 max mesh-edge paths | Corrected specification value is 4 | Phase-0 independent dim0→dim1 calculation also gives 4 | Treat 4 as canonical | No discrepancy with current spec; do not “improve” it to 3 by adding forbidden XY/YX adaptivity |
| Performance numbers | Reference outputs are static path/traffic results | gem5 cycle/latency/throughput depend on actual simulation | Label separately and measure in gem5 | No static value is a Phase-0 measured Sumcheck result |

## Reference validation log

| Check | Command/script | Result | Output/evidence |
|---|---|---|---|
| Bundle contents inspected | exact-name `find` commands above | BLOCKED | No archive path returned |
| p=1/2/4 topology counts and PE→entry distance | Inline `python3 -c` over the four coordinate tables | PASS | p1 `69/104/2.00/4`; p2 `69/108/1.50/3`; p4 staggered `69/116/0.75/1`; corners `69/116/1.00/2` |
| Strict dim0→dim1 maximum mesh-edge path load | Inline `python3 -c` using `collections.Counter` | PASS | p1=8, p2=4, p4 staggered=1, p4 corners=2 |
| Weighted path/full-trace oracle | Expected reference implementation/output | NOT RUN | Bundle unavailable |
| CDG oracle and single-VC witness | Expected `sumcheck_noc.py` / `DEADLOCK_PROOF.md` / outputs | NOT RUN | Bundle unavailable |
| Aggregated/no-aggregation trace counts/dependencies | Expected JSONL/output artifacts | NOT RUN | Bundle unavailable |

## Phase-0 completion assessment

The available reference source is fully indexed: only the canonical project
specification exists. Bundle-specific checks are explicitly blocked rather
than silently claimed. Phase 1 may proceed using the specification and the
repository-specific API map; it must not claim bundle-derived trace, CDG, or
full-hop validation unless the archive is later provided and inspected.
