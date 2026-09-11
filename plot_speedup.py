#!/usr/bin/env python3
"""Plot Experiment 1.1 and 1.2 results from results_speedup/*.csv."""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

import matplotlib.pyplot as plt


SCALES = {
    "small": ("SH 4×4×4", "Mesh 8×8"),
    "large": ("SH 4×8×8", "Mesh 16×16"),
}
VCS_VALUES = (1, 2, 4)
ROUNDS = (14, 15, 16, 17, 18)
SERIES = (
    ("hierarchy", "SumcheckHierarchy", "N/A", "#0072B2", "o"),
    ("center", "MeshSumcheck", "center", "#E69F00", "s"),
    ("corner", "MeshSumcheck", "corner", "#009E73", "^"),
)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(f"Missing input file: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"No data rows in {path}")
    return rows


def number(row: dict[str, str], key: str) -> float:
    try:
        value = float(row[key])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"Invalid {key!r} in row: {row}") from exc
    if not math.isfinite(value):
        raise ValueError(f"Non-finite {key!r} in row: {row}")
    return value


def select_one(
    rows: list[dict[str, str]],
    *,
    scale: str,
    topology: str,
    placement: str,
    vcs: int | None = None,
    rounds: int | None = None,
) -> dict[str, str]:
    matches = [
        row
        for row in rows
        if row["scale"] == scale
        and row["topology"] == topology
        and row["src_placement"] == placement
        and (vcs is None or int(row["vcs_per_vnet"]) == vcs)
        and (rounds is None or int(row["num_sumcheck_rounds"]) == rounds)
    ]
    if len(matches) != 1:
        raise ValueError(
            "Expected exactly one row for "
            f"scale={scale}, topology={topology}, placement={placement}, "
            f"vcs={vcs}, rounds={rounds}; found {len(matches)}"
        )
    return matches[0]


def geomean(values: list[float]) -> float:
    if not values or any(value <= 0 for value in values):
        raise ValueError("Geometric mean requires positive values")
    return math.exp(sum(math.log(value) for value in values) / len(values))


def plot_runtime_curves(rows: list[dict[str, str]], output_dir: Path) -> None:
    for scale, (hier_label, mesh_label) in SCALES.items():
        for vcs in VCS_VALUES:
            fig, ax = plt.subplots(figsize=(7.2, 4.8))
            for series_key, topology, placement, color, marker in SERIES:
                values = [
                    number(
                        select_one(
                            rows,
                            scale=scale,
                            topology=topology,
                            placement=placement,
                            vcs=vcs,
                            rounds=rounds,
                        ),
                        "sim_ticks",
                    )
                    / 1_000_000
                    for rounds in ROUNDS
                ]
                if series_key == "hierarchy":
                    label = hier_label
                else:
                    label = f"{mesh_label} ({series_key})"
                ax.plot(
                    ROUNDS,
                    values,
                    color=color,
                    marker=marker,
                    linewidth=2,
                    markersize=6,
                    label=label,
                )

            ax.set_title(f"End-to-end runtime, VCs per vnet = {vcs}")
            ax.set_xlabel("Number of sumcheck rounds")
            ax.set_ylabel("Simulation ticks (millions)")
            ax.set_xticks(ROUNDS)
            ax.set_ylim(bottom=0)
            ax.grid(axis="y", alpha=0.25)
            ax.legend(frameon=False)
            fig.tight_layout()
            path = output_dir / f"exp1_1_{scale}_vcs{vcs}.png"
            fig.savefig(path, dpi=240, bbox_inches="tight")
            plt.close(fig)
            print(f"Saved: {path}")


def build_speedup_table(rows: list[dict[str, str]]) -> tuple[list[str], list[list[float]]]:
    labels: list[str] = []
    table: list[list[float]] = []
    for scale, (hier_label, mesh_label) in SCALES.items():
        for placement in ("center", "corner"):
            labels.append(f"{hier_label} vs {mesh_label} {placement}")
            values: list[float] = []
            for vcs in VCS_VALUES:
                per_workload: list[float] = []
                for rounds in ROUNDS:
                    hierarchy = number(
                        select_one(
                            rows,
                            scale=scale,
                            topology="SumcheckHierarchy",
                            placement="N/A",
                            vcs=vcs,
                            rounds=rounds,
                        ),
                        "sim_ticks",
                    )
                    mesh = number(
                        select_one(
                            rows,
                            scale=scale,
                            topology="MeshSumcheck",
                            placement=placement,
                            vcs=vcs,
                            rounds=rounds,
                        ),
                        "sim_ticks",
                    )
                    per_workload.append(mesh / hierarchy)
                values.append(geomean(per_workload))
            table.append(values)
    return labels, table


