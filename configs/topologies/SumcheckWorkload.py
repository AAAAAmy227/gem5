"""Deterministic logical Sumcheck traces and causal replay validation.

The reference bundle is not available in this checkout.  This module derives
the Phase-3 event graph directly from ``docs/sumcheck_spec.md`` and keeps it
independent of m5 so the graph can be regression-tested before gem5 starts.
"""

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import random

from topologies.SumcheckConfig import (
    NUM_CLUSTERS,
    NUM_WORKERS,
    ROOT_ID,
    STAGGERED,
    WORKERS_PER_CLUSTER,
    entry_router,
    gateway_id,
    nearest_entry_index,
)


FIELD_BYTES = 32
PARTIAL_BYTES = 128
PHASE_A_ROUNDS = 14
PHASE_B_ROUNDS = 4
AGGREGATED_EVENT_COUNT = 2004
NO_AGGREGATION_EVENT_COUNT = 1856


@dataclass(frozen=True)
class TraceEvent:
    event_id: str
    source: int
    destination: int
    size_bytes: int
    phase: str
    round_index: int
    kind: str
    depends_on: tuple[str, ...]
    release_cycle: int = 0

    def wire_record(self) -> str:
        """Serialize to the deliberately simple C++ SimObject parameter form."""

        dependencies = ",".join(self.depends_on)
        fields = (
                self.event_id,
                str(self.source),
                str(self.destination),
                str(self.size_bytes),
                self.phase,
                str(self.round_index),
                self.kind,
                dependencies,
            )
        if self.release_cycle:
            fields += (str(self.release_cycle),)
        return ";".join(fields)

    def json_record(self) -> dict:
        return {
            "event_id": self.event_id,
            "source": self.source,
            "destination": self.destination,
            "size_bytes": self.size_bytes,
            "phase": self.phase,
            "round": self.round_index,
            "kind": self.kind,
            "depends_on": list(self.depends_on),
            "release_cycle": self.release_cycle,
        }


class _TraceBuilder:
    def __init__(self):
        self.events: list[TraceEvent] = []

    def add(
        self,
        source: int,
        destination: int,
        size_bytes: int,
        phase: str,
        round_index: int,
        kind: str,
        depends_on=(),
        release_cycle=0,
    ) -> str:
        event_id = f"e{len(self.events):04d}"
        event = TraceEvent(
            event_id,
            source,
            destination,
            size_bytes,
            phase,
            round_index,
            kind,
            tuple(depends_on),
            release_cycle,
        )
        self.events.append(event)
        return event_id


def _entry_groups(cluster, entries_per_cluster, entry_placement):
    groups = {index: [] for index in range(entries_per_cluster)}
    base = cluster * WORKERS_PER_CLUSTER
    for worker in range(base, base + WORKERS_PER_CLUSTER):
        index = nearest_entry_index(
            worker, entries_per_cluster, entry_placement
        )
        groups[index].append(worker)
    return groups


