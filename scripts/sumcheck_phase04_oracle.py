#!/usr/bin/env python3
"""Phase-04 static path/oracle checks; never reports these as gem5 data."""

import argparse
from collections import Counter
import json
from pathlib import Path

from topologies.SumcheckConfig import deterministic_route, mesh_xy_route
from topologies.SumcheckWorkload import (
    build_aggregated_trace,
    build_no_aggregation_trace,
)


def traffic_cost(events, route_function):
    links = Counter()
    total = 0
    for event in events:
        route = route_function(event.source, event.destination)
        flits = (event.size_bytes + 15) // 16
        total += flits * (len(route) - 1)
        for node_a, node_b in zip(route, route[1:]):
            links[tuple(sorted((node_a, node_b)))] += flits
    return {
        "total_flit_hops": total,
        "peak_undirected_link_flits": max(links.values(), default=0),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    cases = {}
    expected = {
        "Hierarchy_p1_fixed": (22448, 1016),
        "Hierarchy_p2_fixed": (18160, 536),
        "Hierarchy_p4_fixed": (11952, 256),
        "Hierarchy_p4_no_aggregation": (26048, 2368),
    }
    for name, entries, no_aggregation in (
        ("Hierarchy_p1_fixed", 1, False),
        ("Hierarchy_p2_fixed", 2, False),
        ("Hierarchy_p4_fixed", 4, False),
        ("Hierarchy_p4_no_aggregation", 4, True),
    ):
        events = (
            build_no_aggregation_trace()
            if no_aggregation
            else build_aggregated_trace(entries, "staggered")
        )
        result = traffic_cost(
            events,
            lambda source, destination, p=entries: deterministic_route(
                source, destination, p, "staggered"
            ),
        )
        result["spec_expected"] = {
            "total_flit_hops": expected[name][0],
            "peak_undirected_link_flits": expected[name][1],
        }
        result["matches_spec"] = tuple(result.values())[:2] == expected[name]
        if not result["matches_spec"]:
            raise SystemExit(f"static oracle mismatch: {name}: {result}")
        cases[name] = result

    mesh = traffic_cost(build_aggregated_trace(4), mesh_xy_route)
    mesh["spec_expected"] = {
        "total_flit_hops": 16208,
        "peak_undirected_link_flits": 632,
    }
    mesh["matches_spec"] = False
    mesh["discrepancy"] = (
        "Strict 8x8 XY gives 15824/624. The unavailable reference's "
        "16208/632 is reproduced only by forcing A->B worker states through "
        "hierarchy entry waypoints, which is not conventional XY. Measured "
        "Mesh runs retain strict XY and this difference is explicit."
    )
    cases["Mesh_8x8_XY"] = mesh

    output = {
        "provenance": "independently calculated from docs/sumcheck_spec.md",
        "measurement_kind": "static_not_gem5",
        "flit_bytes": 16,
        "cases": cases,
    }
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print("PHASE04_STATIC_PASS hierarchy=4/4 mesh_discrepancy=recorded")


if __name__ == "__main__":
    main()
