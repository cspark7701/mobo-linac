"""
Validation Campaign Script for mobo_linac (Task 09).

Executes a reproducible Multi-Objective Bayesian Optimization campaign for the
200 MeV linac injector, exporting all required scientific artifacts, CSVs,
checkpoints, plots, and failure diagnostics.
"""

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys
import os
import platform
import time

import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import numpy as np
import pandas as pd
import torch
from botorch.utils.multi_objective.pareto import is_non_dominated

import botorch
import gpytorch
from mobo_linac import __version__
from mobo_linac.acquisition.mobo import (
    build_acquisition_function,
    generate_next_candidates,
)
from mobo_linac.config import load_config
from mobo_linac.evaluation import create_evaluation_result
from mobo_linac.execution.parallel import BatchEvaluator
from mobo_linac.io.results import (
    DESIGN_VAR_COLUMNS,
    MODEL_OBJ_COLUMNS,
    PHYSICAL_OBJ_COLUMNS,
    get_train_tensors,
    load_run_checkpoint,
    results_to_dataframe,
    save_evaluation_results,
    save_run_checkpoint,
)
from mobo_linac.metrics.hypervolume import (
    HypervolumeTracker,
    compute_reference_point,
)
from mobo_linac.models.gp import build_gp_models, fit_gp_models


def export_environment_info(target_path: Path) -> None:
    """Exports system and dependency version metadata to environment.txt."""
    lines = [
        f"mobo_linac version: {__version__}",
        f"Python version: {platform.python_version()}",
        f"PyTorch version: {torch.__version__}",
        f"BoTorch version: {botorch.__version__}",
        f"GPyTorch version: {gpytorch.__version__}",
        f"NumPy version: {np.__version__}",
        f"Pandas version: {pd.__version__}",
        f"ASTRA_BIN: {os.environ.get('ASTRA_BIN', 'Not set')}",
        f"GENERATOR_BIN: {os.environ.get('GENERATOR_BIN', 'Not set')}",
        f"Platform: {platform.platform()}",
        f"Timestamp: {datetime.now().isoformat()}",
    ]
    target_path.write_text("\n".join(lines) + "\n")


