"""
Convergence and optimization progress visualization routines.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from mobo_linac.evaluation import EvaluationResult
from mobo_linac.io.results import results_to_dataframe
from mobo_linac.plotting.common import (
    EMIT_SCALE,
    ENERGY_SCALE,
    OBJ_LABELS,
    save_fig,
)


def plot_hypervolume_progress(
    history: Union[pd.DataFrame, List[dict]],
    output_path: Optional[Union[str, Path]] = None,
) -> plt.Figure:
    """Hypervolume progress (feasible + all-point) over cumulative evaluations or iterations."""
    df = pd.DataFrame(history) if isinstance(history, list) else history

    if "cumulative_astra_evaluations" in df.columns:
        x = df["cumulative_astra_evaluations"]
        xlabel = "Cumulative ASTRA Evaluations"
    elif "cumulative_evaluations" in df.columns:
        x = df["cumulative_evaluations"]
        xlabel = "Cumulative ASTRA Evaluations"
    elif "num_valid_points" in df.columns:
        x = df["num_valid_points"]
        xlabel = "Cumulative Evaluations"
    elif "iteration" in df.columns:
        x = df["iteration"]
        xlabel = "Iteration"
    else:
        x = range(1, len(df) + 1)
        xlabel = "Step"

    fig, ax = plt.subplots(figsize=(9, 5))
    if "feasible_hypervolume" in df.columns:
        ax.plot(x, df["feasible_hypervolume"], "o-", color="steelblue",
                linewidth=2, markersize=5, label="Feasible Hypervolume")
    elif "fixed_ref_feasible_hv" in df.columns:
        ax.plot(x, df["fixed_ref_feasible_hv"], "o-", color="steelblue",
                linewidth=2, markersize=5, label="Feasible Hypervolume")

    if "all_point_hypervolume" in df.columns:
        ax.plot(x, df["all_point_hypervolume"], "s--", color="slategray",
                linewidth=1.5, alpha=0.7, label="All-Point Hypervolume")
    elif "fixed_ref_all_valid_hv" in df.columns:
        ax.plot(x, df["fixed_ref_all_valid_hv"], "s--", color="slategray",
                linewidth=1.5, alpha=0.7, label="All-Point Hypervolume")

    ax.set_xlabel(xlabel, fontsize=13)
    ax.set_ylabel("Hypervolume", fontsize=13)
    ax.set_title("Hypervolume Progress", fontsize=15)
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(fontsize=11)
    fig.tight_layout()
    save_fig(fig, output_path)
    return fig


def plot_objective_evolution(
    results: List[EvaluationResult],
    output_path: Optional[Union[str, Path]] = None,
) -> plt.Figure:
    """Three-panel time-series of each physical objective across evaluations."""
    df = results_to_dataframe(results)
    valid = df[df["simulation_valid"]].reset_index(drop=True)
    idx = range(1, len(valid) + 1)

    fig, axes = plt.subplots(3, 1, figsize=(11, 8), sharex=True)
    colors = ["steelblue", "darkorange", "seagreen"]
    cols = ["norm_emit_x_m_rad", "norm_emit_y_m_rad", "sigma_energy_eV"]
    scales = [EMIT_SCALE, EMIT_SCALE, ENERGY_SCALE]

    for ax, col, scale, label, color in zip(axes, cols, scales, OBJ_LABELS, colors):
        vals = valid[col] * scale
        ax.plot(idx, vals, color=color, linewidth=1.5, alpha=0.8)
        ax.scatter(idx, vals, c=color, s=18, zorder=3)
        # rolling minimum line
        ax.plot(idx, vals.cummin(), color=color, linestyle="--",
                linewidth=1.2, alpha=0.5, label="Best so far")
        ax.set_ylabel(label, fontsize=11)
        ax.grid(True, linestyle=":", alpha=0.6)
        ax.legend(fontsize=9, loc="upper right")

    axes[-1].set_xlabel("Evaluation Index", fontsize=12)
    fig.suptitle("Physical Objectives — Evaluation History", fontsize=14)
    fig.tight_layout()
    save_fig(fig, output_path)
    return fig


def plot_best_so_far(
    results: List[EvaluationResult],
    output_path: Optional[Union[str, Path]] = None,
) -> plt.Figure:
    """
    Running best (feasible) value for each objective vs evaluation index.
    Only improves when a new feasible evaluation beats the previous best.
    """
    df = results_to_dataframe(results)
    feas = df[df["simulation_valid"] & df["physically_feasible"]].reset_index(drop=True)

    fig, axes = plt.subplots(3, 1, figsize=(11, 8), sharex=True)
    colors = ["steelblue", "darkorange", "seagreen"]
    cols = ["norm_emit_x_m_rad", "norm_emit_y_m_rad", "sigma_energy_eV"]
    scales = [EMIT_SCALE, EMIT_SCALE, ENERGY_SCALE]

    for ax, col, scale, label, color in zip(axes, cols, scales, OBJ_LABELS, colors):
        vals = feas[col] * scale
        best = vals.cummin()
        idx = range(1, len(feas) + 1)
        ax.step(idx, best, where="post", color=color, linewidth=2.5, label="Best (feasible)")
        ax.scatter(idx, vals, c="lightgray", s=18, zorder=2, label="Feasible evals")
        ax.set_ylabel(label, fontsize=11)
        ax.grid(True, linestyle=":", alpha=0.6)
        ax.legend(fontsize=9, loc="upper right")

    axes[-1].set_xlabel("Feasible Evaluation Index", fontsize=12)
    fig.suptitle("Best-so-Far Progression (Feasible Evaluations)", fontsize=14)
    fig.tight_layout()
    save_fig(fig, output_path)
    return fig


def plot_scalarized_objective_trace(
    results: List[EvaluationResult],
    weights: Sequence[float] = (1.0, 1.0, 1.0),
    output_path: Optional[Union[str, Path]] = None,
) -> plt.Figure:
    """
    Phase 1 specific: plots the scalarised merit function value
    f(x) = w1*ε_nx + w2*ε_ny + w3*σ_E (normalised by first value) and the
    individual objective contributions, over evaluation history.
    """
    df = results_to_dataframe(results)
    valid = df[df["simulation_valid"]].reset_index(drop=True)
    w = np.array(weights, dtype=float)

    ex = valid["norm_emit_x_m_rad"].values * EMIT_SCALE
    ey = valid["norm_emit_y_m_rad"].values * EMIT_SCALE
    se = valid["sigma_energy_eV"].values * ENERGY_SCALE

    def _safe_norm(arr: np.ndarray) -> np.ndarray:
        ref = arr[arr > 0][0] if np.any(arr > 0) else 1.0
        return arr / ref

    ex_n, ey_n, se_n = _safe_norm(ex), _safe_norm(ey), _safe_norm(se)
    scalar = w[0] * ex_n + w[1] * ey_n + w[2] * se_n
    idx = range(1, len(valid) + 1)

    fig, (ax_top, ax_bot) = plt.subplots(2, 1, figsize=(11, 7), sharex=True)

    ax_top.plot(idx, scalar, color="steelblue", linewidth=1.5, alpha=0.8, label="f(x)")
    ax_top.plot(idx, pd.Series(scalar).cummin(), color="crimson", linestyle="--",
                linewidth=2, label="Best so far")
    ax_top.set_ylabel(f"f(x) = {w[0]:.1f}·ε̃_x + {w[1]:.1f}·ε̃_y + {w[2]:.1f}·σ̃_E", fontsize=11)
    ax_top.set_title(f"Scalarized Objective Trace  (weights {w.tolist()})", fontsize=13)
    ax_top.grid(True, linestyle=":", alpha=0.6)
    ax_top.legend(fontsize=10)

    ax_bot.stackplot(
        idx, w[0] * ex_n, w[1] * ey_n, w[2] * se_n,
        labels=[r"$w_1\tilde\varepsilon_{n,x}$",
                r"$w_2\tilde\varepsilon_{n,y}$",
                r"$w_3\tilde\sigma_E$"],
        colors=["steelblue", "darkorange", "seagreen"],
        alpha=0.65,
    )
    ax_bot.set_xlabel("Evaluation Index", fontsize=12)
    ax_bot.set_ylabel("Normalised contribution", fontsize=11)
    ax_bot.set_title("Objective Contribution Breakdown", fontsize=12)
    ax_bot.grid(True, linestyle=":", alpha=0.6)
    ax_bot.legend(loc="upper right", fontsize=9)

    fig.tight_layout()
    save_fig(fig, output_path)
    return fig


def plot_hypervolume_comparison(
    trackers: Optional[Dict[str, Any]] = None,
    hist_p2: Optional[pd.DataFrame] = None,
    hist_p3: Optional[pd.DataFrame] = None,
    output_path: Optional[Union[str, Path]] = None,
) -> plt.Figure:
    """Overlaid hypervolume progress for multi-phase comparison."""
    fig, ax = plt.subplots(figsize=(9, 5))

    colors = ["steelblue", "seagreen", "darkorange", "purple", "crimson"]

    if trackers is not None:
        for i, (label, tracker) in enumerate(trackers.items()):
            history = tracker.history
            if not history:
                continue
            iters = [h.iteration for h in history]
            hvs = [h.feasible_hypervolume for h in history]
            color = colors[i % len(colors)]
            ax.plot(iters, hvs, "o-", color=color, linewidth=2, label=label)
    elif hist_p2 is not None and hist_p3 is not None:
        iters_p2 = hist_p2.get("iteration", range(len(hist_p2)))
        iters_p3 = hist_p3.get("iteration", range(len(hist_p3)))

        ax.plot(iters_p2, hist_p2["feasible_hypervolume"], "o-",
                color="steelblue", linewidth=2, label="Phase 2 (Unconstrained HV)")
        ax.plot(iters_p3, hist_p3["feasible_hypervolume"], "s-",
                color="seagreen", linewidth=2, label="Phase 3 (Constrained HV)")

        for (iters, hist, color) in [(iters_p2, hist_p2, "steelblue"),
                                      (iters_p3, hist_p3, "seagreen")]:
            if "all_point_hypervolume" in hist.columns:
                ax.plot(iters, hist["all_point_hypervolume"], linestyle="--",
                        color=color, alpha=0.4)

    ax.set_xlabel("Iteration", fontsize=13)
    ax.set_ylabel("Hypervolume", fontsize=13)
    ax.set_title("Feasible Hypervolume Comparison", fontsize=14)
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(fontsize=11)
    fig.tight_layout()
    save_fig(fig, output_path)
    return fig


def plot_benchmark_comparison(
    aggregate_df: pd.DataFrame,
    output_path: Optional[Union[str, Path]] = None,
    title: str = "Benchmark Campaign Comparison: Median Feasible Hypervolume",
) -> plt.Figure:
    """Plots median feasible hypervolume progress with 95% bootstrap CI bands for all algorithms."""
    fig, ax = plt.subplots(figsize=(10, 6))
    palette = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#7f7f7f"]

    algorithms = aggregate_df["algorithm"].unique()
    for i, algo in enumerate(algorithms):
        sub = aggregate_df[aggregate_df["algorithm"] == algo].sort_values("cumulative_astra_evaluations")
        color = palette[i % len(palette)]
        evals = sub["cumulative_astra_evaluations"].values
        med = sub["median_feasible_hv"].values
        lo = sub["ci_lower_feasible_hv"].values
        hi = sub["ci_upper_feasible_hv"].values

        label = algo.replace("_", " ").title()
        ax.plot(evals, med, color=color, linewidth=2, label=label)
        ax.fill_between(evals, lo, hi, color=color, alpha=0.15)

    ax.set_xlabel("Cumulative ASTRA Evaluations", fontsize=12)
    ax.set_ylabel("Median Feasible Hypervolume (fixed ref.)", fontsize=12)
    ax.set_title(title, fontsize=14)
    ax.legend(fontsize=10, loc="lower right")
    ax.grid(True, linestyle=":", alpha=0.5)
    fig.tight_layout()
    save_fig(fig, output_path)
    return fig


def plot_benchmark_feasibility_comparison(
    aggregate_df: pd.DataFrame,
    output_path: Optional[Union[str, Path]] = None,
    title: str = "Benchmark Campaign Comparison: Feasible Fraction",
) -> plt.Figure:
    """Plots median feasible fraction over cumulative evaluations with 95% CI bands."""
    fig, ax = plt.subplots(figsize=(10, 5))
    palette = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2"]

    algorithms = aggregate_df["algorithm"].unique()
    for i, algo in enumerate(algorithms):
        sub = aggregate_df[aggregate_df["algorithm"] == algo].sort_values("cumulative_astra_evaluations")
        color = palette[i % len(palette)]
        evals = sub["cumulative_astra_evaluations"].values
        med = sub["median_feasible_fraction"].values
        lo = sub["ci_lower_feasible_fraction"].values
        hi = sub["ci_upper_feasible_fraction"].values

        label = algo.replace("_", " ").title()
        ax.plot(evals, med, color=color, linewidth=2, label=label)
        ax.fill_between(evals, lo, hi, color=color, alpha=0.15)

    ax.set_xlabel("Cumulative ASTRA Evaluations", fontsize=12)
    ax.set_ylabel("Median Feasible Fraction", fontsize=12)
    ax.set_title(title, fontsize=14)
    ax.set_ylim(0.0, 1.05)
    ax.legend(fontsize=10, loc="lower right")
    ax.grid(True, linestyle=":", alpha=0.5)
    fig.tight_layout()
    save_fig(fig, output_path)
    return fig
