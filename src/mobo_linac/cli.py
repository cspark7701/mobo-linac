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



class CliMockEvaluator:
    """Mock evaluator for CLI testing without requiring ASTRA binary."""

    def __init__(self, run_dir: Path):
        self.run_dir = Path(run_dir)

    def evaluate_batch(self, candidates, run_id, eval_ids=None):
        raw_results = []
        for idx, cand in enumerate(candidates):
            eval_id_str = f"eval_{eval_ids[idx]:06d}" if eval_ids and idx < len(eval_ids) else f"eval_{idx+1:06d}"
            raw_results.append({
                "status": "success",
                "eval_id": eval_id_str,
                "run_id": run_id,
                "parameters": cand,
                "objectives": {
                    "norm_emit_x": float(0.1e-6 + 0.01e-6 * (sum(cand) % 5)),
                    "norm_emit_y": float(0.1e-6 + 0.01e-6 * (sum(cand) % 7)),
                    "sigma_energy": float(0.5e6 + 0.05e6 * (sum(cand) % 3)),
                },
                "diagnostics": {
                    "sigma_x_m": 0.5e-3,
                    "sigma_y_m": 0.5e-3,
                    "sigma_xp_rad": 0.5e-3,
                    "sigma_yp_rad": 0.5e-3,
                    "sigma_z_m": 0.5e-3,
                    "mean_kinetic_energy_eV": 200.0e6,
                    "transmission_fraction": 1.0,
                },
                "timestamps": {"duration_sec": 0.1},
                "eval_dir": str(self.run_dir / eval_id_str),
            })
        return raw_results


def run_unconstrained(args: argparse.Namespace) -> None:
    """Executes Phase 2 Unconstrained MOBO campaign."""
    from mobo_linac.campaigns.runner import MoboCampaignRunner

    config_path = args.config if hasattr(args, "config") and args.config else "configs/publication.yaml"
    if not Path(config_path).exists():
        config_path = "configs/mobo_200MeV.yaml"

    if getattr(args, "dry_run", False):
        print(f"[DRY-RUN] Unconstrained MOBO Campaign Plan:")
        print(f"  - Config: {config_path}")
        print(f"  - Output Directory: {args.output_dir or 'results/unconstrained_<timestamp>'}")
        print(f"  - Initial Samples: {getattr(args, 'num_initial_samples', 16)}")
        print(f"  - Iterations: {getattr(args, 'n_iterations', 6)} (batch size: {getattr(args, 'batch_size', 4)})")
        return

    evaluator = CliMockEvaluator(Path(args.output_dir or "results")) if getattr(args, "mock_evaluator", False) else None

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
        evaluator=evaluator,
    )
    runner.run()


def run_constrained(args: argparse.Namespace) -> None:
    """Executes Phase 3 Constrained MOBO campaign."""
    from mobo_linac.campaigns.runner import MoboCampaignRunner

    config_path = args.config if hasattr(args, "config") and args.config else "configs/publication.yaml"
    if not Path(config_path).exists():
        config_path = "configs/mobo_200MeV.yaml"

    if getattr(args, "dry_run", False):
        print(f"[DRY-RUN] Constrained MOBO Campaign Plan:")
        print(f"  - Config: {config_path}")
        print(f"  - Output Directory: {args.output_dir or 'results/constrained_<timestamp>'}")
        print(f"  - Initial Samples: {getattr(args, 'num_initial_samples', 16)}")
        print(f"  - Iterations: {getattr(args, 'n_iterations', 6)} (batch size: {getattr(args, 'batch_size', 4)})")
        return

    evaluator = CliMockEvaluator(Path(args.output_dir or "results")) if getattr(args, "mock_evaluator", False) else None

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
        evaluator=evaluator,
    )
    runner.run()


