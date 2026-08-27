# Sumcheck NoC deadlock argument

## Claim and scope

For the implemented Sumcheck routing relation, the directed internal-channel
dependency graph is acyclic when each protocol vnet uses separate VC_U and
VC_D resource classes. This is a routing/channel proof, not a proof of every
possible Ruby protocol or message-class dependency. The causal Garnet-
standalone workload uses endpoint termination and one ordered request vnet;
adding other protocols, blocking controller dependencies, multicast resource
holding, or cross-vnet request/response cycles requires a separate audit.

## Physical channels and endpoint boundary

The physical internal channels are the directed halves of:

- dim0 and dim1 worker-mesh links;
- entry-to-gateway shortcuts;
- gateway-to-root links.

The CDG resource key is `(VC class, directed source router, directed destination
router)`. ExtLink/NI channels are not chained through controller computation:
an arriving tail is admitted to the endpoint MessageBuffer, a VC-free credit is
sent, and only then is the causal controller notified. Any aggregate or
challenge is a fresh message injected no earlier than the next endpoint clock.
The proof therefore assumes and the implementation enforces ejection followed
by reinjection rather than a router holding a wormhole channel while computing.

## VC_U / VC_D partition and allocator enforcement

Within every vnet:

- offsets 0 and 1 are VC_U;
- offsets 2 and 3 are VC_D;
- `vcs_per_vnet < 4` is rejected at Python initialization and again by the
  Garnet constructor.

The partition is enforced in the real data path:

1. `NetworkInterface::calculateVC()` derives the first-hop class from
   `(source router, destination router)` and searches only the two offsets in
   that class.
2. `SwitchAllocator::requiredVcClass()` derives the current required class,
   compares it with the input VC offset, rejects D-to-U, and rejects U-to-D
   outside root router 68.
3. `SwitchAllocator::send_allowed()` calls subset-aware
   `OutputUnit::has_free_vc()`.
4. `SwitchAllocator::vc_allocate()` calls subset-aware
   `OutputUnit::select_free_vc()` and asserts the result is valid.
5. Body/tail flits reuse the allocated out-VC and are checked against the same
   required class.

No U/D fallback exists when the other class has idle VCs or credits.

## Allowed route phases

The centralized `routeVcClass()` classifier assigns:

| Segment | Class |
|---|---|
| same-cluster worker-to-worker dim0/dim1 | U |
| worker-to-entry mesh | U |
| entry-to-gateway | U |
| gateway-to-root | U |
| root-to-gateway | D |
| gateway-to-entry | D |
| destination entry-to-worker mesh | D |

Consequently every route is one of `U*`, `D*`, or `U*D*`. U-to-D occurs only
when root R=68 requests its destination-gateway output. D-to-U is never legal.
Adaptive routing only chooses among destination gateway-to-entry D channels;
it does not add turns in either worker mesh.

## CDG construction

`tests/pyunit/sumcheck_cdg.py` independently constructs strict dim0-then-dim1
mesh paths, direct gateway/entry/root channels, assigns the class at every hop
using the generated-equivalent classifier, adds a dependency edge for each
adjacent pair of channel resources, and performs directed DFS cycle detection.
Every route is checked against the physical adjacency table and against the
U*/D*/U*D* transition rules.

Phase 05 corrected an evidence ambiguity by checking two explicit relations:

- **exact C++ runtime relation:** the source worker always uses fixed nearest;
  destination gateway choice is nearest in fixed mode or any legal entry in
  adaptive mode;
- **specification-counted conservative superset:** all legal source entries
  and all legal destination entries. It retains the specification's route
  counts and is a strict superset for p2/p4, not a runtime source-adaptivity
  claim.

The checker asserts the exact adaptive relation is a subset of the conservative
relation and proves both separated graphs acyclic.

## Enumerated results

Fresh Phase-05 output is
`m5out/sumcheck_phase05/regressions/cdg_report.json`.

| p | Ordered pairs | Exact fixed routes | Exact adaptive routes | Conservative routes | Exact adaptive U/D | Conservative U/D |
|---:|---:|---:|---:|---:|---|---|
| 1 | 4692 | 4692 | 4692 | 4692 | acyclic | acyclic |
| 2 | 4692 | 4692 | 8084 | 14548 | acyclic | acyclic |
| 4 | 4692 | 4692 | 14868 | 52692 | acyclic | acyclic |

The conservative p1/p2/p4 counts are the specification acceptance values.
The exact counts are the claim about `RoutingUnit::outportComputeSumcheck()`.

## Collapsed-single-VC negative control

Collapsing U and D into one resource class leaves p1 acyclic but produces
cycles for p2 and p4 in both the exact adaptive relation and the conservative
relation. Concrete witnesses from the exact relation are:

### p2 witness

`64->68 -> 68->65 -> 65->17 -> 17->21 -> 21->25 -> 25->29 -> 29->30 -> 30->65 -> 65->68 -> 68->64 -> 64->1 -> 1->5 -> 5->9 -> 9->13 -> 13->14 -> 14->64 -> 64->68`

### p4 witness

`64->68 -> 68->65 -> 65->17 -> 17->21 -> 21->22 -> 22->23 -> 23->65 -> 65->68 -> 68->64 -> 64->1 -> 1->5 -> 5->6 -> 6->7 -> 7->64 -> 64->68`

The repeated `64->68` closes each directed resource cycle. These witnesses are
why physical hierarchy/tree intuition or a collapsed VC is insufficient.

## Validation commands

```bash
python3 tests/pyunit/pyunit_sumcheck_phase02.py
python3 tests/pyunit/sumcheck_cdg.py \
  --output m5out/sumcheck_phase05/regressions/cdg_report.json
g++ -std=c++17 -Isrc tests/pyunit/sumcheck_adaptive_cpp_test.cc \
  -o m5out/sumcheck_phase05/regressions/sumcheck_adaptive_cpp_test
m5out/sumcheck_phase05/regressions/sumcheck_adaptive_cpp_test
```

Results: 13/13 Python tests pass; p1/p2/p4 exact and conservative separated
graphs are acyclic; p2/p4 collapsed witnesses exist; the C++ selector/class
test exits 0.

## Remaining proof limitations and human review

- The offline checker mirrors the generated mapping/classifier and route
  relation but is not a formal extraction from compiled C++. Generated header
  equality, exact-relation counts, smokes, and code review reduce rather than
  eliminate model-divergence risk.
- Live tests exercise U and D allocations and fatal guards exist, but there is
  no fault-injection simulation that deliberately corrupts an allocated VC to
  demonstrate every negative allocator assertion.
- The proof excludes arbitrary Ruby protocol/message-class dependencies,
  controller queue cycles, and the branch-separated Wormhole implementation.
- Endpoint ejection/reinjection is an explicit assumption. Future in-router
  aggregation, held credits during computation, or hardware multicast would
  invalidate this proof and require a new CDG/resource model.

The highest-value review points are `routeVcClass()` in `SumcheckConfig.hh`,
`RoutingUnit::outportComputeSumcheck()`, `requiredVcClass()` and
`SwitchAllocator::vc_allocate()`, `NetworkInterface::calculateVC()`, and the
route generator in `tests/pyunit/sumcheck_cdg.py`.
