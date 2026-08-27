#!/usr/bin/env python3
"""Emit structured Phase-3 logical/static workload regression evidence."""

import argparse
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "configs"))

from topologies.SumcheckWorkload import (  # noqa: E402
    build_aggregated_trace,
    build_no_aggregation_trace,
    root_cut_flits,
    trace_digest,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--flit-bytes", type=int, default=16)
    args = parser.parse_args()

    aggregated = {
        str(entries): build_aggregated_trace(entries)
        for entries in (1, 2, 4)
    }
    no_aggregation = build_no_aggregation_trace()
    report = {
        "provenance": "derived from docs/sumcheck_spec.md; reference bundle unavailable",
        "flit_bytes": args.flit_bytes,
        "aggregated": {
            entries: {
                "events": len(events),
                "trace_sha256": trace_digest(events),
                "root_cut_per_cluster_per_round": root_cut_flits(
                    events, args.flit_bytes
                ),
            }
            for entries, events in aggregated.items()
        },
        "no_aggregation": {
            "events": len(no_aggregation),
            "trace_sha256": trace_digest(no_aggregation),
            "root_cut_per_cluster_per_round": root_cut_flits(
                no_aggregation, args.flit_bytes
            ),
        },
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
