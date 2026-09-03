"""
Design parameter distributions, heatmaps, and parallel coordinate visualizations.
"""

from pathlib import Path
from typing import List, Optional, Union

import matplotlib.cm as cm
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from mobo_linac.evaluation import EvaluationResult
from mobo_linac.io.results import (
    DESIGN_VAR_COLUMNS,
    results_to_dataframe,
)
from mobo_linac.plotting.common import (
    DESIGN_VAR_LABELS,
    DESIGN_VAR_SHORT_LABELS,
    save_fig,
)


def plot_design_variable_heatmap(
    results: List[EvaluationResult],
    feasible_only: bool = True,
    output_path: Optional[Union[str, Path]] = None,
) -> plt.Figure:
    """
    Pearson correlation heatmap between all 6 design variables.
    Optionally restricted to feasible evaluations only.
    """
    df = results_to_dataframe(results)
    subset = df[df["simulation_valid"]]
    if feasible_only:
        subset = subset[subset["physically_feasible"]]

    corr = subset[DESIGN_VAR_COLUMNS].dropna().corr()

    fig, ax = plt.subplots(figsize=(7, 6))
    im = ax.imshow(corr.values, vmin=-1, vmax=1, cmap="RdBu_r", aspect="auto")
    fig.colorbar(im, ax=ax, label="Pearson r", shrink=0.85)

    ax.set_xticks(range(6))
    ax.set_yticks(range(6))
    ax.set_xticklabels(DESIGN_VAR_SHORT_LABELS, fontsize=11, rotation=30, ha="right")
    ax.set_yticklabels(DESIGN_VAR_SHORT_LABELS, fontsize=11)

    for i in range(6):
        for j in range(6):
            val = corr.values[i, j]
            txt_color = "white" if abs(val) > 0.6 else "black"
            ax.text(j, i, f"{val:.2f}", ha="center", va="center",
                    fontsize=9, color=txt_color)

    label = "Feasible" if feasible_only else "All Valid"
    ax.set_title(f"Design Variable Correlation ({label} Evaluations)", fontsize=13)
    fig.tight_layout()
    save_fig(fig, output_path)
    return fig


def plot_parallel_coordinates(
    results: List[EvaluationResult],
    color_by: str = "norm_emit_x_m_rad",
    feasible_only: bool = True,
    n_lines: int = 200,
    output_path: Optional[Union[str, Path]] = None,
) -> plt.Figure:
    """
    Parallel coordinates plot of the 6 design variables, coloured by one
    physical objective (default: ε_nx).
    """
    df = results_to_dataframe(results)
    subset = df[df["simulation_valid"]]
    if feasible_only:
        subset = subset[subset["physically_feasible"]]
    subset = subset.dropna(subset=DESIGN_VAR_COLUMNS + [color_by])
    if len(subset) > n_lines:
        subset = subset.sample(n_lines, random_state=0)

    # normalise each axis to [0, 1] for plotting
    norm_df = subset[DESIGN_VAR_COLUMNS].copy()
    for col in DESIGN_VAR_COLUMNS:
        lo, hi = norm_df[col].min(), norm_df[col].max()
        norm_df[col] = (norm_df[col] - lo) / (hi - lo + 1e-30)

    c_vals = subset[color_by].values
    cmap = cm.plasma
    c_norm = mcolors.Normalize(c_vals.min(), c_vals.max())
    sm = cm.ScalarMappable(cmap=cmap, norm=c_norm)

    fig, ax = plt.subplots(figsize=(12, 6))
    n_vars = len(DESIGN_VAR_COLUMNS)
    xs = np.arange(n_vars)

    for _, row in norm_df.iterrows():
        orig_idx = row.name
        rgba = cmap(c_norm(c_vals[list(subset.index).index(orig_idx)]))
        ax.plot(xs, row.values, color=rgba, alpha=0.4, linewidth=0.9)

    ax.set_xticks(xs)
    ax.set_xticklabels(DESIGN_VAR_LABELS, fontsize=11)
    ax.set_ylim(-0.05, 1.05)
    ax.set_ylabel("Normalised Value", fontsize=11)
    label = "Feasible" if feasible_only else "All Valid"
    cb_label = (r"$\varepsilon_{n,x}$ [m·rad]" if color_by == "norm_emit_x_m_rad"
                else color_by)
    ax.set_title(f"Parallel Coordinates — Design Variables ({label})", fontsize=13)
    fig.colorbar(sm, ax=ax, label=cb_label, shrink=0.85, pad=0.01)
    ax.grid(True, axis="x", linestyle=":", alpha=0.5)
    fig.tight_layout()
    save_fig(fig, output_path)
    return fig
