#!/usr/bin/env python3
"""
Experiment 2: Number of Entries.
Left: avg_hops (zoomed). Right: network_latency.
Both show SumHier advantage; contrast highlights that
entries affect hops but not latency.
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

small = pd.read_csv("results_entries/small_scale.csv")
large = pd.read_csv("results_entries/large_scale.csv")

ENTRIES_VALS = [1, 2, 4]
METRICS = [
    ("avg_hops", "Average Hops"),
    ("network_latency", "Network Latency (ticks)"),
]
COLORMAPS = ["Oranges", "Blues"]

CONFIGS = [
    ("small", small, "4×4×4 Hierarchy vs 8×8 Mesh"),
    ("large", large, "4×8×8 Hierarchy vs 16×16 Mesh"),
]

for scale, df, title in CONFIGS:
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))

    mesh = df[df["topology"] == "MeshSumcheck"]
    hier = df[df["topology"] == "SumcheckHierarchy"].sort_values("entries_per_cluster")

    for col, (metric, metric_label) in enumerate(METRICS):
        ax = axes[col]
        baseline = mesh[metric].values[0]

        labels = ["Mesh"]
        abs_vals = [baseline]
        norm_vals = [1.0]

        for _, row in hier.iterrows():
            labels.append(f"E={int(row['entries_per_cluster'])}")
            abs_vals.append(row[metric])
            norm_vals.append(row[metric] / baseline)

        x = np.arange(len(labels))
        cmap = plt.get_cmap(COLORMAPS[col])
        colors = ["gray"] + [cmap(v) for v in np.linspace(0.4, 0.9, len(ENTRIES_VALS))]

        bars = ax.bar(x, norm_vals, color=colors, edgecolor="black", linewidth=0.5)

        for i, (bar, abs_v, norm_v) in enumerate(zip(bars, abs_vals, norm_vals)):
            if i == 0:
                text = f"{abs_v:.1f}" if metric == "network_latency" else f"{abs_v:.2f}"
            else:
                text = f"{norm_v:.2f}×"
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                    text, ha="center", va="bottom", fontsize=9, fontweight="bold")

        ax.axhline(y=1.0, linestyle="--", color="gray", linewidth=0.8, alpha=0.4)
        ax.set_xticks(x)
        ax.set_xticklabels(labels)
        ax.set_ylabel(f"Normalized {metric_label}")
        ax.set_title(metric_label)
        ax.grid(axis="y", alpha=0.3)

        # zoom
        ymin = min(norm_vals) * 0.92
        ymax = max(norm_vals) * 1.08
        ax.set_ylim(ymin, ymax)

    fig.suptitle(title, fontsize=13, fontweight="bold")
    fig.tight_layout()
    fname = f"results_entries/{scale}_scale.png"
    fig.savefig(fname, dpi=200)
    plt.close(fig)
    print(f"Saved: {fname}")

# ============================================================
# Absolute values table
# ============================================================
print("\n--- Absolute Values Table ---")
for scale, df, title in CONFIGS:
    mesh = df[df["topology"] == "MeshSumcheck"]
    hier = df[df["topology"] == "SumcheckHierarchy"].sort_values("entries_per_cluster")
    print(f"\n{title}")
    print(f"{'Topology':<25} {'Net Latency':>12} {'Avg Hops':>10}")
    print("-" * 50)
    for _, row in mesh.iterrows():
        print(f"Mesh {row['src_placement']:<18} {row['network_latency']:>12.1f} {row['avg_hops']:>10.2f}")
    for _, row in hier.iterrows():
        print(f"Hier entries={int(row['entries_per_cluster']):<9} {row['network_latency']:>12.1f} {row['avg_hops']:>10.2f}")