def save_speedup_table(
    labels: list[str], table: list[list[float]], output_dir: Path
) -> None:
    csv_path = output_dir / "exp1_1_speedup_geomean.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["comparison", *(f"vcs={vcs}" for vcs in VCS_VALUES)])
        for label, values in zip(labels, table):
            writer.writerow([label, *(f"{value:.6f}" for value in values)])
    print(f"Saved: {csv_path}")

    fig, ax = plt.subplots(figsize=(9.4, 3.1))
    ax.axis("off")
    display = [[f"{value:.2f}×" for value in values] for values in table]
    chart = ax.table(
        cellText=display,
        rowLabels=labels,
        colLabels=[f"VCs = {vcs}" for vcs in VCS_VALUES],
        cellLoc="center",
        rowLoc="left",
        loc="center",
    )
    chart.auto_set_font_size(False)
    chart.set_fontsize(9.5)
    chart.scale(1, 1.55)
    for (row, _), cell in chart.get_celld().items():
        cell.set_edgecolor("#D0D0D0")
        if row == 0:
            cell.set_facecolor("#DCEAF7")
            cell.set_text_props(weight="bold")
    ax.set_title(
        "Geometric-mean speedup of SumcheckHierarchy over Mesh",
        fontsize=12,
        weight="bold",
        pad=14,
    )
    path = output_dir / "exp1_1_speedup_geomean.png"
    fig.savefig(path, dpi=240, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {path}")


def plot_metrics(rows: list[dict[str, str]], output_dir: Path) -> None:
    metrics = (
        ("queueing_latency", "Queueing latency"),
        ("network_latency", "Network latency"),
        ("avg_hops", "Average hops"),
    )
    topologies = (
        ("small", "SumcheckHierarchy", "N/A", "SH\n4×4×4"),
        ("small", "MeshSumcheck", "center", "Mesh 8×8\ncenter"),
        ("small", "MeshSumcheck", "corner", "Mesh 8×8\ncorner"),
        ("large", "SumcheckHierarchy", "N/A", "SH\n4×8×8"),
        ("large", "MeshSumcheck", "center", "Mesh 16×16\ncenter"),
        ("large", "MeshSumcheck", "corner", "Mesh 16×16\ncorner"),
    )
    colors = ("#0072B2", "#E69F00", "#009E73", "#56B4E9", "#F0C36E", "#63C29A")
    group_width = 0.78
    bar_width = group_width / len(topologies)

    fig, ax = plt.subplots(figsize=(12.5, 5.5))
    legend_bars = []
    for metric_index, (metric, metric_label) in enumerate(metrics):
        for topo_index, (scale, topology, placement, label) in enumerate(topologies):
            row = select_one(
                rows,
                scale=scale,
                topology=topology,
                placement=placement,
                vcs=4,
                rounds=15,
            )
            baseline = select_one(
                rows,
                scale=scale,
                topology="SumcheckHierarchy",
                placement="N/A",
                vcs=4,
                rounds=15,
            )
            absolute = number(row, metric)
            normalized = absolute / number(baseline, metric)
            x = metric_index - group_width / 2 + bar_width / 2 + topo_index * bar_width
            bar = ax.bar(
                x,
                normalized,
                width=bar_width * 0.9,
                color=colors[topo_index],
                edgecolor="white",
                linewidth=0.5,
            )[0]
            if metric_index == 0:
                legend_bars.append(bar)
            if topology == "SumcheckHierarchy":
                annotation = f"{absolute:.1f}"
            else:
                annotation = f"{normalized:.2f}×"
            ax.annotate(
                annotation,
                (x, normalized),
                xytext=(0, 4),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=7.5,
                rotation=90 if normalized > 2.5 else 0,
            )

    ax.axhline(1, color="#777777", linestyle="--", linewidth=1, alpha=0.7)
    ax.set_xticks(range(len(metrics)), [label for _, label in metrics])
    ax.set_ylabel("Normalized to the matching SumcheckHierarchy")
    ax.set_title("Latency and hop metrics (VCs = 4, sumcheck rounds = 15)")
    max_height = max(bar.get_height() for bar in ax.patches)
    ax.set_ylim(0, max_height * 1.18)
    ax.grid(axis="y", alpha=0.2)
    ax.legend(
        legend_bars,
        [label.replace("\n", " ") for *_, label in topologies],
        ncol=3,
        frameon=False,
        loc="upper left",
    )
    fig.tight_layout()
    path = output_dir / "exp1_2_metrics.png"
    fig.savefig(path, dpi=240, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {path}")


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--result-dir",
        type=Path,
        default=script_dir / "results_speedup",
        help="Directory containing speed_up.csv and metric.csv",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory (default: RESULT_DIR/figures)",
    )
    args = parser.parse_args()
    result_dir = args.result_dir.resolve()
    output_dir = (args.output_dir or result_dir / "figures").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    speedup_rows = read_csv(result_dir / "speed_up.csv")
    metric_rows = read_csv(result_dir / "metric.csv")
    if len(speedup_rows) != 90:
        raise ValueError(f"Expected 90 speedup rows, found {len(speedup_rows)}")
    if len(metric_rows) != 6:
        raise ValueError(f"Expected 6 metric rows, found {len(metric_rows)}")

    plot_runtime_curves(speedup_rows, output_dir)
    labels, table = build_speedup_table(speedup_rows)
    save_speedup_table(labels, table, output_dir)
    plot_metrics(metric_rows, output_dir)


if __name__ == "__main__":
    main()
