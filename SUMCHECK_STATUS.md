# Sumcheck NoC — Persistent Project Status

> Cross-session external memory. Read this file before acting.

## Current state

- **Current phase:** `00_recon`
- **Phase status:** **PASS**
- **Last known-good commit:** `86686aa3b4e015fc961c9f41e27af4e2dfef8096`
  for the current-branch build, ordinary Mesh smoke, and Lab3 Ring smoke.
  Wormhole has a separate last commit, `61eb8c18beeb013d5d3c320cfa0014bed2809d19`,
  which is not an ancestor of the current `sumcheck` HEAD.
- **Latest Sumcheck checkpoint commit:** `9804d7f938fdea70ca0b5f7f4e16eb9d2d026e4f`
  (`sumcheck: document phase 00 reconnaissance`).
- **Checkpoint state:** **COMMITTED LOCALLY; NOT PUSHED** — authorized
  documentation-only Phase-0 checkpoint.
- **Current HEAD after the Phase-0 evidence checkpoint:**
  `9804d7f938fdea70ca0b5f7f4e16eb9d2d026e4f`.
- **Current branch:** `sumcheck`
- **Upstream branch:** `origin/sumcheck`; HEAD matched upstream at run start.
- **Git remote(s):**
  - `origin git@github.com:AAAAAmy227/gem5.git` (fetch/push)
  - `upstream https://github.com/gem5/gem5.git` (fetch/push)
- **Worktree/repository path:** `/root/gem5` (WSL Ubuntu)
- **Working tree state at entry:** no staged/unstaged tracked changes; untracked
  `AGENTS.md`, `CODEX_START_HERE.md`, `SUMCHECK_STATUS.md`, `docs/`,
  and `tasks/`.
- **Working tree state at finish:** still no staged/unstaged tracked changes.
  Exact untracked files are listed under “Git / worktree state”.
- **gem5 revision/version:** gem5 `23.0.0.1`, Git describe
  `v23.0.0.1-8-g86686aa` before documentation edits; Garnet `3.0`.
- **Primary build target/config:** `build/NULL/gem5.debug`,
  `PROTOCOL='Garnet_standalone'`, `USE_NULL_ISA=True`.
- **Reference bundle found:** **NO** — searched the full WSL repository and the
  supplied Windows task-material directory.
- **Phase 01 authorization:** not part of this run. It was not started.

`Phase status` and `Checkpoint state` are separate. Phase 0 passes because
all repository-specific APIs and the baseline/blockers are now concrete; its
documentation is committed locally and its network-code baseline remains the
separately tested commit listed above.

## Phase tracker

| Phase | Scope | Status | Checkpoint commit | Acceptance evidence |
|---|---|---|---|---|
| 00 | Repository/API/reference reconnaissance | **PASS** | `9804d7f` (local only) | `docs/sumcheck_api_map.md`; `docs/sumcheck_reference_map.md`; build and smoke outputs under `m5out/sumcheck_recon/` |
| 01 | Topology + deterministic routing | NOT STARTED | — | API no longer guessed; exact first step recorded below |
| 02 | Adaptive routing + VC discipline + CDG | BLOCKED ON 01 | — | Output credit/allocation APIs mapped; no implementation |
| 03 | Causal Sumcheck workload + aggregation | BLOCKED ON 02 | — | NI arrival boundary and workload mismatch mapped; no implementation |
| 04 | Baselines + experiments | BLOCKED ON 03 | — | Existing/missing stats hooks mapped; no experiments |
| 05 | Final regression + evidence audit | BLOCKED ON 04 | — | — |

## Phase-0 completion table

