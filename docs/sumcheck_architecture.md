# Sumcheck NoC architecture

## Audited implementation

This document describes the final implementation audited in Phase 05 on the
`sumcheck` branch, based on gem5 23.0.0.1 / Garnet 3.0. The hierarchy uses
routing algorithm 3; algorithm 2 remains the pre-existing Lab3 Ring routing.
The unavailable reference bundle is not an implementation or measurement
source.

## Logical roles and endpoint mapping

The hierarchy has 69 logical roles and 69 routers:

| Role | Logical/NI/router ID | Mapping |
|---|---:|---|
| Workers | 0..63 | `cluster*16 + row*4 + col` |
| Gateways/controllers G0..G3 | 64..67 | `64 + cluster` |
| Root controller R | 68 | fixed root ID |

The causal harness creates 64 L1 and five Directory controllers in MachineID
order. Each role has one controller queue, NI, ExtLink, and router-local port;
logical ID, NI ID, and router ID are identical. This is assembled by
`_create_sumcheck_causal_system()` in `configs/ruby/Garnet_standalone.py` and
`SumcheckHierarchy.makeTopology()`.

The 8x8 Mesh baseline preserves the same 69 endpoint roles but has 64 routers.
Workers occupy four 4x4 quadrants. G0..G3 attach to routers 18, 21, 42, and 45;
R also attaches to router 18. All 69 ExtLinks/NIs/local ports are materialized,
so the co-located G0/R endpoints compete at router 18 and are counted in cost.

The older 64-L1 + 8-Directory, 72-controller mapping remains only for the
single-packet synthetic routing regression. Its three extra Directory
controllers are co-located at R and are not used for causal measurements.

## Physical topology

Each cluster is a 4x4 worker mesh with 24 undirected mesh edges. Every gateway
has `p` gateway-entry shortcuts and one gateway-root link. Every undirected
edge is emitted as two Garnet `IntLink` objects.

| p | Routers | Undirected/directed internal links | Causal ExtLinks |
|---:|---:|---:|---:|
| 1 | 69 | 104/208 | 69 |
| 2 | 69 | 108/216 | 69 |
| 4 | 69 | 116/232 | 69 |

Stable port names are `Dim0Pos/Dim0Neg`, `Dim1Pos/Dim1Neg`, `Gateway`,
`Entry0..Entry3`, `RootUp`, and `RootToG0..RootToG3`. The canonical Python
mapping and link model are in `configs/topologies/SumcheckConfig.py`; the C++
constants and classifiers in `SumcheckConfig.hh` are generated from it and
checked byte-for-byte.

Entry coordinates are:

| Configuration | Coordinates `(row,col)` |
|---|---|
| p1 staggered | `(1,1)` |
| p2 staggered | `(0,1), (3,2)` |
| p4 staggered | `(0,1), (1,3), (2,0), (3,2)` |
| p4 corners | `(0,0), (0,3), (3,0), (3,3)` |

Ordinary mesh edges use `--link-latency`. Gateway-entry and root-gateway
links independently use `--gateway-entry-link-latency` and
`--root-gateway-link-latency`, each restricted to 1, 2, or 4 cycles. Executed
Phase-04 measurements use latency 1; the non-unit choices are parameterized but
were not part of the measured matrix.

## Routing relation

### Fixed routing

Worker-to-worker traffic within one cluster follows strict dim0 (row), then
dim1 (column). A non-local worker packet follows the source worker's nearest
entry, breaking ties by smaller entry index, then the direct entry-to-gateway
link. Gateway/root traversal is direct. A destination gateway selects the
destination's nearest entry with the same tie rule, then the packet follows
strict dim0-then-dim1 in the destination mesh. Cross-cluster traffic must pass
through R.

`RoutingUnit::outportComputeSumcheck()` implements the relation. Invalid IDs,
roles, missing directions, and unsupported cases terminate with `fatal`; they
do not fall back to table routing.

### Credit-aware adaptive routing

Adaptive freedom exists only at a gateway selecting an entry into its
destination cluster. For entry `e` it calculates:

`ManhattanDistance(e,destination) + lambda*(1-freeCredits/capacity)`

`freeCredits` and `capacity` are summed only over offsets 2 and 3 (VC_D) of
that candidate output port in the packet's vnet. The default `lambda` is 4.0.
Minimum-score ties use a rotating pointer stored per gateway `RoutingUnit`.
Different credit state and arbitration history can therefore select different
legal entries without random routing.

`InputUnit::wakeup()` computes an outport once for a head/head-tail flit and
stores it in the input VC. A blocked packet waits for a legal output VC; it does
not recompute its entry. After the direct gateway-entry hop, routing returns to
strict dim0-then-dim1.

