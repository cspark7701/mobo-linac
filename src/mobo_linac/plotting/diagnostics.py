"""
Constraint diagnostics, feasibility rates, and GP posterior predictive residual plots.
"""

from pathlib import Path
from typing import Any, List, Optional, Union

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch

from mobo_linac.config import ConstraintsConfig
from mobo_linac.evaluation import EvaluationResult
from mobo_linac.io.results import results_to_dataframe
from mobo_linac.plotting.common import (
    DESIGN_VAR_LABELS,
    ENERGY_SCALE,
    OBJ_LABELS,
    save_fig,
)


def plot_feasibility_rate(
    results: List[EvaluationResult],
    window: int = 10,
    output_path: Optional[Union[str, Path]] = None,
) -> plt.Figure:
    """
    Cumulative and rolling feasibility rate (fraction of valid, feasible
    evaluations) as BO progresses.
    """
    df = results_to_dataframe(results)
    valid = df[df["simulation_valid"]].reset_index(drop=True)
    feasible_flag = valid["physically_feasible"].astype(float)
    idx = range(1, len(valid) + 1)

    cumulative_rate = feasible_flag.expanding().mean() * 100
    rolling_rate = feasible_flag.rolling(window=window, min_periods=1).mean() * 100

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(idx, cumulative_rate, color="steelblue", linewidth=2,
            label="Cumulative feasibility rate")
    ax.plot(idx, rolling_rate, color="darkorange", linewidth=1.8,
            linestyle="--", label=f"Rolling {window}-eval window")
    ax.fill_between(idx, cumulative_rate, alpha=0.12, color="steelblue")
    ax.set_ylim(0, 105)
    ax.set_xlabel("Valid Evaluation Index", fontsize=12)
    ax.set_ylabel("Feasibility Rate [%]", fontsize=12)
    ax.set_title("Beam Feasibility Rate Over BO Campaign", fontsize=14)
    ax.axhline(50, color="gray", linestyle=":", alpha=0.5, label="50% reference")
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(fontsize=10)
    fig.tight_layout()
    save_fig(fig, output_path)
    return fig


def plot_constraint_diagnostics(
    results: List[EvaluationResult],
    output_path: Optional[Union[str, Path]] = None,
) -> plt.Figure:
    """
    2×2 grid of constraint-diagnostic time-series with limit reference lines:
    beam sizes, divergences, bunch length, and mean kinetic energy.
    """
    df = results_to_dataframe(results)
    valid = df[df["simulation_valid"]].reset_index(drop=True)
    idx = range(1, len(valid) + 1)

    fig, axes = plt.subplots(2, 2, figsize=(13, 8))

    # 1. Transverse beam sizes
    axes[0, 0].plot(idx, valid["sigma_x_m"] * 1e3, label=r"$\sigma_x$", color="steelblue")
    axes[0, 0].plot(idx, valid["sigma_y_m"] * 1e3, label=r"$\sigma_y$", color="darkorange")
    axes[0, 0].axhline(1.0, color="crimson", linestyle="--", linewidth=1.4, label="Limit 1.0 mm")
    axes[0, 0].set_ylabel(r"$\sigma_{x,y}$ [mm]", fontsize=11)
    axes[0, 0].set_title("Transverse Beam Size", fontsize=12)
    axes[0, 0].grid(True, linestyle=":", alpha=0.6)
    axes[0, 0].legend(fontsize=9)

    # 2. Transverse divergence
    axes[0, 1].plot(idx, valid["sigma_xp_rad"] * 1e3, label=r"$\sigma_{x'}$", color="seagreen")
    axes[0, 1].plot(idx, valid["sigma_yp_rad"] * 1e3, label=r"$\sigma_{y'}$", color="purple")
    axes[0, 1].axhline(1.0, color="crimson", linestyle="--", linewidth=1.4, label="Limit 1.0 mrad")
    axes[0, 1].set_ylabel(r"$\sigma_{x',y'}$ [mrad]", fontsize=11)
    axes[0, 1].set_title("Transverse Divergence", fontsize=12)
    axes[0, 1].grid(True, linestyle=":", alpha=0.6)
    axes[0, 1].legend(fontsize=9)

    # 3. Bunch length
    axes[1, 0].plot(idx, valid["sigma_z_m"] * 1e3, label=r"$\sigma_z$", color="firebrick")
    axes[1, 0].axhline(1.0, color="crimson", linestyle="--", linewidth=1.4, label="Limit 1.0 mm")
    axes[1, 0].set_ylabel(r"$\sigma_z$ [mm]", fontsize=11)
    axes[1, 0].set_xlabel("Evaluation Index", fontsize=11)
    axes[1, 0].set_title("Bunch Length", fontsize=12)
    axes[1, 0].grid(True, linestyle=":", alpha=0.6)
    axes[1, 0].legend(fontsize=9)

    # 4. Mean kinetic energy
    axes[1, 1].plot(idx, valid["mean_kinetic_energy_eV"] * ENERGY_SCALE,
                    label=r"$E_{kin}$", color="saddlebrown")
    axes[1, 1].axhline(195.0, color="crimson", linestyle="--", linewidth=1.4, label="Min 195 MeV")
    axes[1, 1].axhline(205.0, color="crimson", linestyle="--", linewidth=1.4, label="Max 205 MeV")
    axes[1, 1].fill_between(idx, 195.0, 205.0, alpha=0.06, color="seagreen")
    axes[1, 1].set_ylabel("Kinetic Energy [MeV]", fontsize=11)
    axes[1, 1].set_xlabel("Evaluation Index", fontsize=11)
    axes[1, 1].set_title("Mean Kinetic Energy", fontsize=12)
    axes[1, 1].grid(True, linestyle=":", alpha=0.6)
    axes[1, 1].legend(fontsize=9)

    fig.suptitle("Beam Quality Constraint Diagnostics", fontsize=14)
    fig.tight_layout()
    save_fig(fig, output_path)
    return fig