| Step | Completed | Missing / blocked | Evidence |
|---|---|---|---|
| Repository identity and worktree safety | Yes | Nothing critical | branch/HEAD/remotes/status commands below |
| Locate and preserve Lab3 Ring | Yes | No dedicated pre-existing unit test | commit `3776811c...`; `Ring.py`; passing current-branch smoke |
| Locate and preserve Lab3 Wormhole | Yes, as a separate branch/commit | Cannot run on current branch without an unauthorized integration/switch | branch `wormhole`, commit `61eb8c1...`; current parser probe exits 2 |
| Establish relevant build | Yes | Optional PNG/HDF5 libraries absent, irrelevant to NoC | `scons build/NULL/gem5.debug -j16` exit 0 |
| Establish network and Ring smoke | Yes | Fixed-cycle tester lacks drain; use bounded packet count | two single-packet runs each report 1 injected = 1 received |
| Inspect topology/routing/credit/VC/NI/stats/build APIs | Yes | No critical Phase-1 API guess remains | concrete file/function table in `docs/sumcheck_api_map.md` |
| Inspect/index reference bundle | Indexed expected files and searched | Archive unavailable, so trace/CDG/full-hop artifacts cannot be verified | `docs/sumcheck_reference_map.md` |
| Recompute locally available static placement facts | Yes | Weighted/full-trace/CDG/trace counts need missing bundle or later checker | inline Python outputs match topology size, distances and max edge paths |
| Decide Phase-1 file surface/first action | Yes | Actual implementation intentionally not begun | final sections of API map and Exact next action |

## Git / checkpoint ledger

| Checkpoint | Phase | Commit | Local/remote state | Tests supporting checkpoint | Notes |
|---|---|---|---|---|---|
| Initial current-branch baseline | pre-Sumcheck | `86686aa3b4e015fc961c9f41e27af4e2dfef8096` | local = `origin/sumcheck` at entry | current build PASS; Mesh single-packet PASS; Ring single-packet PASS | Known-good only for current build/Mesh/Ring scope |
| Lab3 Ring historical checkpoint | pre-Sumcheck | `3776811c288ed9d1f08caa04a8fa8975b106f7f5` | ancestor of current branch | current Ring smoke PASS | Adds `Ring.py` and custom routing algorithm 2 |
| Lab3 Wormhole historical checkpoint | pre-Sumcheck | `61eb8c18beeb013d5d3c320cfa0014bed2809d19` | `wormhole` / `origin/wormhole`, not current branch | historical ignored results exist; current-branch run blocked | Must not be overwritten when allocator/NI code changes later |
| Phase 00 | 00 | `9804d7f938fdea70ca0b5f7f4e16eb9d2d026e4f` | committed locally; not pushed | recon/build/baselines recorded here | Documentation-only checkpoint; no Phase-1 code |
| Phase 01 | 01 | — | — | — | Not started |
| Phase 02 | 02 | — | — | — | — |
| Phase 03 | 03 | — | — | — | — |
| Phase 04 | 04 | — | — | — | — |
| Phase 05 | 05 | — | — | — | — |

## Known pre-existing work that must be preserved

### Lab3 Ring — current branch

- Commit: `3776811c288ed9d1f08caa04a8fa8975b106f7f5`.
- Files:
  - `configs/topologies/Ring.py`
  - `src/mem/ruby/network/garnet/RoutingUnit.cc`
- Interface: `--topology=Ring --mesh-rows=1 --routing-algorithm=2`.
- Critical collision: algorithm value 2 and
  `RoutingUnit::outportComputeCustom()` belong to Ring. Sumcheck must use a
  distinct routing enum/value and retain Ring behavior.
- Baseline evidence:
  `m5out/sumcheck_recon/ring_single_packet/{stats.txt,config.ini}`.

### Lab3 Wormhole — separate branch

