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
    config_path: str = "configs/mobo_200mev.yaml",
    num_initial_samples: int = 16,
    num_batches: int = 6,
    batch_size: int = 4,
    num_workers: int = 4,
    seed: int = 42,
    base_results_dir: str = "results",
) -> Path:
    """Executes the validation campaign."""
    config = load_config(config_path)

    torch.manual_seed(seed)
    np.random.seed(seed)
    torch.set_default_dtype(torch.double)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_id = f"validation_{timestamp}"
    run_dir = Path(base_results_dir) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== Starting Validation Campaign: {run_id} ===")
    print(f"Initial samples: {num_initial_samples}, Batches: {num_batches}, Batch size: {batch_size}, Workers: {num_workers}")

    # Export environment.txt and configs
    export_environment_info(run_dir / "environment.txt")
    config.save_yaml(run_dir / "config.yaml")
    config.save_json(run_dir / "config.json")

    bounds = config.get_parameter_bounds_tensor()

    evaluator = BatchEvaluator(
        base_results_dir=run_dir.parent,
        template_dir=".",
        max_workers=num_workers,
        timeout=config.execution.timeout_sec,
        retries=config.execution.retries,
    )

    # Sobol initial sampling
    sobol_engine = torch.quasirandom.SobolEngine(dimension=bounds.shape[1], scramble=True, seed=seed)
    sobol_samples = sobol_engine.draw(num_initial_samples).to(dtype=torch.double)
    lower_b, upper_b = bounds[0], bounds[1]
    initial_candidates = (lower_b + (upper_b - lower_b) * sobol_samples).tolist()

    raw_initial = evaluator.evaluate_batch(initial_candidates, run_id=run_id)
    results = [create_evaluation_result(r, config) for r in raw_initial]

    train_X, train_Y, train_feas_mask = get_train_tensors(results, exclude_invalid=True)

    # Establish fixed reporting reference point from initial set
    reporting_ref_point = compute_reference_point(train_Y, offset_ratio=0.10)
    tracker = HypervolumeTracker(reporting_ref_point=reporting_ref_point, config=config)

    tracker.track_iteration(0, train_Y, train_feas_mask)
    save_evaluation_results(results, run_dir, tracker.to_dataframe()["feasible_hypervolume"].tolist())

    # Iterative MOBO Loop with Checkpoints
    total_iterations = num_batches
    for iteration in range(1, total_iterations + 1):
        train_X, train_Y, train_feas_mask = get_train_tensors(results, exclude_invalid=True)

        if train_X.shape[0] < 2:
            new_sobol = sobol_engine.draw(batch_size).to(dtype=torch.double)
            next_cand_list = (lower_b + (upper_b - lower_b) * new_sobol).tolist()
        else:
            gp_model = build_gp_models(train_X, train_Y, bounds)
            gp_model = fit_gp_models(gp_model)

            acq_ref_point = compute_reference_point(train_Y, offset_ratio=0.05)
            acq_func = build_acquisition_function(
                model=gp_model,
                train_X=train_X,
                train_Y=train_Y,
                ref_point=acq_ref_point,
                train_feas_mask=train_feas_mask,
                acq_type="qLogNEHVI",
            )

            next_cand_tensor, _ = generate_next_candidates(
                acq_func=acq_func,
                bounds=bounds,
                batch_size=batch_size,
            )
            next_cand_list = next_cand_tensor.tolist()

        start_eval_id = len(results) + 1
        eval_ids = [start_eval_id + i for i in range(len(next_cand_list))]

        raw_batch = evaluator.evaluate_batch(next_cand_list, run_id=run_id, eval_ids=eval_ids)
        batch_results = [create_evaluation_result(r, config) for r in raw_batch]
        results.extend(batch_results)

        train_X, train_Y, train_feas_mask = get_train_tensors(results, exclude_invalid=True)
        hv_record = tracker.track_iteration(iteration, train_Y, train_feas_mask)

        print(
            f"Iter {iteration:02d}/{total_iterations:02d} | "
            f"Evaluations: {len(results):02d} | "
            f"Valid: {train_X.shape[0]:02d} | "
            f"Feasible: {hv_record['num_feasible_points']:02d} | "
            f"HV: {hv_record['feasible_hypervolume']:.6e}"
        )

        # Save checkpoint after every batch
        ckpt_dir = run_dir / "checkpoints"
        ckpt_dir.mkdir(parents=True, exist_ok=True)
        ckpt_path = ckpt_dir / f"checkpoint_iter_{iteration:02d}.pt"
        save_run_checkpoint(
            iteration=iteration,
            results=results,
            hypervolumes=tracker.to_dataframe()["feasible_hypervolume"].tolist(),
            checkpoint_path=ckpt_path,
        )

    # Save all required CSV files
    df_all = results_to_dataframe(results)
    df_all.to_csv(run_dir / "evaluations.csv", index=False)
    df_all.to_csv(run_dir / "candidate_history.csv", index=False)

    # Objectives CSVs
    valid_mask = df_all["simulation_valid"] == True
    df_valid = df_all[valid_mask]

    df_valid[PHYSICAL_OBJ_COLUMNS].to_csv(run_dir / "objectives_physical.csv", index=False)
    df_valid[MODEL_OBJ_COLUMNS].to_csv(run_dir / "objectives_model.csv", index=False)

    # Constraints CSV
    diag_cols = [c for c in df_all.columns if "sigma" in c or "energy" in c or "transmission" in c or "feasible" in c]
    df_all[diag_cols].to_csv(run_dir / "constraints.csv", index=False)

    # Hypervolume CSV
    tracker.save_csv(run_dir / "hypervolume.csv")

    # Pareto CSVs
    train_X, train_Y, train_feas_mask = get_train_tensors(results, exclude_invalid=True)
    if train_X.shape[0] > 0:
        pareto_mask_all = is_non_dominated(train_Y)
        p_X_all = train_X[pareto_mask_all]
        p_Y_all_phys = -train_Y[pareto_mask_all]
        df_p_all = pd.DataFrame(
            np.hstack([p_X_all.numpy(), p_Y_all_phys.numpy()]),
            columns=DESIGN_VAR_COLUMNS + PHYSICAL_OBJ_COLUMNS,
        )
        df_p_all.to_csv(run_dir / "pareto_all.csv", index=False)

        if train_feas_mask.sum().item() > 0:
            feas_X = train_X[train_feas_mask]
            feas_Y = train_Y[train_feas_mask]
            pareto_mask_feas = is_non_dominated(feas_Y)
            p_X_feas = feas_X[pareto_mask_feas]
            p_Y_feas_phys = -feas_Y[pareto_mask_feas]
            df_p_feas = pd.DataFrame(
                np.hstack([p_X_feas.numpy(), p_Y_feas_phys.numpy()]),
                columns=DESIGN_VAR_COLUMNS + PHYSICAL_OBJ_COLUMNS,
            )
            df_p_feas.to_csv(run_dir / "pareto_feasible.csv", index=False)

    # Failures CSV
    df_failures = df_all[(df_all["simulation_valid"] == False) | (df_all["physically_feasible"] == False)]
    df_failures.to_csv(run_dir / "failures.csv", index=False)

    # Generate required plots
    generate_validation_plots(results, tracker, run_dir / "figures")

    # Print Campaign Summary
    print(f"\n=== Validation Campaign Complete ===")
    print(f"Total Evaluations: {len(results)}")
    print(f"Valid Simulations: {train_X.shape[0]}")
    print(f"Physically Feasible: {train_feas_mask.sum().item()}")
    print(f"Infeasible / Failures: {len(df_failures)}")
    print(f"All output files written to: {run_dir.resolve()}")

    return run_dir


if __name__ == "__main__":
    run_campaign(
        num_initial_samples=16,
        num_batches=6,
        batch_size=4,
        num_workers=4,
        seed=42,
    )
