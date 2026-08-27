# Sumcheck NoC — Phase 02 Handoff

## Current phase/status
- Phase 01 (`01_topology_fixed`): **PASS / complete**; Phase 02 (`02_adaptive_vc_cdg`): **READY, not started**.
- Worktree: `/root/gem5` (WSL Ubuntu); Phase 01 implementation is unstaged, uncommitted, and not pushed.

## Git baseline
- Branch: `sumcheck`; HEAD: `c644910f321ec672151058db663e026de68afd9d` (ahead of `origin/sumcheck` by 2 documentation commits).
- Last known-good committed network baseline/upstream: `86686aa3b4e015fc961c9f41e27af4e2dfef8096`.

## Phase 01 completed functionality
- 69-router hierarchy: workers `0..63`, gateways `64..67`, root `68`; four 4x4 worker meshes.
- Entry configurations: p1/p2/p4 staggered and p4 corners; stable bidirectional port names; configurable gateway-entry/root-gateway latencies in `{1,2,4}`.
- Routing algorithm 3 implements fatal-on-invalid deterministic Sumcheck routing: nearest legal source entry with smaller-index tie-break, hierarchical traversal, then strict dim0→dim1 mesh suffix.
- Routing algorithm 2 Ring behavior is preserved.

## Durable Phase 02 implementation/API facts
- Canonical topology/config mapping: `configs/topologies/SumcheckConfig.py`; generated C++ mirror: `src/mem/ruby/network/garnet/SumcheckConfig.hh`; generation equality is tested.
- Topology: `configs/topologies/SumcheckHierarchy.py`; fixed routing entry point: `RoutingUnit::outportComputeSumcheck()`.
- Phase 01 smoke endpoint map is temporary: 64 L1s + 8 Directories, 72 ExtLinks; extra Directories are co-located at root and affect NI/buffer/arbitration costs.
- No Phase 01 edits touched `InputUnit`, `OutputUnit`, `SwitchAllocator`, or `NetworkInterface`; Phase 02 must synchronize the Python route/checker model with the C++ routing relation.
- Credit/allocator API notes: `docs/sumcheck_api_map.md`; Phase 02 task: `tasks/02_adaptive_vc_cdg.md`.

## Known-good evidence
- Static suite: `tests/pyunit/pyunit_sumcheck_topology.py` — 8 PASS, including all 18,768 ordered-route checks and generated-header consistency.
- Build: `build/NULL/gem5.debug` (`Garnet_standalone`) — PASS.
- Sumcheck smokes: `m5out/sumcheck_phase01/` — five variants PASS, each 1 injected = 1 received; deterministic main cases average 4 and 3 hops.
- Ring regression: `m5out/sumcheck_phase01/ring_single_packet/` — PASS, 1/1, average 8 hops.
- Reproduction script: `scripts/run_sumcheck_smoke.sh`; full Phase 01 record: `docs/history/phase01_status_full.md`.

## Unresolved risks/blockers
- Deadlock freedom is unproven: VC_U/VC_D allocation enforcement, adaptive credit-aware selection, and CDG verification are not implemented.
- Wormhole support is only on branch `wormhole`, commit `61eb8c18beeb013d5d3c320cfa0014bed2809d19`; current branch rejects `--wormhole`, and its allocator/NI overlap must be reviewed before edits.
- Reference bundle is unavailable; reference trace/CDG/flit-hop provenance cannot yet be validated.
- Temporary asymmetric endpoint harness and fixed-cycle synthetic termination are not suitable for Phase 03 causal measurements.

## Exact next action
- Read `tasks/02_adaptive_vc_cdg.md`, then diff Wormhole commit `61eb8c1` against current `OutputUnit`/`SwitchAllocator`/`NetworkInterface` APIs before implementing credit-aware entry choice and strict VC_U/VC_D allocation.
