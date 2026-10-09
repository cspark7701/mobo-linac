#!/usr/bin/env python3
"""
Phase 1: Multi-Case Scalarized BO Suite Runner.

Runs the weighted-sum cases defined under ``scalarized_cases`` in the configuration
(for the 200 MeV configs: balanced, high_brightness, low_energy_spread, x_dominant,
y_dominant). Each case uses ``seed + seed_offset``, so its result does not depend on
which other cases are selected. Aggregates the cases into a unified history, Pareto
front and per-case hypervolume progression, and exports the LaTeX summary table.
"""

import argparse
from pathlib import Path
import sys

from mobo_linac.campaigns.scalarized_suite import run_scalarized_suite


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
        help="Subset of configured scalarized case ids to run, or 'all' (default: all)",
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
