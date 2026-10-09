"""
Objective-space projections, Pareto fronts and verification comparisons.

Projections draw all valid evaluations, feasible evaluations, and the actual
non-dominated feasible front for every pair of configured objectives.
"""

from itertools import combinations
from pathlib import Path
from typing import List, Mapping, Optional, Sequence, Union

import matplotlib.pyplot as plt
import numpy as np

from mobo_linac.evaluation import EvaluationResult
from mobo_linac.io.results import results_to_dataframe
from mobo_linac.metrics.latex import measured, verification_records
from mobo_linac.plotting.common import PlotSchema, grid_shape, nondominated_mask, save_fig, scaled

COLORS = ["steelblue", "seagreen", "darkorange", "purple", "crimson"]
MARKERS = ["o", "^", "s", "D", "v"]


def _pairs(schema: PlotSchema):
    pairs = list(combinations(schema.objectives, 2))
    if not pairs:
        raise ValueError("Objective projections require at least two configured objectives.")
    return pairs


def _frames(results, config):
    df = results_to_dataframe(results, config)
    valid = df[df["simulation_valid"] == True].reset_index(drop=True)
    feasible = valid[valid["physically_feasible"] == True].reset_index(drop=True)
    return valid, feasible


def plot_pareto_front(
    results: List[EvaluationResult],
    output_path: Optional[Union[str, Path]] = None,
    config=None,
) -> plt.Figure:
    """Pairwise objective projections with the non-dominated feasible front highlighted."""
    schema = PlotSchema.from_config(config)
    valid, feasible = _frames(results, config)
    front = feasible[nondominated_mask(feasible, schema)]
    pairs = _pairs(schema)
    rows, columns = grid_shape(len(pairs))
    fig, axes = plt.subplots(rows, columns, figsize=(6 * columns, 5 * rows), squeeze=False)
    for ax, (x, y) in zip(axes.flat, pairs):
        ax.scatter(scaled(valid, x.column, x.scale), scaled(valid, y.column, y.scale), c="lightgray", s=25, alpha=0.6, label="All valid")
        ax.scatter(scaled(feasible, x.column, x.scale), scaled(feasible, y.column, y.scale), c="steelblue", s=35, alpha=0.8, label="Feasible")
        ax.scatter(scaled(front, x.column, x.scale), scaled(front, y.column, y.scale), facecolors="none", edgecolors="crimson",
                   s=80, linewidths=1.5, label="Feasible Pareto front")
        ax.set_xlabel(x.label, fontsize=12)
        ax.set_ylabel(y.label, fontsize=12)
        ax.grid(True, linestyle=":", alpha=0.6)
        ax.legend(fontsize=9)
    for ax in list(axes.flat)[len(pairs):]:
        ax.set_visible(False)
    fig.suptitle("Objective Space — Pairwise Projections", fontsize=15)
    fig.tight_layout()
    save_fig(fig, output_path)
    return fig


def plot_pareto_front_3d(
    results: List[EvaluationResult],
    output_path: Optional[Union[str, Path]] = None,
    config=None,
    objectives: Optional[Sequence[str]] = None,
    elev: float = 25.0,
    azim: float = 45.0,
) -> plt.Figure:
    """Three configured objectives (default: the first three) with the feasible front highlighted."""
    schema = PlotSchema.from_config(config)
    specs = [schema.objective(name) for name in objectives] if objectives else list(schema.objectives[:3])
    if len(specs) != 3:
        raise ValueError("A 3D projection requires exactly three objectives.")
    valid, feasible = _frames(results, config)
    front = feasible[nondominated_mask(feasible, schema)]
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection="3d")
    for frame, style in ((valid[valid["physically_feasible"] != True], dict(c="lightgray", s=15, alpha=0.3, label="Infeasible")),
                         (feasible, dict(c="steelblue", s=30, alpha=0.6, label="Feasible")),
                         (front, dict(c="crimson", s=60, alpha=0.9, label="Feasible Pareto front"))):
        if len(frame):
            ax.scatter(*(scaled(frame, spec.column, spec.scale) for spec in specs), **style)
    ax.set_xlabel(specs[0].label, fontsize=11, labelpad=8)
    ax.set_ylabel(specs[1].label, fontsize=11, labelpad=8)
    ax.set_zlabel(specs[2].label, fontsize=11, labelpad=8)
    ax.set_title("3D Objective Space", fontsize=14)
    ax.view_init(elev=elev, azim=azim)
    ax.legend(fontsize=10)
    fig.tight_layout()
    save_fig(fig, output_path)
    return fig


def plot_pareto_front_overlay(
    results_by_label: Mapping[str, List[EvaluationResult]],
    config,
    output_path: Optional[Union[str, Path]] = None,
) -> plt.Figure:
    """Overlay the non-dominated feasible fronts of several campaigns in every objective pair."""
    schema = PlotSchema.from_config(config)
    pairs = _pairs(schema)
    rows, columns = grid_shape(len(pairs))
    fig, axes = plt.subplots(rows, columns, figsize=(6 * columns, 5 * rows), squeeze=False)
    for index, (label, results) in enumerate(results_by_label.items()):
        _, feasible = _frames(results, config)
        front = feasible[nondominated_mask(feasible, schema)]
        for ax, (x, y) in zip(axes.flat, pairs):
            ax.scatter(scaled(front, x.column, x.scale), scaled(front, y.column, y.scale), c=COLORS[index % len(COLORS)],
                       marker=MARKERS[index % len(MARKERS)], s=45, alpha=0.75, label=label)
    for ax, (x, y) in zip(axes.flat, pairs):
        ax.set_xlabel(x.label, fontsize=12)
        ax.set_ylabel(y.label, fontsize=12)
        ax.grid(True, linestyle=":", alpha=0.6)
        ax.legend(fontsize=10)
    for ax in list(axes.flat)[len(pairs):]:
        ax.set_visible(False)
    fig.suptitle("Feasible Pareto Front Comparison", fontsize=15)
    fig.tight_layout()
    save_fig(fig, output_path)
    return fig


def plot_pareto_verification_comparison(
    verification: Union[List[dict], str, Path],
    config,
    output_path: Optional[Union[str, Path]] = None,
) -> plt.Figure:
    """Stored vs rerun value of every configured objective per verified role; missing values are gaps."""
    schema = PlotSchema.from_config(config)
    records = verification_records(verification)
    roles = [str(record.get("role", f"Cand {i + 1}")) for i, record in enumerate(records)]
    fig, axes = plt.subplots(1, len(schema.objectives), figsize=(6 * len(schema.objectives), 5), squeeze=False)
    x = np.arange(len(roles))
    for ax, spec in zip(axes[0], schema.objectives):
        for offset, group, label, color in ((-0.175, "stored_objectives", "Stored", "steelblue"),
                                            (0.175, "rerun_objectives", "Rerun", "seagreen")):
            values = [measured(record.get(group, {}).get(spec.column)) / spec.scale for record in records]
            ax.bar(x + offset, values, 0.35, label=label, color=color, alpha=0.85)
        ax.set_xticks(x)
        ax.set_xticklabels(roles, rotation=15, ha="right", fontsize=9)
        ax.set_ylabel(spec.label, fontsize=11)
        ax.grid(True, linestyle=":", alpha=0.6, axis="y")
        ax.legend(fontsize=10)
    fig.suptitle("Pareto Candidate Verification (Stored vs Independent Rerun)", fontsize=14)
    fig.tight_layout()
    save_fig(fig, output_path)
    return fig
