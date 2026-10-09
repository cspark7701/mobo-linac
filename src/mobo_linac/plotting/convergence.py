"""
Convergence and optimization progress figures.
"""

from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Union

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from mobo_linac.evaluation import EvaluationResult
from mobo_linac.io.results import results_to_dataframe
from mobo_linac.plotting.common import PlotSchema, best_so_far, save_fig, scaled

COLORS = ["steelblue", "darkorange", "seagreen", "purple", "crimson", "saddlebrown"]


def _history_frame(history) -> pd.DataFrame:
    if hasattr(history, "to_dataframe"):  # HypervolumeTracker
        return history.to_dataframe()
    return pd.DataFrame(history) if isinstance(history, list) else history


def _progress_axis(df: pd.DataFrame):
    for column, label in (("cumulative_astra_evaluations", "Cumulative ASTRA Evaluations"),
                          ("num_valid_points", "Cumulative Valid Observations"), ("iteration", "Iteration")):
        if column in df.columns:
            return df[column], label
    return range(1, len(df) + 1), "Step"


def _hv_columns(df: pd.DataFrame):
    feasible = "feasible_hypervolume" if "feasible_hypervolume" in df.columns else "fixed_ref_feasible_hv"
    all_points = "all_point_hypervolume" if "all_point_hypervolume" in df.columns else "fixed_ref_all_valid_hv"
    return feasible, all_points


def plot_hypervolume_progress(
    history: Union[pd.DataFrame, List[dict]],
    output_path: Optional[Union[str, Path]] = None,
) -> plt.Figure:
    """Feasible and all-point hypervolume over iterations or cumulative evaluations."""
    df = _history_frame(history)
    x, xlabel = _progress_axis(df)
    feasible, all_points = _hv_columns(df)
    fig, ax = plt.subplots(figsize=(9, 5))
    if feasible in df.columns:
        ax.plot(x, df[feasible], "o-", color="steelblue", linewidth=2, markersize=5, label="Feasible Hypervolume")
    if all_points in df.columns:
        ax.plot(x, df[all_points], "s--", color="slategray", linewidth=1.5, alpha=0.7, label="All-Point Hypervolume")
    ax.set_xlabel(xlabel, fontsize=13)
    ax.set_ylabel("Hypervolume", fontsize=13)
    ax.set_title("Hypervolume Progress", fontsize=15)
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(fontsize=11)
    fig.tight_layout()
    save_fig(fig, output_path)
    return fig


def plot_hypervolume_histories(
    histories: Mapping[str, Any],
    output_path: Optional[Union[str, Path]] = None,
) -> plt.Figure:
    """Overlay feasible (solid) and all-point (dashed) hypervolume of several campaigns.

    ``histories`` maps a label to a HypervolumeTracker, a history DataFrame or a list of records.
    """
    fig, ax = plt.subplots(figsize=(9, 5))
    xlabel = "Iteration"
    for index, (label, history) in enumerate(histories.items()):
        df = _history_frame(history)
        if df.empty:
            continue
        x, xlabel = _progress_axis(df)
        feasible, all_points = _hv_columns(df)
        color = COLORS[index % len(COLORS)]
        ax.plot(x, df[feasible], "o-", color=color, linewidth=2, label=label)
        if all_points in df.columns:
            ax.plot(x, df[all_points], linestyle="--", color=color, alpha=0.4)
    ax.set_xlabel(xlabel, fontsize=13)
    ax.set_ylabel("Hypervolume", fontsize=13)
    ax.set_title("Feasible Hypervolume Comparison", fontsize=14)
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(fontsize=11)
    fig.tight_layout()
    save_fig(fig, output_path)
    return fig


def _objective_panels(results, config, feasible_only: bool):
    schema = PlotSchema.from_config(config)
    df = results_to_dataframe(results, config)
    mask = df["simulation_valid"] == True
    if feasible_only:
        mask &= df["physically_feasible"] == True
    data = df[mask].reset_index(drop=True)
    fig, axes = plt.subplots(len(schema.objectives), 1, figsize=(11, 3 * len(schema.objectives)),
                             sharex=True, squeeze=False)
    return schema, data, fig, axes[:, 0]


def plot_objective_evolution(
    results: List[EvaluationResult],
    output_path: Optional[Union[str, Path]] = None,
    config=None,
) -> plt.Figure:
    """Each configured objective across valid evaluations, with its running best."""
    schema, valid, fig, axes = _objective_panels(results, config, feasible_only=False)
    idx = np.arange(1, len(valid) + 1)
    for i, (ax, spec) in enumerate(zip(axes, schema.objectives)):
        color = COLORS[i % len(COLORS)]
        values = scaled(valid, spec.column, spec.scale)
        ax.plot(idx, values, color=color, linewidth=1.5, alpha=0.8)
        ax.scatter(idx, values, c=color, s=18, zorder=3)
        ax.plot(idx, best_so_far(values, spec.sign), color=color, linestyle="--", linewidth=1.2, alpha=0.5, label="Best so far")
        ax.set_ylabel(spec.label, fontsize=11)
        ax.grid(True, linestyle=":", alpha=0.6)
        ax.legend(fontsize=9, loc="upper right")
    axes[-1].set_xlabel("Valid Evaluation Index", fontsize=12)
    fig.suptitle("Physical Objectives — Evaluation History", fontsize=14)
    fig.tight_layout()
    save_fig(fig, output_path)
    return fig


