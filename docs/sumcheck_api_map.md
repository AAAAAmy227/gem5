# Sumcheck NoC — gem5/Garnet API Map

> Phase 0 repository-specific map for `/root/gem5` at
> `86686aa3b4e015fc961c9f41e27af4e2dfef8096`. This records observed APIs;
> it is not based on another gem5 release.

## Repository identity

| Item | Actual value | Evidence / command |
|---|---|---|
| Repository path | `/root/gem5` | `pwd` |
| Current branch | `sumcheck` | `git branch --show-current` |
| HEAD commit | `86686aa3b4e015fc961c9f41e27af4e2dfef8096` (`modify gitignore`) | `git rev-parse HEAD`; `git show -s --format='%H%n%ad%n%s' --date=iso-strict HEAD` |
| Upstream | `origin/sumcheck` | `git rev-parse --abbrev-ref --symbolic-full-name @{upstream}` |
| gem5 version/revision | gem5 `23.0.0.1`, Garnet `3.0`; Git describe `v23.0.0.1-8-g86686aa` before the Phase-0 documentation edits | smoke banner; `git describe --always --dirty --tags`; `GarnetNetwork.hh::garnetVersion` |
| Working tree at entry | No tracked modifications; untracked `AGENTS.md`, `CODEX_START_HERE.md`, `SUMCHECK_STATUS.md`, `docs/`, `tasks/` | `git status --short` |
| Existing build target | `build/NULL/gem5.debug`, `PROTOCOL='Garnet_standalone'`, `USE_NULL_ISA=True` | `build/NULL/gem5.build/variables`; successful `scons build/NULL/gem5.debug -j16` |
| Existing Garnet configuration | 3 vnets; default 128-bit/16-byte flit, 4 VCs/vnet, 4 data slots/VC, 1 control slot/VC; CLI is in `configs/network/Network.py` | `Garnet_standalone.py:114-116`; `GarnetNetwork.py:43-52`; `Network.py:38-113` |
| Existing Ring implementation | `configs/topologies/Ring.py::Ring`; custom direction routing in `RoutingUnit::outportComputeCustom`; CLI uses `--topology=Ring --mesh-rows=1 --routing-algorithm=2` | commit `3776811c288ed9d1f08caa04a8fa8975b106f7f5`; passing Phase-0 Ring smoke |
| Existing Wormhole implementation | **Not in current `sumcheck` HEAD.** Preserved on local/remote branch `wormhole` / `origin/wormhole`, commit `61eb8c18beeb013d5d3c320cfa0014bed2809d19`, touching 12 files including `Network.py`, `GarnetNetwork.*`, `InputUnit.*`, `NetworkInterface.cc`, `OutputUnit.*`, `SwitchAllocator.cc`, and `VirtualChannel.hh` | `git log --all --grep='wormhole'`; `git show --stat 61eb8c1`; current-branch `--wormhole` probe exits 2 as unrecognized |

## Build and test entry points

| Purpose | Exact command | Verified? | Notes |
|---|---|---|---|
| Build relevant gem5 binary | `scons build/NULL/gem5.debug -j16` | PASS | Exit 0. Warnings only: missing optional PNG/HDF5 support. Rebuilt current `sumcheck` sources, replacing stale objects left by the separate Wormhole branch. |
| Existing network smoke | `./build/NULL/gem5.debug --outdir=m5out/sumcheck_recon/mesh_single_packet configs/example/garnet_synth_traffic.py --network=garnet --num-cpus=16 --num-dirs=16 --topology=Mesh_XY --mesh-rows=4 --routing-algorithm=1 --inj-vnet=0 --synthetic=uniform_random --sim-cycles=500 --injectionrate=1.0 --num-packets-max=1 --single-sender-id=0 --single-dest-id=15` | PASS | Exit 0; 1 packet/flit injected and 1 received. Evidence: `m5out/sumcheck_recon/mesh_single_packet/{stats.txt,config.ini}`. |
| Ring regression | `./build/NULL/gem5.debug --outdir=m5out/sumcheck_recon/ring_single_packet configs/example/garnet_synth_traffic.py --network=garnet --num-cpus=16 --num-dirs=16 --topology=Ring --mesh-rows=1 --routing-algorithm=2 --inj-vnet=0 --synthetic=uniform_random --sim-cycles=500 --injectionrate=1.0 --num-packets-max=1 --single-sender-id=0 --single-dest-id=8` | PASS | Exit 0; 1 packet/flit injected and 1 received; 8 hops. Evidence: `m5out/sumcheck_recon/ring_single_packet/{stats.txt,config.ini}`. |
| Wormhole regression | Same single-packet Mesh command plus `--vcs-per-vnet=16 --wormhole` | BLOCKED | Current branch parser exits 2: `unrecognized arguments: --wormhole`. The implementation is preserved only at `61eb8c1` on the separate Wormhole branch; no branch switch/merge/cherry-pick was authorized in Phase 0. |
| Python syntax checks | `python3 -m py_compile configs/topologies/Ring.py configs/network/Network.py configs/example/garnet_synth_traffic.py labs/lab3_task2_experiments.py` | PASS | Exit 0. |
| Repository Python suite | `cd tests && ../build/NULL/gem5.debug run_pyunit.py` | INCOMPLETE / PRE-EXISTING ERRORS | Many unrelated stdlib/resource tests errored and a resource-specialization test stopped making progress; the run was interrupted with Ctrl-C. There are no existing Ring/Wormhole/Sumcheck Python unit tests in `tests/`. |