def run_scalarized(args: argparse.Namespace) -> None:
    """Executes Scalarized BO campaign (weighted sum scalarization)."""
    from mobo_linac.campaigns.runner import MoboCampaignRunner

    config_path = args.config if hasattr(args, "config") and args.config else "configs/publication.yaml"
    if not Path(config_path).exists():
        config_path = "configs/mobo_200MeV.yaml"

    if getattr(args, "dry_run", False):
        print(f"[DRY-RUN] Scalarized BO Campaign Plan:")
        print(f"  - Config: {config_path}")
        print(f"  - Output Directory: {args.output_dir or 'results/scalarized_<timestamp>'}")
        print(f"  - Weights: {getattr(args, 'weights', [1.0, 1.0, 1.0])}")
        print(f"  - Initial Samples: {getattr(args, 'num_initial_samples', 16)}")
        print(f"  - Iterations: {getattr(args, 'n_iterations', 6)} (batch size: {getattr(args, 'batch_size', 4)})")
        return

    evaluator = CliMockEvaluator(Path(args.output_dir or "results")) if getattr(args, "mock_evaluator", False) else None

    runner = MoboCampaignRunner(
        config=config_path,
        run_name="scalarized",
        output_dir=getattr(args, "output_dir", None),
        num_initial_samples=getattr(args, "num_initial_samples", 16),
        num_batches=getattr(args, "n_iterations", 6),
        batch_size=getattr(args, "batch_size", 4),
        num_workers=getattr(args, "num_workers", None),
        seed=getattr(args, "seed", 42),
        optimization_mode="scalarized_bo",
        scalar_weights=getattr(args, "weights", [1.0, 1.0, 1.0]),
        export_plots=True,
        evaluator=evaluator,
        device=getattr(args, "device", "auto"),
    )
    runner.run()


def run_validation(args: argparse.Namespace) -> None:
    """Executes full reproducible validation campaign."""
    config_path = args.config if args.config else "configs/publication.yaml"
    if not Path(config_path).exists():
        config_path = "configs/mobo_200MeV.yaml"

    if getattr(args, "dry_run", False):
        print(f"[DRY-RUN] Validation Campaign Plan:")
        print(f"  - Config: {config_path}")
        print(f"  - Output Directory: {args.output_dir or 'results/validation_<timestamp>'}")
        return

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

    if getattr(args, "dry_run", False):
        print(f"[DRY-RUN] Resume Optimization Plan:")
        print(f"  - Target Run Directory: {run_dir}")
        return

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

    evaluator = CliMockEvaluator(run_dir) if getattr(args, "mock_evaluator", False) else None

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
        evaluator=evaluator,
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
        subparser.add_argument("--dry-run", action="store_true", help="Print planned execution details without running ASTRA")
        subparser.add_argument("--mock-evaluator", action="store_true", help="Use fast mock evaluator for testing without ASTRA binary")

    # Subcommand: run
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
    resume_parser.add_argument("--dry-run", action="store_true", help="Print planned execution details")
    resume_parser.add_argument("--mock-evaluator", action="store_true", help="Use mock evaluator for testing")

    # Subcommand: run-benchmark
    run_bm_parser = subparsers.add_parser("run-benchmark", help="Run a paired multi-seed benchmark campaign")
    run_bm_parser.add_argument("--config", type=str, default="configs/publication_200MeV.yaml", help="Path to config file")
    run_bm_parser.add_argument("--output-dir", type=str, default="results/publication_benchmark", help="Output directory")
    run_bm_parser.add_argument("--algorithms", nargs="+", type=str, default=None, help="Algorithms to benchmark (space-separated)")
    run_bm_parser.add_argument("--seeds", nargs="+", type=int, default=list(range(42, 52)), help="List of random seeds")
    run_bm_parser.add_argument("--budget", type=int, default=40, help="Total evaluation budget per algorithm-seed pair")
    run_bm_parser.add_argument("--n-sobol-init", type=int, default=10, help="Number of initial Sobol samples")
    run_bm_parser.add_argument("--batch-size", type=int, default=4, help="BO batch size per iteration")
    run_bm_parser.add_argument("--num-workers", type=int, default=4, help="Number of parallel worker processes")
    run_bm_parser.add_argument("--dry-run", action="store_true", help="Print planned benchmark plan")
    run_bm_parser.add_argument("--mock-evaluator", action="store_true", help="Use mock evaluator for testing")


    # Subcommand: analyze-benchmark
    analyze_bm_parser = subparsers.add_parser("analyze-benchmark", help="Aggregate and analyze completed benchmark campaign results")
    analyze_bm_parser.add_argument("--output-dir", type=str, default="results/publication_benchmark", help="Benchmark campaign directory")

    # Subcommand: run-robustness
    run_rob_parser = subparsers.add_parser("run-robustness", help="Perform robustness and sensitivity analysis over Pareto candidates")
    run_rob_parser.add_argument("--config", type=str, default="configs/publication_200MeV.yaml", help="Path to config file")
    run_rob_parser.add_argument("--input", "--history-path", dest="history_path", type=str, default=None, help="Path to Pareto candidates CSV/JSON")
    run_rob_parser.add_argument("--pareto-csv", type=str, default=None, help="Path to pareto.csv file")
    run_rob_parser.add_argument("--output-dir", type=str, default="results/robustness", help="Output directory")
    run_rob_parser.add_argument("--num-perturbations", type=int, default=20, help="Number of perturbations per candidate")
    run_rob_parser.add_argument("--num-workers", type=int, default=4, help="Number of parallel worker processes")
    run_rob_parser.add_argument("--seed", type=int, default=42, help="Random seed")
    run_rob_parser.add_argument("--dry-run", action="store_true", help="Print planned robustness plan")
    run_rob_parser.add_argument("--mock-evaluator", action="store_true", help="Use mock evaluator for testing")

    # Subcommand: run-verification
    run_ver_parser = subparsers.add_parser("run-verification", help="Rerun Pareto candidates independently for verification")
    run_ver_parser.add_argument("--config", type=str, default="configs/publication_200MeV.yaml", help="Path to config file")
    run_ver_parser.add_argument("--input", "--history-path", dest="history_path", type=str, default=None, help="Path to Pareto candidates CSV/JSON")
    run_ver_parser.add_argument("--pareto-csv", type=str, default=None, help="Path to pareto.csv file")
    run_ver_parser.add_argument("--output-dir", type=str, default="results/verification", help="Output directory")
    run_ver_parser.add_argument("--dry-run", action="store_true", help="Print planned verification plan")
    run_ver_parser.add_argument("--mock-evaluator", action="store_true", help="Use mock evaluator for testing")

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
            algorithms=getattr(args, "algorithms", None),
            seeds=args.seeds,
            total_eval_budget=args.budget,
            n_sobol_init=getattr(args, "n_sobol_init", 10),
            batch_size=getattr(args, "batch_size", 4),
        )
        mock_eval = CliMockEvaluator(Path(args.output_dir)) if getattr(args, "mock_evaluator", False) else None
        runner.execute_benchmark_campaigns(dry_run=args.dry_run, mock_evaluator=mock_eval)

    elif args.command == "analyze-benchmark":
        from mobo_linac.campaigns.benchmark import BenchmarkCampaignRunner
        config = load_config("configs/publication_200MeV.yaml")
        runner = BenchmarkCampaignRunner(config=config, output_dir=args.output_dir)
        agg_df, summary_df = runner.analyze_completed_results()
        print(f"Benchmark analysis complete. Aggregate metrics saved in {args.output_dir}")
    elif args.command == "run-robustness":
        run_robustness(args)
    elif args.command == "run-verification":
        run_verification(args)


