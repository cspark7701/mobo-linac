"""
Command Line Interface (CLI) for mobo_linac.

Provides console commands:
    mobo-linac run-unconstrained --config configs/publication.yaml
    mobo-linac run-constrained --config configs/publication.yaml
    mobo-linac run-scalarized --config configs/publication.yaml
    mobo-linac run-validation --config configs/publication.yaml
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
import pandas as pd
import torch

from botorch.acquisition.logei import qLogNoisyExpectedImprovement
from botorch.acquisition.multi_objective.objective import IdentityMCMultiOutputObjective
from botorch.models import SingleTaskGP, ModelListGP
from botorch.models.transforms.input import Normalize
from botorch.models.transforms.outcome import Standardize
from botorch.optim import optimize_acqf
from botorch.utils.multi_objective.pareto import is_non_dominated

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
from mobo_linac.plotting.visualizations import (
    plot_constraint_diagnostics,
    plot_hypervolume_progress,
    plot_objective_evolution,
    plot_pareto_front,
)

from mobo_linac.constraints import get_botorch_constraint_functions

# Dynamic constraint evaluators for constrained MOBO
CONSTRAINT_FUNCTIONS = get_botorch_constraint_functions()



def run_unconstrained(args: argparse.Namespace) -> None:
    """Executes Phase 2 Unconstrained MOBO campaign."""
    from mobo_linac.campaigns.runner import MoboCampaignRunner

    config_path = args.config if hasattr(args, "config") and args.config else "configs/publication.yaml"
    if not Path(config_path).exists():
        config_path = "configs/mobo_200MeV.yaml"

    runner = MoboCampaignRunner(
        config=config_path,
        run_name="unconstrained",
        output_dir=getattr(args, "output_dir", None),
        num_initial_samples=getattr(args, "num_initial_samples", 16),
        num_batches=getattr(args, "n_iterations", 6),
        batch_size=getattr(args, "batch_size", 4),
        num_workers=getattr(args, "num_workers", None),
        seed=getattr(args, "seed", 42),
        acq_type=getattr(args, "acquisition", "qLogNEHVI"),
        constrained=False,
        export_plots=True,
    )
    runner.run()


def run_constrained(args: argparse.Namespace) -> None:
    """Executes Phase 3 Constrained MOBO campaign."""
    from mobo_linac.campaigns.runner import MoboCampaignRunner

    config_path = args.config if hasattr(args, "config") and args.config else "configs/publication.yaml"
    if not Path(config_path).exists():
        config_path = "configs/mobo_200MeV.yaml"

    runner = MoboCampaignRunner(
        config=config_path,
        run_name="constrained",
        output_dir=getattr(args, "output_dir", None),
        num_initial_samples=getattr(args, "num_initial_samples", 16),
        num_batches=getattr(args, "n_iterations", 6),
        batch_size=getattr(args, "batch_size", 4),
        num_workers=getattr(args, "num_workers", None),
        seed=getattr(args, "seed", 42),
        acq_type=getattr(args, "acquisition", "qLogNEHVI"),
        constrained=True,
        export_plots=True,
    )
    runner.run()



def run_scalarized(args: argparse.Namespace) -> None:
    """Executes Scalarized BO campaign (weighted sum scalarization)."""
    config_path = args.config if args.config else "configs/publication.yaml"
    if not Path(config_path).exists():
        config_path = "configs/mobo_200MeV.yaml"
    config = load_config(config_path)

    seed = args.seed
    torch.manual_seed(seed)
    np.random.seed(seed)
    torch.set_default_dtype(torch.double)

    if args.output_dir:
        run_dir = Path(args.output_dir)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = Path("results") / f"scalarized_{timestamp}"

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
    )

    print(f"Generating {args.num_initial_samples} initial Sobol samples for Scalarized BO...")
    sobol_engine = torch.quasirandom.SobolEngine(dimension=bounds.shape[1], scramble=True, seed=seed)
    sobol_samples = sobol_engine.draw(args.num_initial_samples).to(dtype=torch.double)
    lower_b, upper_b = bounds[0], bounds[1]
    initial_candidates = (lower_b + (upper_b - lower_b) * sobol_samples).tolist()

    raw_results = evaluator.evaluate_batch(initial_candidates, run_id=run_id)
    results = [create_evaluation_result(res, config) for res in raw_results]

    train_X, train_Y, train_feas_mask = get_train_tensors(results, exclude_invalid=True)
    reporting_ref_point = compute_reference_point(train_Y, offset_ratio=0.10)
    tracker = HypervolumeTracker(reporting_ref_point=reporting_ref_point, config=config)
    tracker.track_iteration(0, train_Y, train_feas_mask)

    weights = torch.tensor(args.weights, dtype=torch.double) if hasattr(args, "weights") and args.weights else torch.tensor([1.0, 1.0, 1.0], dtype=torch.double)
    weights = weights / weights.sum()

    print(f"\nStarting Scalarized BO loop for {args.n_iterations} iterations with weights {weights.tolist()}...")

    for iteration in range(1, args.n_iterations + 1):
        train_X, train_Y, train_feas_mask = get_train_tensors(results, exclude_invalid=True)
        if train_X.shape[0] < 2:
            new_sobol = sobol_engine.draw(args.batch_size).to(dtype=torch.double)
            next_cand_list = (lower_b + (upper_b - lower_b) * new_sobol).tolist()
        else:
            # Compute scalar outcome: y_scalar = sum(w_i * Y_i)
            scalar_Y = (train_Y * weights).sum(dim=-1, keepdim=True)
            input_transform = Normalize(d=bounds.shape[1], bounds=bounds)
            gp = SingleTaskGP(train_X, scalar_Y, input_transform=input_transform, outcome_transform=Standardize(m=1))
            fit_gp_models(ModelListGP(gp))

            acq_func = qLogNoisyExpectedImprovement(model=gp, X_baseline=train_X, prune_baseline=True)
            candidates, _ = optimize_acqf(
                acq_function=acq_func,
                bounds=bounds,
                q=args.batch_size,
                num_restarts=20,
                raw_samples=128,
            )
            next_cand_list = candidates.tolist()

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

    figures_dir = run_dir / "figures"
    plot_hypervolume_progress(tracker.to_dataframe(), figures_dir / "hypervolume_progress.png")
    plot_pareto_front(results, figures_dir / "pareto_front.png")
    print(f"\nScalarized BO Campaign finished successfully! Artifacts in: {run_dir.resolve()}")


def run_validation(args: argparse.Namespace) -> None:
    """Executes full reproducible validation campaign."""
    config_path = args.config if args.config else "configs/publication.yaml"
    if not Path(config_path).exists():
        config_path = "configs/mobo_200MeV.yaml"
    
    from scripts.run_validation_campaign import run_campaign
    run_campaign(
        config_path=config_path,
        num_initial_samples=args.num_initial_samples,
        num_batches=args.n_iterations,
        batch_size=args.batch_size,
        num_workers=args.num_workers,
        seed=args.seed,
        base_results_dir=args.output_dir or "results",
    )


def resume_optimization(args: argparse.Namespace) -> None:
    """Resumes an existing optimization campaign from checkpoint."""
    from mobo_linac.campaigns.runner import MoboCampaignRunner
    from mobo_linac.io.results import load_run_checkpoint

    run_dir = Path(getattr(args, "run_dir", getattr(args, "output_dir", "results")))
    ckpt_data = load_run_checkpoint(run_dir)
    if not ckpt_data:
        raise FileNotFoundError(f"No valid checkpoint found in: {run_dir}")

    config_path = run_dir / "config.yaml"
    if not config_path.exists():
        config_path = run_dir / "config.json"
    if not config_path.exists():
        config_path = getattr(args, "config", "configs/publication.yaml")

    acq_type = ckpt_data.get("acquisition_mode", getattr(args, "acquisition", "qLogNEHVI"))
    constrained = ckpt_data.get("constrained", False)
    seed = ckpt_data.get("seed", getattr(args, "seed", 42))
    batch_size = ckpt_data.get("batch_size", getattr(args, "batch_size", 4))

    runner = MoboCampaignRunner(
        config=config_path,
        output_dir=run_dir,
        num_batches=getattr(args, "n_iterations", 6),
        batch_size=batch_size,
        num_workers=getattr(args, "num_workers", None),
        seed=seed,
        acq_type=acq_type,
        constrained=constrained,
        resume=True,
    )
    runner.run()



def analyze_run(args: argparse.Namespace) -> None:
    """Analyzes results from a completed optimization run."""
    run_dir = Path(args.run_dir)
    history_csv = run_dir / "candidate_history.csv"
    if not history_csv.exists():
        history_csv = run_dir / "evaluations.csv"
    if not history_csv.exists():
        raise FileNotFoundError(f"Candidate history / evaluations CSV not found in: {run_dir}")

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

    def add_common_run_args(subparser):
        subparser.add_argument("--config", type=str, default="configs/publication.yaml", help="Path to config file")
        subparser.add_argument("--n-iterations", type=int, default=300, help="Total BO iterations")
        subparser.add_argument("-q", "--batch-size", type=int, default=8, help="Batch size for q-MOBO")
        subparser.add_argument("--num-initial-samples", type=int, default=16, help="Initial random Sobol samples")
        subparser.add_argument("--num-workers", type=int, default=4, help="Number of parallel worker processes")
        subparser.add_argument("--acquisition", type=str, choices=["qLogNEHVI", "qEHVI"], default="qLogNEHVI", help="Acquisition function")
        subparser.add_argument("--seed", type=int, default=42, help="Random seed")
        subparser.add_argument("--output-dir", type=str, default=None, help="Custom output directory")

    # Subcommand: run (backward compatible, alias to run-unconstrained)
    run_parser = subparsers.add_parser("run", help="Start a new MOBO optimization campaign (unconstrained)")
    add_common_run_args(run_parser)

    # Subcommand: run-unconstrained
    run_un_parser = subparsers.add_parser("run-unconstrained", help="Start an unconstrained MOBO campaign")
    add_common_run_args(run_un_parser)

    # Subcommand: run-constrained
    run_co_parser = subparsers.add_parser("run-constrained", help="Start a constraint-aware MOBO campaign")
    add_common_run_args(run_co_parser)

    # Subcommand: run-scalarized
    run_sc_parser = subparsers.add_parser("run-scalarized", help="Start a scalarized BO campaign")
    add_common_run_args(run_sc_parser)
    run_sc_parser.add_argument("--weights", nargs=3, type=float, default=[1.0, 1.0, 1.0], help="Weights for 3 objectives")

    # Subcommand: run-validation
    run_val_parser = subparsers.add_parser("run-validation", help="Run a validation campaign")
    add_common_run_args(run_val_parser)

    # Subcommand: resume
    resume_parser = subparsers.add_parser("resume", help="Resume an existing optimization campaign")
    resume_parser.add_argument("--run-dir", type=str, required=True, help="Path to run directory")
    resume_parser.add_argument("--n-iterations", type=int, default=300, help="Total BO iterations")
    resume_parser.add_argument("--num-workers", type=int, default=4, help="Number of parallel worker processes")

    # Subcommand: run-benchmark
    run_bm_parser = subparsers.add_parser("run-benchmark", help="Run a paired multi-seed benchmark campaign")
    run_bm_parser.add_argument("--config", type=str, default="configs/publication_200MeV.yaml", help="Path to config file")
    run_bm_parser.add_argument("--output-dir", type=str, default="results/publication_benchmark", help="Output directory")
    run_bm_parser.add_argument("--seeds", nargs="+", type=int, default=list(range(42, 52)), help="List of random seeds")
    run_bm_parser.add_argument("--budget", type=int, default=40, help="Total evaluation budget")
    run_bm_parser.add_argument("--num-workers", type=int, default=4, help="Number of parallel worker processes")

    # Subcommand: analyze-benchmark
    analyze_bm_parser = subparsers.add_parser("analyze-benchmark", help="Aggregate and analyze completed benchmark campaign results")
    analyze_bm_parser.add_argument("--output-dir", type=str, default="results/publication_benchmark", help="Benchmark campaign directory")

    # Subcommand: run-robustness
    run_rob_parser = subparsers.add_parser("run-robustness", help="Perform robustness and sensitivity analysis over Pareto candidates")
    run_rob_parser.add_argument("--config", type=str, default="configs/publication_200MeV.yaml", help="Path to config file")
    run_rob_parser.add_argument("--perturb-config", type=str, default="configs/perturbation_config.yaml", help="Path to perturbation config")
    run_rob_parser.add_argument("--history-path", type=str, default="results/pareto/pareto_candidates.csv", help="Path to Pareto candidates CSV/JSON")
    run_rob_parser.add_argument("--output-dir", type=str, default="results/robustness", help="Output directory")
    run_rob_parser.add_argument("--num-perturbations", type=int, default=50, help="Number of perturbations per candidate")
    run_rob_parser.add_argument("--seed", type=int, default=42, help="Random seed")

    # Subcommand: run-verification
    run_ver_parser = subparsers.add_parser("run-verification", help="Rerun Pareto candidates independently for verification")
    run_ver_parser.add_argument("--config", type=str, default="configs/publication_200MeV.yaml", help="Path to config file")
    run_ver_parser.add_argument("--history-path", type=str, default="results/pareto/pareto_candidates.csv", help="Path to Pareto candidates CSV/JSON")
    run_ver_parser.add_argument("--output-dir", type=str, default="results/verification", help="Output directory")

    args = parser.parse_args()

    if args.command in ("run", "run-unconstrained"):
        run_unconstrained(args)
    elif args.command == "run-constrained":
        run_constrained(args)
    elif args.command == "run-scalarized":
        run_scalarized(args)
    elif args.command == "run-validation":
        run_validation(args)
    elif args.command == "resume":
        resume_optimization(args)
    elif args.command == "analyze":
        analyze_run(args)
    elif args.command == "run-benchmark":
        from mobo_linac.campaigns.benchmark import BenchmarkCampaignRunner
        config = load_config(args.config)
        runner = BenchmarkCampaignRunner(
            config=config,
            output_dir=args.output_dir,
            seeds=args.seeds,
            total_eval_budget=args.budget,
        )
        runner.run_campaign_manifest()
        print(f"Benchmark campaign manifest created at {args.output_dir}/campaign_manifest.csv")
    elif args.command == "analyze-benchmark":
        from mobo_linac.campaigns.benchmark import BenchmarkCampaignRunner
        config = load_config("configs/publication_200MeV.yaml")
        runner = BenchmarkCampaignRunner(config=config, output_dir=args.output_dir)
        agg_df, summary_df = runner.analyze_completed_results()
        print(f"Benchmark analysis complete. Aggregate metrics saved in {args.output_dir}")
    elif args.command == "run-robustness":
        print(f"Robustness analysis configuration initialized. Artifacts directory: {args.output_dir}")
    elif args.command == "run-verification":
        run_verification(args)


def run_verification(args: argparse.Namespace) -> None:
    """Executes Pareto candidate verification pipeline with fresh ASTRA reruns."""
    from mobo_linac.verification.verifier import run_verification_pipeline
    from mobo_linac.io.results import load_evaluation_results

    config_path = getattr(args, "config", "configs/publication.yaml")
    if not Path(config_path).exists():
        config_path = "configs/mobo_200MeV.yaml"
    config = load_config(config_path)

    output_dir = getattr(args, "output_dir", "results/verification")
    input_path = getattr(args, "input", None)

    results = []
    if input_path and Path(input_path).exists():
        p = Path(input_path)
        if p.is_dir():
            target_file = p / "candidate_history.json"
            if not target_file.exists():
                target_file = p / "pareto.csv"
            if not target_file.exists():
                target_file = p / "candidate_history.csv"
            results = load_evaluation_results(target_file)
        else:
            results = load_evaluation_results(p)
    else:
        results_dir = Path("results")
        candidates_files = list(results_dir.glob("**/candidate_history.json")) + list(results_dir.glob("**/pareto.csv"))
        if candidates_files:
            latest_file = max(candidates_files, key=lambda f: f.stat().st_mtime)
            print(f"Loading evaluation results from {latest_file} for verification...")
            results = load_evaluation_results(latest_file)

    if not results:
        print("No evaluation results found for verification.")
        return

    records, manifest_path, tex_path = run_verification_pipeline(
        results=results,
        config=config,
        output_dir=output_dir,
    )
    print(f"Pareto verification completed successfully for {len(records)} candidates.")


if __name__ == "__main__":
    main()