The fixed-duration 2,000-cycle Mesh and Ring runs also exited 0, but each
reported `146 injected / 145 received`: `GarnetSyntheticTraffic::tick()` exits
at `simCycles` without a drain phase. Use the single-packet commands above as
the clean baseline, and do not use fixed-cycle termination for a Sumcheck
`injected == received` acceptance gate.

## Specification → implementation mapping

| Spec concept | Actual repository API / implementation point | File(s) | Status / notes |
|---|---|---|---|
| Topology registration / selection | `Ruby.create_topology()` imports `topologies.<options.topology>` and constructs the same-named class; `Ruby.create_system()` calls `topology.makeTopology(...)` then `Network.init_network(...)` | `configs/ruby/Ruby.py:204-212, 231-265`; `configs/topologies/BaseTopology.py` | A new `configs/topologies/SumcheckHierarchy.py` class is sufficient for discovery; no registry table exists. |
| CLI topology options | `Network.define_options(parser)` owns topology/Garnet options and `Network.init_network()` copies them to the SimObject | `configs/network/Network.py:32-113, 164-280`; called by `configs/ruby/Ruby.py:122-125` | Sumcheck topology/routing options belong here, not in `configs/common/Options.py`. |
| InternalLink / ExtLink construction | Python builds `GarnetIntLink`/`GarnetExtLink`. `BasicIntLink` has `src_node`, `dst_node`, `src_outport`, `dst_inport`, latency, weight. An internal link is unidirectional; an ExtLink is bidirectional. | `src/mem/ruby/network/BasicLink.py:31-73`; `src/mem/ruby/network/garnet/GarnetLink.py:38-176`; `configs/topologies/Mesh_XY.py`, `Ring.py` | Every undirected Sumcheck internal edge needs two `IntLink` objects with explicit reciprocal direction strings. Per-link latency is set directly on each `IntLink`. |
| Port-name propagation | `Topology` copies `src_outport`/`dst_inport` strings into `Network::makeInternalLink`; `GarnetNetwork` passes them to `Router::addOutPort/addInPort`; `RoutingUnit` maps strings to integer indices | `Topology.cc:93-110, 250-327`; `GarnetNetwork.cc:307-365`; `Router.cc:100-147`; `RoutingUnit.cc:148-160` | `PortDirection` is a string. Direction names must be unique per router: `m_outports_dirn2idx[name] = index` overwrites duplicate names. ExtLink directions are always `Local`, but local ejection is selected through the routing table before custom routing. |
| Router ID and topology metadata | `BasicRouter(router_id=...)`; C++ exposes `Router::get_id()`. Existing router params contain no topology-specific cluster/entry metadata. | `BasicRouter.py:32-40`; `BasicRouter.cc:37-42`; `Router.hh:85-119`; `GarnetNetwork.py:73-85` | Worker/gateway/root role and coordinates must be reconstructed centrally from fixed IDs or new explicit Garnet params. Do not use `num_rows/num_cols`: 69 routers are not a rectangle. |
| Routing algorithm selection | Integer CLI copied to `GarnetNetwork.routing_algorithm`; enum is table=0, XY=1, custom=2; `RoutingUnit::outportCompute()` dispatches | `Network.py:90-99, 164-171`; `CommonTypes.hh:53-54`; `RoutingUnit.cc:168-201` | Algorithm 2 is already the Lab3 Ring path. Sumcheck must add a distinct enum/value (recommended 3) or dispatch explicitly by topology without breaking Ring. |
| Route computation | `int RoutingUnit::outportCompute(RouteInfo route, int inport, PortDirection inport_dirn)`; topology-specific hooks return an integer outport | `RoutingUnit.hh:52-83`; `RoutingUnit.cc:168-292`; `CommonTypes.hh:56-73` | `RouteInfo` includes vnet, source/destination NI/router, and hop count. Unsupported role/turn cases should `fatal`/`panic`, not fall back to table routing. |
| Head-flit route persistence | On HEAD/HEAD_TAIL arrival, `InputUnit::wakeup()` calls `Router::route_compute()` once and writes the outport into the input `VirtualChannel`; body/tail flits reuse it | `InputUnit.cc:67-111`; `InputUnit.hh:66-100`; `VirtualChannel.hh:55-66,101-106` | This already satisfies “choose once per head flit”; a blocked packet does not recompute its entry choice. |
| Output port lookup | Direction maps are private to `RoutingUnit`; `Router::getOutputUnit(outport)` and `getOutportDirection()` expose an indexed output | `RoutingUnit.hh:89-97`; `Router.hh:100-119`; `Router.cc:123-165` | Fixed/adaptive selection should resolve a stable direction name once, then use its mapped index. |
| Output unit / downstream VC state | One `OutputUnit` per outport holds one `OutVcState` per vnet VC; it consumes returned credits before switch allocation | `OutputUnit.hh/.cc`; `OutVcState.hh/.cc`; `Router.cc:71-96` | Route computation occurs while input units are processed, before `OutputUnit::wakeup()` consumes credits arriving in that same router wakeup. A credit-aware score therefore observes real state from the prior completed update, not credits arriving later in the same cycle. |
| Per-VC free credit / occupancy | `OutputUnit::get_credit_count(vc)` is already public; `OutVcState` tracks current/max credits, but only current count is exposed | `OutputUnit.hh:67-79`; `OutVcState.hh:46-74`; `OutVcState.cc:44-77` | No new credit getter is needed. Capacity can be derived from `GarnetNetwork::getBuffersPerDataVC/getBuffersPerCtrlVC()` and vnet type, or a minimal max-capacity accessor can be added. Score only offsets 2 and 3 of the candidate output's vnet. |
| VC allocator | Garnet 3.0 has no separate VCAllocator stage. `SwitchAllocator::send_allowed()` asks `OutputUnit::has_free_vc(vnet)`; the output winner calls `vc_allocate()`, which calls `select_free_vc(vnet)` and stores the result in the input VC | `SwitchAllocator.cc:80-352`; `OutputUnit.cc:96-122` | This is the enforcement point for U/D output-VC partitions. Both availability and selection must use the same allowed subset. |
| `vcs_per_vnet` layout | Global VC index is `vnet * m_vc_per_vnet + offset`; `get_vnet(invc)` divides by `m_vc_per_vnet` | `OutputUnit.cc:98-115`; `SwitchAllocator.cc:326-328, 375-380`; `NetworkInterface.cc:460-472` | With 4 VCs/vnet, offsets 0/1 are U and 2/3 are D. Startup must reject `<4`. NI VC allocation also needs class filtering because its chosen VC is the first router's input VC. |
| VC_U / VC_D output restriction | No route class exists today and `has_free_vc/select_free_vc` scan every offset | `CommonTypes.hh::RouteInfo`; `VirtualChannel.hh`; `OutputUnit.cc:96-122`; `SwitchAllocator.cc:283-352` | Phase 2 must carry or deterministically derive the required class, add subset-aware availability/allocation, and ensure NI injection chooses the first-hop class. Do not change only an offline checker. |
| Root-only U→D transition | No explicit route-phase/class field or transition assertion exists | same as above | At R=68, an input U VC may request a D out-VC. All other U→D and every D→U must be excluded/asserted using router ID, current input VC offset, and required output class. |
| NI injection | `NetworkInterface::wakeup()` dequeues protocol `MessageBuffer`s; `flitisizeMessage()` clones multicast to unicasts, computes destination router, allocates an NI VC, builds flits, and updates injected stats | `NetworkInterface.cc:180-312, 367-455`; `NetworkInterface.hh` | Multicast already becomes independent unicast packets, matching the no-hardware-multicast assumption. |
| NI ejection / packet arrival | A tail/head-tail flit is considered arrived only when the NI can enqueue its `MsgPtr` into `outNode_ptr[vnet]`; stats update then. Stalled tails update only after later enqueue | `NetworkInterface.cc:226-279, 315-360`; `incrementStats()` at 154-178 | This NI enqueue (or subsequent custom controller consumption) is the correct dependency-completion boundary. Injection time or tester request callback is not. |
| Current tester / traffic generator | `configs/example/garnet_synth_traffic.py` creates one `GarnetSyntheticTraffic` per CPU and uses `Garnet_standalone`; `generatePkt()` sends L1→Directory messages selected by address | config above; `GarnetSyntheticTraffic.cc:142-324`; `Garnet_standalone.py:45-117` | Useful for generic smokes only. It does not supply arbitrary symmetric endpoints or causal replay. |
| Controller/aggregator endpoint | Ruby controllers own to/from-network `MessageBuffer`s; NI ejection releases the network VC before the controller consumes/reinjects | `Network.cc:120-143, 208-232`; `Garnet_standalone.py:70-116`; generated SLICC controllers | A custom endpoint/controller path is required in Phase 3. Aggregation can be correct if the controller waits after ejection and reinjects a new message. |
| Packet-arrival callback/event | `GarnetSyntheticTraffic::CpuPort::recvTimingResp()` calls `completeRequest()`, but `Garnet_standalone-cache.sm` immediately calls back the sequencer before the network message arrives | `GarnetSyntheticTraffic.cc:53-73, 127-138, 259-274`; `Garnet_standalone-cache.sm` | **Do not use tester responses as arrival evidence.** Drive dependency completion from destination-controller consumption/NI ejection metadata. |
| Packet size → flit conversion | `ceil(MessageSizeType_to_int(type) / output_bitWidth)`; default flit width is 16 bytes. Current message-size enum maps control to 8 B and data to cache-line+8 B (normally 72 B). | `NetworkInterface.cc:377-386, 440-446`; `Network.cc:55-66, 163-189`; `Network.py:50,63-67` | Exact 32 B and 128 B Sumcheck packets are not representable by current two-size mapping. Phase 3 needs an explicit byte-size field/type or carefully scoped conversion extension; changing cache-line size alone cannot produce both sizes. |
| Link statistics | Each `NetworkLink` internally counts utilization and per-VC load; `GarnetNetwork::collateStats()` currently publishes only aggregate ext/int utilization and average VC load | `NetworkLink.hh:56-105`; `NetworkLink.cc:83-120`; `GarnetNetwork.cc:558-631` | Per root/gateway-entry link stats require named per-link exposure or a network vector keyed by link ID/direction. |
| Latency/hop statistics | Injected/received packet/flit counts, summed/mean packet/flit latency, total/average hops, and router activity exist | `GarnetNetwork.cc:385-600`; `GarnetNetwork.hh:114-205`; `Router.cc:190-235` | P95/P99 and per-round completion are absent and need workload-side samples/stats. |
| Watchdog / stuck VC diagnosis | NI VC allocation has a busy counter and generic deadlock fatal; synthetic tester has a no-response watchdog | `NetworkInterface.cc:458-480`; `GarnetSyntheticTraffic.cc:142-180`; associated Params | Neither reports pending event/router/input VC/class/waited resource. Sumcheck needs a richer workload/router diagnostic. |
| SConscript / SimObject changes | Garnet sources are enumerated in Garnet `SConscript`; the tester has its own SimObject Python declaration and `SConscript` | `src/mem/ruby/network/garnet/SConscript`; `src/cpu/testers/garnet_synthetic_traffic/{SConscript,GarnetSyntheticTraffic.py}` | Phase 1 can avoid new C++ files by extending existing routing files. A new Phase-3 controller/tester will require SimObject and `SConscript` entries. |

