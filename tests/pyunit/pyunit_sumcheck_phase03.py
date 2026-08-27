import sys
import unittest
from dataclasses import replace
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "configs"))

from topologies.SumcheckConfig import STAGGERED  # noqa: E402
from topologies.SumcheckWorkload import (  # noqa: E402
    AGGREGATED_EVENT_COUNT,
    NO_AGGREGATION_EVENT_COUNT,
    CausalReplayState,
    build_aggregated_trace,
    build_no_aggregation_trace,
    root_cut_flits,
    trace_digest,
    validate_trace,
)


class TraceRegressionTests(unittest.TestCase):
    def test_aggregated_counts_for_all_entry_counts(self):
        for entries in (1, 2, 4):
            with self.subTest(entries=entries):
                events = build_aggregated_trace(entries, STAGGERED)
                self.assertEqual(len(events), AGGREGATED_EVENT_COUNT)

    def test_no_aggregation_count(self):
        self.assertEqual(
            len(build_no_aggregation_trace()),
            NO_AGGREGATION_EVENT_COUNT,
        )

    def test_missing_and_forward_dependencies_are_rejected(self):
        events = list(build_aggregated_trace(1))
        with self.assertRaisesRegex(ValueError, "missing dependency"):
            validate_trace(
                [
                    replace(
                        events[0],
                        depends_on=("does-not-exist",),
                    )
                ]
                + events[1:]
            )

        with self.assertRaisesRegex(ValueError, "forward/invalid"):
            validate_trace(
                [replace(events[0], depends_on=(events[1].event_id,))]
                + events[1:]
            )

    def test_stable_ids_and_digest_are_reproducible(self):
        first = build_aggregated_trace(4)
        second = build_aggregated_trace(4)
        self.assertEqual(first, second)
        self.assertEqual(trace_digest(first), trace_digest(second))
        self.assertEqual(first[0].event_id, "e0000")
        self.assertEqual(first[-1].event_id, "e2003")


class CausalSemanticsTests(unittest.TestCase):
    def test_aggregation_waits_for_every_required_arrival(self):
        events = build_aggregated_trace(1)
        state = CausalReplayState(events)
        aggregate = next(
            event for event in events if event.kind == "entry_aggregate"
        )
        self.assertGreater(len(aggregate.depends_on), 1)
        for dependency in aggregate.depends_on[:-1]:
            state.arrive(dependency)
            self.assertNotIn(aggregate.event_id, state.injected)
        state.arrive(aggregate.depends_on[-1])
        self.assertIn(aggregate.event_id, state.injected)

    def test_successor_never_injects_before_dependency_arrival(self):
        events = build_no_aggregation_trace()
        state = CausalReplayState(events)
        successor = next(event for event in events if event.depends_on)
        self.assertNotIn(successor.event_id, state.injected)
        for dependency in successor.depends_on:
            state.arrive(dependency)
        self.assertIn(successor.event_id, state.injected)

    def test_controller_outputs_are_fresh_dependency_events(self):
        events = build_aggregated_trace(4)
        aggregate_kinds = {
            "entry_aggregate",
            "cluster_aggregate",
            "entry_terminal_aggregate",
            "gateway_partial",
        }
        aggregates = [event for event in events if event.kind in aggregate_kinds]
        self.assertTrue(aggregates)
        self.assertTrue(all(event.depends_on for event in aggregates))
        self.assertTrue(
            all(
                event.event_id not in event.depends_on
                for event in aggregates
            )
        )

    def test_runtime_ejects_and_frees_vc_before_next_cycle_reinjection(self):
        interface = (
            REPO_ROOT / "src/mem/ruby/network/garnet/NetworkInterface.cc"
        ).read_text()
        workload = (
            REPO_ROOT / "src/mem/ruby/network/garnet/SumcheckWorkload.cc"
        ).read_text()
        ejection = interface[interface.index("Space is available. Enqueue"):]
        self.assertLess(
            ejection.index("iPort->sendCredit(cFlit)"),
            ejection.index("notifySumcheckArrival"),
        )
        self.assertIn(
            "schedule(injectionEvent, clockEdge(Cycles(1)))", workload
        )
        self.assertIn("runLocalPhase", workload)
        self.assertIn("phaseCLocalRound < 2", workload)

    def test_runtime_preserves_event_id_and_exact_packet_bytes(self):
        workload = (
            REPO_ROOT / "src/mem/ruby/network/garnet/SumcheckWorkload.cc"
        ).read_text()
        interface = (
            REPO_ROOT / "src/mem/ruby/network/garnet/NetworkInterface.cc"
        ).read_text()
        self.assertIn("setSumcheckEventId(index)", workload)
        self.assertIn("setMessageSizeBytes(event.bytes)", workload)
        self.assertIn("getMessageSizeBytes()", interface)

    def test_root_cut_accounts_for_actual_and_reference_flit_size(self):
        aggregated = root_cut_flits(build_aggregated_trace(4), 16)
        no_aggregation = root_cut_flits(build_no_aggregation_trace(), 16)
        for cluster in range(4):
            self.assertEqual(aggregated[cluster], {"up": 8, "down": 2})
            self.assertEqual(
                no_aggregation[cluster], {"up": 128, "down": 32}
            )

        actual_32b = root_cut_flits(build_no_aggregation_trace(), 32)
        for cluster in range(4):
            self.assertEqual(actual_32b[cluster], {"up": 64, "down": 16})


if __name__ == "__main__":
    unittest.main(verbosity=2)