def plot_constraint_violins(
    results: List[EvaluationResult],
    constraints_config: Optional[ConstraintsConfig] = None,
    output_path: Optional[Union[str, Path]] = None,
) -> plt.Figure:
    """
    Violin plots of each constraint diagnostic split by feasibility status,
    making the margin and tail behaviour immediately visible.
    """
    df = results_to_dataframe(results)
    valid = df[df["simulation_valid"]].copy()

    diag_cols = {
        r"$\sigma_x$ [mm]": ("sigma_x_m", 1e3, 1.0),
        r"$\sigma_y$ [mm]": ("sigma_y_m", 1e3, 1.0),
        r"$\sigma_{x'}$ [mrad]": ("sigma_xp_rad", 1e3, 1.0),
        r"$\sigma_{y'}$ [mrad]": ("sigma_yp_rad", 1e3, 1.0),
        r"$\sigma_z$ [mm]": ("sigma_z_m", 1e3, 1.0),
    }

    fig, axes = plt.subplots(1, len(diag_cols), figsize=(15, 5), sharey=False)

    feas = valid[valid["physically_feasible"]]
    infeas = valid[~valid["physically_feasible"]]

    for ax, (ylabel, (col, scale, limit)) in zip(axes, diag_cols.items()):
        data_f = (feas[col].dropna() * scale).values
        data_i = (infeas[col].dropna() * scale).values
        data_list = [d for d in [data_f, data_i] if len(d)]
        if data_list:
            parts = ax.violinplot(
                data_list,
                positions=list(range(1, len(data_list) + 1)),
                showmedians=True, showextrema=True,
            )
            for pc in parts["bodies"]:
                pc.set_alpha(0.6)
        ax.axhline(limit, color="crimson", linestyle="--", linewidth=1.3)
        labels = [lbl for lbl, d in zip(["Feasible", "Infeasible"], [data_f, data_i]) if len(d)]
        ax.set_xticks(range(1, len(labels) + 1))
        ax.set_xticklabels(labels, fontsize=9, rotation=15)
        ax.set_ylabel(ylabel, fontsize=10)
        ax.grid(True, axis="y", linestyle=":", alpha=0.6)

    fig.suptitle("Constraint Diagnostic Distributions (Feasible vs Infeasible)", fontsize=13)
    fig.tight_layout()
    save_fig(fig, output_path)
    return fig


def plot_gp_surrogate_slice(
    model: Any,
    bounds: torch.Tensor,
    fixed_x: torch.Tensor,
    dim: int = 0,
    obj_idx: int = 0,
    n_points: int = 100,
    output_path: Optional[Union[str, Path]] = None,
) -> plt.Figure:
    """
    1D slice through the GP surrogate posterior along one design variable,
    keeping all other dimensions fixed at `fixed_x`.
    """
    lo, hi = bounds[0, dim].item(), bounds[1, dim].item()
    sweep = torch.linspace(lo, hi, n_points, dtype=torch.double)

    X_test = fixed_x.unsqueeze(0).repeat(n_points, 1).clone()
    X_test[:, dim] = sweep

    # Handle ModelListGP vs single GP
    try:
        m = model.models[obj_idx]
    except AttributeError:
        m = model

    with torch.no_grad():
        post = m.posterior(X_test)
        mean = post.mean.squeeze().cpu().numpy()
        std = post.variance.clamp_min(0).sqrt().squeeze().cpu().numpy()

    sweep_np = sweep.cpu().numpy()
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(sweep_np, mean, color="steelblue", linewidth=2, label="GP mean")
    ax.fill_between(sweep_np, mean - 2 * std, mean + 2 * std,
                    alpha=0.25, color="steelblue", label="±2σ")
    ax.set_xlabel(DESIGN_VAR_LABELS[dim], fontsize=12)
    ax.set_ylabel(OBJ_LABELS[obj_idx] if obj_idx < 3 else f"Output {obj_idx}", fontsize=12)
    ax.set_title(f"GP Posterior Slice — dim {dim} ({DESIGN_VAR_LABELS[dim]})", fontsize=13)
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(fontsize=10)
    fig.tight_layout()
    save_fig(fig, output_path)
    return fig
