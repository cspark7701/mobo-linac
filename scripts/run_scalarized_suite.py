#!/usr/bin/env python3
"""
Phase 1: Option 2 Multi-Case Scalarized BO Suite Runner.

Executes representative operational linac archetypes for the 200 MeV electron injector linac:
  1. balanced:          [1/3, 1/3, 1/3]
  2. high_brightness:   [0.45, 0.45, 0.10]
  3. low_energy_spread: [0.10, 0.10, 0.80]
  4. x_dominant:        [0.60, 0.20, 0.20]
  5. y_dominant:        [0.20, 0.60, 0.20]

Aggregates individual case runs into unified candidate history, non-dominated Pareto front,
and cumulative hypervolume progression, exporting publication LaTeX summary tables.
"""

import argparse
from pathlib import Path
import sys

from mobo_linac.campaigns.scalarized_suite import OPTION_2_CASES, run_scalarized_suite


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run Phase 1 Option 2 Multi-Case Scalarized BO Suite"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="configs/mobo_200MeV.yaml",
        help="Path to YAML config file",
    )
    parser.add_argument(
        "--n-iterations",
        type=int,
        default=20,
        help="Total BO iterations per case",
    )
    parser.add_argument(
        "-q",
        "--batch-size",
        type=int,
        default=8,
        help="Batch size q for candidate proposal per iteration",
    )
    parser.add_argument(
        "--num-initial-samples",
        type=int,
        default=16,
        help="Number of initial Sobol samples per case",
    )
    parser.add_argument(
        "--num-workers",
        type=int,
        default=4,
        help="Number of parallel workers for ASTRA",
    )
    parser.add_argument(
        "--cases",
        nargs="*",
        default=None,
        choices=list(OPTION_2_CASES.keys()) + ["all"],
        help="Subset of Option 2 cases to run (default: all)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed base for reproducibility",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="results/full_production/phase1_scalarized",
        help="Base output directory for suite results",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="auto",
        help="Target PyTorch compute device ('auto', 'cuda', 'cpu')",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume optimization from latest checkpoints",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    cases = None if (args.cases is None or "all" in args.cases) else args.cases

    run_scalarized_suite(
        config=args.config,
        n_iterations=args.n_iterations,
        batch_size=args.batch_size,
        num_initial_samples=args.num_initial_samples,
        num_workers=args.num_workers,
        seed=args.seed,
        output_dir=args.output_dir,
        device=args.device,
        cases_to_run=cases,
        resume=args.resume,
    )


if __name__ == "__main__":
    main()