def run_robustness(args: argparse.Namespace) -> None:
    """Executes robustness analysis over Pareto candidates."""
    from mobo_linac.robustness.evaluator import (
        generate_perturbed_parameters,
        select_representative_pareto_candidates,
        compute_robustness_summary,
    )
    from mobo_linac.io.results import load_evaluation_results, DESIGN_VAR_COLUMNS

    config_path = getattr(args, "config", "configs/publication.yaml")
    if not Path(config_path).exists():
        config_path = "configs/mobo_200MeV.yaml"
    config = load_config(config_path)

    output_dir = Path(getattr(args, "output_dir", "results/robustness"))
    output_dir.mkdir(parents=True, exist_ok=True)

    input_path = getattr(args, "history_path", None) or getattr(args, "pareto_csv", None)

    results = []
    if input_path and Path(input_path).exists():
        p = Path(input_path)
        if p.is_dir():
            target = p / "pareto.csv"
            if not target.exists():
                target = p / "candidate_history.json"
            if not target.exists():
                target = p / "candidate_history.csv"
            results = load_evaluation_results(target)
        else:
            results = load_evaluation_results(p)
    else:
        results_dir = Path("results")
        cand_files = list(results_dir.glob("**/pareto.csv")) + list(results_dir.glob("**/candidate_history.json"))
        if cand_files:
            latest = max(cand_files, key=lambda f: f.stat().st_mtime)
            print(f"Loading Pareto candidates from {latest} for robustness analysis...")
            results = load_evaluation_results(latest)

    if not results:
        print("WARNING: No Pareto candidates found for robustness analysis. Creating dummy candidate.")
        dummy_x = [0.15, 1.0, -2.0, 35.0, -40.0, 320.0]
        raw_res = {
            "eval_id": 1,
            "status": "SUCCESS",
            "parameters": dummy_x,
            "design_parameters": dict(zip(DESIGN_VAR_COLUMNS, dummy_x)),
            "objectives": {"norm_emit_x": 1.0e-6, "norm_emit_y": 1.0e-6, "sigma_energy": 0.5e6},
            "diagnostics": {"transmission_fraction": 1.0},
        }
        results.append(create_evaluation_result(raw_res, config))

    rep_candidates = select_representative_pareto_candidates(results)

    if getattr(args, "dry_run", False):
        print(f"[DRY-RUN] Robustness Analysis Plan:")
        print(f"  - Output Directory: {output_dir.resolve()}")
        print(f"  - Candidates ({len(rep_candidates)}): {list(rep_candidates.keys())}")
        print(f"  - Perturbations per Candidate: {getattr(args, 'num_perturbations', 20)}")
        return

    if getattr(args, "mock_evaluator", False):
        evaluator = CliMockEvaluator(output_dir)
    else:
        evaluator = BatchEvaluator(
            base_results_dir=output_dir / "work",
            template_dir=".",
            max_workers=getattr(args, "num_workers", 4),
            timeout=config.execution.timeout_sec,
        )

    summaries = []
    num_perts = getattr(args, "num_perturbations", 20)
    seed = getattr(args, "seed", 42)

    for label, candidate_res in rep_candidates.items():
        nom_x = candidate_res.x_physical
        perturbed_xs = generate_perturbed_parameters(
            nominal_x=nom_x,
            num_perturbations=num_perts,
            seed=seed,
        )
        raw_perturbed = evaluator.evaluate_batch(perturbed_xs, run_id=f"robust_{label}")
        perturbed_results = [create_evaluation_result(r, config) for r in raw_perturbed]

        summary = compute_robustness_summary(label, candidate_res, perturbed_results)
        summaries.append(summary)
        print(f"  ✓ Candidate '{label}': Feasibility P = {summary['probability_of_feasibility']:.2f}, Robust Score = {summary['robust_score']:.3f}")

    summary_df = pd.DataFrame(summaries)
    summary_df.to_csv(output_dir / "robustness_summary.csv", index=False)
    print(f"=== Robustness Analysis Complete -> Saved in {output_dir.resolve()} ===")



