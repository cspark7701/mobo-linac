"""
Constraint diagnostics, feasibility rates, and GP posterior slices.

Constraint limit lines come from the active constraint profile of the supplied
configuration, so they always match the limits used to judge feasibility.
"""

from pathlib import Path
from typing import Any, List, Optional, Union

import matplotlib.pyplot as plt
import numpy as np
import torch

from mobo_linac.evaluation import EvaluationResult
from mobo_linac.io.results import results_to_dataframe
from mobo_linac.plotting.common import PlotSchema, grid_shape, save_fig, scaled


def plot_feasibility_rate(
    results: List[EvaluationResult],
    config,
    window: int = 10,
    output_path: Optional[Union[str, Path]] = None,
) -> plt.Figure:
    """Cumulative and rolling fraction of valid evaluations that are feasible."""
    df = results_to_dataframe(results, config)
    valid = df[df["simulation_valid"] == True].reset_index(drop=True)
    feasible_flag = (valid["physically_feasible"] == True).astype(float)
    idx = np.arange(1, len(valid) + 1)
    cumulative_rate = feasible_flag.expanding().mean() * 100
    rolling_rate = feasible_flag.rolling(window=window, min_periods=1).mean() * 100

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(idx, cumulative_rate, color="steelblue", linewidth=2, label="Cumulative feasibility rate")
    ax.plot(idx, rolling_rate, color="darkorange", linewidth=1.8, linestyle="--", label=f"Rolling {window}-eval window")
    ax.fill_between(idx, cumulative_rate, alpha=0.12, color="steelblue")
    ax.set_ylim(0, 105)
    ax.set_xlabel("Valid Evaluation Index", fontsize=12)
    ax.set_ylabel("Feasibility Rate [%]", fontsize=12)
    ax.set_title("Beam Feasibility Rate Over BO Campaign", fontsize=14)
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(fontsize=10)
    fig.tight_layout()
    save_fig(fig, output_path)
    return fig


def _limit_lines(ax, spec, horizontal: bool = True):
    for side, bound, style in (("Min", spec.lower, ":"), ("Max", spec.upper, "--")):
        if bound is not None:
            value = bound / spec.scale
            (ax.axhline if horizontal else ax.axvline)(value, color="crimson", linestyle=style, linewidth=1.3,
                                                       label=f"{side} {value:g}")


def plot_constraint_diagnostics(
    results: List[EvaluationResult],
    config,
    output_path: Optional[Union[str, Path]] = None,
) -> plt.Figure:
    """Every constraint channel across valid evaluations with the configured limits."""
    schema = PlotSchema.from_config(config)
    df = results_to_dataframe(results, config)
    valid = df[df["simulation_valid"] == True].reset_index(drop=True)
    idx = np.arange(1, len(valid) + 1)
    rows, columns = grid_shape(len(schema.constraints))
    fig, axes = plt.subplots(rows, columns, figsize=(5 * columns, 3.5 * rows), squeeze=False)
    for ax, spec in zip(axes.flat, schema.constraints):
        ax.plot(idx, scaled(valid, spec.column, spec.scale), color="steelblue", marker=".", linewidth=1)
        _limit_lines(ax, spec)
        ax.set_ylabel(spec.label, fontsize=11)
        ax.set_xlabel("Valid Evaluation Index", fontsize=10)
        ax.grid(True, linestyle=":", alpha=0.6)
        ax.legend(fontsize=8)
    for ax in list(axes.flat)[len(schema.constraints):]:
        ax.set_visible(False)
    fig.suptitle("Beam Quality Constraint Diagnostics (active profile limits)", fontsize=14)
    fig.tight_layout()
    save_fig(fig, output_path)
    return fig


def plot_constraint_violins(
    results: List[EvaluationResult],
    config,
    output_path: Optional[Union[str, Path]] = None,
) -> plt.Figure:
    """Distribution of each constraint channel for feasible and infeasible valid evaluations."""
    schema = PlotSchema.from_config(config)
    df = results_to_dataframe(results, config)
    valid = df[df["simulation_valid"] == True]
    feasible = valid[valid["physically_feasible"] == True]
    infeasible = valid[valid["physically_feasible"] != True]
    fig, axes = plt.subplots(1, len(schema.constraints), figsize=(3 * len(schema.constraints), 5), squeeze=False)
    for ax, spec in zip(axes[0], schema.constraints):
        groups = [(name, scaled(frame, spec.column, spec.scale).dropna().to_numpy())
                  for name, frame in (("Feasible", feasible), ("Infeasible", infeasible))]
        groups = [(name, data) for name, data in groups if len(data)]
        if groups:
            parts = ax.violinplot([data for _, data in groups], positions=list(range(1, len(groups) + 1)),
                                  showmedians=True, showextrema=True)
            for body in parts["bodies"]:
                body.set_alpha(0.6)
        _limit_lines(ax, spec)
        ax.set_xticks(range(1, len(groups) + 1))
        ax.set_xticklabels([name for name, _ in groups], fontsize=9, rotation=15)
        ax.set_ylabel(spec.label, fontsize=10)
        ax.grid(True, axis="y", linestyle=":", alpha=0.6)
    fig.suptitle("Constraint Diagnostic Distributions (Feasible vs Infeasible)", fontsize=13)
    fig.tight_layout()
    save_fig(fig, output_path)
    return fig


def plot_gp_surrogate_slice(
    model: Any,
    bounds: torch.Tensor,
    fixed_x: torch.Tensor,
    config,
    dim: int = 0,
    obj_idx: int = 0,
    n_points: int = 100,
    output_path: Optional[Union[str, Path]] = None,
) -> plt.Figure:
    """1D slice of one GP output along one design variable, others fixed at ``fixed_x``.

    The surrogate is in model space; ``obj_idx`` indexes the model outputs, and the
    label names the configured objective when the index is an objective.
    """
    schema = PlotSchema.from_config(config)
    lo, hi = bounds[0, dim].item(), bounds[1, dim].item()
    sweep = torch.linspace(lo, hi, n_points, dtype=torch.double)
    X_test = fixed_x.unsqueeze(0).repeat(n_points, 1).clone()
    X_test[:, dim] = sweep
    sub_model = model.models[obj_idx] if hasattr(model, "models") else model
    with torch.no_grad():
        posterior = sub_model.posterior(X_test)
        mean = posterior.mean.squeeze().cpu().numpy()
        std = posterior.variance.clamp_min(0).sqrt().squeeze().cpu().numpy()
    x = sweep.cpu().numpy()
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(x, mean, color="steelblue", linewidth=2, label="GP mean")
    ax.fill_between(x, mean - 2 * std, mean + 2 * std, alpha=0.25, color="steelblue", label="±2σ")
    ax.set_xlabel(schema.design[dim].label, fontsize=12)
    output_label = schema.objectives[obj_idx].column if obj_idx < len(schema.objectives) else f"Output {obj_idx}"
    ax.set_ylabel(f"model-space {output_label}", fontsize=12)
    ax.set_title(f"GP Posterior Slice — {schema.design[dim].label}", fontsize=13)
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(fontsize=10)
    fig.tight_layout()
    save_fig(fig, output_path)
    return fig
