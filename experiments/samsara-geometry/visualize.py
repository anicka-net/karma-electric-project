#!/usr/bin/env python3
"""Visualize samsara geometry experiment results."""

import json
import os

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import seaborn as sns

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
FIGURES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figures")

# Realm colors
REALM_COLORS = {
    "hell": "#C0392B",         # crimson
    "hot_anger": "#E74C3C",
    "cold_anger": "#C0392B",
    "preta": "#8E44AD",        # dark purple
    "insatiable_craving": "#9B59B6",
    "hoarding_scarcity": "#8E44AD",
    "animal": "#795548",       # brown
    "willful_ignorance": "#8D6E63",
    "dull_bewilderment": "#795548",
    "asura": "#1E8449",        # dark green
    "competitive_jealousy": "#27AE60",
    "resentful_envy": "#1E8449",
    "deva": "#F1C40F",         # gold
    "inflated_pride": "#F39C12",
    "subtle_pride": "#F1C40F",
    "human": "#2980B9",        # teal-blue
    "clinging_attachment": "#3498DB",
    "consuming_desire": "#2980B9",
    "compassion": "#E67E22",   # saffron
    "chenrezig": "#E67E22",
    "agape": "#2E86C1",
    "rahma": "#27AE60",
    "generic": "#7F8C8D",      # gray
    "empty": "#BDC3C7",        # light gray
}

DISPLAY = {
    "generic": "Generic Assistant",
    "empty": "No System Prompt",
    "hot_anger": "Hot Anger (hell)",
    "cold_anger": "Cold Anger (hell)",
    "insatiable_craving": "Insatiable Craving (preta)",
    "hoarding_scarcity": "Hoarding Scarcity (preta)",
    "willful_ignorance": "Willful Ignorance (animal)",
    "dull_bewilderment": "Dull Bewilderment (animal)",
    "competitive_jealousy": "Competitive Jealousy (asura)",
    "resentful_envy": "Resentful Envy (asura)",
    "inflated_pride": "Inflated Pride (deva)",
    "subtle_pride": "Subtle Pride (deva)",
    "clinging_attachment": "Clinging Attachment (human)",
    "consuming_desire": "Consuming Desire (human)",
    "chenrezig": "Chenrezig",
    "agape": "Agape",
    "rahma": "Rahma",
}

REALM_DISPLAY = {
    "hell": "Hell (naraka)",
    "preta": "Hungry Ghost (preta)",
    "animal": "Animal (tiryak)",
    "asura": "Jealous God (asura)",
    "deva": "God (deva)",
    "human": "Human",
    "compassion": "Compassion",
}


def load(name):
    with open(os.path.join(RESULTS_DIR, name)) as f:
        return json.load(f)


def fig_grand_samsara_axis(projections_data):
    """Grand samsara axis projection at L31 — all 17 frameworks."""
    samsara = projections_data["samsara"]["31"]

    # Sort by projection value
    sorted_items = sorted(samsara.items(), key=lambda x: x[1])
    names = [DISPLAY.get(k, k) for k, _ in sorted_items]
    values = [v for _, v in sorted_items]
    colors = [REALM_COLORS.get(k, "#999999") for k, _ in sorted_items]

    fig, ax = plt.subplots(figsize=(13, 8))
    bars = ax.barh(names, values, color=colors, edgecolor="white", height=0.7)

    # Value labels
    for bar, (key, val) in zip(bars, sorted_items):
        ax.text(
            val + 300,
            bar.get_y() + bar.get_height() / 2,
            f"+{val:,.0f}",
            va="center",
            fontsize=9,
            color="#333333",
        )

    # Shade the affliction zone
    affliction_keys = [k for k, _ in sorted_items if k not in ("chenrezig", "agape", "rahma")]
    if affliction_keys:
        aff_min = min(samsara[k] for k in affliction_keys) - 500
        aff_max = max(samsara[k] for k in affliction_keys) + 500
        ax.axvspan(aff_min, aff_max, alpha=0.06, color="#E74C3C", zorder=0)

    ax.set_xlabel(
        "Projection onto Grand Samsara Axis (compassion_mean \u2212 affliction_mean)",
        fontsize=11,
    )
    ax.set_title(
        "The Grand Samsara Axis at Layer 31",
        fontsize=14,
        fontweight="bold",
        pad=12,
    )
    ax.grid(True, axis="x", alpha=0.3)
    plt.tight_layout()

    path = os.path.join(FIGURES_DIR, "grand_samsara_axis_L31.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  {path}")


