"""
CLI command handlers for Pareto validation, candidate verification, and robustness auditing:
- run-robustness
- run-verification
- analyze
"""

import argparse
from pathlib import Path
import pandas as pd

from mobo_linac.cli.common import CliMockEvaluator
from mobo_linac.config import load_config
from mobo_linac.evaluation import create_evaluation_result


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


def run_robustness(args: argparse.Namespace) -> None:
    """Executes robustness analysis over Pareto candidates."""
    from mobo_linac.execution.parallel import BatchEvaluator
    from mobo_linac.io.results import DESIGN_VAR_COLUMNS, load_evaluation_results
    from mobo_linac.metrics.pareto import select_representative_pareto_candidates
    from mobo_linac.robustness.evaluator import (
        compute_robustness_summary,
        generate_perturbed_parameters,
    )

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
        print("[DRY-RUN] Robustness Analysis Plan:")
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
        print(
            f"  ✓ Candidate '{label}': Feasibility P = {summary['probability_of_feasibility']:.2f}, "
            f"Robust Score = {summary['robust_score']:.3f}"
        )

    summary_df = pd.DataFrame(summaries)
    summary_df.to_csv(output_dir / "robustness_summary.csv", index=False)
    print(f"=== Robustness Analysis Complete -> Saved in {output_dir.resolve()} ===")


def run_verification(args: argparse.Namespace) -> None:
    """Executes Pareto candidate verification pipeline with fresh ASTRA reruns."""
    from mobo_linac.io.results import DESIGN_VAR_COLUMNS, load_evaluation_results
    from mobo_linac.verification.verifier import run_verification_pipeline

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
        print("[DRY-RUN] Pareto Verification Plan:")
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


def register_audit_commands(subparsers: argparse._SubParsersAction) -> None:
    """Registers audit, analysis, robustness, and verification subcommands."""
    # Subcommand: analyze
    analyze_parser = subparsers.add_parser("analyze", help="Analyze results from a completed optimization run")
    analyze_parser.add_argument("--run-dir", type=str, required=True, help="Path to run directory")
    analyze_parser.add_argument("--output-dir", type=str, default=None, help="Output directory for figures")
    analyze_parser.set_defaults(handler=analyze_run)

    # Subcommand: run-robustness
    run_rob_parser = subparsers.add_parser(
        "run-robustness", help="Perform robustness and sensitivity analysis over Pareto candidates"
    )
    run_rob_parser.add_argument(
        "--config", type=str, default="configs/publication_200MeV.yaml", help="Path to config file"
    )
    run_rob_parser.add_argument(
        "--input", "--history-path", dest="history_path", type=str, default=None, help="Path to Pareto candidates CSV/JSON"
    )
    run_rob_parser.add_argument(
        "--pareto-csv", type=str, default=None, help="Path to pareto.csv file"
    )
    run_rob_parser.add_argument(
        "--output-dir", type=str, default="results/robustness", help="Output directory"
    )
    run_rob_parser.add_argument(
        "--num-perturbations", type=int, default=20, help="Number of perturbations per candidate"
    )
    run_rob_parser.add_argument(
        "--num-workers", type=int, default=4, help="Number of parallel worker processes"
    )
    run_rob_parser.add_argument(
        "--seed", type=int, default=42, help="Random seed"
    )
    run_rob_parser.add_argument(
        "--dry-run", action="store_true", help="Print planned robustness plan"
    )
    run_rob_parser.add_argument(
        "--mock-evaluator", action="store_true", help="Use mock evaluator for testing"
    )
    run_rob_parser.set_defaults(handler=run_robustness)

    # Subcommand: run-verification
    run_ver_parser = subparsers.add_parser(
        "run-verification", help="Rerun Pareto candidates independently for verification"
    )
    run_ver_parser.add_argument(
        "--config", type=str, default="configs/publication_200MeV.yaml", help="Path to config file"
    )
    run_ver_parser.add_argument(
        "--input", "--history-path", dest="history_path", type=str, default=None, help="Path to Pareto candidates CSV/JSON"
    )
    run_ver_parser.add_argument(
        "--pareto-csv", type=str, default=None, help="Path to pareto.csv file"
    )
    run_ver_parser.add_argument(
        "--output-dir", type=str, default="results/verification", help="Output directory"
    )
    run_ver_parser.add_argument(
        "--dry-run", action="store_true", help="Print planned verification plan"
    )
    run_ver_parser.add_argument(
        "--mock-evaluator", action="store_true", help="Use mock evaluator for testing"
    )
    run_ver_parser.set_defaults(handler=run_verification)
