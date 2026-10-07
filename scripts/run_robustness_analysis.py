#!/usr/bin/env python3
"""
Robustness and Sensitivity Analysis Production Script for mobo_linac.

Evaluates machine and beam perturbation sensitivity across representative Pareto candidates.
"""

import argparse
from pathlib import Path
from typing import Optional

from mobo_linac.config import load_config
from mobo_linac.execution.mock import MockBatchEvaluator
from mobo_linac.io.results import load_evaluation_results
from mobo_linac.robustness.workflow import run_robustness_workflow


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run Engineering Tolerance & Robustness Analysis"
    )
    parser.add_argument(
        "--pareto-csv",
        type=str,
        default=None,
        help="Path to pareto.csv file containing non-dominated candidates",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="configs/mobo_200MeV.yaml",
        help="Path to YAML config file",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="results/robustness",
        help="Output directory for robustness artifacts",
    )
    parser.add_argument(
        "--num-workers",
        "-w",
        type=int,
        default=4,
        help="Number of parallel worker processes",
    )
    parser.add_argument(
        "--num-perturbations",
        type=int,
        default=20,
        help="Number of perturbed parameter samples per candidate",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--mock-evaluator", action="store_true")
    return parser.parse_args()


def find_pareto_csv(user_path_str: Optional[str]) -> Optional[Path]:
    """Finds pareto.csv supporting files, directories, and subdirectories."""
    search_paths = []
    if user_path_str:
        p = Path(user_path_str)
        search_paths.append(p)
        if p.is_dir():
            search_paths.append(p / "pareto.csv")
            search_paths.extend(list(p.rglob("pareto.csv")))
            search_paths.extend(list(p.rglob("pareto_feasible.csv")))

    fallbacks = [
        Path("results/full_production/phase3_constrained/pareto.csv"),
        Path("results/full_production/phase3_constrained"),
        Path("results/phase3_constrained"),
        Path("results/pareto.csv"),
        Path("results"),
    ]
    for fb in fallbacks:
        search_paths.append(fb)
        if fb.is_dir():
            search_paths.append(fb / "pareto.csv")
            search_paths.extend(list(fb.rglob("pareto.csv")))
            search_paths.extend(list(fb.rglob("pareto_feasible.csv")))

    for candidate in search_paths:
        if candidate.is_file() and candidate.exists() and candidate.stat().st_size > 0:
            return candidate

    return None


def run_robustness_analysis(args: argparse.Namespace) -> Path:
    config = load_config(args.config)
    pareto_path = find_pareto_csv(args.pareto_csv)
    results = load_evaluation_results(pareto_path, config=config) if pareto_path is not None else []
    mock = getattr(args, "mock_evaluator", None)
    if mock is True:
        mock = MockBatchEvaluator(args.output_dir)
    elif mock is False:
        mock = None
    return run_robustness_workflow(
        results, config, args.output_dir, num_perturbations=args.num_perturbations,
        num_workers=args.num_workers, seed=args.seed,
        dry_run=getattr(args, "dry_run", False), batch_evaluator=mock,
    )


if __name__ == "__main__":
    args = parse_args()
    run_robustness_analysis(args)