- Branches: `wormhole`, `origin/wormhole`.
- Commit: `61eb8c18beeb013d5d3c320cfa0014bed2809d19`.
- Modified files:
  - `.gitignore`
  - `configs/network/Network.py`
  - `src/mem/ruby/network/garnet/GarnetNetwork.cc`
  - `src/mem/ruby/network/garnet/GarnetNetwork.hh`
  - `src/mem/ruby/network/garnet/GarnetNetwork.py`
  - `src/mem/ruby/network/garnet/InputUnit.cc`
  - `src/mem/ruby/network/garnet/InputUnit.hh`
  - `src/mem/ruby/network/garnet/NetworkInterface.cc`
  - `src/mem/ruby/network/garnet/OutputUnit.cc`
  - `src/mem/ruby/network/garnet/OutputUnit.hh`
  - `src/mem/ruby/network/garnet/SwitchAllocator.cc`
  - `src/mem/ruby/network/garnet/VirtualChannel.hh`
- Ignored support/evidence still present:
  `labs/Lab3.md`, `labs/lab3_task2_experiments.py`,
  `labs/Lab3_Task2_Report.tex`, and `lab3_results/task2/`.
- Current-branch exact blocker: `--wormhole` is unrecognized (exit 2).
- Critical collision: Phase 2 is expected to edit `OutputUnit`,
  `SwitchAllocator`, `NetworkInterface`, and possibly route/VC state—the
  same surface as Wormhole. Review/integrate explicitly; never replace its
  semantics accidentally.

## Last known-good regression baseline

| Regression / build | Command | Result | Evidence / notes |
|---|---|---|---|
| Existing build | `scons build/NULL/gem5.debug -j16` | **PASS**, exit 0 | Current `sumcheck` sources rebuilt. Optional PNG/HDF5 warnings only. |
| Existing Mesh network smoke | `./build/NULL/gem5.debug --outdir=m5out/sumcheck_recon/mesh_single_packet configs/example/garnet_synth_traffic.py --network=garnet --num-cpus=16 --num-dirs=16 --topology=Mesh_XY --mesh-rows=4 --routing-algorithm=1 --inj-vnet=0 --synthetic=uniform_random --sim-cycles=500 --injectionrate=1.0 --num-packets-max=1 --single-sender-id=0 --single-dest-id=15` | **PASS**, exit 0 | packets/flits `1 injected == 1 received`; average hops 6; latency 17 ticks/cycles at this configured clock |
| Existing Ring regression | `./build/NULL/gem5.debug --outdir=m5out/sumcheck_recon/ring_single_packet configs/example/garnet_synth_traffic.py --network=garnet --num-cpus=16 --num-dirs=16 --topology=Ring --mesh-rows=1 --routing-algorithm=2 --inj-vnet=0 --synthetic=uniform_random --sim-cycles=500 --injectionrate=1.0 --num-packets-max=1 --single-sender-id=0 --single-dest-id=8` | **PASS**, exit 0 | packets/flits `1 == 1`; average hops 8; latency 21 |
| Fixed-duration Mesh | same Mesh config, `--sim-cycles=2000 --injectionrate=0.01`, no bounded packet count | PASS process, **not drained** | `146 injected / 145 received`; output `m5out/sumcheck_recon/mesh_smoke/` |
| Fixed-duration Ring | same Ring config, `--sim-cycles=2000 --injectionrate=0.01`, no bounded packet count | PASS process, **not drained** | `146 injected / 145 received`; output `m5out/sumcheck_recon/ring_smoke/` |
| Existing Wormhole regression | single-packet Mesh command plus `--vcs-per-vnet=16 --wormhole` | **BLOCKED**, parser exit 2 | `unrecognized arguments: --wormhole`; implementation is only on separate commit `61eb8c1` |
| Relevant Python syntax | `python3 -m py_compile configs/topologies/Ring.py configs/network/Network.py configs/example/garnet_synth_traffic.py labs/lab3_task2_experiments.py` | **PASS**, exit 0 | No existing Sumcheck/Ring/Wormhole Python unit suite |
| Generic repository pyunit | `cd tests && ../build/NULL/gem5.debug run_pyunit.py` | **INCOMPLETE / unrelated errors** | Numerous stdlib/resource errors; later resource test stopped progressing; manually interrupted. Not used as NoC evidence. |

## Phase acceptance ledger

Do not reinterpret baseline smoke results as Sumcheck implementation evidence.