def fig_inter_realm_heatmap(inter_realm_data):
    """Inter-realm similarity heatmap at L28."""
    realms = ["hell", "preta", "animal", "asura", "deva", "human", "compassion"]
    labels = [REALM_DISPLAY[r] for r in realms]

    matrix = np.zeros((len(realms), len(realms)))
    for i, r1 in enumerate(realms):
        for j, r2 in enumerate(realms):
            matrix[i, j] = inter_realm_data["28"][r1][r2]

    fig, ax = plt.subplots(figsize=(10, 8.5))
    sns.heatmap(
        matrix,
        xticklabels=labels,
        yticklabels=labels,
        annot=True,
        fmt=".2f",
        cmap="RdYlBu_r",
        vmin=0.3,
        vmax=1.0,
        center=0.65,
        square=True,
        linewidths=0.5,
        linecolor="white",
        cbar_kws={"label": "Cosine Similarity", "shrink": 0.8},
        ax=ax,
    )
    ax.set_title(
        "Inter-Realm Similarity at Layer 28",
        fontsize=14,
        fontweight="bold",
        pad=16,
    )
    plt.xticks(rotation=30, ha="right")
    plt.yticks(rotation=0)
    plt.tight_layout()

    path = os.path.join(FIGURES_DIR, "inter_realm_L28.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  {path}")


def fig_distance_from_compassion(distances_data):
    """Distance from compassion centroid at L31 — ranked bars."""
    # Exclude compassion traditions (they'd be ~0)
    exclude = {"chenrezig", "agape", "rahma"}
    items = {k: v for k, v in distances_data["31"].items() if k not in exclude}

    sorted_items = sorted(items.items(), key=lambda x: x[1], reverse=True)
    names = [DISPLAY.get(k, k) for k, _ in sorted_items]
    values = [v for _, v in sorted_items]
    colors = [REALM_COLORS.get(k, "#999999") for k, _ in sorted_items]

    fig, ax = plt.subplots(figsize=(12, 6))
    bars = ax.barh(names, values, color=colors, edgecolor="white", height=0.7)

    for bar, val in zip(bars, values):
        ax.text(
            val + 100,
            bar.get_y() + bar.get_height() / 2,
            f"{val:,.0f}",
            va="center",
            fontsize=9,
            color="#333333",
        )

    ax.set_xlabel("L2 Distance from Compassion Centroid", fontsize=12)
    ax.set_title(
        "Distance from Compassion at Layer 31",
        fontsize=14,
        fontweight="bold",
        pad=12,
    )
    ax.grid(True, axis="x", alpha=0.3)
    ax.invert_yaxis()
    plt.tight_layout()

    path = os.path.join(FIGURES_DIR, "distance_from_compassion_L31.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  {path}")


def fig_path_convergence(cosines_data):
    """Direct axis cosines at L28 — path convergence heatmap."""
    realms = ["hell", "preta", "animal", "asura", "deva", "human", "samsara"]
    labels = [
        "Hell", "Preta", "Animal", "Asura", "Deva", "Human", "Grand Samsara"
    ]

    matrix = np.zeros((len(realms), len(realms)))
    for i, r1 in enumerate(realms):
        for j, r2 in enumerate(realms):
            matrix[i, j] = cosines_data["28"][r1][r2]

    fig, ax = plt.subplots(figsize=(9, 7.5))
    sns.heatmap(
        matrix,
        xticklabels=labels,
        yticklabels=labels,
        annot=True,
        fmt=".2f",
        cmap="RdYlBu_r",
        vmin=0.4,
        vmax=1.0,
        center=0.7,
        square=True,
        linewidths=0.5,
        linecolor="white",
        cbar_kws={"label": "Cosine Similarity\n(between paths to compassion)", "shrink": 0.8},
        ax=ax,
    )
    ax.set_title(
        "Do All Paths to Compassion Converge? (Layer 28)",
        fontsize=14,
        fontweight="bold",
        pad=16,
    )
    plt.xticks(rotation=25, ha="right")
    plt.yticks(rotation=0)
    plt.tight_layout()

    path = os.path.join(FIGURES_DIR, "path_convergence_L28.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  {path}")


def main():
    os.makedirs(FIGURES_DIR, exist_ok=True)

    print("Loading data...")
    projections = load("direct_axis_projections.json")
    inter_realm = load("inter_realm_similarity.json")
    distances = load("distances_from_compassion.json")
    cosines = load("direct_axis_cosines.json")

    print("Generating figures:")
    fig_grand_samsara_axis(projections)
    fig_inter_realm_heatmap(inter_realm)
    fig_distance_from_compassion(distances)
    fig_path_convergence(cosines)

    print(f"\nAll figures saved to {FIGURES_DIR}/")


if __name__ == "__main__":
    main()
