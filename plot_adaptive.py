#!/usr/bin/env python3
"""
Plot adaptive routing results: 4 separate figures.
Each figure: x-axis = β, 7 lines = different α.
Mesh baselines shown as horizontal reference lines.
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# ============================================================
# Load data
# ============================================================
small = pd.read_csv("results_adaptive/small_scale.csv")
large = pd.read_csv("results_adaptive/large_scale.csv")

# ============================================================
# Extract Mesh baselines
# ============================================================
def get_baseline(df):
    mesh = df[df["topology"] == "MeshSumcheck"]
    out = {}
    for _, row in mesh.iterrows():
        out[row["src_placement"]] = {
            "network_latency": row["network_latency"],
            "avg_hops": row["avg_hops"],
        }
    return out

small_bl = get_baseline(small)
large_bl = get_baseline(large)

# ============================================================
# Preprocess Hierarchy data
# ============================================================
def prep_hier(df, avg_seeds):
    hier = df[df["topology"] == "SumcheckHierarchy"].copy()
    if avg_seeds:
        adaptive = hier[hier["routing_mode"] == "adaptive"]
        adaptive = adaptive.groupby(
            ["routing_mode", "alpha", "beta"]
        ).agg(
            {"network_latency": "mean", "avg_hops": "mean",
             "reroute_rate": "mean",
             "latency": "mean", "queueing_latency": "mean"}
        ).reset_index()
        fixed = hier[hier["routing_mode"] == "fixed"].drop_duplicates(
            subset=["routing_mode", "alpha", "beta"]
        )
        hier = pd.concat([fixed, adaptive], ignore_index=True)
    return hier

small_hier = prep_hier(small, avg_seeds=True)
large_hier = prep_hier(large, avg_seeds=False)

# ============================================================
# Common plot settings
# ============================================================
ALPHA_VALS = [0, 0.5, 1, 2, 4, 8, 16]
BETA_VALS  = [0, 0.5, 1, 2, 4, 8, 16]
COLORS = plt.cm.tab10(np.linspace(0, 1, len(ALPHA_VALS)))

CONFIGS = [
   ("small", small_hier, small_bl, "4×4×4 Hierarchy", "8×8 Mesh"),
   ("large", large_hier, large_bl, "4×8×8 Hierarchy", "16×16 Mesh"),
]

METRICS = [
    ("network_latency", "Network Latency (ticks)"),
    ("avg_hops", "Average Hops"),
]

# ============================================================
# Generate 4 figures
# ============================================================
for scale, hier, baseline, hier_label, mesh_label in CONFIGS:
    for metric, metric_label in METRICS:
        fig, ax = plt.subplots(figsize=(9, 5.5))

        # --- adaptive (solid lines) ---
        for i, alpha in enumerate(ALPHA_VALS):
            subset = hier[
                (hier["routing_mode"] == "adaptive") & (hier["alpha"] == alpha)
            ].sort_values("beta")
            if not subset.empty:
                ax.plot(subset["beta"], subset[metric],
                        marker="o", markersize=5, linewidth=1.5,
                        color=COLORS[i], label=f"α={alpha}")

        # --- fixed (dashed lines) ---
        for i, alpha in enumerate(ALPHA_VALS):
            subset = hier[
                (hier["routing_mode"] == "fixed") & (hier["alpha"] == alpha)
            ].sort_values("beta")
            if not subset.empty:
                ax.plot(subset["beta"], subset[metric],
                        marker="s", markersize=4, linewidth=0.8,
                        linestyle="--", color=COLORS[i], alpha=0.5)

        # --- Mesh baselines (horizontal lines) ---
        for place, fmt in [("corner", "-."), ("center", ":")]:
            if place in baseline:
                val = baseline[place][metric]
                label = f"Mesh {place} ({val:.1f})" if metric == "network_latency" \
                        else f"Mesh {place} ({val:.2f})"
                ax.axhline(y=val, linestyle=fmt, color="gray",
                           linewidth=1.2, label=label)

        # --- axes ---
        ax.set_xlabel("β")
        ax.set_ylabel(metric_label)
        ax.set_xticks(BETA_VALS)
        ax.set_xlim(-0.5, 16.5)
        ax.grid(True, alpha=0.3)

        # zoom y-axis
        vals = hier[metric].dropna()
        if len(vals) > 0:
            ymin, ymax = vals.min(), vals.max()
            margin = (ymax - ymin) * 0.15
            ax.set_ylim(ymin - margin, ymax + margin)

        ax.legend(fontsize=7, ncol=2, loc="best")
        ax.set_title(f"{hier_label} vs {mesh_label} — {metric_label}")

        fname = f"results_adaptive/{scale}_{metric}.png"
        fig.tight_layout()
        fig.savefig(fname, dpi=200)
        plt.close(fig)
        print(f"Saved: {fname}")

# ============================================================
# Reroute rate: 2 figures (small / large), adaptive only, 7 lines
# ============================================================
for scale, hier, _, hier_label, mesh_label in CONFIGS:
    fig, ax = plt.subplots(figsize=(9, 5.5))

    # --- adaptive (solid lines) ---
    for i, alpha in enumerate(ALPHA_VALS):
        subset = hier[
            (hier["routing_mode"] == "adaptive") & (hier["alpha"] == alpha)
        ].sort_values("beta")
        if not subset.empty and "reroute_rate" in subset.columns:
            ax.plot(subset["beta"], subset["reroute_rate"],
                    marker="o", markersize=5, linewidth=1.5,
                    color=COLORS[i], label=f"α={alpha}")

    # --- fixed (dashed lines) ---
    for i, alpha in enumerate(ALPHA_VALS):
        subset = hier[
            (hier["routing_mode"] == "fixed") & (hier["alpha"] == alpha)
        ].sort_values("beta")
        if not subset.empty and "reroute_rate" in subset.columns:
            ax.plot(subset["beta"], subset["reroute_rate"],
                    marker="s", markersize=4, linewidth=0.8,
                    linestyle="--", color=COLORS[i], alpha=0.5)

    ax.set_xlabel("β")
    ax.set_ylabel("Reroute Rate")
    ax.set_xticks(BETA_VALS)
    ax.set_xlim(-0.5, 16.5)
    ax.grid(True, alpha=0.3)

    vals = hier[hier["routing_mode"].isin(["adaptive", "fixed"])]["reroute_rate"].dropna()
    if len(vals) > 0:
        ymin, ymax = vals.min(), vals.max()
        if ymax > ymin:
            ax.set_ylim(max(0, ymin), ymax)

    ax.legend(fontsize=7, ncol=2, loc="best")
    ax.set_title(f"{hier_label} vs {mesh_label} — Reroute Rate")

    fname = f"results_adaptive/{scale}_reroute_rate.png"
    fig.tight_layout()
    fig.savefig(fname, dpi=200)
    plt.close(fig)
    print(f"Saved: {fname}")