#!/usr/bin/env python3

import sys
import unittest

sys.path.insert(0, "configs")

from topologies.SumcheckConfig import (  # noqa: E402
    MESH_CONTROLLER_TO_ROUTER,
    build_undirected_links,
    deterministic_route,
    mesh_xy_route,
)
from topologies.SumcheckWorkload import (  # noqa: E402
    build_aggregated_trace,
    build_synthetic_trace,
)


class Phase04Tests(unittest.TestCase):
    def test_mesh_quadrants_and_controllers(self):
        self.assertEqual(len(MESH_CONTROLLER_TO_ROUTER), 69)
        self.assertEqual(MESH_CONTROLLER_TO_ROUTER[:16], tuple(
            row * 8 + col for row in range(4) for col in range(4)
        ))
        self.assertEqual(MESH_CONTROLLER_TO_ROUTER[64:], (18, 21, 42, 45, 18))

    def test_mesh_xy_routes_are_real(self):
        for source in range(69):
            for destination in range(69):
                if source == destination:
                    continue
                route = mesh_xy_route(source, destination)
                for node_a, node_b in zip(route, route[1:]):
                    self.assertIn(abs(node_a - node_b), (1, 8))

    def test_hierarchy_reference_flit_hops(self):
        expected = {1: 22448, 2: 18160, 4: 11952}
        for entries, total in expected.items():
            events = build_aggregated_trace(entries)
            actual = sum(
                ((event.size_bytes + 15) // 16)
                * (len(deterministic_route(
                    event.source, event.destination, entries, "staggered"
                )) - 1)
                for event in events
            )
            self.assertEqual(actual, total)

    def test_synthetic_is_deterministic_and_released(self):
        first = build_synthetic_trace("uniform-random", 0.02, 7, 200)
        second = build_synthetic_trace("uniform-random", 0.02, 7, 200)
        self.assertEqual(first, second)
        self.assertTrue(all(event.release_cycle > 0 for event in first))
        self.assertTrue(all(not event.depends_on for event in first))

    def test_buffer_bracket_arithmetic(self):
        mesh_inputs = 224 + 69
        hierarchy_inputs = 232 + 69
        mesh_slots = mesh_inputs * (2 * 4 * 1 + 4 * 4)
        lower = hierarchy_inputs * (2 * 4 * 1 + 4 * 3)
        upper = hierarchy_inputs * (2 * 4 * 1 + 4 * 4)
        self.assertLess(lower, mesh_slots)
        self.assertGreater(upper, mesh_slots)


if __name__ == "__main__":
    unittest.main()
