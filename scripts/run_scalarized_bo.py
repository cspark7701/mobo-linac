#!/usr/bin/env python3
"""
Phase 1: Scalarized Bayesian Optimization (BO) for 200 MeV Electron Injector Linac.

Production execution script for scalarized Bayesian Optimization using single-objective
GP surrogates (SingleTaskGP / qLogNEI) across specified objective weight combinations.
"""

import argparse
from mobo_linac.cli import run_scalarized


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run Phase 1 Scalarized BO for 200 MeV Linac Injector"
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
        default=300,
        help="Total BO iterations",
    )
    parser.add_argument(
        "-q",
        "--batch-size",
        type=int,
        default=8,
        help="Batch size for q-scalarized BO",
    )
    parser.add_argument(
        "--num-initial-samples",
        type=int,
        default=16,
        help="Number of initial Sobol samples",
    )
    parser.add_argument(
        "--num-workers",
        type=int,
        default=4,
        help="Number of parallel workers for ASTRA",
    )
    parser.add_argument(
        "--weights",
        nargs=3,
        type=float,
        default=[1.0, 1.0, 1.0],
        help="Weights for 3 objectives (emittance_x, emittance_y, energy_spread)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Custom output directory for run artifacts",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_scalarized(args)
