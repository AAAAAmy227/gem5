# Sumcheck NoC substantive-requirement audit

Classification is against `docs/sumcheck_spec.md` and the actual gem5 23.0.0.1
execution path, not filenames or comments. Evidence was refreshed in Phase 05.

| Area / requirement | Classification | Evidence or precise gap |
|---|---|---|
| New 69-router hierarchy topology | IMPLEMENTED + TESTED | `SumcheckHierarchy.py`; topology 8/8; fresh p1/p2/p4 smokes |
| Fixed IDs workers 0..63, G0..G3 64..67, R=68 | IMPLEMENTED + TESTED | `SumcheckConfig.py/.hh`; generated-header equality test |
| Central mapping rather than scattered magic numbers | IMPLEMENTED + TESTED | Python canonical model generates C++ header; equality is tested |
| 64 workers + four gateway controllers + root controller as endpoints | IMPLEMENTED + TESTED | causal harness has exact 69 controllers/NIs/ExtLinks; config/result audit |
| Aggregation at endpoint, not router | IMPLEMENTED + TESTED | NI sends free credit before callback; successor injects next clock; Phase03 10/10 |
| p1/p2/p4 router and internal-link counts | IMPLEMENTED + TESTED | 69 routers; 104/108/116 undirected links; exhaustive topology tests |
| Exact staggered/corners entry coordinates | IMPLEMENTED + TESTED | four tables checked exactly; invalid p2 corners rejected |
| Stable unique direction names | IMPLEMENTED + TESTED | exhaustive per-router port uniqueness test |
| Gateway-entry/root-gateway latency knobs 1/2/4 | IMPLEMENTED + NOT FULLY TESTED | knobs construct links; prior single-packet sensitivities exist, but no Phase04 performance sensitivity |
| 32-byte fields and 128-byte partials | IMPLEMENTED + TESTED | optional exact message bytes; trace and flit/accounting tests |
| Phase A 14 rounds, A-B boundary, Phase B four rounds, B-C boundary, Phase C two local rounds | IMPLEMENTED + TESTED | trace builder, 2004-event runs, `phase_c_local_rounds=2` |
| Phase-A entry/gateway/root aggregation sequence | IMPLEMENTED + TESTED | dependency graph kinds and arrival gating; causal smokes |
| Separate gateway-to-worker unicast challenges | IMPLEMENTED + TESTED | 64 challenge events per round; trace-count/root-cut tests |
| Successor injects only after actual destination arrival | IMPLEMENTED + TESTED | NI enqueue callback -> `notifyArrival()` -> dependency decrement; host and gem5 tests |
| Aggregated p1/p2/p4 event count 2004 | IMPLEMENTED + TESTED | workload oracle and Phase03 tests |
| No-aggregation trace 1856 events | IMPLEMENTED + TESTED | workload oracle and fresh smoke |
| No-aggregation 16x root-cut difference at 16-byte flits | IMPLEMENTED + TESTED | static root-cut test gives 8/2 versus 128/32 |
| Same-cluster strict dim0-then-dim1 | IMPLEMENTED + TESTED | all ordered routes and all legal CDG routes checked |
| Worker uses assigned nearest entry with smaller-index tie | IMPLEMENTED + TESTED | exhaustive Python relation, generated C++ helper, gem5 smokes |
| Entry-to-gateway and gateway/root direct routing | IMPLEMENTED + TESTED | physical-route enumeration and smokes |
| Destination gateway fixed nearest/tie behavior | IMPLEMENTED + TESTED | exhaustive gateway-to-worker tests |
| Cross-cluster traffic passes through root | IMPLEMENTED + TESTED | exhaustive routes and two-direction synthetic smoke |
| Unsupported routing cases fatal/assert | IMPLEMENTED + TESTED | C++ `fatal` paths inspected; invalid configuration tests; not every fatal path injected live |
| Adaptive freedom only at destination gateway entry choice | IMPLEMENTED + TESTED | `outportComputeSumcheck()` execution path; CDG exact relation |
| Specified credit score with configurable lambda=4 | IMPLEMENTED + TESTED | Python/C++ synthetic-credit tests and live instrumentation |
| Credit state reads legal downstream VC_D only | IMPLEMENTED + TESTED | `OutputUnit::free_credits(...Down)` offsets 2/3; source inspection test and live candidate counters |
| Credit/arbitration-state-dependent non-deterministic relation | IMPLEMENTED + TESTED | fresh adaptive smoke: 328/896 non-nearest, 108 ties, all entries used; fixed mode remains 0 reroutes |
| Minimum score and rotating per-gateway tie pointer | IMPLEMENTED + TESTED | Python and compiled C++ helper tests |
| Head outport stable while blocked | IMPLEMENTED + TESTED | InputUnit route compute once/head and stores outport; allocator never recomputes; code-path test |
| No mesh adaptivity/wandering/backtracking/reselection | IMPLEMENTED + TESTED | strict route enumeration and C++ control-flow audit |
| Entry/credit/tie/reroute instrumentation | IMPLEMENTED + TESTED | named Garnet stats parsed into JSON; fresh nonzero adaptive evidence |
| Root/gateway-entry and all-link flit instrumentation | IMPLEMENTED + TESTED | tracked/all-link stats; collector reports cut utilization/max link load |
| Four VCs/vnet minimum | IMPLEMENTED + TESTED | Python and C++ startup guards; partition tests |
| Offsets 0/1 U and 2/3 D within each vnet | IMPLEMENTED + TESTED | generated constants; NI/allocator/output-unit path |
| Initial NI VC allocation respects U/D | IMPLEMENTED + TESTED | `calculateVC(route)` subset search; static path test and live U/D allocations |
| Real output-VC check and allocation use same subset | IMPLEMENTED + TESTED | `send_allowed()` and `vc_allocate()` share `requiredVcClass`; Phase02 tests |
| U-to-D only at root | IMPLEMENTED + TESTED | allocator fatal guard; exact and superset route enumeration |
| D-to-U never | IMPLEMENTED + TESTED | allocator fatal guard; exact and superset route enumeration |
| Live negative test that intentionally forces a wrong-class out-VC | IMPLEMENTED + NOT FULLY TESTED | enforcement/assertions exist and normal runs exercise both classes; no corruption/fault-injection simulation |
| CDG covers all 69x68 ordered pairs | IMPLEMENTED + TESTED | 4692 pairs for every p |
| CDG exactly matches C++ fixed/adaptive relation | IMPLEMENTED + TESTED | Phase05 exact relation counts 4692 fixed and 4692/8084/14868 adaptive; asserted subset of spec relation |
| Specification CDG counts 4692/14548/52692 | IMPLEMENTED + TESTED | separately labeled conservative source/destination-entry superset |
| p1/p2/p4 separated CDG acyclic | IMPLEMENTED + TESTED | exact and conservative graphs both acyclic |
| p2/p4 collapsed-single-VC cycle witnesses | IMPLEMENTED + TESTED | exact and conservative witnesses in Phase05 CDG JSON |
| Ruby/message-class dependency limitation documented | IMPLEMENTED + TESTED | deadlock document explicitly scopes claim; audit is documentary, not a protocol proof |
| Stable IDs and missing/forward dependency rejection | IMPLEMENTED + TESTED | Phase03 tests and C++ pre-simulation validation |
| Watchdog reports useful stuck logical state | PARTIAL | reports injected/received and up to eight pending events; cannot name router/input VC/waited output resource |
| Workload completion and per-round completion | IMPLEMENTED + TESTED | reports completion cycle/tick and round completion ticks |
| Packets/flits injected equal received | IMPLEMENTED + TESTED | runners, collector, and Phase05 evidence audit enforce equality |
| Same seed/config reproducibility | IMPLEMENTED + TESTED | fresh byte-identical trace/report repeat with recorded SHA-256 |
| Mesh quadrant/controller placement with real contention | IMPLEMENTED + TESTED | 64 routers, 69 ExtLinks/NIs, placement tests/config costs |
| Mesh preserves same logical workload/packet sizes | IMPLEMENTED + TESTED | identical aggregated event generator; fresh 2004/10224 accounting |
| Required eight variants exist | IMPLEMENTED + TESTED | Phase04 runner and fresh Phase05 8/8 smoke |
| Primary equal-clock/link/flit/vnet/VC/depth comparison | IMPLEMENTED + TESTED | per-run configuration metadata and cost audit |
| Actual topology/cost accounting from config.ini | IMPLEMENTED + TESTED | collector reports routers, links, ports, VCs, slots/bits, radix proxies |
| Exact total-buffer-slot match | NOT APPLICABLE due to an explicitly documented repository/API constraint | only global integer depths; 6020 lower and 7224 upper bracket around Mesh 7032 |
| Buffer bracket labeled accurately | IMPLEMENTED + TESTED | `lower_buffer_bracket_not_exact` in reports and docs |
| Causal, uniform-random, and skewed/bursty traffic | IMPLEMENTED + TESTED | causal 8-variant smoke and 40-point representative sweep |
| At least five seeds per formal executed point | IMPLEMENTED + TESTED | representative p4 fixed/adaptive cells use seeds 1..5 |
| Five causal seeds for every ablation | PARTIAL | only one-seed causal smokes; prepared full matrix unrun |
| Broad nine-load saturation sweep | PARTIAL | only loads 0.01 and 0.08 executed; precise saturation unavailable |
| Long-link latency sensitivity results | IMPLEMENTED + NOT FULLY TESTED | knobs exist; no Phase04 measured sensitivity table |
| Mean/P95/P99 latency, completion, throughput, hops | IMPLEMENTED + TESTED | workload/Garnet reports and collector |
| Root/gateway-entry utilization, max-link load, entry distribution, reroute rate | IMPLEMENTED + TESTED | collected JSON from raw stats |
| Buffer/VC allocator stall counters | NOT APPLICABLE due to an explicitly documented repository/API constraint | this Garnet revision has no allocator reason counters; endpoint stall time retained |
| Failed/timeout runs explicitly retained/marked | PARTIAL | accepted sets are empty and two overwritten development preflights are disclosed; original failed raw logs were overwritten |
| Static/reference results separate from gem5 measurements | IMPLEMENTED + TESTED | oracle says `static_not_gem5`; evidence audit enforces label |
| Static hierarchy flit-hop/peak-link oracles | IMPLEMENTED + TESTED | p1 22448/1016, p2 18160/536, p4 11952/256, no-agg 26048/2368 |
| Mesh static oracle 16208/632 | PARTIAL | strict XY yields 15824/624; discrepancy and reason explicit, implementation is not distorted to match |
| Reference bundle inspection | NOT APPLICABLE due to an explicitly documented repository/API constraint | archive absent from repository and supplied task-material path |
| Reproducible smoke/sweep/full-matrix scripts | IMPLEMENTED + TESTED | smoke/sweep executed; full matrix is resumable but unrun |
| Ring regression preserved | IMPLEMENTED + TESTED | fresh 1/1 packet, average hops 8 |
| Wormhole regression preserved on current branch | NOT APPLICABLE due to an explicitly documented repository/API constraint | implementation is branch-separated; current parser rejects `--wormhole`, exit 2 |
| Required architecture/deadlock/evaluation/final-status documents | IMPLEMENTED + TESTED | Phase05 docs plus final cleanliness/link audit |

## Audit conclusion

The implementation and its bounded evidence support the course-project claims:
a new topology, fixed and live credit-aware adaptive routing, real U/D VC
enforcement, internal-channel CDG proof, causal endpoint aggregation, required
baselines, and reproducible measured results. Remaining partial items are
experiment breadth, detailed stuck-resource diagnostics, original logs for two
development-only preflight failures, and a deliberately strict-XY Mesh static
discrepancy. None is silently promoted to completed measured evidence.
