"""
Pareto frontier and multi-objective trade-off plotting routines.
"""

from pathlib import Path
from typing import Dict, List, Optional, Union

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


def plot_pareto_front(
    results: List[EvaluationResult],
    output_path: Optional[Union[str, Path]] = None,
) -> plt.Figure:
    """2D projections of objective space highlighting feasible Pareto front."""
    df = results_to_dataframe(results)
    valid = df[df["simulation_valid"]]
    feas = valid[valid["physically_feasible"]]

    ex_a = valid["norm_emit_x_m_rad"] * EMIT_SCALE
    ey_a = valid["norm_emit_y_m_rad"] * EMIT_SCALE
    se_a = valid["sigma_energy_eV"] * ENERGY_SCALE
    ex_f = feas["norm_emit_x_m_rad"] * EMIT_SCALE
    ey_f = feas["norm_emit_y_m_rad"] * EMIT_SCALE
    se_f = feas["sigma_energy_eV"] * ENERGY_SCALE

    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    pairs = [
        (ex_a, ey_a, ex_f, ey_f, OBJ_LABELS[0], OBJ_LABELS[1],
         r"$\varepsilon_{n,x}$ vs $\varepsilon_{n,y}$"),
        (se_a, ex_a, se_f, ex_f, OBJ_LABELS[2], OBJ_LABELS[0],
         r"$\sigma_E$ vs $\varepsilon_{n,x}$"),
        (se_a, ey_a, se_f, ey_f, OBJ_LABELS[2], OBJ_LABELS[1],
         r"$\sigma_E$ vs $\varepsilon_{n,y}$"),
    ]
    for ax, (xa, ya, xf, yf, xl, yl, title) in zip(axes, pairs):
        ax.scatter(xa, ya, c="lightgray", s=25, alpha=0.5, label="All valid")
        ax.scatter(xf, yf, c="steelblue", s=45, alpha=0.85, label="Feasible")
        ax.set_xlabel(xl, fontsize=12)
        ax.set_ylabel(yl, fontsize=12)
        ax.set_title(title, fontsize=13)
        ax.grid(True, linestyle=":", alpha=0.6)
        ax.legend(fontsize=10)

    fig.suptitle("Objective Space — 2D Projections", fontsize=15, y=1.01)
    fig.tight_layout()
    save_fig(fig, output_path)
    return fig


def plot_pareto_front_3d(
    results: List[EvaluationResult],
    output_path: Optional[Union[str, Path]] = None,
    elev: float = 25.0,
    azim: float = 45.0,
) -> plt.Figure:
    """3D scatter of the feasible Pareto front across all three objectives."""
    df = results_to_dataframe(results)
    valid = df[df["simulation_valid"]]
    feas = valid[valid["physically_feasible"]]
    infeas = valid[~valid["physically_feasible"]]

    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection="3d")

    if len(infeas):
        ax.scatter(
            infeas["norm_emit_x_m_rad"] * EMIT_SCALE,
            infeas["norm_emit_y_m_rad"] * EMIT_SCALE,
            infeas["sigma_energy_eV"] * ENERGY_SCALE,
            c="lightgray", s=15, alpha=0.3, label="Infeasible",
        )
    if len(feas):
        sc = ax.scatter(
            feas["norm_emit_x_m_rad"] * EMIT_SCALE,
            feas["norm_emit_y_m_rad"] * EMIT_SCALE,
            feas["sigma_energy_eV"] * ENERGY_SCALE,
            c=feas["sigma_energy_eV"] * ENERGY_SCALE,
            cmap="plasma", s=55, alpha=0.9, label="Feasible Pareto",
        )
        fig.colorbar(sc, ax=ax, pad=0.1, shrink=0.6, label=r"$\sigma_E$ [MeV]")

    ax.set_xlabel(OBJ_LABELS[0], fontsize=11, labelpad=8)
    ax.set_ylabel(OBJ_LABELS[1], fontsize=11, labelpad=8)
    ax.set_zlabel(OBJ_LABELS[2], fontsize=11, labelpad=8)
    ax.set_title("3D Pareto Front — Objective Space", fontsize=14)
    ax.view_init(elev=elev, azim=azim)
    ax.legend(fontsize=10)
    fig.tight_layout()
    save_fig(fig, output_path)
    return fig