| Requirement | Status | Evidence |
|---|---|---|
| p=1/2/4 router and link counts | STATIC SPEC CHECK ONLY | Arithmetic independently gives 69 routers and 104/108/116 links; no topology implemented |
| entry coordinate tables | STATIC SPEC CHECK ONLY | Local coordinate calculation matches p1/p2/p4 staggered/corners |
| generated routes use real physical links | NOT RUN | Phase 01 |
| deterministic nearest-entry + fixed tie-break | NOT RUN | Phase 01 |
| deterministic smoke completes | NOT RUN | Phase 01; only existing Mesh/Ring smokes ran |
| adaptive changes entry under synthetic credit state | NOT RUN | Phase 02 |
| equal-score rotating tie arbitration | NOT RUN | Phase 02 |
| adaptive chooses only legal cluster entries | NOT RUN | Phase 02 |
| mesh suffix strictly dim0-then-dim1 | STATIC SPEC CHECK ONLY | Local placement path calculation used dim0→dim1; no C++ route |
| route classes are U*, D*, or U*D* | NOT RUN | Phase 02 |
| U→D only at root | NOT RUN | Phase 02 |
| no D→U | NOT RUN | Phase 02 |
| output VC allocation never crosses U/D partition | NOT RUN | Phase 02 |
| p=1/2/4 U/D CDG acyclic | NOT RUN | Reference archive/checker absent; Phase 02 |
| p=2/4 collapsed single-VC cycle witness | NOT RUN | Reference archive/checker absent; Phase 02 |
| trace dependencies have no missing/forward dependency | NOT RUN | Reference archive/traces absent; Phase 03 |
| aggregated trace event count = 2004 | NOT RUN | Reference archive/traces absent; Phase 03 |
| no-aggregation trace event count = 1856 | NOT RUN | Reference archive/traces absent; Phase 03 |
| no-aggregation root-cut traffic matches spec | NOT RUN | Phase 03 |
| small Sumcheck smoke injected == received | NOT RUN | Existing Mesh/Ring single-packet baselines both satisfy 1==1 |
| same seed/config reproducible | NOT RUN | Phase 03/04 |
| Ring regression preserved | **PASS** | current-branch single-packet Ring smoke |
| Wormhole regression preserved | **BLOCKED / PRE-EXISTING BRANCH SEPARATION** | exact current parser failure plus preserved branch/commit; no current-branch implementation to run |

## Files changed in current phase

Only Phase-0 documentation:

- `docs/sumcheck_api_map.md` — concrete repository/API/build/test mapping and
  Phase-1 surface.
- `docs/sumcheck_reference_map.md` — bundle absence, static-oracle provenance,
  validation/discrepancy/reread map.
- `SUMCHECK_STATUS.md` — this evidence and handoff.

No topology, deterministic/adaptive routing, VC allocator, workload,
experiment, or Garnet production source was implemented or modified.

Generated/ignored evidence under `build/` and `m5out/sumcheck_recon/` was
created by the documented build/smokes and is not tracked.

## Git / worktree state

Final `git status --short --untracked-files=all`:

```text
?? AGENTS.md
?? CODEX_START_HERE.md
?? SUMCHECK_STATUS.md
?? docs/sumcheck_api_map.md
?? docs/sumcheck_reference_map.md
?? docs/sumcheck_spec.md
?? tasks/00_recon.md
?? tasks/01_topology_fixed.md
?? tasks/02_adaptive_vc_cdg.md
?? tasks/03_causal_workload.md
?? tasks/04_baselines_experiments.md
?? tasks/05_final_review.md
```

`git diff --stat` and `git diff --check` are empty because every Phase-0
project document was already untracked at entry. Nothing is staged.

## Exact command log

Only commands actually executed are recorded. Read-only source inspection used
`sed`, `nl`, `grep`, `find`, and `git show` on the exact paths named in
the API map.

### Repository/Git/reference discovery

