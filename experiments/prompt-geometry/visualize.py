#!/usr/bin/env python3
"""Visualize compassion geometry experiment results."""

import json
import os

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import seaborn as sns

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
FIGURES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figures")

# Display names (publication-safe)
DISPLAY = {
    "chenrezig": "Buddhist (Chenrezig)",
    "tara": "Buddhist (Tara)",
    "agape": "Christian (Agape)",
    "rahma": "Islamic (Rahma)",
    "secular": "Secular Humanism",
    "empty": "No System Prompt",
}

# Colors — colorblind-friendly, tradition-coded
COLORS = {
    "chenrezig": "#E67E22",  # saffron
    "tara": "#F39C12",       # lighter saffron
    "agape": "#2E86C1",      # deep blue
    "rahma": "#27AE60",      # emerald
    "secular": "#7F8C8D",    # gray
    "empty": "#BDC3C7",      # light gray
}


def load(name):
    with open(os.path.join(RESULTS_DIR, name)) as f:
        return json.load(f)


def fig_similarity_heatmap(cosine_data):
    """Cosine similarity heatmap at L31 — the identity layer."""
    frameworks = ["chenrezig", "tara", "agape", "rahma", "secular"]
    labels = [DISPLAY[fw] for fw in frameworks]

    matrix = np.zeros((len(frameworks), len(frameworks)))
    for i, fw1 in enumerate(frameworks):
        for j, fw2 in enumerate(frameworks):
            matrix[i, j] = cosine_data["31"][fw1][fw2]

    fig, ax = plt.subplots(figsize=(9, 7.5))
    sns.heatmap(
        matrix,
        xticklabels=labels,
        yticklabels=labels,
        annot=True,
        fmt=".2f",
        cmap="RdYlBu_r",
        vmin=-0.1,
        vmax=1.0,
        center=0.5,
        square=True,
        linewidths=0.5,
        linecolor="white",
        cbar_kws={"label": "Cosine Similarity", "shrink": 0.8},
        ax=ax,
    )
    ax.set_title(
        "Framework Similarity at Layer 31 (Identity Layer)",
        fontsize=14,
        fontweight="bold",
        pad=16,
    )
    plt.xticks(rotation=30, ha="right")
    plt.yticks(rotation=0)
    plt.tight_layout()

    path = os.path.join(FIGURES_DIR, "similarity_L31.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  {path}")


def fig_axis_norms(norms_data):
    """Axis norms across all 32 layers — separation from generic."""
    frameworks = ["chenrezig", "tara", "agape", "rahma", "secular", "empty"]
    layers = list(range(32))

    fig, ax = plt.subplots(figsize=(12, 6))
    for fw in frameworks:
        values = [norms_data[fw][str(l)] for l in layers]
        ax.plot(
            layers,
            values,
            color=COLORS[fw],
            linewidth=2.2,
            label=DISPLAY[fw],
            marker="o",
            markersize=3,
        )

    ax.set_xlabel("Layer", fontsize=12)
    ax.set_ylabel("Axis Norm (distance from generic)", fontsize=12)
    ax.set_title(
        "Compassion Axis Magnitude Across Network Layers",
        fontsize=14,
        fontweight="bold",
        pad=12,
    )
    ax.legend(fontsize=10, loc="upper left")
    ax.set_xlim(0, 31)
    ax.xaxis.set_major_locator(ticker.MultipleLocator(4))
    ax.grid(True, alpha=0.3)
    plt.tight_layout()

    path = os.path.join(FIGURES_DIR, "axis_norms.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  {path}")


def fig_convergence(cosine_data):
    """Pairwise convergence across upper layers — the key finding."""
    pairs = {
        "Chenrezig - Tara (Buddhist)": ("chenrezig", "tara"),
        "Chenrezig - Agape (Buddhist-Christian)": ("chenrezig", "agape"),
        "Chenrezig - Rahma (Buddhist-Islamic)": ("chenrezig", "rahma"),
        "Chenrezig - Secular": ("chenrezig", "secular"),
    }
    pair_colors = {
        "Chenrezig - Tara (Buddhist)": "#E67E22",
        "Chenrezig - Agape (Buddhist-Christian)": "#2E86C1",
        "Chenrezig - Rahma (Buddhist-Islamic)": "#27AE60",
        "Chenrezig - Secular": "#7F8C8D",
    }
    layers = list(range(22, 32))

    fig, ax = plt.subplots(figsize=(12, 6))
    for label, (fw1, fw2) in pairs.items():
        values = [cosine_data[str(l)][fw1][fw2] for l in layers]
        ax.plot(
            layers,
            values,
            color=pair_colors[label],
            linewidth=2.5,
            label=label,
            marker="o",
            markersize=6,
        )

    # Highlight L31
    ax.axvline(x=31, color="#CCCCCC", linestyle="--", linewidth=1, alpha=0.6)
    ax.annotate(
        "Identity\nlayer",
        xy=(31, 0.0),
        fontsize=9,
        color="#999999",
        ha="center",
        va="bottom",
    )

    ax.set_xlabel("Layer", fontsize=12)
    ax.set_ylabel("Cosine Similarity", fontsize=12)
    ax.set_title(
        "Cross-Tradition Convergence in Upper Network",
        fontsize=14,
        fontweight="bold",
        pad=12,
    )
    ax.set_ylim(-0.05, 1.05)
    ax.set_xlim(21.5, 31.5)
    ax.xaxis.set_major_locator(ticker.MultipleLocator(1))
    ax.legend(fontsize=10, loc="lower left")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()

    path = os.path.join(FIGURES_DIR, "convergence.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  {path}")


def main():
    os.makedirs(FIGURES_DIR, exist_ok=True)

    print("Loading data...")
    cosine_data = load("cosine_similarity.json")
    norms_data = load("axis_norms.json")

    print("Generating figures:")
    fig_similarity_heatmap(cosine_data)
    fig_axis_norms(norms_data)
    fig_convergence(cosine_data)

    print(f"\nAll figures saved to {FIGURES_DIR}/")


if __name__ == "__main__":
    main()
