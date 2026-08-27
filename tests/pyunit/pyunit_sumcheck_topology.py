import sys
import unittest
from collections import Counter
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "configs"))

from topologies.SumcheckConfig import (  # noqa: E402
    CONTROLLER_TO_ROUTER,
    CORNERS,
    ENTRY_PLACEMENTS,
    GATEWAY_BASE_ID,
    NUM_ROUTERS,
    NUM_WORKERS,
    ROOT_ID,
    STAGGERED,
    build_undirected_links,
    deterministic_route,
    entry_coordinates,
    entry_router,
    gateway_id,
    is_gateway,
    is_root,
    is_worker,
    nearest_entry_index,
    physical_adjacency,
    render_cpp_header,
    worker_cluster,
    worker_coordinate,
    worker_id,
)


CONFIGURATIONS = (
    (1, STAGGERED, 104),
    (2, STAGGERED, 108),
    (4, STAGGERED, 116),
    (4, CORNERS, 116),
)


class SumcheckMappingTests(unittest.TestCase):
    def test_all_router_ids_and_controller_mapping(self):
        self.assertEqual(NUM_ROUTERS, 69)
        self.assertEqual(len(CONTROLLER_TO_ROUTER), 72)
        self.assertEqual(len(set(CONTROLLER_TO_ROUTER)), 69)
        self.assertEqual(CONTROLLER_TO_ROUTER[:63], tuple(range(63)))
        self.assertEqual(CONTROLLER_TO_ROUTER[63], ROOT_ID)
        self.assertEqual(CONTROLLER_TO_ROUTER[64], 63)
        self.assertEqual(CONTROLLER_TO_ROUTER[65:69], tuple(range(64, 68)))
        self.assertEqual(CONTROLLER_TO_ROUTER[69:], (ROOT_ID,) * 3)

        for router_id in range(NUM_ROUTERS):
            roles = (
                is_worker(router_id),
                is_gateway(router_id),
                is_root(router_id),
            )
            self.assertEqual(sum(roles), 1)
            if is_worker(router_id):
                cluster = worker_cluster(router_id)
                row, col = worker_coordinate(router_id)
                self.assertEqual(worker_id(cluster, row, col), router_id)
            elif is_gateway(router_id):
                self.assertEqual(
                    gateway_id(router_id - GATEWAY_BASE_ID), router_id
                )

    def test_exact_entry_coordinates(self):
        expected = {
            (1, STAGGERED): ((1, 1),),
            (2, STAGGERED): ((0, 1), (3, 2)),
            (4, STAGGERED): ((0, 1), (1, 3), (2, 0), (3, 2)),
            (4, CORNERS): ((0, 0), (0, 3), (3, 0), (3, 3)),
        }
        self.assertEqual(ENTRY_PLACEMENTS, expected)
        for key, coordinates in expected.items():
            self.assertEqual(entry_coordinates(*key), coordinates)
        with self.assertRaises(ValueError):
            entry_coordinates(2, CORNERS)

    def test_generated_cpp_mapping_is_current(self):
        header = (
            REPO_ROOT / "src/mem/ruby/network/garnet/SumcheckConfig.hh"
        ).read_text()
        self.assertEqual(header, render_cpp_header())


class SumcheckTopologyTests(unittest.TestCase):
    def test_router_and_undirected_link_counts(self):
        for entries, placement, expected_links in CONFIGURATIONS:
            with self.subTest(entries=entries, placement=placement):
                links = build_undirected_links(entries, placement)
                self.assertEqual(NUM_ROUTERS, 69)
                self.assertEqual(len(links), expected_links)
                self.assertEqual(
                    len(physical_adjacency(entries, placement)),
                    2 * expected_links,
                )
                self.assertEqual(
                    Counter(link.latency_class for link in links),
                    {
                        "mesh": 96,
                        "gateway_entry": 4 * entries,
                        "root_gateway": 4,
                    },
                )

    def test_port_names_are_unique_and_stable(self):
        for entries, placement, _ in CONFIGURATIONS:
            with self.subTest(entries=entries, placement=placement):
                ports = set()
                undirected_edges = set()
                for link in build_undirected_links(entries, placement):
                    edge = frozenset((link.node_a, link.node_b))
                    self.assertNotIn(edge, undirected_edges)
                    undirected_edges.add(edge)
                    for endpoint in (
                        (link.node_a, link.port_a),
                        (link.node_b, link.port_b),
                    ):
                        self.assertNotIn(endpoint, ports)
                        ports.add(endpoint)

    def test_every_ordered_route_uses_physical_links(self):
        for entries, placement, _ in CONFIGURATIONS:
            adjacency = physical_adjacency(entries, placement)
            for source in range(NUM_ROUTERS):
                for destination in range(NUM_ROUTERS):
                    if source == destination:
                        continue
                    route = deterministic_route(
                        source, destination, entries, placement
                    )
                    self.assertEqual(route[0], source)
                    self.assertEqual(route[-1], destination)
                    self.assertEqual(len(route), len(set(route)))
                    for edge in zip(route, route[1:]):
                        self.assertIn(edge, adjacency)

    def test_nearest_entry_and_smaller_index_tie_break(self):
        ties_checked = 0
        for entries, placement, _ in CONFIGURATIONS:
            coordinates = entry_coordinates(entries, placement)
            for cluster in range(4):
                gateway = gateway_id(cluster)
                for row in range(4):
                    for col in range(4):
                        destination = worker_id(cluster, row, col)
                        distances = [
                            abs(entry_row - row) + abs(entry_col - col)
                            for entry_row, entry_col in coordinates
                        ]
                        expected = distances.index(min(distances))
                        actual = nearest_entry_index(
                            destination, entries, placement
                        )
                        self.assertEqual(actual, expected)
                        route = deterministic_route(
                            gateway, destination, entries, placement
                        )
                        self.assertEqual(
                            route[1],
                            entry_router(
                                cluster, expected, entries, placement
                            ),
                        )
                        if distances.count(min(distances)) > 1:
                            ties_checked += 1
                            self.assertEqual(
                                actual,
                                min(
                                    index
                                    for index, distance in enumerate(distances)
                                    if distance == min(distances)
                                ),
                            )
        self.assertGreater(ties_checked, 0)

    def test_all_mesh_segments_are_strict_dim0_then_dim1(self):
        for entries, placement, _ in CONFIGURATIONS:
            for source in range(NUM_ROUTERS):
                for destination in range(NUM_ROUTERS):
                    if source == destination:
                        continue
                    route = deterministic_route(
                        source, destination, entries, placement
                    )
                    saw_dim1 = False
                    previous_cluster = None
                    for current, next_hop in zip(route, route[1:]):
                        if not is_worker(current) or not is_worker(next_hop):
                            saw_dim1 = False
                            previous_cluster = None
                            continue
                        cluster = worker_cluster(current)
                        if cluster != worker_cluster(next_hop):
                            self.fail("worker mesh edge crossed clusters")
                        if previous_cluster != cluster:
                            saw_dim1 = False
                        current_row, current_col = worker_coordinate(current)
                        next_row, next_col = worker_coordinate(next_hop)
                        if current_row != next_row:
                            self.assertFalse(saw_dim1)
                            self.assertEqual(current_col, next_col)
                        else:
                            self.assertNotEqual(current_col, next_col)
                            saw_dim1 = True
                        previous_cluster = cluster


if __name__ == "__main__":
    unittest.main(verbosity=2)