```bash
cd ~/gem5
pwd
git branch --show-current
git rev-parse HEAD
git status --short
git status --branch --short
git remote -v
git rev-parse --abbrev-ref --symbolic-full-name @{upstream}
git log -8 --oneline --decorate --no-abbrev-commit
git describe --always --dirty --tags
git show -s --format="%H%n%ad%n%s" --date=iso-strict HEAD
git show --stat --summary 3776811c288ed9d1f08caa04a8fa8975b106f7f5
git show --stat --summary 61eb8c18beeb013d5d3c320cfa0014bed2809d19
git merge-base HEAD 61eb8c1
git branch -a --contains 61eb8c1
find /root/gem5 -type f -name "sumcheck_noc_reference_bundle.zip" -print
find "/mnt/d/faq/清华/大二下暑/lab1作业材料" -maxdepth 4 -type f   -name "sumcheck_noc_reference_bundle.zip" -print
```

Results: branch/HEAD/remotes as recorded; Ring and Wormhole commits located;
no reference archive found.

### Build/config/API inspection

```bash
grep -E "^(PROTOCOL|USE_|TARGET_ISA|BUILD_ISA|PYTHON_CONFIG|CC|CXX)"   build/NULL/gem5.build/variables
nl -ba configs/network/Network.py
nl -ba configs/ruby/Ruby.py
nl -ba configs/topologies/BaseTopology.py
nl -ba configs/topologies/Mesh_XY.py
nl -ba configs/topologies/Ring.py
nl -ba src/mem/ruby/network/BasicLink.py
nl -ba src/mem/ruby/network/Topology.cc
nl -ba src/mem/ruby/network/garnet/CommonTypes.hh
nl -ba src/mem/ruby/network/garnet/RoutingUnit.hh
nl -ba src/mem/ruby/network/garnet/RoutingUnit.cc
nl -ba src/mem/ruby/network/garnet/Router.hh
nl -ba src/mem/ruby/network/garnet/Router.cc
nl -ba src/mem/ruby/network/garnet/InputUnit.hh
nl -ba src/mem/ruby/network/garnet/InputUnit.cc
nl -ba src/mem/ruby/network/garnet/VirtualChannel.hh
nl -ba src/mem/ruby/network/garnet/OutputUnit.hh
nl -ba src/mem/ruby/network/garnet/OutputUnit.cc
nl -ba src/mem/ruby/network/garnet/OutVcState.hh
nl -ba src/mem/ruby/network/garnet/OutVcState.cc
nl -ba src/mem/ruby/network/garnet/SwitchAllocator.hh
nl -ba src/mem/ruby/network/garnet/SwitchAllocator.cc
nl -ba src/mem/ruby/network/garnet/GarnetNetwork.py
nl -ba src/mem/ruby/network/garnet/GarnetNetwork.hh
nl -ba src/mem/ruby/network/garnet/GarnetNetwork.cc
nl -ba src/mem/ruby/network/garnet/NetworkInterface.hh
nl -ba src/mem/ruby/network/garnet/NetworkInterface.cc
nl -ba src/mem/ruby/network/garnet/NetworkLink.hh
nl -ba src/mem/ruby/network/garnet/NetworkLink.cc
nl -ba configs/example/garnet_synth_traffic.py
nl -ba configs/ruby/Garnet_standalone.py
nl -ba src/cpu/testers/garnet_synthetic_traffic/GarnetSyntheticTraffic.py
nl -ba src/cpu/testers/garnet_synthetic_traffic/GarnetSyntheticTraffic.cc
nl -ba src/mem/ruby/network/garnet/SConscript
nl -ba src/cpu/testers/garnet_synthetic_traffic/SConscript
scons build/NULL/gem5.debug -j16
```

Build result: PASS, exit 0. The first attempt to query
`build/NULL/gem5.debug --version` produced the gem5 option-usage error because
this release has no such option; the successful smoke banner supplied version
`23.0.0.1`.

### Simulation/test commands