## Topology API facts established for Phase 1

- `src_outport` and `dst_inport` are arbitrary stable strings passed unchanged
  from Python through `Topology`/`GarnetNetwork` into `RoutingUnit` maps.
- Every physical direction must use its own unidirectional `IntLink`; IDs must
  be globally unique within `network.int_links`.
- Multiple ExtLinks may attach to one router. `Network.init_network()` creates
  one NI per ExtLink. The router then has multiple `Local` ports; exact local
  ejection is selected by `lookupRoutingTable()` when
  `dest_router == my_id`. Co-location therefore adds real NIs, ExtLinks,
  local ports, arbitration, and buffer cost—it is not free.
- `IntLink(latency=...)` controls forward link latency (and its paired credit
  link via the parent). Separate gateway-entry and root-gateway CLI values can
  be applied during topology construction without a C++ API change.
- Existing generated `config.ini` makes router/int-link/ext-link counts easy
  to assert. Phase-0 examples counted Mesh `16/48/32` and Ring `16/32/32`.
- `GarnetNetwork::init()` derives `num_cols = routers/num_rows` whenever
  `mesh_rows > 0`; 69 is not rectangular. Sumcheck must leave
  `mesh_rows=0` and use the fixed ID mapping, not `outportComputeXY()`.

## Adaptive / VC facts established for Phase 2

