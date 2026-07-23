"""
Command Line Interface (CLI) for mobo_linac.

Provides console commands:
    mobo-linac run --config configs/mobo_200mev.yaml
    mobo-linac resume --run-dir results/<run_id>
    mobo-linac analyze --run-dir results/<run_id>
"""

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import sys
from typing import List, Optional
import numpy as np
import torch

from mobo_linac import __version__
from mobo_linac.acquisition.mobo import (
    build_acquisition_function,
    generate_next_candidates,
)
from mobo_linac.config import load_config
from mobo_linac.evaluation import create_evaluation_result
from mobo_linac.execution.parallel import BatchEvaluator
from mobo_linac.io.results import (
    get_train_tensors,
    load_run_checkpoint,
    save_evaluation_results,
    save_run_checkpoint,
)
from mobo_linac.metrics.hypervolume import (
    HypervolumeTracker,
    compute_reference_point,
)
from mobo_linac.models.gp import build_gp_models, fit_gp_models
from mobo_linac.plotting.visualizations import (
    plot_constraint_diagnostics,
    plot_hypervolume_progress,
    plot_objective_evolution,
    plot_pareto_front,
)


def run_optimization(args: argparse.Namespace) -> None:
    """Executes a MOBO optimization campaign from configuration."""
    config = load_config(args.config)
    seed = args.seed
    torch.manual_seed(seed)
    np.random.seed(seed)
    torch.set_default_dtype(torch.double)

    if args.output_dir:
        run_dir = Path(args.output_dir)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = Path("results") / timestamp

    run_dir.mkdir(parents=True, exist_ok=True)
    run_id = run_dir.name

    config.save_json(run_dir / "config.json")
    config.save_yaml(run_dir / "config.yaml")

    bounds = config.get_parameter_bounds_tensor()
    num_workers = args.num_workers or config.execution.max_workers

    evaluator = BatchEvaluator(
        base_results_dir=run_dir.parent,
        template_dir=".",
        max_workers=num_workers,
        timeout=config.execution.timeout_sec,
        retries=config.execution.retries,
        clean_on_success=config.execution.clean_on_success,
    )

    # Generate initial Sobol samples
    print(f"Generating {args.num_initial_samples} initial Sobol samples...")
    sobol_engine = torch.quasirandom.SobolEngine(dimension=bounds.shape[1], scramble=True, seed=seed)
    sobol_samples = sobol_engine.draw(args.num_initial_samples).to(dtype=torch.double)
    lower_b, upper_b = bounds[0], bounds[1]
    initial_candidates = (lower_b + (upper_b - lower_b) * sobol_samples).tolist()

    print(f"Evaluating {args.num_initial_samples} initial samples across {num_workers} processes...")
    raw_results = evaluator.evaluate_batch(initial_candidates, run_id=run_id)

    results = [create_evaluation_result(res, config) for res in raw_results]

    train_X, train_Y, train_feas_mask = get_train_tensors(results, exclude_invalid=True)
    feasible_count = int(train_feas_mask.sum().item())
    print(f"Initial sampling complete. Valid: {train_X.shape[0]}, Feasible: {feasible_count} / {len(results)}")

    # Compute fixed reporting reference point
    reporting_ref_point = compute_reference_point(train_Y, offset_ratio=0.10)
    tracker = HypervolumeTracker(reporting_ref_point=reporting_ref_point, config=config)

    tracker.track_iteration(0, train_Y, train_feas_mask)
    save_evaluation_results(results, run_dir, tracker.to_dataframe()["feasible_hypervolume"].tolist())
    tracker.save_csv(run_dir / "hypervolume.csv")

    # Main MOBO loop
    print(f"\nStarting MOBO loop for {args.n_iterations} iterations (q={args.batch_size}, acq={args.acquisition})...")

    for iteration in range(1, args.n_iterations + 1):
        train_X, train_Y, train_feas_mask = get_train_tensors(results, exclude_invalid=True)
        if train_X.shape[0] < 2:
            print("Not enough valid training samples to fit GP. Continuing sampling...")
            new_sobol = sobol_engine.draw(args.batch_size).to(dtype=torch.double)
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
                acq_type=args.acquisition,
            )

            next_candidates_tensor, _ = generate_next_candidates(
                acq_func=acq_func,
                bounds=bounds,
                batch_size=args.batch_size,
            )
            next_cand_list = next_candidates_tensor.tolist()

        start_eval_id = len(results) + 1
        eval_ids = [start_eval_id + i for i in range(len(next_cand_list))]

        raw_batch_res = evaluator.evaluate_batch(next_cand_list, run_id=run_id, eval_ids=eval_ids)
        batch_results = [create_evaluation_result(res, config) for res in raw_batch_res]
        results.extend(batch_results)

        train_X, train_Y, train_feas_mask = get_train_tensors(results, exclude_invalid=True)
        hv_record = tracker.track_iteration(iteration, train_Y, train_feas_mask)

        print(
            f"Iter {iteration:03d}/{args.n_iterations:03d} | "
            f"Valid: {train_X.shape[0]} | Feasible: {hv_record['num_feasible_points']} | "
            f"HV: {hv_record['feasible_hypervolume']:.6e}"
        )

        save_evaluation_results(results, run_dir, tracker.to_dataframe()["feasible_hypervolume"].tolist())
        tracker.save_csv(run_dir / "hypervolume.csv")

        # Save checkpoint
        ckpt_path = run_dir / "gp_checkpoint" / "checkpoint.pt"
        save_run_checkpoint(
            iteration=iteration,
            results=results,
            hypervolumes=tracker.to_dataframe()["feasible_hypervolume"].tolist(),
            checkpoint_path=ckpt_path,
            acquisition_mode=args.acquisition,
        )

    # Generate final plots
    figures_dir = run_dir / "figures"
    plot_hypervolume_progress(tracker.to_dataframe(), figures_dir / "hypervolume_progress.png")
    plot_pareto_front(results, figures_dir / "pareto_front.png")
    plot_objective_evolution(results, figures_dir / "objective_evolution.png")
    plot_constraint_diagnostics(results, figures_dir / "constraint_diagnostics.png")

    print(f"\nMOBO Campaign finished successfully! All artifacts saved to: {run_dir.resolve()}")


