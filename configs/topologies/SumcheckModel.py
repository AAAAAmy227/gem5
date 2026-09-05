"""Canonical, m5-free model of the Sumcheck Minimal NoC."""

from dataclasses import dataclass


CLUSTERS = 4
ROWS = COLS = 4
WORKERS_PER_CLUSTER = ROWS * COLS
NUM_WORKERS = CLUSTERS * WORKERS_PER_CLUSTER
GATEWAY_BASE = NUM_WORKERS
ROOT = GATEWAY_BASE + CLUSTERS
NUM_ROUTERS = ROOT + 1
ENTRY_COORDINATES = {
    1: ((1, 1),),
    2: ((0, 1), (3, 2)),
    4: ((0, 1), (1, 3), (2, 0), (3, 2)),
}
MESH_ENDPOINT_ROUTERS = tuple(range(64)) + (18, 21, 42, 45, 18)
# map 69 endpoints to 64 actual routers in sumcheck mesh

class IllegalRoute(ValueError):
    pass


@dataclass(frozen=True)
class Link:
    a: int
    b: int
    a_port: str
    b_port: str
    kind: str


def check_p(p):
    if p not in ENTRY_COORDINATES:
        raise ValueError(f"entries_per_cluster must be 1, 2, or 4; got {p}")


def is_worker(router):
    return 0 <= router < NUM_WORKERS


def is_gateway(router):
    return GATEWAY_BASE <= router < ROOT


def worker_id(cluster, row, col):
    if not (0 <= cluster < CLUSTERS and 0 <= row < ROWS and 0 <= col < COLS):
        raise ValueError("invalid worker coordinate")
    return cluster * WORKERS_PER_CLUSTER + row * COLS + col


def worker_cluster(worker):
    if not is_worker(worker):
        raise ValueError(f"router {worker} is not a worker")
    return worker // WORKERS_PER_CLUSTER


def worker_coordinate(worker):
    return divmod(worker % WORKERS_PER_CLUSTER, COLS)


def gateway_id(cluster):
    if not 0 <= cluster < CLUSTERS:
        raise ValueError(f"invalid cluster {cluster}")
    return GATEWAY_BASE + cluster


def gateway_cluster(gateway): # return the cluster that the gateway is in
    if not is_gateway(gateway):
        raise ValueError(f"router {gateway} is not a gateway")
    return gateway - GATEWAY_BASE


def entry_routers(cluster, p):
    check_p(p)
    return tuple(worker_id(cluster, *coord) for coord in ENTRY_COORDINATES[p])


def assigned_entry_index(worker, p):
    """Nearest entry(Manhattan-distance). Break ties using index"""
    check_p(p)
    row, col = worker_coordinate(worker)
    return min(
        range(p),
        key=lambda i: (
            abs(row - ENTRY_COORDINATES[p][i][0])
            + abs(col - ENTRY_COORDINATES[p][i][1]),
            i,
        ),
    )


def assigned_entry(worker, p):
    return entry_routers(worker_cluster(worker), p)[assigned_entry_index(worker, p)]


def physical_links(p):
    """All undirected internal links, in stable construction order."""
    check_p(p)
    links = []
    for cluster in range(CLUSTERS):
        for row in range(ROWS):
            for col in range(COLS):
                here = worker_id(cluster, row, col)
                if row + 1 < ROWS:
                    links.append(Link(
                        here, worker_id(cluster, row + 1, col),
                        "Dim0Pos", "Dim0Neg", "mesh"))
                if col + 1 < COLS:
                    links.append(Link(
                        here, worker_id(cluster, row, col + 1),
                        "Dim1Pos", "Dim1Neg", "mesh"))
        gateway = gateway_id(cluster)
        for index, entry in enumerate(entry_routers(cluster, p)):
            links.append(Link(
                entry, gateway, "Gateway", f"Entry{index}", "gateway_entry"))
        links.append(Link(
            gateway, ROOT, "RootUp", f"RootToG{cluster}", "root_gateway"))
    return tuple(links)


def adjacency(p):  #(cur_router, next_router) -> which port of current router
    result = {}
    for link in physical_links(p):
        result[(link.a, link.b)] = link.a_port
        result[(link.b, link.a)] = link.b_port
    return result


def mesh_route(source, destination):
    """Strict Dim0-then-Dim1 path, including both endpoints."""
    if not (is_worker(source) and is_worker(destination)):
        raise IllegalRoute("mesh endpoints must be workers")
    if worker_cluster(source) != worker_cluster(destination):
        raise IllegalRoute("mesh path cannot cross clusters")
    cluster = worker_cluster(source)
    row, col = worker_coordinate(source)
    dest_row, dest_col = worker_coordinate(destination)
    route = [source]
    while row != dest_row:
        row += 1 if row < dest_row else -1
        route.append(worker_id(cluster, row, col))
    while col != dest_col:
        col += 1 if col < dest_col else -1
        route.append(worker_id(cluster, row, col))
    return tuple(route)


def legal_pair(source, destination, p):
    check_p(p)
    if is_worker(source):
        own_gateway = gateway_id(worker_cluster(source))
        return destination == own_gateway or (
            destination == assigned_entry(source, p) and destination != source)
    if is_gateway(source):
        cluster = gateway_cluster(source)
        return destination == ROOT or (
            is_worker(destination) and worker_cluster(destination) == cluster)
    return source == ROOT and is_gateway(destination)


def legal_pairs(p):
    return tuple(
        (source, destination)
        for source in range(NUM_ROUTERS)
        for destination in range(NUM_ROUTERS)
        if legal_pair(source, destination, p)
    )


def route(source, destination, p, entry_index=None):
    """One legal route; entry_index is allowed only for gateway->worker."""
    if not legal_pair(source, destination, p):
        raise IllegalRoute(f"unsupported Sumcheck pair {source}->{destination}")

    if is_worker(source):
        if destination == gateway_id(worker_cluster(source)):
            entry = assigned_entry(source, p)
            path = list(mesh_route(source, entry))
            path.append(destination)
            result = tuple(path)
        else:
            result = mesh_route(source, destination)
    elif is_gateway(source):
        if destination == ROOT:
            result = (source, ROOT)
        else:
            if entry_index is None:
                entry_index = assigned_entry_index(destination, p)
            if not 0 <= entry_index < p:
                raise IllegalRoute(f"invalid entry index {entry_index}")
            entry = entry_routers(gateway_cluster(source), p)[entry_index]
            result = (source,) + mesh_route(entry, destination)
    else:
        result = (ROOT, destination)

    graph = adjacency(p)
    if any(edge not in graph for edge in zip(result, result[1:])):
        raise AssertionError(f"route uses absent link: {result}")
    return result


def deterministic_route(source, destination, p):
    return route(source, destination, p)


def legal_routes(p):
    """Complete relation, expanding every adaptive gateway entry choice."""
    routes = []
    for source, destination in legal_pairs(p):
        choices = range(p) if is_gateway(source) and is_worker(destination) else (None,)
        routes.extend(route(source, destination, p, choice) for choice in choices)
    return tuple(routes)


# Descriptive aliases used by topology/tests without duplicating constants.
NUM_CLUSTERS = CLUSTERS
NUM_GATEWAYS = CLUSTERS
ROOT_ID = ROOT
GATEWAY_BASE_ID = GATEWAY_BASE
build_undirected_links = physical_links