1. A head route is chosen in `InputUnit::wakeup()` and persisted in the input
   `VirtualChannel`; it is not recomputed while waiting.
2. `RoutingUnit` can resolve a candidate direction to an outport, call
   `m_router->getOutputUnit(outport)`, and read each legal D VC's current
   credit with `get_credit_count(vc)`.
3. For vnet `v`, legal D indices are `v * vcs_per_vnet + 2` and `+3`
   when `vcs_per_vnet == 4`; use offsets, not global indices hard-coded for
   vnet 0.
4. Credit capacity is network-wide per data/control VC in this revision.
5. `SwitchAllocator::send_allowed()` and `OutputUnit::select_free_vc()`
   must share the same subset logic; otherwise the check and actual allocation
   can disagree. NI `calculateVC()` must also respect the initial route class.
6. `RouteInfo` has no phase/class field. Phase 2 must add one or implement a
   single central classifier from source/destination/current-router role and
   validate it against the offline route checker.
7. Ring commit `3776811c...` owns custom algorithm 2, while Wormhole commit
   `61eb8c1...` modifies the same allocator/output/NI files Phase 2 will
   touch. Integration must be reviewed explicitly; neither prior feature may
   be overwritten by a Sumcheck-only shortcut.

## Workload API facts established for Phase 3