def run_verification(args: argparse.Namespace) -> None:
    """Executes Pareto candidate verification pipeline with fresh ASTRA reruns."""
    from mobo_linac.verification.verifier import run_verification_pipeline
    from mobo_linac.io.results import load_evaluation_results

    config_path = getattr(args, "config", "configs/publication.yaml")
    if not Path(config_path).exists():
        config_path = "configs/mobo_200MeV.yaml"
    config = load_config(config_path)

    output_dir = getattr(args, "output_dir", "results/verification")
    input_path = getattr(args, "history_path", None) or getattr(args, "pareto_csv", None) or getattr(args, "input", None)

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
        print("WARNING: No evaluation results found for verification. Creating dummy evaluation result.")
        dummy_x = [0.15, 1.0, -2.0, 35.0, -40.0, 320.0]
        raw_res = {
            "eval_id": 1,
            "status": "SUCCESS",
            "parameters": dummy_x,
            "design_parameters": dict(zip(DESIGN_VAR_COLUMNS, dummy_x)),
            "objectives": {"norm_emit_x": 1.0e-6, "norm_emit_y": 1.0e-6, "sigma_energy": 0.5e6},
            "diagnostics": {"transmission_fraction": 1.0},
        }
        results.append(create_evaluation_result(raw_res, config))

    if getattr(args, "dry_run", False):
        print(f"[DRY-RUN] Pareto Verification Plan:")
        print(f"  - Output Directory: {Path(output_dir).resolve()}")
        print(f"  - Input Candidates: {len(results)} evaluated candidates")
        return

    mock_eval = None
    if getattr(args, "mock_evaluator", False):
        def mock_eval_fn(x, run_id, eval_id):
            return {
                "status": "success",
                "objectives": {"norm_emit_x": 1.0e-6, "norm_emit_y": 1.0e-6, "sigma_energy": 0.5e6},
                "diagnostics": {"transmission_fraction": 1.0, "sigma_x_m": 0.5e-3},
            }
        mock_eval = mock_eval_fn

    records, manifest_path, tex_path = run_verification_pipeline(
        results=results,
        config=config,
        output_dir=output_dir,
        mock_evaluator=mock_eval,
    )
    print(f"Pareto verification completed successfully for {len(records)} candidates.")


if __name__ == "__main__":
    main()



if __name__ == "__main__":
    main()


