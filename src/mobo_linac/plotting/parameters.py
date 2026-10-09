"""
Design parameter correlation heatmaps and parallel coordinate figures.
"""

from pathlib import Path
from typing import List, Optional, Union

import matplotlib.cm as cm
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np

from mobo_linac.evaluation import EvaluationResult
from mobo_linac.io.results import results_to_dataframe
from mobo_linac.plotting.common import PlotSchema, save_fig


def _subset(results, config, feasible_only):
    df = results_to_dataframe(results, config)
    subset = df[df["simulation_valid"] == True]
    if feasible_only:
        subset = subset[subset["physically_feasible"] == True]
    return subset


def plot_design_variable_heatmap(
    results: List[EvaluationResult],
    config,
    feasible_only: bool = True,
    output_path: Optional[Union[str, Path]] = None,
) -> plt.Figure:
    """Pearson correlation between the configured design variables."""
    schema = PlotSchema.from_config(config)
    columns = [spec.column for spec in schema.design]
    corr = _subset(results, config, feasible_only)[columns].dropna().corr().to_numpy()
    n = len(columns)
    fig, ax = plt.subplots(figsize=(1.2 * n + 2, 1.0 * n + 2))
    image = ax.imshow(corr, vmin=-1, vmax=1, cmap="RdBu_r", aspect="auto")
    fig.colorbar(image, ax=ax, label="Pearson r", shrink=0.85)
    labels = [spec.label for spec in schema.design]
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(labels, fontsize=10, rotation=30, ha="right")
    ax.set_yticklabels(labels, fontsize=10)
    for i in range(n):
        for j in range(n):
            if np.isfinite(corr[i, j]):
                ax.text(j, i, f"{corr[i, j]:.2f}", ha="center", va="center", fontsize=9,
                        color="white" if abs(corr[i, j]) > 0.6 else "black")
    ax.set_title(f"Design Variable Correlation ({'Feasible' if feasible_only else 'All Valid'} Evaluations)", fontsize=13)
    fig.tight_layout()
    save_fig(fig, output_path)
    return fig


def plot_parallel_coordinates(
    results: List[EvaluationResult],
    config,
    color_by: Optional[str] = None,
    feasible_only: bool = True,
    n_lines: int = 200,
    output_path: Optional[Union[str, Path]] = None,
) -> plt.Figure:
    """Design variables normalized to [0, 1], colored by one configured objective (default: the first)."""
    schema = PlotSchema.from_config(config)
    columns = [spec.column for spec in schema.design]
    objective = schema.objective(color_by) if color_by else schema.objectives[0]
    subset = _subset(results, config, feasible_only).dropna(subset=columns + [objective.column])
    if len(subset) > n_lines:
        subset = subset.sample(n_lines, random_state=0)
    values = subset[columns].to_numpy(dtype=float)
    span = values.max(axis=0) - values.min(axis=0) if len(values) else np.ones(len(columns))
    normalized = (values - (values.min(axis=0) if len(values) else 0)) / np.where(span > 0, span, 1.0)
    colors = subset[objective.column].to_numpy(dtype=float) / objective.scale
    norm = mcolors.Normalize(colors.min() if len(colors) else 0, colors.max() if len(colors) else 1)
    mappable = cm.ScalarMappable(cmap=cm.plasma, norm=norm)
    fig, ax = plt.subplots(figsize=(12, 6))
    xs = np.arange(len(columns))
    for row, value in zip(normalized, colors):
        ax.plot(xs, row, color=cm.plasma(norm(value)), alpha=0.4, linewidth=0.9)
    ax.set_xticks(xs)
    ax.set_xticklabels([spec.label for spec in schema.design], fontsize=10)
    ax.set_ylim(-0.05, 1.05)
    ax.set_ylabel("Normalised Value", fontsize=11)
    ax.set_title(f"Parallel Coordinates — Design Variables ({'Feasible' if feasible_only else 'All Valid'})", fontsize=13)
    fig.colorbar(mappable, ax=ax, label=objective.label, shrink=0.85, pad=0.01)
    ax.grid(True, axis="x", linestyle=":", alpha=0.5)
    fig.tight_layout()
    save_fig(fig, output_path)
    return fig
