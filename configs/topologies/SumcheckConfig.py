"""Canonical logical model for the Sumcheck hierarchy topology.

This module deliberately has no ``m5`` imports so the mapping and path model
can be tested with the host Python interpreter. ``SumcheckHierarchy`` uses
the link descriptions below directly, and ``SumcheckConfig.hh`` is generated
from :func:`render_cpp_header` and checked byte-for-byte by Phase-1 tests.
"""

from math import isclose
from typing import NamedTuple


NUM_CLUSTERS = 4
CLUSTER_ROWS = 4
CLUSTER_COLS = 4
WORKERS_PER_CLUSTER = CLUSTER_ROWS * CLUSTER_COLS
NUM_WORKERS = NUM_CLUSTERS * WORKERS_PER_CLUSTER
GATEWAY_BASE_ID = NUM_WORKERS
ROOT_ID = GATEWAY_BASE_ID + NUM_CLUSTERS
NUM_ROUTERS = ROOT_ID + 1

STAGGERED = "staggered"
CORNERS = "corners"

VC_U = "U"
VC_D = "D"

ENTRY_PLACEMENTS = {
    (1, STAGGERED): ((1, 1),),
    (2, STAGGERED): ((0, 1), (3, 2)),
    (4, STAGGERED): ((0, 1), (1, 3), (2, 0), (3, 2)),
    (4, CORNERS): ((0, 0), (0, 3), (3, 0), (3, 3)),
}

# Garnet_standalone lists L1 controllers before Directory controllers. Its
# MachineID set in this build cannot represent 65 L1s, while the directory
# count must remain a power of two. The Phase-1 harness therefore uses L1
# 0..62 as workers 0..62, L1 63 as root, Directory 0 as worker 63, Directory
# 1..4 as gateways, and co-locates Directory 5..7 on root. This arrangement
# lets the asymmetric synthetic tester exercise both up and down routes.
# Extra root endpoints remain real NIs/ExtLinks/local ports and are not free.
# This is a smoke mapping, not the final causal controller implementation.
CONTROLLER_TO_ROUTER = (
    tuple(range(NUM_WORKERS - 1))
    + (ROOT_ID, NUM_WORKERS - 1)
    + tuple(range(GATEWAY_BASE_ID, ROOT_ID))
    + (ROOT_ID,) * 3
)