def resume_optimization(args: argparse.Namespace) -> None:
    """Resumes an existing optimization run from checkpoint."""
    run_dir = Path(args.run_dir)
    ckpt_path = run_dir / "gp_checkpoint" / "checkpoint.pt"

    ckpt_data = load_run_checkpoint(ckpt_path)
    if not ckpt_data:
        raise FileNotFoundError(f"Checkpoint not found at: {ckpt_path}")

    start_iteration = ckpt_data["iteration"]
    results = ckpt_data["results"]
    print(f"Resuming run '{run_dir.name}' from iteration {start_iteration} with {len(results)} total samples...")

    # Forward to run_optimization with updated iteration count
    config_path = run_dir / "config.yaml"
    if not config_path.exists():
        config_path = run_dir / "config.json"

    args.config = str(config_path)
    args.output_dir = str(run_dir)
    args.seed = 42
    args.num_initial_samples = len(results)
    args.batch_size = 8
    args.acquisition = ckpt_data.get("acquisition_mode", "qLogNEHVI")
    run_optimization(args)


def analyze_run(args: argparse.Namespace) -> None:
    """Analyzes results from a completed optimization run."""
    run_dir = Path(args.run_dir)
    history_csv = run_dir / "candidate_history.csv"
    if not history_csv.exists():
        raise FileNotFoundError(f"Candidate history CSV not found at: {history_csv}")

    df = pd.read_csv(history_csv)
    print(f"\n--- Analysis Summary for {run_dir.name} ---")
    print(f"Total Evaluations: {len(df)}")
    print(f"Valid Simulations: {df['simulation_valid'].sum()} / {len(df)}")
    print(f"Feasible Beams: {df['physically_feasible'].sum()} / {len(df)}")

    output_dir = Path(args.output_dir) if args.output_dir else run_dir / "figures"
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Figures exported to: {output_dir.resolve()}")


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="mobo-linac",
        description="Multi-Objective Bayesian Optimization framework for 200 MeV Electron Injector Linac",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: run
    run_parser = subparsers.add_parser("run", help="Start a new MOBO optimization campaign")
    run_parser.add_argument("--config", type=str, default="configs/mobo_200mev.yaml", help="Path to config file")
    run_parser.add_argument("--n-iterations", type=int, default=300, help="Total BO iterations")
    run_parser.add_argument("-q", "--batch-size", type=int, default=8, help="Batch size for q-MOBO")
    run_parser.add_argument("--num-initial-samples", type=int, default=16, help="Initial random Sobol samples")
    run_parser.add_argument("--num-workers", type=int, default=4, help="Number of parallel worker processes")
    run_parser.add_argument("--acquisition", type=str, choices=["qLogNEHVI", "qEHVI"], default="qLogNEHVI", help="Acquisition function")
    run_parser.add_argument("--seed", type=int, default=42, help="Random seed")
    run_parser.add_argument("--output-dir", type=str, default=None, help="Custom output directory")

    # Subcommand: resume
    resume_parser = subparsers.add_parser("resume", help="Resume an existing optimization campaign")
    resume_parser.add_argument("--run-dir", type=str, required=True, help="Path to run directory")
    resume_parser.add_argument("--n-iterations", type=int, default=300, help="Total BO iterations")
    resume_parser.add_argument("--num-workers", type=int, default=4, help="Number of parallel worker processes")

    # Subcommand: analyze
    analyze_parser = subparsers.add_parser("analyze", help="Analyze results and generate plots for a run")
    analyze_parser.add_argument("--run-dir", type=str, required=True, help="Path to run directory")
    analyze_parser.add_argument("--output-dir", type=str, default=None, help="Custom output directory for figures")

    args = parser.parse_args()

    if args.command == "run":
        run_optimization(args)
    elif args.command == "resume":
        resume_optimization(args)
    elif args.command == "analyze":
        analyze_run(args)


if __name__ == "__main__":
    main()
