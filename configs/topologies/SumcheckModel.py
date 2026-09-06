"""Canonical, m5-free model of the Sumcheck hierarchical NoC."""

from dataclasses import dataclass


DEFAULT_NUM_CLUSTERS = 4
DEFAULT_CLUSTER_ROWS = 4
DEFAULT_CLUSTER_COLS = 4
SUPPORTED_ENTRY_COUNTS = (1, 2, 4)
DEFAULT_BASELINE_GATEWAY_ROUTERS = (18, 21, 42, 45)
DEFAULT_BASELINE_ROOT_ROUTER = DEFAULT_BASELINE_GATEWAY_ROUTERS[0]


class IllegalRoute(ValueError):
    pass


@dataclass(frozen=True)
class Link:
    a: int
    b: int
    a_port: str
    b_port: str
    kind: str


@dataclass(frozen=True)
class HierarchyModel:
    num_clusters: int = DEFAULT_NUM_CLUSTERS
    rows: int = DEFAULT_CLUSTER_ROWS
    cols: int = DEFAULT_CLUSTER_COLS

    def __post_init__(self):
        if self.num_clusters <= 0:
            raise ValueError("num_clusters must be positive")
        if self.rows <= 0 or self.cols <= 0:
            raise ValueError("cluster dimensions must be positive")

    @property
    def workers_per_cluster(self):
        return self.rows * self.cols

    @property
    def num_workers(self):
        return self.num_clusters * self.workers_per_cluster

    @property
    def gateway_base(self):
        return self.num_workers

    @property
    def root(self):
        return self.gateway_base + self.num_clusters

    @property
    def num_routers(self):
        return self.root + 1

    def entry_coordinates(self, entries):
        check_p(entries)
        coordinates = (
            (0, (self.cols - 1) // 2),
            ((self.rows - 1) // 2, self.cols - 1),
            (self.rows // 2, 0),
            (self.rows - 1, self.cols // 2),
        )
        if entries == 1:
            coordinates = (
                ((self.rows - 1) // 2, (self.cols - 1) // 2),
            )
        elif entries == 2:
            coordinates = (coordinates[0], coordinates[3])
        if len(set(coordinates)) != entries:
            raise ValueError(
                f"{self.rows}x{self.cols} cluster cannot place "
                f"{entries} distinct entries"
            )
        return coordinates

    def is_worker(self, router):
        return 0 <= router < self.num_workers

    def is_gateway(self, router):
        return self.gateway_base <= router < self.root

    def worker_id(self, cluster, row, col):
        if not (
            0 <= cluster < self.num_clusters
            and 0 <= row < self.rows
            and 0 <= col < self.cols
        ):
            raise ValueError("invalid worker coordinate")
        return cluster * self.workers_per_cluster + row * self.cols + col

    def worker_cluster(self, worker):
        if not self.is_worker(worker):
            raise ValueError(f"router {worker} is not a worker")
        return worker // self.workers_per_cluster

    def worker_coordinate(self, worker):
        if not self.is_worker(worker):
            raise ValueError(f"router {worker} is not a worker")
        return divmod(worker % self.workers_per_cluster, self.cols)

    def gateway_id(self, cluster):
        if not 0 <= cluster < self.num_clusters:
            raise ValueError(f"invalid cluster {cluster}")
        return self.gateway_base + cluster

    def gateway_cluster(self, gateway):
        if not self.is_gateway(gateway):
            raise ValueError(f"router {gateway} is not a gateway")
        return gateway - self.gateway_base

    def entry_routers(self, cluster, entries):
        return tuple(
            self.worker_id(cluster, row, col)
            for row, col in self.entry_coordinates(entries)
        )

    def assigned_entry_index(self, worker, entries):
        row, col = self.worker_coordinate(worker)
        coordinates = self.entry_coordinates(entries)
        return min(
            range(entries),
            key=lambda index: (
                abs(row - coordinates[index][0])
                + abs(col - coordinates[index][1]),
                index,
            ),
        )

    def assigned_entry(self, worker, entries):
        cluster = self.worker_cluster(worker)
        index = self.assigned_entry_index(worker, entries)
        return self.entry_routers(cluster, entries)[index]

    def physical_links(self, entries):
        self.entry_coordinates(entries)
        links = []
        for cluster in range(self.num_clusters):
            for row in range(self.rows):
                for col in range(self.cols):
                    here = self.worker_id(cluster, row, col)
                    if row + 1 < self.rows:
                        links.append(Link(
                            here, self.worker_id(cluster, row + 1, col),
                            "Dim0Pos", "Dim0Neg", "mesh"))
                    if col + 1 < self.cols:
                        links.append(Link(
                            here, self.worker_id(cluster, row, col + 1),
                            "Dim1Pos", "Dim1Neg", "mesh"))
            gateway = self.gateway_id(cluster)
            for index, entry in enumerate(self.entry_routers(cluster, entries)):
                links.append(Link(
                    entry, gateway, "Gateway", f"Entry{index}",
                    "gateway_entry"))
            links.append(Link(
                gateway, self.root, "RootUp", f"RootToG{cluster}",
                "root_gateway"))
        return tuple(links)

    def adjacency(self, entries):
        result = {}
        for link in self.physical_links(entries):
            result[(link.a, link.b)] = link.a_port
            result[(link.b, link.a)] = link.b_port
        return result

    def mesh_route(self, source, destination):
        if not (self.is_worker(source) and self.is_worker(destination)):
            raise IllegalRoute("mesh endpoints must be workers")
        if self.worker_cluster(source) != self.worker_cluster(destination):
            raise IllegalRoute("mesh path cannot cross clusters")
        cluster = self.worker_cluster(source)
        row, col = self.worker_coordinate(source)
        dest_row, dest_col = self.worker_coordinate(destination)
        path = [source]
        while row != dest_row:
            row += 1 if row < dest_row else -1
            path.append(self.worker_id(cluster, row, col))
        while col != dest_col:
            col += 1 if col < dest_col else -1
            path.append(self.worker_id(cluster, row, col))
        return tuple(path)

    def legal_pair(self, source, destination, entries):
        self.entry_coordinates(entries)
        if self.is_worker(source):
            own_gateway = self.gateway_id(self.worker_cluster(source))
            return destination == own_gateway or (
                destination == self.assigned_entry(source, entries)
                and destination != source
            )
        if self.is_gateway(source):
            cluster = self.gateway_cluster(source)
            return destination == self.root or (
                self.is_worker(destination)
                and self.worker_cluster(destination) == cluster
            )
        return source == self.root and self.is_gateway(destination)

    def legal_pairs(self, entries):
        return tuple(
            (source, destination)
            for source in range(self.num_routers)
            for destination in range(self.num_routers)
            if self.legal_pair(source, destination, entries)
        )

    def route(self, source, destination, entries, entry_index=None):
        if not self.legal_pair(source, destination, entries):
            raise IllegalRoute(
                f"unsupported Sumcheck pair {source}->{destination}"
            )

        if self.is_worker(source):
            if destination == self.gateway_id(self.worker_cluster(source)):
                entry = self.assigned_entry(source, entries)
                path = list(self.mesh_route(source, entry))
                path.append(destination)
                result = tuple(path)
            else:
                result = self.mesh_route(source, destination)
        elif self.is_gateway(source):
            if destination == self.root:
                result = (source, self.root)
            else:
                if entry_index is None:
                    entry_index = self.assigned_entry_index(
                        destination, entries
                    )
                if not 0 <= entry_index < entries:
                    raise IllegalRoute(f"invalid entry index {entry_index}")
                entry = self.entry_routers(
                    self.gateway_cluster(source), entries
                )[entry_index]
                result = (source,) + self.mesh_route(entry, destination)
        else:
            result = (self.root, destination)

        graph = self.adjacency(entries)
        if any(edge not in graph for edge in zip(result, result[1:])):
            raise AssertionError(f"route uses absent link: {result}")
        return result

    def legal_routes(self, entries):
        routes = []
        for source, destination in self.legal_pairs(entries):
            choices = (
                range(entries)
                if self.is_gateway(source) and self.is_worker(destination)
                else (None,)
            )
            routes.extend(
                self.route(source, destination, entries, choice)
                for choice in choices
            )
        return tuple(routes)


def check_p(entries):
    if entries not in SUPPORTED_ENTRY_COUNTS:
        supported = ", ".join(map(str, SUPPORTED_ENTRY_COUNTS))
        raise ValueError(
            f"entries_per_cluster must be one of {supported}; got {entries}"
        )


DEFAULT_MODEL = HierarchyModel()
CLUSTERS = DEFAULT_MODEL.num_clusters
ROWS = DEFAULT_MODEL.rows
COLS = DEFAULT_MODEL.cols
WORKERS_PER_CLUSTER = DEFAULT_MODEL.workers_per_cluster
NUM_WORKERS = DEFAULT_MODEL.num_workers
GATEWAY_BASE = DEFAULT_MODEL.gateway_base
ROOT = DEFAULT_MODEL.root
NUM_ROUTERS = DEFAULT_MODEL.num_routers
ENTRY_COORDINATES = {
    entries: DEFAULT_MODEL.entry_coordinates(entries)
    for entries in SUPPORTED_ENTRY_COUNTS
}


def is_worker(router):
    return DEFAULT_MODEL.is_worker(router)


def is_gateway(router):
    return DEFAULT_MODEL.is_gateway(router)


def worker_id(cluster, row, col):
    return DEFAULT_MODEL.worker_id(cluster, row, col)


def worker_cluster(worker):
    return DEFAULT_MODEL.worker_cluster(worker)


def worker_coordinate(worker):
    return DEFAULT_MODEL.worker_coordinate(worker)


def gateway_id(cluster):
    return DEFAULT_MODEL.gateway_id(cluster)


def gateway_cluster(gateway):
    return DEFAULT_MODEL.gateway_cluster(gateway)


def entry_routers(cluster, entries):
    return DEFAULT_MODEL.entry_routers(cluster, entries)


def assigned_entry_index(worker, entries):
    return DEFAULT_MODEL.assigned_entry_index(worker, entries)


def assigned_entry(worker, entries):
    return DEFAULT_MODEL.assigned_entry(worker, entries)


def physical_links(entries):
    return DEFAULT_MODEL.physical_links(entries)


def adjacency(entries):
    return DEFAULT_MODEL.adjacency(entries)


def mesh_route(source, destination):
    return DEFAULT_MODEL.mesh_route(source, destination)


def legal_pair(source, destination, entries):
    return DEFAULT_MODEL.legal_pair(source, destination, entries)


def legal_pairs(entries):
    return DEFAULT_MODEL.legal_pairs(entries)


def route(source, destination, entries, entry_index=None):
    return DEFAULT_MODEL.route(source, destination, entries, entry_index)


def deterministic_route(source, destination, entries):
    return DEFAULT_MODEL.route(source, destination, entries)


def legal_routes(entries):
    return DEFAULT_MODEL.legal_routes(entries)


# The default 8x8 baseline maps gateways and root onto worker routers.
MESH_ENDPOINT_ROUTERS = (
    tuple(range(NUM_WORKERS))
    + DEFAULT_BASELINE_GATEWAY_ROUTERS
    + (DEFAULT_BASELINE_ROOT_ROUTER,)
)

# Descriptive compatibility aliases.
NUM_CLUSTERS = CLUSTERS
NUM_GATEWAYS = CLUSTERS
ROOT_ID = ROOT
GATEWAY_BASE_ID = GATEWAY_BASE
build_undirected_links = physical_links