def plot_pareto_front_comparison(
    results_dict: Optional[Dict[str, List[EvaluationResult]]] = None,
    results_p2: Optional[List[EvaluationResult]] = None,
    results_p3: Optional[List[EvaluationResult]] = None,
    output_path: Optional[Union[str, Path]] = None,
) -> plt.Figure:
    """Overlaid 2D projections comparing feasible Pareto fronts across campaign variants."""
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    pairs_info = [
        (OBJ_LABELS[0], OBJ_LABELS[1], r"$\varepsilon_{n,x}$ vs $\varepsilon_{n,y}$", "norm_emit_x_m_rad", "norm_emit_y_m_rad"),
        (OBJ_LABELS[2], OBJ_LABELS[0], r"$\sigma_E$ vs $\varepsilon_{n,x}$", "sigma_energy_eV", "norm_emit_x_m_rad"),
        (OBJ_LABELS[2], OBJ_LABELS[1], r"$\sigma_E$ vs $\varepsilon_{n,y}$", "sigma_energy_eV", "norm_emit_y_m_rad"),
    ]

    # Support dictionary of arbitrary phases or legacy (p2, p3) arguments
    if results_dict is None:
        results_dict = {}
        if results_p2 is not None:
            results_dict["Phase 2 (Unconstrained)"] = results_p2
        if results_p3 is not None:
            results_dict["Phase 3 (Constrained)"] = results_p3

    colors = ["steelblue", "seagreen", "darkorange", "purple", "crimson"]
    markers = ["o", "^", "s", "D", "v"]

    for i, (label, res_list) in enumerate(results_dict.items()):
        df = results_to_dataframe(res_list)
        feas = df[df["simulation_valid"] & df["physically_feasible"]]
        color = colors[i % len(colors)]
        marker = markers[i % len(markers)]

        ex = feas["norm_emit_x_m_rad"] * EMIT_SCALE
        ey = feas["norm_emit_y_m_rad"] * EMIT_SCALE
        se = feas["sigma_energy_eV"] * ENERGY_SCALE

        val_map = {"norm_emit_x_m_rad": ex, "norm_emit_y_m_rad": ey, "sigma_energy_eV": se}

        for ax, (xl, yl, title, kx, ky) in zip(axes, pairs_info):
            ax.scatter(val_map[kx], val_map[ky], c=color, s=45, alpha=0.75, marker=marker, label=label)

    for ax, (xl, yl, title, _, _) in zip(axes, pairs_info):
        ax.set_xlabel(xl, fontsize=12)
        ax.set_ylabel(yl, fontsize=12)
        ax.set_title(title, fontsize=13)
        ax.grid(True, linestyle=":", alpha=0.6)
        ax.legend(fontsize=10)

    fig.suptitle("Pareto Front Multi-Phase Comparison", fontsize=15, y=1.01)
    fig.tight_layout()
    save_fig(fig, output_path)
    return fig


def plot_pareto_verification_comparison(
    verification_records: List[dict],
    output_path: Optional[Union[str, Path]] = None,
) -> plt.Figure:
    """Stored vs rerun ε_nx for each verified Pareto candidate."""
    fig, ax = plt.subplots(figsize=(10, 5))
    roles = [rec.get("role", f"Cand {i+1}") for i, rec in enumerate(verification_records)]
    stored = [rec.get("stored_emit_x_m_rad", 0.0) * EMIT_SCALE for rec in verification_records]
    rerun = [rec.get("rerun_emit_x_m_rad", 0.0) * EMIT_SCALE for rec in verification_records]

    x = np.arange(len(roles))
    w = 0.35
    ax.bar(x - w / 2, stored, w, label="Stored", color="steelblue", alpha=0.85)
    ax.bar(x + w / 2, rerun, w, label="Rerun", color="seagreen", alpha=0.85)

    ax.set_ylabel(OBJ_LABELS[0], fontsize=12)
    ax.set_title("Pareto Candidate Verification (Stored vs Independent Rerun)", fontsize=14)
    ax.set_xticks(x)
    ax.set_xticklabels(roles, rotation=15, ha="right", fontsize=10)
    ax.legend(fontsize=11)
    ax.grid(True, linestyle=":", alpha=0.6, axis="y")
    fig.tight_layout()
    save_fig(fig, output_path)
    return fig