- The physical network can host the 69 logical endpoints, but Garnet
  standalone creates `num_cpus` L1 controllers plus `num_dirs` Directory
  controllers and only sends L1→Directory traffic. This build's MachineID
  set also rejects 65 same-type L1 controllers, and the Directory count must
  remain a power of two. It is not a ready-made 69-role endpoint system.
- The working Phase-1 harness therefore uses 64 L1s plus 8 Directories (72
  ExtLinks/NIs): L1 0..62 map to workers 0..62, L1 63 maps to root,
  Directory 0 maps to worker 63, Directories 1..4 map to G0..G3, and
  Directories 5..7 are explicitly co-located on root. The three extras add
  real local ports, NIs, ExtLinks, buffers, and arbitration cost. This is
  only a smoke harness, not final Sumcheck controller semantics.
- Final causal replay needs a custom endpoint/controller or protocol extension
  whose destination-side consumer can identify an event ID and notify the
  workload manager after ejection. The manager may schedule a successor only
  after every predecessor has reached that boundary.
- Current `MsgPtr`/`MessageSizeType` needs scoped metadata for event ID and
  an exact byte count, or equivalent custom message types. Encoding dependency
  completion using estimated timestamps is not acceptable.
- `NetworkInterface` already returns the tail credit before controller
  computation, so controller wait/aggregate/reinject naturally creates the
  required packet termination boundary if implemented above the NI.
- Deterministic traffic randomness is available through gem5's random stream,
  but the existing experiment script records only `gem5_default`; formal
  runs need explicit seed/config capture.

## Experiment/statistics facts established for Phase 4

- Existing: packet/flit injected/received, mean queue/network/total latency,
  average hops, aggregate link utilization, average VC load, traffic matrix,
  and router buffer/crossbar/arbiter activity.
- Missing: latency samples/P95/P99, per-round completion, named per-link
  utilization, adaptive choice/reroute/tie counters, VC/buffer stall reasons,
  detailed stuck-resource watchdog, and constructed topology/cost totals.
- Router radix is available from `Router::get_num_inports/outports()` after
  links are created. ExtLink count and NI count are available from Python
  config vectors; actual buffer slots must count every input port × every VC ×
  the data/control depth. Do not reuse the reference's simplified 288-port
  cost.

## Deviations / required adaptations

