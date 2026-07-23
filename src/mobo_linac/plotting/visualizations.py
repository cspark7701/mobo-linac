"""
Plotting and Visualization Routines for mobo_linac.

Reads physical objective values and diagnostic metrics to produce publication-ready figures.
"""

from pathlib import Path
from typing import List, Optional, Union
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from mobo_linac.evaluation import EvaluationResult
from mobo_linac.io.results import results_to_dataframe


def plot_hypervolume_progress(
    history: Union[pd.DataFrame, List[dict]],
    output_path: Optional[Union[str, Path]] = None,
) -> plt.Figure:
    """
    Plots hypervolume progress over iterations.

    Args:
        history: DataFrame or list of dicts containing hypervolume tracking history.
        output_path: Optional output file path to save plot.

    Returns:
        Matplotlib Figure object.
    """
    if isinstance(history, list):
        df = pd.DataFrame(history)
    else:
        df = history

    fig, ax = plt.subplots(figsize=(8, 5))
    if "iteration" in df.columns:
        x = df["iteration"]
    else:
        x = range(1, len(df) + 1)

    if "feasible_hypervolume" in df.columns:
        ax.plot(x, df["feasible_hypervolume"], marker="o", linestyle="-", color="blue", label="Feasible Hypervolume")
    if "all_point_hypervolume" in df.columns:
        ax.plot(x, df["all_point_hypervolume"], marker="s", linestyle="--", color="gray", alpha=0.7, label="All-Point Hypervolume")

    ax.set_xlabel("Iteration", fontsize=14)
    ax.set_ylabel("Hypervolume", fontsize=14)
    ax.set_title("Hypervolume Progress", fontsize=16)
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(fontsize=12)
    fig.tight_layout()

    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=300)

    return fig


def plot_pareto_front(
    results: List[EvaluationResult],
    output_path: Optional[Union[str, Path]] = None,
) -> plt.Figure:
    """
    Plots 2D projections of physical objective space highlighting feasible Pareto front.
    """
    df = results_to_dataframe(results)
    valid_df = df[df["simulation_valid"] == True]
    feasible_df = valid_df[valid_df["physically_feasible"] == True]

    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    # Convert physical objectives for convenient plot units: mm-mrad and MeV
    all_emit_x = valid_df["norm_emit_x_m_rad"] * 1e6
    all_emit_y = valid_df["norm_emit_y_m_rad"] * 1e6
    all_sigma_e = valid_df["sigma_energy_eV"] * 1e-6

    feas_emit_x = feasible_df["norm_emit_x_m_rad"] * 1e6
    feas_emit_y = feasible_df["norm_emit_y_m_rad"] * 1e6
    feas_sigma_e = feasible_df["sigma_energy_eV"] * 1e-6

    # 1. Emit X vs Emit Y
    axes[0].scatter(all_emit_x, all_emit_y, color="lightgray", label="Infeasible / All", alpha=0.6)
    axes[0].scatter(feas_emit_x, feas_emit_y, color="tab:blue", label="Feasible", alpha=0.8)
    axes[0].set_xlabel(r"$\varepsilon_{n,x}$ [mm-mrad]", fontsize=12)
    axes[0].set_ylabel(r"$\varepsilon_{n,y}$ [mm-mrad]", fontsize=12)
    axes[0].set_title(r"$\varepsilon_{n,x}$ vs $\varepsilon_{n,y}$", fontsize=14)
    axes[0].grid(True, linestyle=":", alpha=0.6)
    axes[0].legend()

    # 2. Sigma E vs Emit X
    axes[1].scatter(all_sigma_e, all_emit_x, color="lightgray", label="Infeasible / All", alpha=0.6)
    axes[1].scatter(feas_sigma_e, feas_emit_x, color="tab:blue", label="Feasible", alpha=0.8)
    axes[1].set_xlabel(r"$\sigma_E$ [MeV]", fontsize=12)
    axes[1].set_ylabel(r"$\varepsilon_{n,x}$ [mm-mrad]", fontsize=12)
    axes[1].set_title(r"$\sigma_E$ vs $\varepsilon_{n,x}$", fontsize=14)
    axes[1].grid(True, linestyle=":", alpha=0.6)
    axes[1].legend()

    # 3. Sigma E vs Emit Y
    axes[2].scatter(all_sigma_e, all_emit_y, color="lightgray", label="Infeasible / All", alpha=0.6)
    axes[2].scatter(feas_sigma_e, feas_emit_y, color="tab:blue", label="Feasible", alpha=0.8)
    axes[2].set_xlabel(r"$\sigma_E$ [MeV]", fontsize=12)
    axes[2].set_ylabel(r"$\varepsilon_{n,y}$ [mm-mrad]", fontsize=12)
    axes[2].set_title(r"$\sigma_E$ vs $\varepsilon_{n,y}$", fontsize=14)
    axes[2].grid(True, linestyle=":", alpha=0.6)
    axes[2].legend()

    fig.tight_layout()
    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=300)

    return fig