Fresh Phase-05 adaptive causal smoke evidence records 896 destination-entry
selections, 328 departures from fixed nearest, 108 tie arbitrations, all four
entries used at every gateway, and reroute rate 0.366071. Candidate credit and
occupancy sums differ across outputs, confirming that live state was observed.

## VC discipline

Each vnet requires at least four VCs. Offsets 0/1 are VC_U and offsets 2/3 are
VC_D. Extra offsets, if configured, are not used by Sumcheck routing.
`NetworkInterface::calculateVC()` selects the initial subset;
`SwitchAllocator::send_allowed()` checks the required subset and transition;
`SwitchAllocator::vc_allocate()` and `OutputUnit::select_free_vc()` allocate
from the same subset. D-to-U is fatal, and U-to-D is fatal outside router 68.
The full proof and its scope are in `docs/sumcheck_deadlock_proof.md`.

## Causal controller boundary

`configs/topologies/SumcheckWorkload.py` constructs stable-ID event graphs for
14 Phase-A rounds, the A-to-B boundary, four Phase-B rounds, the B-to-C
boundary, and two root-local Phase-C rounds. Network messages are exactly 32 or
128 bytes. Aggregated p1/p2/p4 traces have 2004 events; no aggregation has 1856.

`SumcheckWorkload` injects an event only after every dependency's tail has
arrived at the destination NI and the message can enter the endpoint queue.
The NI sends the VC-free credit before notifying the manager. A successor is
scheduled no earlier than the next endpoint clock, creating the required:

`eject -> release network resource -> endpoint wait/aggregate -> reinject`

boundary. SLICC endpoint transitions drain the received queue. The centralized
workload object models controller computation/dependency coordination; it does
not aggregate inside a router or retain an input VC.

The no-aggregation control uses direct worker-to-root partials and individual
root-to-worker challenges. Mesh uses the identical aggregated logical trace
and exact packet sizes; only physical endpoint placement and XY routing differ.

## User-facing knobs

| Option | Meaning/default |
|---|---|
| `--topology` | `SumcheckHierarchy` or `SumcheckMesh` |
| `--routing-algorithm` | 3 for hierarchy; 1 for Mesh XY |
| `--sumcheck-routing` | `fixed` or `adaptive`; fixed default |
| `--entry-congestion-weight` | adaptive lambda; 4.0 default |
| `--entries-per-cluster` | 1, 2, or 4 |
| `--entry-placement` | `staggered`; `corners` only for p4 |
| `--gateway-entry-link-latency` | 1, 2, or 4 |
| `--root-gateway-link-latency` | 1, 2, or 4 |
| `--vcs-per-vnet` | at least 4 for algorithm 3 |
| `--buffers-per-data-vc` / `--buffers-per-ctrl-vc` | global VC depths |
| `--sumcheck-mode` | `aggregated` or `no-aggregation` |
| `--traffic-case` | causal, uniform-random, cluster-skewed-bursty |
| `--sumcheck-seed`, `--offered-load`, `--traffic-cycles` | experiment controls |
| `--sumcheck-watchdog-cycles` | arrival-progress watchdog |

## Repository/API adaptations

- A 69-router hierarchy cannot use Garnet's rectangular XY helper, so it keeps
  `mesh_rows=0` and uses centralized fixed IDs.
- Exact bytes and causal event IDs are optional metadata on `Message`; ordinary
  protocol messages retain their original size conversion.
- Garnet standalone cannot provide 65 same-type L1 MachineIDs. The final causal
  path instead uses 64 L1 plus five Directory roles with exact 69 NIs.
- Global integer VC depths cannot exactly match Mesh's 7032 buffer slots:
  p4 depth 3 is a 6020-slot lower bracket and depth 4 is a 7224-slot upper
  bracket. No result is labeled exact buffer matched.
- Allocator stall-reason counters do not exist in this Garnet revision. The
  watchdog reports pending logical events, while endpoint MessageBuffer stall
  statistics remain in raw stats.
- Wormhole support is absent from this branch and remains at separate commit
  `61eb8c18beeb013d5d3c320cfa0014bed2809d19`.

## Primary implementation review points

- `configs/topologies/SumcheckConfig.py`: mappings, routes, generated header.
- `RoutingUnit::outportComputeSumcheck()`: fixed/adaptive output selection.
- `SwitchAllocator::requiredVcClass()`, `send_allowed()`, `vc_allocate()`:
  U/D transition and output-VC enforcement.
- `NetworkInterface::flitisizeMessage()` and `calculateVC()`: exact packet
  bytes, arrival callback, and injection VC class.
- `SumcheckWorkload::inject()`, `notifyArrival()`, and `watchdog()`:
  arrival-triggered controller behavior and completion accounting.