```bash
./build/NULL/gem5.debug --outdir=m5out/sumcheck_recon/mesh_smoke   configs/example/garnet_synth_traffic.py --network=garnet   --num-cpus=16 --num-dirs=16 --topology=Mesh_XY --mesh-rows=4   --routing-algorithm=1 --inj-vnet=0 --synthetic=uniform_random   --sim-cycles=2000 --injectionrate=0.01

./build/NULL/gem5.debug --outdir=m5out/sumcheck_recon/ring_smoke   configs/example/garnet_synth_traffic.py --network=garnet   --num-cpus=16 --num-dirs=16 --topology=Ring --mesh-rows=1   --routing-algorithm=2 --inj-vnet=0 --synthetic=uniform_random   --sim-cycles=2000 --injectionrate=0.01

./build/NULL/gem5.debug --outdir=m5out/sumcheck_recon/mesh_single_packet   configs/example/garnet_synth_traffic.py --network=garnet   --num-cpus=16 --num-dirs=16 --topology=Mesh_XY --mesh-rows=4   --routing-algorithm=1 --inj-vnet=0 --synthetic=uniform_random   --sim-cycles=500 --injectionrate=1.0 --num-packets-max=1   --single-sender-id=0 --single-dest-id=15

./build/NULL/gem5.debug --outdir=m5out/sumcheck_recon/ring_single_packet   configs/example/garnet_synth_traffic.py --network=garnet   --num-cpus=16 --num-dirs=16 --topology=Ring --mesh-rows=1   --routing-algorithm=2 --inj-vnet=0 --synthetic=uniform_random   --sim-cycles=500 --injectionrate=1.0 --num-packets-max=1   --single-sender-id=0 --single-dest-id=8

./build/NULL/gem5.debug --outdir=m5out/sumcheck_recon/wormhole_probe   configs/example/garnet_synth_traffic.py --network=garnet   --num-cpus=16 --num-dirs=16 --topology=Mesh_XY --mesh-rows=4   --routing-algorithm=1 --inj-vnet=0 --synthetic=uniform_random   --sim-cycles=500 --injectionrate=1.0 --num-packets-max=1   --single-sender-id=0 --single-dest-id=15 --vcs-per-vnet=16 --wormhole

python3 -m py_compile configs/topologies/Ring.py configs/network/Network.py   configs/example/garnet_synth_traffic.py labs/lab3_task2_experiments.py
python3 labs/lab3_task2_experiments.py run --rates 0.01   --num-nodes 16 --sim-cycles 100 --dry-run
cd tests && ../build/NULL/gem5.debug run_pyunit.py
```

Outcomes are in the regression table. The Wormhole command returned parser
status 2. The generic pyunit command was interrupted after unrelated errors
and a no-progress resource test.

### Static diagnostic commands

Two successful inline `python3 -c` calculations used the exact entry tables:

- router/link/mean/max output:
  - `p1 69/104/2.00/4`
  - `p2 69/108/1.50/3`
  - `p4_staggered 69/116/0.75/1`
  - `p4_corners 69/116/1.00/2`
- dim0→dim1 maximum mesh-edge path counts: `8, 4, 1, 2`.

One earlier heredoc attempt was malformed by Windows→WSL shell quoting and
failed before running Python or changing any file; it is not used as evidence.

### Final safety inspection

```bash
git status --short --untracked-files=all
git diff --stat
git diff --check
wc -l SUMCHECK_STATUS.md docs/sumcheck_api_map.md docs/sumcheck_reference_map.md
grep -n "[[:blank:]]$" SUMCHECK_STATUS.md docs/sumcheck_api_map.md \
  docs/sumcheck_reference_map.md
```

Result before the authorized checkpoint commit: only the exact untracked
documentation/task files listed above; no tracked diff, no staged files, and
no trailing whitespace in the three Phase-0 documents. The three Phase-0
documents were then staged explicitly and committed as `9804d7f`; no unrelated
untracked task material was staged.

## Git actions actually performed

