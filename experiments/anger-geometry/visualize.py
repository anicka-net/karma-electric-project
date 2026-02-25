#!/usr/bin/env python3
"""Visualize anger-compassion geometry experiment results."""

import json
import os

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import seaborn as sns

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
FIGURES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figures")

# Display names (twilight — full lineage language ok)
DISPLAY = {
    "hot_anger": "Hot Anger",
    "cold_anger": "Cold Anger",
    "chenrezig": "Chenrezig",
    "agape": "Agape",
    "rahma": "Rahma",
    "generic": "Generic Assistant",
    "empty": "No System Prompt",
}

COLORS_BAR = {
    "hot_anger": "#E74C3C",
    "cold_anger": "#C0392B",
    "generic": "#95A5A6",
    "empty": "#BDC3C7",
    "agape": "#2E86C1",
    "rahma": "#27AE60",
    "chenrezig": "#E67E22",
}


def load(name):
    with open(os.path.join(RESULTS_DIR, name)) as f:
        return json.load(f)


def fig_direct_axis_projection():
    """Direct axis projection at L31 — generic IS anger."""
    # Values from the experiment (projection onto compassion_mean - anger_mean)
    projections = {
        "hot_anger": 30208,
        "generic": 31232,
        "cold_anger": 32512,
        "empty": 36864,
        "agape": 37376,
        "rahma": 39680,
        "chenrezig": 46080,
    }

    # Sort by projection value
    sorted_items = sorted(projections.items(), key=lambda x: x[1])
    names = [DISPLAY[k] for k, _ in sorted_items]
    values = [v for _, v in sorted_items]
    colors = [COLORS_BAR[k] for k, _ in sorted_items]

    fig, ax = plt.subplots(figsize=(12, 5))
    bars = ax.barh(names, values, color=colors, edgecolor="white", height=0.65)

    # Add value labels
    for bar, val in zip(bars, values):
        ax.text(
            val + 400,
            bar.get_y() + bar.get_height() / 2,
            f"+{val:,}",
            va="center",
            fontsize=10,
            color="#333333",
        )

    # Bracket showing generic in anger zone
    ax.axvspan(
        projections["hot_anger"] - 500,
        projections["cold_anger"] + 500,
        alpha=0.08,
        color="#E74C3C",
        zorder=0,
    )
    ax.annotate(
        "anger zone",
        xy=((projections["hot_anger"] + projections["cold_anger"]) / 2, -0.6),
        fontsize=9,
        color="#C0392B",
        ha="center",
        style="italic",
    )

    ax.set_xlabel("Projection onto Direct Compassion-Anger Axis", fontsize=12)
    ax.set_title(
        "Where Does Generic Land? — Direct Axis at Layer 31",
        fontsize=14,
        fontweight="bold",
        pad=12,
    )
    ax.set_xlim(28000, 48500)
    ax.grid(True, axis="x", alpha=0.3)
    plt.tight_layout()

    path = os.path.join(FIGURES_DIR, "direct_axis_L31.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  {path}")


def fig_similarity_heatmap(cosine_data):
    """Cosine similarity heatmap at L31."""
    frameworks = ["hot_anger", "cold_anger", "chenrezig", "agape", "rahma"]
    labels = [DISPLAY[fw] for fw in frameworks]

    matrix = np.zeros((len(frameworks), len(frameworks)))
    for i, fw1 in enumerate(frameworks):
        for j, fw2 in enumerate(frameworks):
            matrix[i, j] = cosine_data["31"][fw1][fw2]

    fig, ax = plt.subplots(figsize=(8, 7))
    sns.heatmap(
        matrix,
        xticklabels=labels,
        yticklabels=labels,
        annot=True,
        fmt=".2f",
        cmap="RdYlBu_r",
        vmin=0.0,
        vmax=1.0,
        center=0.5,
        square=True,
        linewidths=0.5,
        linecolor="white",
        cbar_kws={"label": "Cosine Similarity", "shrink": 0.8},
        ax=ax,
    )
    ax.set_title(
        "Anger-Compassion Similarity at Layer 31",
        fontsize=14,
        fontweight="bold",
        pad=16,
    )
    plt.xticks(rotation=25, ha="right")
    plt.yticks(rotation=0)
    plt.tight_layout()

    path = os.path.join(FIGURES_DIR, "similarity_L31.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  {path}")


def fig_divergence_convergence(cosine_data):
    """Hot/cold anger divergence vs chenrezig/tara convergence."""
    layers = list(range(22, 32))

    # Hot vs cold anger from this experiment
    hot_cold = [cosine_data[str(l)]["hot_anger"]["cold_anger"] for l in layers]

    # Chenrezig vs tara from compassion experiment
    compassion_results = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..",
        "prompt-geometry",
        "results",
        "cosine_similarity.json",
    )
    if os.path.exists(compassion_results):
        with open(compassion_results) as f:
            comp_data = json.load(f)
        chen_tara = [comp_data[str(l)]["chenrezig"]["tara"] for l in layers]
    else:
        # Fallback: hardcoded from experiment
        chen_tara = [0.848, 0.844, 0.848, 0.856, 0.859, 0.859, 0.844, 0.852, 0.840, 0.898]

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(
        layers, hot_cold,
        color="#E74C3C", linewidth=2.5, marker="o", markersize=7,
        label="Hot Anger vs Cold Anger",
    )
    ax.plot(
        layers, chen_tara,
        color="#E67E22", linewidth=2.5, marker="s", markersize=7,
        label="Chenrezig vs Tara",
    )

    # Fill between to show divergence/convergence
    ax.fill_between(
        layers, hot_cold, chen_tara,
        alpha=0.1, color="#7F8C8D",
    )

    # Annotate L31
    ax.annotate(
        f"  {hot_cold[-1]:.2f}",
        xy=(31, hot_cold[-1]),
        fontsize=10, color="#E74C3C", fontweight="bold",
    )
    ax.annotate(
        f"  {chen_tara[-1]:.2f}",
        xy=(31, chen_tara[-1]),
        fontsize=10, color="#E67E22", fontweight="bold",
    )

    ax.set_xlabel("Layer", fontsize=12)
    ax.set_ylabel("Cosine Similarity (within pair)", fontsize=12)
    ax.set_title(
        "Anger Diverges Where Compassion Converges",
        fontsize=14,
        fontweight="bold",
        pad=12,
    )
    ax.set_ylim(0.6, 1.0)
    ax.set_xlim(21.5, 31.5)
    ax.xaxis.set_major_locator(ticker.MultipleLocator(1))
    ax.legend(fontsize=11, loc="lower left")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()

    path = os.path.join(FIGURES_DIR, "divergence_convergence.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  {path}")


def main():
    os.makedirs(FIGURES_DIR, exist_ok=True)

    print("Loading data...")
    cosine_data = load("cosine_similarity.json")

    print("Generating figures:")
    fig_direct_axis_projection()
    fig_similarity_heatmap(cosine_data)
    fig_divergence_convergence(cosine_data)

    print(f"\nAll figures saved to {FIGURES_DIR}/")


if __name__ == "__main__":
    main()