def generate_validation_plots(results, tracker, figures_dir: Path) -> None:
    """Generates all required validation campaign plots."""
    figures_dir.mkdir(parents=True, exist_ok=True)
    df = results_to_dataframe(results)
    history_df = tracker.to_dataframe()

    # 1. Hypervolume progress (all-point vs feasible)
    fig1, ax1 = plt.subplots(figsize=(8, 5))
    x_iter = history_df["iteration"]
    ax1.plot(x_iter, history_df["feasible_hypervolume"], marker="o", color="blue", label="Feasible Hypervolume")
    ax1.plot(x_iter, history_df["all_point_hypervolume"], marker="s", linestyle="--", color="gray", alpha=0.7, label="All-Point Hypervolume")
    ax1.set_xlabel("Iteration", fontsize=14)
    ax1.set_ylabel("Hypervolume", fontsize=14)
    ax1.set_title("Hypervolume Progress (Fixed Reference Point)", fontsize=14)
    ax1.grid(True, linestyle=":", alpha=0.6)
    ax1.legend()
    fig1.tight_layout()
    fig1.savefig(figures_dir / "hypervolume_progress.png", dpi=300)
    plt.close(fig1)

    # 2. Feasible fraction per iteration
    fig2, ax2 = plt.subplots(figsize=(8, 5))
    feas_ratio = history_df["num_feasible_points"] / np.maximum(1, history_df["num_valid_points"])
    ax2.plot(x_iter, feas_ratio, marker="^", color="green", linestyle="-")
    ax2.set_xlabel("Iteration", fontsize=14)
    ax2.set_ylabel("Feasible Fraction", fontsize=14)
    ax2.set_title("Feasible Sample Fraction by Iteration", fontsize=14)
    ax2.set_ylim(-0.05, 1.05)
    ax2.grid(True, linestyle=":", alpha=0.6)
    fig2.tight_layout()
    fig2.savefig(figures_dir / "feasible_fraction.png", dpi=300)
    plt.close(fig2)

    # 3. 2D Pareto Projections
    valid_df = df[df["simulation_valid"] == True]
    feasible_df = valid_df[valid_df["physically_feasible"] == True]

    fig3, axes = plt.subplots(1, 3, figsize=(18, 5))
    ex_all = valid_df["norm_emit_x_m_rad"] * 1e6
    ey_all = valid_df["norm_emit_y_m_rad"] * 1e6
    se_all = valid_df["sigma_energy_eV"] * 1e-6

    ex_feas = feasible_df["norm_emit_x_m_rad"] * 1e6
    ey_feas = feasible_df["norm_emit_y_m_rad"] * 1e6
    se_feas = feasible_df["sigma_energy_eV"] * 1e-6

    axes[0].scatter(ex_all, ey_all, color="lightgray", label="All valid", alpha=0.6)
    axes[0].scatter(ex_feas, ey_feas, color="tab:blue", label="Feasible", alpha=0.9)
    axes[0].set_xlabel(r"$\varepsilon_{n,x}$ [mm-mrad]", fontsize=12)
    axes[0].set_ylabel(r"$\varepsilon_{n,y}$ [mm-mrad]", fontsize=12)
    axes[0].set_title(r"$\varepsilon_{n,x}$ vs $\varepsilon_{n,y}$", fontsize=14)
    axes[0].grid(True, linestyle=":", alpha=0.6)
    axes[0].legend()

    axes[1].scatter(se_all, ex_all, color="lightgray", label="All valid", alpha=0.6)
    axes[1].scatter(se_feas, ex_feas, color="tab:blue", label="Feasible", alpha=0.9)
    axes[1].set_xlabel(r"$\sigma_E$ [MeV]", fontsize=12)
    axes[1].set_ylabel(r"$\varepsilon_{n,x}$ [mm-mrad]", fontsize=12)
    axes[1].set_title(r"$\sigma_E$ vs $\varepsilon_{n,x}$", fontsize=14)
    axes[1].grid(True, linestyle=":", alpha=0.6)
    axes[1].legend()

    axes[2].scatter(se_all, ey_all, color="lightgray", label="All valid", alpha=0.6)
    axes[2].scatter(se_feas, ey_feas, color="tab:blue", label="Feasible", alpha=0.9)
    axes[2].set_xlabel(r"$\sigma_E$ [MeV]", fontsize=12)
    axes[2].set_ylabel(r"$\varepsilon_{n,y}$ [mm-mrad]", fontsize=12)
    axes[2].set_title(r"$\sigma_E$ vs $\varepsilon_{n,y}$", fontsize=14)
    axes[2].grid(True, linestyle=":", alpha=0.6)
    axes[2].legend()

    fig3.tight_layout()
    fig3.savefig(figures_dir / "pareto_projections.png", dpi=300)
    plt.close(fig3)

    # 4. 3D Pareto Plot
    fig4 = plt.figure(figsize=(9, 7))
    ax4 = fig4.add_subplot(111, projection="3d")
    ax4.scatter(ex_all, ey_all, se_all, color="lightgray", label="All valid", alpha=0.5, s=30)
    ax4.scatter(ex_feas, ey_feas, se_feas, color="red", label="Feasible", alpha=0.9, s=60, edgecolors="k")
    ax4.set_xlabel(r"$\varepsilon_{n,x}$ [mm-mrad]", fontsize=11)
    ax4.set_ylabel(r"$\varepsilon_{n,y}$ [mm-mrad]", fontsize=11)
    ax4.set_zlabel(r"$\sigma_E$ [MeV]", fontsize=11)
    ax4.set_title("3D Objective Space (Physical Values)", fontsize=14)
    ax4.legend()
    fig4.tight_layout()
    fig4.savefig(figures_dir / "pareto_3d.png", dpi=300)
    plt.close(fig4)

    # 5. Runtime per candidate
    fig5, ax5 = plt.subplots(figsize=(8, 4))
    ax5.bar(range(1, len(df) + 1), df["runtime_s"], color="tab:purple", alpha=0.7)
    ax5.set_xlabel("Candidate Index", fontsize=12)
    ax5.set_ylabel("Runtime [s]", fontsize=12)
    ax5.set_title("Candidate Evaluation Runtime", fontsize=14)
    ax5.grid(True, linestyle=":", alpha=0.6)
    fig5.tight_layout()
    fig5.savefig(figures_dir / "candidate_runtimes.png", dpi=300)
    plt.close(fig5)


def run_campaign(
    config_path: str = "configs/mobo_200MeV.yaml",
    num_initial_samples: int = 16,
    num_batches: int = 6,
    batch_size: int = 4,
    num_workers: int = 4,
    seed: int = 42,
    base_results_dir: str = "results",
    device: str = "auto",
) -> Path:
    """Executes the validation campaign using MoboCampaignRunner."""
    from mobo_linac.campaigns.runner import MoboCampaignRunner

    runner = MoboCampaignRunner(
        config=config_path,
        run_name="validation",
        output_dir=base_results_dir,
        num_initial_samples=num_initial_samples,
        num_batches=num_batches,
        batch_size=batch_size,
        num_workers=num_workers,
        seed=seed,
        acq_type="qLogNEHVI",
        export_plots=False,
        device=device,
    )

    results, tracker, run_dir = runner.run()

    # Generate custom validation plots for campaign report
    generate_validation_plots(results, tracker, run_dir / "figures")

    return run_dir



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run linac MOBO validation campaign.")
    parser.add_argument("--num-initial-samples", type=int, default=16, help="Initial Sobol sample count")
    parser.add_argument("--num-batches", "--n-iterations", type=int, default=20, help="Number of BO iterations/batches")
    parser.add_argument("-b", "-q", "--batch-size", type=int, default=8, help="Batch size q")
    parser.add_argument("--num-workers", type=int, default=4, help="Parallel worker count")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--output-dir", "--base-results-dir", type=str, default="results", help="Base output directory")
    parser.add_argument("--device", type=str, default="auto", help="Target PyTorch compute device ('auto', 'cuda', 'cpu')")

    args = parser.parse_args()

    run_campaign(
        num_initial_samples=args.num_initial_samples,
        num_batches=args.num_batches,
        batch_size=args.batch_size,
        num_workers=args.num_workers,
        seed=args.seed,
        base_results_dir=args.output_dir,
        device=args.device,
    )