def plot_objective_evolution(
    results: List[EvaluationResult],
    output_path: Optional[Union[str, Path]] = None,
) -> plt.Figure:
    """
    Plots evolution of physical objectives across candidate evaluations.
    """
    df = results_to_dataframe(results)
    valid_df = df[df["simulation_valid"] == True]

    fig, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
    indices = range(1, len(valid_df) + 1)

    axes[0].plot(indices, valid_df["norm_emit_x_m_rad"] * 1e6, color="tab:blue", label=r"$\varepsilon_{n,x}$")
    axes[0].set_ylabel(r"$\varepsilon_{n,x}$ [mm-mrad]", fontsize=12)
    axes[0].grid(True, linestyle=":", alpha=0.6)

    axes[1].plot(indices, valid_df["norm_emit_y_m_rad"] * 1e6, color="tab:orange", label=r"$\varepsilon_{n,y}$")
    axes[1].set_ylabel(r"$\varepsilon_{n,y}$ [mm-mrad]", fontsize=12)
    axes[1].grid(True, linestyle=":", alpha=0.6)

    axes[2].plot(indices, valid_df["sigma_energy_eV"] * 1e-6, color="tab:green", label=r"$\sigma_E$")
    axes[2].set_ylabel(r"$\sigma_E$ [MeV]", fontsize=12)
    axes[2].set_xlabel("Evaluation Index", fontsize=12)
    axes[2].grid(True, linestyle=":", alpha=0.6)

    fig.suptitle("Physical Objectives Evolution", fontsize=16)
    fig.tight_layout()

    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=300)

    return fig


def plot_constraint_diagnostics(
    results: List[EvaluationResult],
    output_path: Optional[Union[str, Path]] = None,
) -> plt.Figure:
    """
    Plots diagnostic beam sizes and kinetic energy w.r.t constraint limits.
    """
    df = results_to_dataframe(results)
    valid_df = df[df["simulation_valid"] == True]

    fig, axes = plt.subplots(2, 2, figsize=(12, 8))

    indices = range(1, len(valid_df) + 1)

    # 1. Beam sizes (sigma_x, sigma_y)
    axes[0, 0].plot(indices, valid_df["sigma_x_m"] * 1e3, label=r"$\sigma_x$", color="tab:blue")
    axes[0, 0].plot(indices, valid_df["sigma_y_m"] * 1e3, label=r"$\sigma_y$", color="tab:orange")
    axes[0, 0].axhline(1.0, color="red", linestyle="--", label="Max 1.0 mm")
    axes[0, 0].set_ylabel(r"$\sigma_{x,y}$ [mm]", fontsize=12)
    axes[0, 0].set_title("Transverse Beam Size", fontsize=14)
    axes[0, 0].grid(True, linestyle=":", alpha=0.6)
    axes[0, 0].legend()

    # 2. Transverse divergence (sigma_xp, sigma_yp)
    axes[0, 1].plot(indices, valid_df["sigma_xp_rad"] * 1e3, label=r"$\sigma_{xp}$", color="tab:green")
    axes[0, 1].plot(indices, valid_df["sigma_yp_rad"] * 1e3, label=r"$\sigma_{yp}$", color="tab:purple")
    axes[0, 1].axhline(1.0, color="red", linestyle="--", label="Max 1.0 mrad")
    axes[0, 1].set_ylabel(r"$\sigma_{xp,yp}$ [mrad]", fontsize=12)
    axes[0, 1].set_title("Transverse Divergence", fontsize=14)
    axes[0, 1].grid(True, linestyle=":", alpha=0.6)
    axes[0, 1].legend()

    # 3. Bunch length (sigma_z)
    axes[1, 0].plot(indices, valid_df["sigma_z_m"] * 1e3, label=r"$\sigma_z$", color="tab:red")
    axes[1, 0].axhline(1.0, color="red", linestyle="--", label="Max 1.0 mm")
    axes[1, 0].set_ylabel(r"$\sigma_z$ [mm]", fontsize=12)
    axes[1, 0].set_xlabel("Evaluation Index", fontsize=12)
    axes[1, 0].set_title("Bunch Length", fontsize=14)
    axes[1, 0].grid(True, linestyle=":", alpha=0.6)
    axes[1, 0].legend()

    # 4. Kinetic energy
    axes[1, 1].plot(indices, valid_df["mean_kinetic_energy_eV"] * 1e-6, label=r"$E_{kin}$", color="tab:brown")
    axes[1, 1].axhline(195.0, color="red", linestyle="--", label="Min 195 MeV")
    axes[1, 1].axhline(205.0, color="red", linestyle="--", label="Max 205 MeV")
    axes[1, 1].set_ylabel("Kinetic Energy [MeV]", fontsize=12)
    axes[1, 1].set_xlabel("Evaluation Index", fontsize=12)
    axes[1, 1].set_title("Mean Kinetic Energy", fontsize=14)
    axes[1, 1].grid(True, linestyle=":", alpha=0.6)
    axes[1, 1].legend()

    fig.tight_layout()
    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=300)

    return fig