MESH_WORKER_TO_ROUTER = tuple(
    (cluster // 2 * 4 + local // 4) * 8
    + (cluster % 2 * 4 + local % 4)
    for cluster in range(NUM_CLUSTERS)
    for local in range(WORKERS_PER_CLUSTER)
)
MESH_CONTROLLER_TO_ROUTER = MESH_WORKER_TO_ROUTER + (18, 21, 42, 45, 18)


def mesh_xy_route(source_endpoint, destination_endpoint):
    """Strict X-then-Y route for the 8x8 baseline endpoint placement."""

    if not 0 <= source_endpoint < 69 or not 0 <= destination_endpoint < 69:
        raise ValueError("invalid Mesh baseline endpoint")
    current = MESH_CONTROLLER_TO_ROUTER[source_endpoint]
    target = MESH_CONTROLLER_TO_ROUTER[destination_endpoint]
    route = [current]
    row, col = divmod(current, 8)
    target_row, target_col = divmod(target, 8)
    while col != target_col:
        col += 1 if target_col > col else -1
        route.append(row * 8 + col)
    while row != target_row:
        row += 1 if target_row > row else -1
        route.append(row * 8 + col)
    return tuple(route)


class LinkSpec(NamedTuple):
    """One undirected physical link and its stable endpoint port names."""

    node_a: int
    node_b: int
    port_a: str
    port_b: str
    latency_class: str


class AdaptiveChoice(NamedTuple):
    """Result of one stable gateway-to-entry route decision."""

    index: int
    next_tie_pointer: int
    scores: tuple
    tied: bool


def validate_configuration(entries_per_cluster, entry_placement):
    key = (entries_per_cluster, entry_placement)
    if key not in ENTRY_PLACEMENTS:
        raise ValueError(
            "unsupported Sumcheck entry configuration: "
            f"p={entries_per_cluster}, placement={entry_placement}; "
            "corners is valid only for p=4"
        )


def entry_coordinates(entries_per_cluster, entry_placement):
    validate_configuration(entries_per_cluster, entry_placement)
    return ENTRY_PLACEMENTS[(entries_per_cluster, entry_placement)]


def is_worker(router_id):
    return 0 <= router_id < NUM_WORKERS


def is_gateway(router_id):
    return GATEWAY_BASE_ID <= router_id < ROOT_ID


def is_root(router_id):
    return router_id == ROOT_ID


def is_router(router_id):
    return 0 <= router_id < NUM_ROUTERS


def worker_id(cluster, row, col):
    if not 0 <= cluster < NUM_CLUSTERS:
        raise ValueError(f"invalid cluster {cluster}")
    if not 0 <= row < CLUSTER_ROWS or not 0 <= col < CLUSTER_COLS:
        raise ValueError(f"invalid worker coordinate ({row}, {col})")
    return cluster * WORKERS_PER_CLUSTER + row * CLUSTER_COLS + col


def worker_cluster(router_id):
    if not is_worker(router_id):
        raise ValueError(f"router {router_id} is not a worker")
    return router_id // WORKERS_PER_CLUSTER


def worker_coordinate(router_id):
    cluster = worker_cluster(router_id)
    local_id = router_id - cluster * WORKERS_PER_CLUSTER
    return divmod(local_id, CLUSTER_COLS)


def gateway_id(cluster):
    if not 0 <= cluster < NUM_CLUSTERS:
        raise ValueError(f"invalid cluster {cluster}")
    return GATEWAY_BASE_ID + cluster


def gateway_cluster(router_id):
    if not is_gateway(router_id):
        raise ValueError(f"router {router_id} is not a gateway")
    return router_id - GATEWAY_BASE_ID


def nearest_entry_index(worker_router, entries_per_cluster, entry_placement):
    """Return nearest entry, resolving distance ties by smaller index."""

    row, col = worker_coordinate(worker_router)
    entries = entry_coordinates(entries_per_cluster, entry_placement)
    return min(
        range(len(entries)),
        key=lambda index: (
            abs(entries[index][0] - row) + abs(entries[index][1] - col),
            index,
        ),
    )


def choose_adaptive_entry(
    worker_router,
    entries_per_cluster,
    entry_placement,
    free_credits,
    capacities,
    congestion_weight=4.0,
    tie_pointer=0,
):
    """Apply the Phase-2 credit score and deterministic rotating tie rule.

    ``free_credits`` and ``capacities`` contain the aggregate state of the
    two legal VC_D offsets on each candidate gateway output.
    """

    entries = entry_coordinates(entries_per_cluster, entry_placement)
    if len(free_credits) != len(entries) or len(capacities) != len(entries):
        raise ValueError("candidate credit vectors must match entry count")
    if not 0 <= tie_pointer < len(entries):
        raise ValueError("tie pointer is outside the entry table")
    if congestion_weight < 0:
        raise ValueError("entry congestion weight must be non-negative")

    destination_row, destination_col = worker_coordinate(worker_router)
    scores = []
    for index, (entry_row, entry_col) in enumerate(entries):
        capacity = capacities[index]
        credits = free_credits[index]
        if capacity <= 0 or not 0 <= credits <= capacity:
            raise ValueError("candidate credits must be within capacity")
        distance = abs(entry_row - destination_row) + abs(
            entry_col - destination_col
        )
        scores.append(
            distance
            + congestion_weight * (1.0 - float(credits) / capacity)
        )

    best_score = min(scores)
    tied = tuple(
        index
        for index, score in enumerate(scores)
        if isclose(score, best_score, rel_tol=1e-12, abs_tol=1e-12)
    )
    if len(tied) == 1:
        selected = tied[0]
        next_pointer = tie_pointer
    else:
        selected = next(
            index
            for step in range(len(entries))
            for index in ((tie_pointer + step) % len(entries),)
            if index in tied
        )
        next_pointer = (selected + 1) % len(entries)

    return AdaptiveChoice(
        selected, next_pointer, tuple(scores), len(tied) > 1
    )


def route_vc_class(current, source, destination):
    """Return the VC class used by the actual router allocation decision."""

    if not all(is_router(router) for router in (current, source, destination)):
        raise ValueError("VC classification contains an invalid router ID")
    if source == destination:
        return VC_U

    if is_root(current):
        return VC_U if current == destination else VC_D

    if is_gateway(current):
        cluster = gateway_cluster(current)
        if is_worker(destination) and worker_cluster(destination) == cluster:
            return VC_D
        if current == destination:
            if is_worker(source) and worker_cluster(source) == cluster:
                return VC_U
            return VC_D
        return VC_U

    if is_worker(current):
        cluster = worker_cluster(current)
        if is_worker(destination) and worker_cluster(destination) == cluster:
            if is_worker(source) and worker_cluster(source) == cluster:
                return VC_U
            return VC_D
        return VC_U

    raise ValueError("unsupported router role for VC classification")


def vc_offsets(vc_class):
    if vc_class == VC_U:
        return (0, 1)
    if vc_class == VC_D:
        return (2, 3)
    raise ValueError(f"unknown Sumcheck VC class {vc_class}")


def entry_router(cluster, index, entries_per_cluster, entry_placement):
    entries = entry_coordinates(entries_per_cluster, entry_placement)
    if not 0 <= index < len(entries):
        raise ValueError(f"invalid entry index {index}")
    row, col = entries[index]
    return worker_id(cluster, row, col)


def build_undirected_links(entries_per_cluster, entry_placement):
    """Build all physical internal links in deterministic order."""

    entries = entry_coordinates(entries_per_cluster, entry_placement)
    links = []

    for cluster in range(NUM_CLUSTERS):
        for row in range(CLUSTER_ROWS):
            for col in range(CLUSTER_COLS):
                current = worker_id(cluster, row, col)
                if row + 1 < CLUSTER_ROWS:
                    links.append(
                        LinkSpec(
                            current,
                            worker_id(cluster, row + 1, col),
                            "Dim0Pos",
                            "Dim0Neg",
                            "mesh",
                        )
                    )
                if col + 1 < CLUSTER_COLS:
                    links.append(
                        LinkSpec(
                            current,
                            worker_id(cluster, row, col + 1),
                            "Dim1Pos",
                            "Dim1Neg",
                            "mesh",
                        )
                    )

        gateway = gateway_id(cluster)
        for index, (row, col) in enumerate(entries):
            links.append(
                LinkSpec(
                    worker_id(cluster, row, col),
                    gateway,
                    "Gateway",
                    f"Entry{index}",
                    "gateway_entry",
                )
            )

        links.append(
            LinkSpec(
                gateway,
                ROOT_ID,
                "RootUp",
                f"RootToG{cluster}",
                "root_gateway",
            )
        )

    return tuple(links)


def physical_adjacency(entries_per_cluster, entry_placement):
    adjacency = {}
    for link in build_undirected_links(entries_per_cluster, entry_placement):
        adjacency[(link.node_a, link.node_b)] = link.port_a
        adjacency[(link.node_b, link.node_a)] = link.port_b
    return adjacency


def _mesh_next_hop(current, destination):
    if not is_worker(current) or not is_worker(destination):
        raise ValueError("mesh routing requires worker routers")
    if worker_cluster(current) != worker_cluster(destination):
        raise ValueError("mesh routing cannot cross clusters")

    cluster = worker_cluster(current)
    row, col = worker_coordinate(current)
    dest_row, dest_col = worker_coordinate(destination)
    if row < dest_row:
        return worker_id(cluster, row + 1, col)
    if row > dest_row:
        return worker_id(cluster, row - 1, col)
    if col < dest_col:
        return worker_id(cluster, row, col + 1)
    if col > dest_col:
        return worker_id(cluster, row, col - 1)
    raise ValueError("mesh route requested at destination")


def deterministic_next_hop(
    current, source, destination, entries_per_cluster, entry_placement
):
    """Return the complete Phase-1 fixed-routing next hop."""

    validate_configuration(entries_per_cluster, entry_placement)
    if not all(is_router(router) for router in (current, source, destination)):
        raise ValueError("Sumcheck route contains an invalid router ID")
    if current == destination:
        raise ValueError("next hop requested at destination")

    if is_worker(current):
        current_cluster = worker_cluster(current)
        if (
            is_worker(destination)
            and worker_cluster(destination) == current_cluster
        ):
            return _mesh_next_hop(current, destination)

        if not is_worker(source) or worker_cluster(source) != current_cluster:
            raise ValueError("illegal non-local route from a worker router")
        index = nearest_entry_index(
            source, entries_per_cluster, entry_placement
        )
        assigned_entry = entry_router(
            current_cluster, index, entries_per_cluster, entry_placement
        )
        if current != assigned_entry:
            return _mesh_next_hop(current, assigned_entry)
        return gateway_id(current_cluster)

    if is_gateway(current):
        cluster = gateway_cluster(current)
        if is_worker(destination) and worker_cluster(destination) == cluster:
            index = nearest_entry_index(
                destination, entries_per_cluster, entry_placement
            )
            return entry_router(
                cluster, index, entries_per_cluster, entry_placement
            )
        if is_root(destination):
            return ROOT_ID
        if is_gateway(destination) and destination != current:
            return ROOT_ID
        if is_worker(destination) and worker_cluster(destination) != cluster:
            return ROOT_ID
        raise ValueError("unsupported route at gateway")

    if is_root(current):
        if is_worker(destination):
            return gateway_id(worker_cluster(destination))
        if is_gateway(destination):
            return destination
        raise ValueError("unsupported route at root")

    raise ValueError("unsupported router role")


def deterministic_route(source, destination, entries_per_cluster, placement):
    if source == destination:
        return (source,)

    adjacency = physical_adjacency(entries_per_cluster, placement)
    route = [source]
    current = source
    while current != destination:
        next_hop = deterministic_next_hop(
            current, source, destination, entries_per_cluster, placement
        )
        if (current, next_hop) not in adjacency:
            raise ValueError(
                f"route selected absent physical link {current}->{next_hop}"
            )
        if next_hop in route:
            raise ValueError(f"routing loop: {route + [next_hop]}")
        route.append(next_hop)
        current = next_hop
        if len(route) > NUM_ROUTERS:
            raise ValueError("route exceeded router count")
    return tuple(route)


def _cpp_coordinate_list(coordinates):
    padded = tuple(coordinates) + ((0, 0),) * (4 - len(coordinates))
    return ", ".join(f"Coord{{{row}, {col}}}" for row, col in padded)


def render_cpp_header():
    """Render the C++ mapping used by Garnet deterministic routing."""

    p1 = _cpp_coordinate_list(ENTRY_PLACEMENTS[(1, STAGGERED)])
    p2 = _cpp_coordinate_list(ENTRY_PLACEMENTS[(2, STAGGERED)])
    p4 = _cpp_coordinate_list(ENTRY_PLACEMENTS[(4, STAGGERED)])
    corners = _cpp_coordinate_list(ENTRY_PLACEMENTS[(4, CORNERS)])
    return f"""// This file is generated from configs/topologies/SumcheckConfig.py.
// Run tests/pyunit/pyunit_sumcheck_topology.py to verify it is current.

#ifndef __MEM_RUBY_NETWORK_GARNET_SUMCHECK_CONFIG_HH__
#define __MEM_RUBY_NETWORK_GARNET_SUMCHECK_CONFIG_HH__

#include <array>
#include <cassert>
#include <limits>

namespace gem5
{{
namespace ruby
{{
namespace garnet
{{
namespace sumcheck
{{

inline constexpr int NumClusters = {NUM_CLUSTERS};
inline constexpr int ClusterRows = {CLUSTER_ROWS};
inline constexpr int ClusterCols = {CLUSTER_COLS};
inline constexpr int WorkersPerCluster = {WORKERS_PER_CLUSTER};
inline constexpr int NumWorkers = {NUM_WORKERS};
inline constexpr int GatewayBaseId = {GATEWAY_BASE_ID};
inline constexpr int RootId = {ROOT_ID};
inline constexpr int NumRouters = {NUM_ROUTERS};

struct Coord
{{
    int row;
    int col;
}};

enum class VcClass
{{
    Up,
    Down,
    Any,
}};

struct AdaptiveEntryChoice
{{
    int index;
    unsigned next_tie_pointer;
    bool tied;
}};

inline constexpr std::array<Coord, 4> EntriesP1 = {{{{{p1}}}}};
inline constexpr std::array<Coord, 4> EntriesP2 = {{{{{p2}}}}};
inline constexpr std::array<Coord, 4> EntriesP4 = {{{{{p4}}}}};
inline constexpr std::array<Coord, 4> EntriesP4Corners = {{{{{corners}}}}};

constexpr bool isWorker(int router_id)
{{
    return router_id >= 0 && router_id < NumWorkers;
}}

constexpr bool isGateway(int router_id)
{{
    return router_id >= GatewayBaseId && router_id < RootId;
}}

constexpr bool isRoot(int router_id)
{{
    return router_id == RootId;
}}

constexpr bool isRouter(int router_id)
{{
    return router_id >= 0 && router_id < NumRouters;
}}

constexpr int workerCluster(int router_id)
{{
    return router_id / WorkersPerCluster;
}}

constexpr Coord workerCoord(int router_id)
{{
    const int local = router_id % WorkersPerCluster;
    return Coord{{local / ClusterCols, local % ClusterCols}};
}}

constexpr int workerId(int cluster, Coord coord)
{{
    return cluster * WorkersPerCluster + coord.row * ClusterCols + coord.col;
}}

constexpr int gatewayId(int cluster)
{{
    return GatewayBaseId + cluster;
}}

constexpr int gatewayCluster(int router_id)
{{
    return router_id - GatewayBaseId;
}}

constexpr bool validEntryConfiguration(unsigned count, bool corners)
{{
    return (count == 1 && !corners) || (count == 2 && !corners) ||
           count == 4;
}}

inline const std::array<Coord, 4>&
entryTable(unsigned count, bool corners)
{{
    assert(validEntryConfiguration(count, corners));
    if (count == 1)
        return EntriesP1;
    if (count == 2)
        return EntriesP2;
    return corners ? EntriesP4Corners : EntriesP4;
}}

constexpr int absDistance(int value)
{{
    return value < 0 ? -value : value;
}}

inline int
nearestEntryIndex(int worker_id, unsigned count, bool corners)
{{
    assert(isWorker(worker_id));
    const Coord destination = workerCoord(worker_id);
    const auto &entries = entryTable(count, corners);
    int best_index = 0;
    int best_distance = ClusterRows + ClusterCols;
    for (unsigned index = 0; index < count; ++index) {{
        const int distance = absDistance(entries[index].row - destination.row) +
                             absDistance(entries[index].col - destination.col);
        if (distance < best_distance) {{
            best_distance = distance;
            best_index = index;
        }}
    }}
    return best_index;
}}

inline AdaptiveEntryChoice
chooseAdaptiveEntry(int worker_id, unsigned count, bool corners,
                    const std::array<int, 4> &free_credits,
                    const std::array<int, 4> &capacities,
                    double congestion_weight, unsigned tie_pointer)
{{
    assert(isWorker(worker_id));
    assert(validEntryConfiguration(count, corners));
    assert(congestion_weight >= 0.0);
    assert(tie_pointer < count);
    const Coord destination = workerCoord(worker_id);
    const auto &entries = entryTable(count, corners);
    std::array<double, 4> scores{{}};
    double best_score = std::numeric_limits<double>::infinity();
    for (unsigned entry = 0; entry < count; ++entry) {{
        assert(capacities[entry] > 0);
        assert(free_credits[entry] >= 0 &&
               free_credits[entry] <= capacities[entry]);
        const int distance =
            absDistance(entries[entry].row - destination.row) +
            absDistance(entries[entry].col - destination.col);
        scores[entry] = distance + congestion_weight *
            (1.0 - static_cast<double>(free_credits[entry]) /
                   capacities[entry]);
        if (scores[entry] < best_score)
            best_score = scores[entry];
    }}

    std::array<bool, 4> minimum{{}};
    int tie_count = 0;
    for (unsigned entry = 0; entry < count; ++entry) {{
        double difference = scores[entry] - best_score;
        if (difference < 0.0)
            difference = -difference;
        if (difference <= 1e-12) {{
            minimum[entry] = true;
            ++tie_count;
        }}
    }}

    if (tie_count == 1) {{
        for (unsigned entry = 0; entry < count; ++entry) {{
            if (minimum[entry])
                return AdaptiveEntryChoice{{
                    static_cast<int>(entry), tie_pointer, false}};
        }}
    }}

    for (unsigned step = 0; step < count; ++step) {{
        const unsigned entry = (tie_pointer + step) % count;
        if (minimum[entry])
            return AdaptiveEntryChoice{{
                static_cast<int>(entry), (entry + 1) % count, true}};
    }}
    assert(false);
    return AdaptiveEntryChoice{{0, tie_pointer, false}};
}}

constexpr int
vcOffsetBegin(VcClass vc_class)
{{
    return vc_class == VcClass::Down ? 2 : 0;
}}

constexpr int
vcOffsetEnd(VcClass vc_class, int vcs_per_vnet)
{{
    return vc_class == VcClass::Up ? 2 :
           vc_class == VcClass::Down ? 4 : vcs_per_vnet;
}}

inline VcClass
routeVcClass(int current, int source, int destination)
{{
    assert(isRouter(current) && isRouter(source) && isRouter(destination));
    if (source == destination)
        return VcClass::Up;

    if (isRoot(current))
        return current == destination ? VcClass::Up : VcClass::Down;

    if (isGateway(current)) {{
        const int cluster = gatewayCluster(current);
        if (isWorker(destination) && workerCluster(destination) == cluster)
            return VcClass::Down;
        if (current == destination) {{
            if (isWorker(source) && workerCluster(source) == cluster)
                return VcClass::Up;
            return VcClass::Down;
        }}
        return VcClass::Up;
    }}

    if (isWorker(current)) {{
        const int cluster = workerCluster(current);
        if (isWorker(destination) && workerCluster(destination) == cluster) {{
            if (isWorker(source) && workerCluster(source) == cluster)
                return VcClass::Up;
            return VcClass::Down;
        }}
        return VcClass::Up;
    }}

    assert(false);
    return VcClass::Any;
}}

}} // namespace sumcheck
}} // namespace garnet
}} // namespace ruby
}} // namespace gem5

#endif // __MEM_RUBY_NETWORK_GARNET_SUMCHECK_CONFIG_HH__
"""