```text
git add -- SUMCHECK_STATUS.md docs/sumcheck_api_map.md docs/sumcheck_reference_map.md
git commit -m "sumcheck: document phase 00 reconnaissance"
```

No push, branch switch, merge, cherry-pick, rebase, reset, restore, or clean
was performed.

## Current blockers / unresolved risks

1. **Reference archive absent.** Bundle contents, JSONL dependencies/event
   counts, CDG legal-route counts/witnesses, and full-trace flit-hop outputs
   cannot be directly verified. This is non-critical for starting Phase 1
   because the architecture/routing requirements are in the canonical spec.
2. **Wormhole is not on the current branch.** The exact current-branch
   regression is blocked. Phase 2 will overlap its implementation files, so
   preservation needs an explicit integration/review decision; Phase 0 did not
   assume authorization to merge/cherry-pick/switch.
3. **Routing ID collision risk.** Lab3 Ring already owns custom algorithm 2.
   Sumcheck must add a distinct enum/value.
4. **69-router geometry risk.** Existing XY code requires a rectangular router
   count. Sumcheck must keep `mesh_rows=0` and use centralized fixed-ID
   mapping.
5. **Direction-name risk.** Duplicate non-local direction strings overwrite
   entries in `RoutingUnit` maps. Use unique `Entry0..Entry3`,
   `RootUp`, and `RootToG0..RootToG3` names.
6. **Credit timing fact.** Input route computation precedes consumption of
   same-cycle returned credits in `Router::wakeup()`; adaptive scores observe
   the last completed credit state. Test this timing rather than assuming a
   newer API/order.
7. **VC-class gap.** No route-class state exists; allocator and NI currently
   scan every vnet VC. Phase 2 must restrict both availability and actual
   allocation, including the NI's first-hop VC.
8. **Workload/controller gap.** Garnet standalone is asymmetric L1→Directory
   traffic, and its tester callback is not packet arrival. Phase 3 needs a
   custom destination-controller arrival path.
9. **Packet-size gap.** Current messages are 8 B/72 B, not exact 32 B/128 B.
10. **Statistics gap.** Per-link counters, P95/P99, per-round timing, adaptive
    instrumentation, stall reasons, and detailed watchdog state are absent.
11. **Tester termination risk.** Fixed `simCycles` does not drain; formal
    completion must be workload-driven and assert injected==received.
12. **Generic pyunit health.** The unrelated repository Python suite currently
    errors/hangs in stdlib/resource tests. This is not a NoC regression but is
    recorded as a pre-existing environment/test-suite limitation.

## Static/reference oracles vs measured gem5 results

### Static/reference only

- Canonical constants currently come only from `docs/sumcheck_spec.md`.
- Phase-0 local arithmetic confirmed 69 routers, 104/108/116 undirected links,
  placement means/maxima, and max dim0→dim1 edge-path counts 8/4/1/2.
- Event counts, legal-route counts, CDG acyclicity/cycle witnesses, weighted
  flit-hops, and full-trace totals remain unverified because the bundle is
  absent.
- None of these is a measured gem5 performance result.

### Measured gem5 baseline results

Only pre-Sumcheck baselines were measured:

- Mesh single packet: 1 injected = 1 received, 6 hops, latency 17.
- Ring single packet: 1 injected = 1 received, 8 hops, latency 21.
- 2,000-cycle Mesh/Ring: both 146 injected / 145 received due to one in-flight
  packet at fixed termination.

There is no Sumcheck topology, routing, workload, cycle, latency, throughput,
or utilization measurement yet.

## Exact next action

Start a new run with `tasks/01_topology_fixed.md`. First add a centralized
Sumcheck mapping helper and focused tests for all 69 router IDs, p=1/2/4 entry
tables, and 104/108/116 undirected-link counts. Do not edit
`RoutingUnit` or construct `SumcheckHierarchy` until those mapping tests
pass; preserve Ring algorithm 2 and keep Phase-2 adaptive/VC work out of that
run.