| Spec requirement | Repository/API mismatch | Chosen adaptation | Correctness/cost consequence | Evidence/test |
|---|---|---|---|---|
| Keep Lab3 Ring and add Sumcheck routing | Algorithm 2 is already Ring custom routing | Add a distinct Sumcheck routing enum/value and leave algorithm 2 unchanged | Prevents a Sumcheck build from silently breaking Ring | Phase-0 Ring smoke; `RoutingUnit.cc:263-292` |
| 69-router custom mapping | XY helper requires a rectangular `num_rows*num_cols` | Leave `mesh_rows=0`; classify IDs with centralized Sumcheck helpers | Custom routing must not call `getNumCols()`/XY | `GarnetNetwork.cc:124-135` |
| 64 workers + 5 controller endpoints | Garnet standalone only supplies L1→Directory semantics; 65 L1s exceed the 64-bit MachineID set and Directory count must be a power of two | Use the documented 64-L1+8-Directory Phase-1 harness above; build a custom causal controller path in Phase 3 | Three extra root-co-located endpoints are real cost; smoke endpoint types are not final aggregation semantics | Initial 65-L1 smoke fatal; passing two-case 64+8 smoke under `m5out/sumcheck_phase01/deterministic_smoke/` |
| 32 B and 128 B packets | Current enum yields 8 B or normally 72 B | Add exact message byte-size support in the Sumcheck message path | Required for correct flit counts and reference path oracles | `Network.cc:163-189`; `NetworkInterface.cc:377-386` |
| Dependency fires on packet arrival | Synthetic tester callback is immediate protocol callback | Observe destination NI enqueue/custom controller consumption | Prevents pseudo-causal replay | `GarnetSyntheticTraffic.cc:259-274`; NI ejection code |
| Per-link utilization and P95/P99 | Only aggregate link utilization and latency sums/means are exported | Add keyed per-link counters and workload-side latency samples | Required formal metrics; no Phase-0 measured claim | stats code inspection |
| Preserve Wormhole regression | Wormhole is a separate branch, absent from current HEAD | Record exact branch/commit and current-branch blocker; integrate only under explicit later scope | Phase 1 can demonstrate the pre-existing blocker, but Phase 2 allocator edits require conflict-aware review | `git show 61eb8c1`; `--wormhole` probe exit 2 |

## Smallest expected Phase-1 implementation surface

Likely new files:

- `configs/topologies/SumcheckConfig.py` — canonical Python ID/role/coordinate/
  placement helpers;
- `configs/topologies/SumcheckHierarchy.py` — routers, ExtLinks, directed
  internal links, stable port names, and link-latency selection;
- `tests/pyunit/pyunit_sumcheck_topology.py` (or a focused standalone
  `tests/sumcheck/` test invoked explicitly) — counts, placements, real-link
  paths, tie-break, and Python/C++ mapping consistency;
- `scripts/run_sumcheck_smoke.sh` — exact deterministic smoke and counter
  check.

Likely modified files:

- `configs/network/Network.py` — Phase-1 CLI and routing selection;
- `src/mem/ruby/network/garnet/GarnetNetwork.py/.cc/.hh` — only if
  p/placement must be passed explicitly to C++ routing;
- `src/mem/ruby/network/garnet/CommonTypes.hh` — distinct Sumcheck routing
  enum;
- `src/mem/ruby/network/garnet/RoutingUnit.hh/.cc` — complete fixed
  relation, preserving the existing Ring custom function.

No Phase-1 change is expected in `OutputUnit`, `SwitchAllocator`,
`InputUnit`, `NetworkInterface`, SConscript, or workload/controller code.

Python and C++ cannot directly import one another in this legacy topology path.
Use one centralized mapping helper per language (or generate the C++ constants
from the Python table), and make the Phase-1 regression enumerate all 69 router
IDs and all supported entry tables against both representations. The same
regression must validate emitted `IntLink` adjacency before any gem5 smoke.

**Exact first Phase-1 implementation step:** add the centralized mapping model
and its failing/passing p=1/2/4 placement/router/link-count tests before
creating `SumcheckHierarchy` or editing `RoutingUnit`.

## Phase-0 completion assessment

Repository identity, build and current-branch baselines are recorded; topology,
routing, credit, allocator, NI, workload, statistics, and build APIs are
concrete. The reference archive is absent (tracked separately in
`sumcheck_reference_map.md`), and the Wormhole implementation is demonstrably
on a separate branch. Neither absence leaves a Phase-1 topology/routing API as
a guess.