def build_aggregated_trace(entries_per_cluster, entry_placement=STAGGERED):
    """Build the 2004-event endpoint-aggregation trace from the spec."""

    builder = _TraceBuilder()
    previous_challenge = {}

    for round_index in range(PHASE_A_ROUNDS):
        entry_aggregates = {}
        for cluster in range(NUM_CLUSTERS):
            groups = _entry_groups(
                cluster, entries_per_cluster, entry_placement
            )
            for entry_index, workers in groups.items():
                entry = entry_router(
                    cluster,
                    entry_index,
                    entries_per_cluster,
                    entry_placement,
                )
                partials = []
                for worker in workers:
                    if worker == entry:
                        continue
                    dependencies = () if round_index == 0 else (
                        previous_challenge[worker],
                    )
                    partials.append(
                        builder.add(
                            worker,
                            entry,
                            PARTIAL_BYTES,
                            "A",
                            round_index,
                            "worker_partial",
                            dependencies,
                        )
                    )

                # The entry's own partial is local computation.  In later
                # rounds it becomes available only after that worker receives
                # the preceding challenge.
                dependencies = list(partials)
                if round_index > 0:
                    dependencies.append(previous_challenge[entry])
                entry_aggregates[(cluster, entry_index)] = builder.add(
                    entry,
                    gateway_id(cluster),
                    PARTIAL_BYTES,
                    "A",
                    round_index,
                    "entry_aggregate",
                    dependencies,
                )

        cluster_aggregates = []
        for cluster in range(NUM_CLUSTERS):
            dependencies = [
                entry_aggregates[(cluster, index)]
                for index in range(entries_per_cluster)
            ]
            cluster_aggregates.append(
                builder.add(
                    gateway_id(cluster),
                    ROOT_ID,
                    PARTIAL_BYTES,
                    "A",
                    round_index,
                    "cluster_aggregate",
                    dependencies,
                )
            )

        root_challenges = {}
        for cluster in range(NUM_CLUSTERS):
            root_challenges[cluster] = builder.add(
                ROOT_ID,
                gateway_id(cluster),
                FIELD_BYTES,
                "A",
                round_index,
                "root_cluster_challenge",
                cluster_aggregates,
            )

        next_challenge = {}
        for worker in range(NUM_WORKERS):
            cluster = worker // WORKERS_PER_CLUSTER
            next_challenge[worker] = builder.add(
                gateway_id(cluster),
                worker,
                FIELD_BYTES,
                "A",
                round_index,
                "worker_challenge",
                (root_challenges[cluster],),
            )
        previous_challenge = next_challenge

    # A -> B boundary: retain one terminal-state packet per worker. Its
    # worker->gateway route passes through the assigned entry. The reference
    # full-trace oracle counts all 16 packets on each entry->gateway cut.
    gateway_terminal = {}
    for cluster in range(NUM_CLUSTERS):
        base = cluster * WORKERS_PER_CLUSTER
        gateway_terminal[cluster] = []
        for worker in range(base, base + WORKERS_PER_CLUSTER):
            gateway_terminal[cluster].append(builder.add(
                worker,
                gateway_id(cluster),
                PARTIAL_BYTES,
                "AB",
                PHASE_A_ROUNDS,
                "worker_terminal_state",
                (previous_challenge[worker],),
            ))

    previous_gateway_challenge = {}
    for round_index in range(PHASE_B_ROUNDS):
        gateway_partials = []
        for cluster in range(NUM_CLUSTERS):
            if round_index == 0:
                dependencies = gateway_terminal[cluster]
            else:
                dependencies = [previous_gateway_challenge[cluster]]
            gateway_partials.append(
                builder.add(
                    gateway_id(cluster),
                    ROOT_ID,
                    PARTIAL_BYTES,
                    "B",
                    round_index,
                    "gateway_partial",
                    dependencies,
                )
            )

        next_gateway_challenge = {}
        for cluster in range(NUM_CLUSTERS):
            next_gateway_challenge[cluster] = builder.add(
                ROOT_ID,
                gateway_id(cluster),
                FIELD_BYTES,
                "B",
                round_index,
                "gateway_challenge",
                gateway_partials,
            )
        previous_gateway_challenge = next_gateway_challenge

    for cluster in range(NUM_CLUSTERS):
        builder.add(
            gateway_id(cluster),
            ROOT_ID,
            PARTIAL_BYTES,
            "BC",
            PHASE_B_ROUNDS,
            "gateway_terminal_state",
            (previous_gateway_challenge[cluster],),
        )

    events = tuple(builder.events)
    validate_trace(events)
    if len(events) != AGGREGATED_EVENT_COUNT:
        raise ValueError(
            f"aggregated trace has {len(events)} events, expected "
            f"{AGGREGATED_EVENT_COUNT}"
        )
    return events


def build_synthetic_trace(
    traffic,
    offered_load,
    seed,
    cycles,
    burst_period=20,
    burst_on_cycles=5,
):
    """Build deterministic open-loop 64-worker offered-traffic events."""

    if traffic not in ("uniform-random", "cluster-skewed-bursty"):
        raise ValueError(f"unsupported synthetic traffic {traffic}")
    if not 0.0 < offered_load <= 1.0:
        raise ValueError("offered load must be in (0, 1]")
    if cycles <= 0:
        raise ValueError("synthetic cycles must be positive")
    if burst_period <= 0 or not 0 < burst_on_cycles <= burst_period:
        raise ValueError("invalid burst period/on-cycle configuration")

    rng = random.Random(seed)
    builder = _TraceBuilder()
    duty = burst_on_cycles / burst_period
    on_probability = min(1.0, offered_load / duty)
    for cycle in range(cycles):
        burst_on = cycle % burst_period < burst_on_cycles
        for source in range(NUM_WORKERS):
            probability = offered_load
            if traffic == "cluster-skewed-bursty":
                if not burst_on:
                    continue
                probability = on_probability
            if rng.random() >= probability:
                continue

            if traffic == "uniform-random":
                destination = rng.randrange(NUM_WORKERS - 1)
                if destination >= source:
                    destination += 1
            else:
                source_cluster = source // WORKERS_PER_CLUSTER
                if rng.random() < 0.8:
                    hot_cluster = 0 if source_cluster != 0 else 1
                    destination = (
                        hot_cluster * WORKERS_PER_CLUSTER
                        + rng.randrange(WORKERS_PER_CLUSTER)
                    )
                else:
                    destination = rng.randrange(NUM_WORKERS - 1)
                    if destination >= source:
                        destination += 1

            builder.add(
                source,
                destination,
                PARTIAL_BYTES if rng.random() < 0.5 else FIELD_BYTES,
                "SYNTH",
                cycle,
                traffic.replace("-", "_"),
                release_cycle=cycle + 1,
            )

    events = tuple(builder.events)
    validate_trace(events)
    if not events:
        raise ValueError("synthetic configuration generated no packets")
    return events


