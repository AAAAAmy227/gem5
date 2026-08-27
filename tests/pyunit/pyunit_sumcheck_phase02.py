import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "configs"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from topologies.SumcheckConfig import (  # noqa: E402
    NUM_ROUTERS,
    ROOT_ID,
    STAGGERED,
    VC_D,
    VC_U,
    choose_adaptive_entry,
    deterministic_route,
    entry_router,
    nearest_entry_index,
    render_cpp_header,
    route_vc_class,
    vc_offsets,
    worker_cluster,
    worker_coordinate,
    worker_id,
)
from sumcheck_cdg import (  # noqa: E402
    check_configuration,
    enumerate_legal_routes,
    validate_route_phases,
)


class AdaptiveEntryTests(unittest.TestCase):
    def test_congestion_can_choose_a_non_nearest_entry(self):
        destination = worker_id(0, 1, 1)
        self.assertEqual(nearest_entry_index(destination, 2, STAGGERED), 0)
        choice = choose_adaptive_entry(
            destination,
            2,
            STAGGERED,
            free_credits=(0, 8),
            capacities=(8, 8),
        )
        self.assertEqual(choice.index, 1)
        self.assertLess(choice.scores[1], choice.scores[0])

    def test_equal_scores_rotate_without_randomness(self):
        destination = worker_id(0, 1, 2)
        pointer = 0
        choices = []
        for _ in range(4):
            choice = choose_adaptive_entry(
                destination,
                2,
                STAGGERED,
                free_credits=(8, 8),
                capacities=(8, 8),
                tie_pointer=pointer,
            )
            self.assertTrue(choice.tied)
            choices.append(choice.index)
            pointer = choice.next_tie_pointer
        self.assertEqual(choices, [0, 1, 0, 1])

    def test_selected_entry_is_always_in_destination_cluster(self):
        destination = worker_id(3, 1, 1)
        choice = choose_adaptive_entry(
            destination,
            4,
            STAGGERED,
            free_credits=(0, 1, 7, 8),
            capacities=(8, 8, 8, 8),
        )
        selected_router = entry_router(3, choice.index, 4, STAGGERED)
        self.assertEqual(worker_cluster(selected_router), 3)

    def test_runtime_reads_only_candidate_down_vcs(self):
        routing = (
            REPO_ROOT / "src/mem/ruby/network/garnet/RoutingUnit.cc"
        ).read_text()
        self.assertIn("free_credits(\n                    route.vnet, VcClass::Down)", routing)
        self.assertIn("credit_capacity(\n                    route.vnet, VcClass::Down)", routing)

    def test_head_decision_is_persisted_in_input_vc(self):
        input_unit = (
            REPO_ROOT / "src/mem/ruby/network/garnet/InputUnit.cc"
        ).read_text()
        allocator = (
            REPO_ROOT / "src/mem/ruby/network/garnet/SwitchAllocator.cc"
        ).read_text()
        self.assertEqual(input_unit.count("route_compute("), 1)
        self.assertIn("grant_outport(vc, outport)", input_unit)
        self.assertNotIn("route_compute(", allocator)


class VcDisciplineTests(unittest.TestCase):
    def test_partition_offsets_are_exact_and_generated_header_matches(self):
        self.assertEqual(vc_offsets(VC_U), (0, 1))
        self.assertEqual(vc_offsets(VC_D), (2, 3))
        generated = (
            REPO_ROOT / "src/mem/ruby/network/garnet/SumcheckConfig.hh"
        ).read_text()
        self.assertEqual(generated, render_cpp_header())

    def test_real_allocator_uses_required_subset_for_check_and_selection(self):
        allocator = (
            REPO_ROOT / "src/mem/ruby/network/garnet/SwitchAllocator.cc"
        ).read_text()
        ni = (
            REPO_ROOT / "src/mem/ruby/network/garnet/NetworkInterface.cc"
        ).read_text()
        self.assertIn("has_free_vc(vnet, required_class)", allocator)
        self.assertIn("get_vnet(invc), required_class", allocator)
        self.assertIn("Illegal Sumcheck D->U VC transition", allocator)
        self.assertIn("Illegal Sumcheck U->D VC transition outside root", allocator)
        self.assertIn("sumcheck::vcOffsetBegin(vc_class)", ni)

    def test_every_legal_route_has_only_root_ud_transition(self):
        for entries in (1, 2, 4):
            for route in enumerate_legal_routes(entries, STAGGERED):
                validate_route_phases(route)
                saw_down = False
                for channel_class in route.classes:
                    if channel_class == VC_D:
                        saw_down = True
                    if saw_down:
                        self.assertNotEqual(channel_class, VC_U)
                for index in range(1, len(route.classes)):
                    if (
                        route.classes[index - 1] == VC_U
                        and route.classes[index] == VC_D
                    ):
                        self.assertEqual(route.routers[index], ROOT_ID)

    def test_initial_and_destination_classes_agree_with_route_phase(self):
        for source in range(NUM_ROUTERS):
            for destination in range(NUM_ROUTERS):
                if source == destination:
                    continue
                route = deterministic_route(source, destination, 4, STAGGERED)
                first = route_vc_class(source, source, destination)
                last = route_vc_class(destination, source, destination)
                self.assertIn(first, (VC_U, VC_D))
                self.assertIn(last, (VC_U, VC_D))


class CdgTests(unittest.TestCase):
    def test_required_counts_and_positive_negative_controls(self):
        expected = {1: 4692, 2: 14548, 4: 52692}
        for entries in (1, 2, 4):
            with self.subTest(entries=entries):
                report = check_configuration(entries, STAGGERED)
                self.assertEqual(report["ordered_pairs"], 4692)
                self.assertEqual(report["legal_routes"], expected[entries])
                self.assertTrue(report["separated_acyclic"])
                if entries in (2, 4):
                    self.assertFalse(report["collapsed_acyclic"])
                    witness = report["collapsed_cycle_witness"]
                    self.assertGreaterEqual(len(witness), 3)
                    self.assertEqual(witness[0], witness[-1])

    def test_all_legal_mesh_segments_remain_dim0_then_dim1(self):
        for entries in (1, 2, 4):
            for route in enumerate_legal_routes(entries, STAGGERED):
                saw_dim1 = False
                previous_cluster = None
                for current, following in zip(route.routers, route.routers[1:]):
                    if current >= 64 or following >= 64:
                        saw_dim1 = False
                        previous_cluster = None
                        continue
                    cluster = worker_cluster(current)
                    self.assertEqual(worker_cluster(following), cluster)
                    if previous_cluster != cluster:
                        saw_dim1 = False
                    current_row, current_col = worker_coordinate(current)
                    next_row, next_col = worker_coordinate(following)
                    if current_row != next_row:
                        self.assertFalse(saw_dim1)
                        self.assertEqual(current_col, next_col)
                    else:
                        self.assertNotEqual(current_col, next_col)
                        saw_dim1 = True
                    previous_cluster = cluster


class CliTests(unittest.TestCase):
    def test_fixed_and_adaptive_modes_are_both_available(self):
        network_config = (REPO_ROOT / "configs/network/Network.py").read_text()
        self.assertIn('"--sumcheck-routing"', network_config)
        self.assertIn('choices=("fixed", "adaptive")', network_config)
        self.assertIn('default="fixed"', network_config)
        self.assertIn('"--entry-congestion-weight"', network_config)


if __name__ == "__main__":
    unittest.main(verbosity=2)
