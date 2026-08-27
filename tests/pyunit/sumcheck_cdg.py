#!/usr/bin/env python3
"""Independent Sumcheck legal-route and channel-dependency checker.

Two relations are checked deliberately:

* the exact C++ fixed/adaptive relation, whose source entry is always the
  fixed nearest entry and whose destination entry is either nearest (fixed) or
  any legal candidate (adaptive); and
* the specification-counted conservative relation, which additionally allows
  every source entry and therefore has the documented 4692/14548/52692 route
  totals.

The latter is a strict CDG superset for p=2/4, not a claim about runtime
source-side adaptivity. Both must be acyclic with separated U/D resources.
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import NamedTuple


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "configs"))

from topologies.SumcheckConfig import (  # noqa: E402
    NUM_ROUTERS,
    ROOT_ID,
    STAGGERED,
    VC_D,
    VC_U,
    entry_router,
    gateway_cluster,
    gateway_id,
    is_gateway,
    is_root,
    is_worker,
    nearest_entry_index,
    physical_adjacency,
    route_vc_class,
    worker_cluster,
    worker_coordinate,
    worker_id,
)


class LegalRoute(NamedTuple):
    source: int
    destination: int
    routers: tuple
    classes: tuple


def _mesh_path(source, destination):
    """Return strict dim0-then-dim1 routers, including both endpoints."""

    if worker_cluster(source) != worker_cluster(destination):
        raise ValueError("mesh path crossed clusters")
    cluster = worker_cluster(source)
    row, col = worker_coordinate(source)
    destination_row, destination_col = worker_coordinate(destination)
    path = [source]
    while row != destination_row:
        row += 1 if row < destination_row else -1
        path.append(worker_id(cluster, row, col))
    while col != destination_col:
        col += 1 if col < destination_col else -1
        path.append(worker_id(cluster, row, col))
    return path


def _append_mesh(route, destination):
    route.extend(_mesh_path(route[-1], destination)[1:])


def _build_route(
    source,
    destination,
    source_entry,
    destination_entry,
    entries_per_cluster,
    placement,
):
    route = [source]
    same_cluster_workers = (
        is_worker(source)
        and is_worker(destination)
        and worker_cluster(source) == worker_cluster(destination)
    )
    if same_cluster_workers:
        _append_mesh(route, destination)
        return route

    if is_worker(source):
        cluster = worker_cluster(source)
        selected_entry = entry_router(
            cluster, source_entry, entries_per_cluster, placement
        )
        _append_mesh(route, selected_entry)
        route.append(gateway_id(cluster))

    current = route[-1]
    if is_gateway(current):
        current_cluster = gateway_cluster(current)
        if is_worker(destination) and worker_cluster(destination) == current_cluster:
            selected_entry = entry_router(
                current_cluster,
                destination_entry,
                entries_per_cluster,
                placement,
            )
            route.append(selected_entry)
            _append_mesh(route, destination)
            return route
        if current != destination:
            route.append(ROOT_ID)

    current = route[-1]
    if is_root(current):
        if destination == ROOT_ID:
            return route
        if is_gateway(destination):
            route.append(destination)
            return route
        if is_worker(destination):
            destination_cluster = worker_cluster(destination)
            route.append(gateway_id(destination_cluster))
            selected_entry = entry_router(
                destination_cluster,
                destination_entry,
                entries_per_cluster,
                placement,
            )
            route.append(selected_entry)
            _append_mesh(route, destination)
            return route

    if route[-1] != destination:
        raise ValueError(
            f"unsupported legal route {source}->{destination}: {route}"
        )
    return route


def enumerate_legal_routes(entries_per_cluster, placement=STAGGERED):
    """Enumerate the specification-counted conservative route relation."""

    yield from _enumerate_routes(
        entries_per_cluster,
        placement,
        source_policy="all",
        destination_policy="all",
    )


def enumerate_runtime_routes(
    entries_per_cluster, placement=STAGGERED, adaptive=True
):
    """Enumerate exactly the fixed-source relation implemented by C++."""

    yield from _enumerate_routes(
        entries_per_cluster,
        placement,
        source_policy="nearest",
        destination_policy="all" if adaptive else "nearest",
    )


def _enumerate_routes(
    entries_per_cluster, placement, source_policy, destination_policy
):
    if source_policy not in ("all", "nearest"):
        raise ValueError(f"unknown source-entry policy {source_policy}")
    if destination_policy not in ("all", "nearest"):
        raise ValueError(
            f"unknown destination-entry policy {destination_policy}"
        )

    adjacency = physical_adjacency(entries_per_cluster, placement)
    for source in range(NUM_ROUTERS):
        for destination in range(NUM_ROUTERS):
            if source == destination:
                continue
            same_cluster_workers = (
                is_worker(source)
                and is_worker(destination)
                and worker_cluster(source) == worker_cluster(destination)
            )
            source_entries = (None,)
            if is_worker(source) and not same_cluster_workers:
                source_entries = (
                    range(entries_per_cluster)
                    if source_policy == "all"
                    else (
                        nearest_entry_index(
                            source, entries_per_cluster, placement
                        ),
                    )
                )
            destination_entries = (None,)
            if is_worker(destination) and not same_cluster_workers:
                destination_entries = (
                    range(entries_per_cluster)
                    if destination_policy == "all"
                    else (
                        nearest_entry_index(
                            destination, entries_per_cluster, placement
                        ),
                    )
                )
            for source_entry in source_entries:
                for destination_entry in destination_entries:
                    routers = tuple(
                        _build_route(
                            source,
                            destination,
                            source_entry,
                            destination_entry,
                            entries_per_cluster,
                            placement,
                        )
                    )
                    if routers[0] != source or routers[-1] != destination:
                        raise AssertionError("route endpoints do not match")
                    if len(routers) != len(set(routers)):
                        raise AssertionError(f"routing loop: {routers}")
                    for edge in zip(routers, routers[1:]):
                        if edge not in adjacency:
                            raise AssertionError(f"absent physical edge {edge}")
                    classes = tuple(
                        route_vc_class(current, source, destination)
                        for current in routers[:-1]
                    )
                    yield LegalRoute(source, destination, routers, classes)


def _resource(channel_class, source, destination, collapsed):
    return (source, destination) if collapsed else (
        channel_class,
        source,
        destination,
    )


def build_cdg(routes, collapsed=False):
    graph = defaultdict(set)
    for route in routes:
        channels = [
            _resource(channel_class, source, destination, collapsed)
            for channel_class, (source, destination) in zip(
                route.classes, zip(route.routers, route.routers[1:])
            )
        ]
        for channel in channels:
            graph[channel]
        for current, following in zip(channels, channels[1:]):
            graph[current].add(following)
    return graph


def find_cycle(graph):
    state = {}
    stack = []
    stack_index = {}

    def visit(node):
        state[node] = 1
        stack_index[node] = len(stack)
        stack.append(node)
        for successor in sorted(graph[node], key=repr):
            if state.get(successor, 0) == 0:
                witness = visit(successor)
                if witness:
                    return witness
            elif state.get(successor) == 1:
                return stack[stack_index[successor] :] + [successor]
        stack.pop()
        stack_index.pop(node)
        state[node] = 2
        return None

    for node in sorted(graph, key=repr):
        if state.get(node, 0) == 0:
            witness = visit(node)
            if witness:
                return witness
    return None


def _json_resource(resource, collapsed):
    if collapsed:
        source, destination = resource
        return {"channel": f"{source}->{destination}"}
    channel_class, source, destination = resource
    return {"class": channel_class, "channel": f"{source}->{destination}"}


def check_configuration(entries_per_cluster, placement=STAGGERED):
    routes = tuple(enumerate_legal_routes(entries_per_cluster, placement))
    runtime_fixed = tuple(
        enumerate_runtime_routes(
            entries_per_cluster, placement, adaptive=False
        )
    )
    runtime_adaptive = tuple(
        enumerate_runtime_routes(
            entries_per_cluster, placement, adaptive=True
        )
    )
    separated_cycle = find_cycle(build_cdg(routes, collapsed=False))
    collapsed_cycle = find_cycle(build_cdg(routes, collapsed=True))
    runtime_fixed_separated = find_cycle(
        build_cdg(runtime_fixed, collapsed=False)
    )
    runtime_adaptive_separated = find_cycle(
        build_cdg(runtime_adaptive, collapsed=False)
    )
    runtime_adaptive_collapsed = find_cycle(
        build_cdg(runtime_adaptive, collapsed=True)
    )
    spec_route_set = {
        (route.source, route.destination, route.routers, route.classes)
        for route in routes
    }
    runtime_route_set = {
        (route.source, route.destination, route.routers, route.classes)
        for route in runtime_adaptive
    }
    return {
        "entries_per_cluster": entries_per_cluster,
        "placement": placement,
        "ordered_pairs": NUM_ROUTERS * (NUM_ROUTERS - 1),
        "legal_routes": len(routes),
        "relation": "specification_conservative_superset",
        "separated_acyclic": separated_cycle is None,
        "separated_cycle_witness": None
        if separated_cycle is None
        else [_json_resource(item, False) for item in separated_cycle],
        "collapsed_acyclic": collapsed_cycle is None,
        "collapsed_cycle_witness": None
        if collapsed_cycle is None
        else [_json_resource(item, True) for item in collapsed_cycle],
        "runtime_fixed_routes": len(runtime_fixed),
        "runtime_adaptive_routes": len(runtime_adaptive),
        "runtime_relation": "exact_cpp_fixed_source_entry",
        "runtime_relation_is_subset": runtime_route_set <= spec_route_set,
        "runtime_fixed_separated_acyclic": runtime_fixed_separated is None,
        "runtime_adaptive_separated_acyclic": runtime_adaptive_separated is None,
        "runtime_adaptive_collapsed_acyclic": (
            runtime_adaptive_collapsed is None
        ),
        "runtime_adaptive_collapsed_cycle_witness": None
        if runtime_adaptive_collapsed is None
        else [
            _json_resource(item, True)
            for item in runtime_adaptive_collapsed
        ],
    }


def validate_route_phases(route):
    """Raise unless a route is U*, D*, or U*D* with a root transition."""

    saw_down = False
    for index, channel_class in enumerate(route.classes):
        if channel_class == VC_D:
            saw_down = True
        elif channel_class == VC_U and saw_down:
            raise AssertionError(f"D->U transition in {route}")
        elif channel_class != VC_U:
            raise AssertionError(f"unknown VC class in {route}")
        if index and route.classes[index - 1] == VC_U and channel_class == VC_D:
            if route.routers[index] != ROOT_ID:
                raise AssertionError(f"U->D outside root in {route}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--placement", default=STAGGERED)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    reports = [check_configuration(p, args.placement) for p in (1, 2, 4)]
    expected_routes = {1: 4692, 2: 14548, 4: 52692}
    expected_runtime_adaptive = {1: 4692, 2: 8084, 4: 14868}
    for report in reports:
        p = report["entries_per_cluster"]
        if report["ordered_pairs"] != 4692:
            raise SystemExit("ordered-pair count mismatch")
        if report["legal_routes"] != expected_routes[p]:
            raise SystemExit(f"p={p} legal-route count mismatch")
        if report["runtime_fixed_routes"] != 4692:
            raise SystemExit(f"p={p} runtime fixed-route count mismatch")
        if report["runtime_adaptive_routes"] != expected_runtime_adaptive[p]:
            raise SystemExit(f"p={p} runtime adaptive-route count mismatch")
        if not report["runtime_relation_is_subset"]:
            raise SystemExit(f"p={p} runtime relation escaped spec superset")
        if not report["runtime_fixed_separated_acyclic"]:
            raise SystemExit(f"p={p} runtime fixed CDG is cyclic")
        if not report["runtime_adaptive_separated_acyclic"]:
            raise SystemExit(f"p={p} runtime adaptive CDG is cyclic")
        if not report["separated_acyclic"]:
            raise SystemExit(f"p={p} separated CDG is cyclic")
        if p in (2, 4) and report["collapsed_acyclic"]:
            raise SystemExit(f"p={p} collapsed CDG lacks a cycle")
        witness = report["collapsed_cycle_witness"]
        witness_text = "none" if witness is None else " -> ".join(
            item["channel"] for item in witness
        )
        print(
            f"p={p}: pairs=4692 spec_routes={report['legal_routes']} "
            f"runtime_fixed={report['runtime_fixed_routes']} "
            f"runtime_adaptive={report['runtime_adaptive_routes']} "
            f"separated=acyclic collapsed_witness={witness_text}"
        )

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(reports, indent=2) + "\n")


if __name__ == "__main__":
    main()