def build_no_aggregation_trace():
    """Build the specified 1856-event pure-router negative control."""

    builder = _TraceBuilder()
    previous_challenge = {}
    for round_index in range(PHASE_A_ROUNDS):
        partials = []
        for worker in range(NUM_WORKERS):
            dependencies = () if round_index == 0 else (
                previous_challenge[worker],
            )
            partials.append(
                builder.add(
                    worker,
                    ROOT_ID,
                    PARTIAL_BYTES,
                    "A",
                    round_index,
                    "direct_worker_partial",
                    dependencies,
                )
            )

        next_challenge = {}
        for worker in range(NUM_WORKERS):
            next_challenge[worker] = builder.add(
                ROOT_ID,
                worker,
                FIELD_BYTES,
                "A",
                round_index,
                "direct_worker_challenge",
                partials,
            )
        previous_challenge = next_challenge

    for worker in range(NUM_WORKERS):
        builder.add(
            worker,
            ROOT_ID,
            PARTIAL_BYTES,
            "AB",
            PHASE_A_ROUNDS,
            "direct_worker_terminal_state",
            (previous_challenge[worker],),
        )

    events = tuple(builder.events)
    validate_trace(events)
    if len(events) != NO_AGGREGATION_EVENT_COUNT:
        raise ValueError(
            f"no-aggregation trace has {len(events)} events, expected "
            f"{NO_AGGREGATION_EVENT_COUNT}"
        )
    return events


def validate_trace(events):
    """Reject duplicate IDs plus missing, self, or forward dependencies."""

    positions = {}
    for index, event in enumerate(events):
        if event.event_id in positions:
            raise ValueError(f"duplicate event ID {event.event_id}")
        if not 0 <= event.source <= ROOT_ID:
            raise ValueError(f"event {event.event_id} has invalid source")
        if not 0 <= event.destination <= ROOT_ID:
            raise ValueError(f"event {event.event_id} has invalid destination")
        if event.source == event.destination:
            raise ValueError(f"event {event.event_id} is not a network message")
        if event.size_bytes not in (FIELD_BYTES, PARTIAL_BYTES):
            raise ValueError(f"event {event.event_id} has invalid byte size")
        if event.release_cycle < 0:
            raise ValueError(f"event {event.event_id} has invalid release")
        positions[event.event_id] = index

    for index, event in enumerate(events):
        seen = set()
        for dependency in event.depends_on:
            if dependency in seen:
                raise ValueError(
                    f"event {event.event_id} repeats dependency {dependency}"
                )
            seen.add(dependency)
            if dependency not in positions:
                raise ValueError(
                    f"event {event.event_id} has missing dependency "
                    f"{dependency}"
                )
            if positions[dependency] >= index:
                raise ValueError(
                    f"event {event.event_id} has forward/invalid dependency "
                    f"{dependency}"
                )
    return True


class CausalReplayState:
    """Small host-side model of the same arrival-triggered C++ scheduler."""

    def __init__(self, events):
        validate_trace(events)
        self.events = tuple(events)
        self.by_id = {event.event_id: event for event in self.events}
        self.dependents = {event.event_id: [] for event in self.events}
        self.remaining = {}
        for event in self.events:
            self.remaining[event.event_id] = len(event.depends_on)
            for dependency in event.depends_on:
                self.dependents[dependency].append(event.event_id)
        self.injected = {
            event.event_id
            for event in self.events
            if self.remaining[event.event_id] == 0
        }
        self.arrived = set()

    def arrive(self, event_id):
        if event_id not in self.injected:
            raise ValueError(f"event {event_id} arrived before injection")
        if event_id in self.arrived:
            raise ValueError(f"duplicate arrival for event {event_id}")
        self.arrived.add(event_id)
        newly_ready = []
        for successor in self.dependents[event_id]:
            self.remaining[successor] -= 1
            if self.remaining[successor] == 0:
                dependencies = self.by_id[successor].depends_on
                if not set(dependencies).issubset(self.arrived):
                    raise AssertionError("readiness preceded dependency arrival")
                self.injected.add(successor)
                newly_ready.append(successor)
        return tuple(newly_ready)


def trace_digest(events):
    payload = "\n".join(event.wire_record() for event in events)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def write_jsonl(events, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as output:
        for event in events:
            output.write(json.dumps(event.json_record(), sort_keys=True))
            output.write("\n")


def root_cut_flits(events, flit_bytes, round_index=0):
    """Return per-cluster Phase-A root-cut flits for one logical round."""

    if flit_bytes <= 0:
        raise ValueError("flit size must be positive")
    counts = {
        cluster: {"up": 0, "down": 0}
        for cluster in range(NUM_CLUSTERS)
    }
    for event in events:
        if event.phase != "A" or event.round_index != round_index:
            continue
        flits = (event.size_bytes + flit_bytes - 1) // flit_bytes
        if event.destination == ROOT_ID and event.source != ROOT_ID:
            cluster = (
                event.source // WORKERS_PER_CLUSTER
                if event.source < NUM_WORKERS
                else event.source - NUM_WORKERS
            )
            counts[cluster]["up"] += flits
        elif event.source == ROOT_ID and event.destination != ROOT_ID:
            cluster = (
                event.destination // WORKERS_PER_CLUSTER
                if event.destination < NUM_WORKERS
                else event.destination - NUM_WORKERS
            )
            counts[cluster]["down"] += flits
    return counts