def plot_best_so_far(
    results: List[EvaluationResult],
    output_path: Optional[Union[str, Path]] = None,
    config=None,
) -> plt.Figure:
    """Running best feasible value of each objective, in its preferred direction."""
    schema, feasible, fig, axes = _objective_panels(results, config, feasible_only=True)
    idx = np.arange(1, len(feasible) + 1)
    for i, (ax, spec) in enumerate(zip(axes, schema.objectives)):
        values = scaled(feasible, spec.column, spec.scale)
        ax.step(idx, best_so_far(values, spec.sign), where="post", color=COLORS[i % len(COLORS)], linewidth=2.5,
                label="Best (feasible)")
        ax.scatter(idx, values, c="lightgray", s=18, zorder=2, label="Feasible evals")
        ax.set_ylabel(spec.label, fontsize=11)
        ax.grid(True, linestyle=":", alpha=0.6)
        ax.legend(fontsize=9, loc="upper right")
    axes[-1].set_xlabel("Feasible Evaluation Index", fontsize=12)
    fig.suptitle("Best-so-Far Progression (Feasible Evaluations)", fontsize=14)
    fig.tight_layout()
    save_fig(fig, output_path)
    return fig


def plot_scalarized_objective_trace(
    results: List[EvaluationResult],
    weights: Sequence[float],
    output_path: Optional[Union[str, Path]] = None,
    config=None,
) -> plt.Figure:
    """Weighted sum of scale-normalized objective costs (as optimized by scalarized BO) and its parts."""
    schema = PlotSchema.from_config(config)
    df = results_to_dataframe(results, config)
    valid = df[df["simulation_valid"] == True].reset_index(drop=True)
    w = np.asarray(weights, dtype=float)
    if w.shape != (len(schema.objectives),):
        raise ValueError("Weights must match the configured objectives.")
    w = w / w.sum()
    parts = [w[i] * scaled(valid, spec.column, spec.scale).to_numpy() * -spec.sign
             for i, spec in enumerate(schema.objectives)]
    total = np.sum(parts, axis=0) if parts else np.zeros(0)
    idx = np.arange(1, len(valid) + 1)
    fig, (ax_top, ax_bot) = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
    ax_top.plot(idx, total, color="steelblue", linewidth=1.5, alpha=0.8, label="weighted cost")
    ax_top.plot(idx, pd.Series(total).cummin(), color="crimson", linestyle="--", linewidth=2, label="Best so far")
    ax_top.set_ylabel("Weighted scaled cost", fontsize=11)
    ax_top.set_title(f"Scalarized Objective Trace (weights {np.round(w, 3).tolist()})", fontsize=13)
    ax_top.grid(True, linestyle=":", alpha=0.6)
    ax_top.legend(fontsize=10)
    for i, (part, spec) in enumerate(zip(parts, schema.objectives)):
        ax_bot.plot(idx, part, color=COLORS[i % len(COLORS)], label=f"w·{spec.label}")
    ax_bot.set_xlabel("Valid Evaluation Index", fontsize=12)
    ax_bot.set_ylabel("Weighted contribution", fontsize=11)
    ax_bot.grid(True, linestyle=":", alpha=0.6)
    ax_bot.legend(loc="upper right", fontsize=9)
    fig.tight_layout()
    save_fig(fig, output_path)
    return fig


def _benchmark_bands(aggregate_df, median, lower, upper, ylabel, title, output_path, ylim=None):
    fig, ax = plt.subplots(figsize=(10, 6))
    palette = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#7f7f7f"]
    for i, algo in enumerate(aggregate_df["algorithm"].unique()):
        sub = aggregate_df[aggregate_df["algorithm"] == algo].sort_values("cumulative_astra_evaluations")
        color = palette[i % len(palette)]
        evals = sub["cumulative_astra_evaluations"].values
        ax.plot(evals, sub[median].values, color=color, linewidth=2, label=algo.replace("_", " ").title())
        ax.fill_between(evals, sub[lower].values, sub[upper].values, color=color, alpha=0.15)
    ax.set_xlabel("Cumulative ASTRA Evaluations", fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_title(title, fontsize=14)
    if ylim:
        ax.set_ylim(*ylim)
    ax.legend(fontsize=10, loc="lower right")
    ax.grid(True, linestyle=":", alpha=0.5)
    fig.tight_layout()
    save_fig(fig, output_path)
    return fig


def plot_benchmark_comparison(aggregate_df: pd.DataFrame, output_path=None,
                              title: str = "Benchmark Campaign Comparison: Median Feasible Hypervolume") -> plt.Figure:
    """Median feasible hypervolume with bootstrap CI bands per algorithm."""
    return _benchmark_bands(aggregate_df, "median_feasible_hv", "ci_lower_feasible_hv", "ci_upper_feasible_hv",
                            "Median Feasible Hypervolume (fixed ref.)", title, output_path)


def plot_benchmark_feasibility_comparison(aggregate_df: pd.DataFrame, output_path=None,
                                          title: str = "Benchmark Campaign Comparison: Feasible Fraction") -> plt.Figure:
    """Median feasible fraction with bootstrap CI bands per algorithm."""
    return _benchmark_bands(aggregate_df, "median_feasible_fraction", "ci_lower_feasible_fraction",
                            "ci_upper_feasible_fraction", "Median Feasible Fraction", title, output_path, (0.0, 1.05))
