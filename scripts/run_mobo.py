#!/usr/bin/env python3
"""
Phase 2: Multi-Objective Bayesian Optimization (MOBO) for 200 MeV Linac Injector.

Thin production wrapper using the process-safe mobo_linac package APIs.
"""

import argparse
from mobo_linac.cli import run_unconstrained


def parse_args():
    parser = argparse.ArgumentParser(description="Run Phase 2 MOBO for 200 MeV Linac")
    parser.add_argument("--config", type=str, default="configs/publication.yaml", help="Path to config file")
    parser.add_argument("--n-iterations", type=int, default=300, help="Total BO iterations")
    parser.add_argument("-q", "--batch-size", type=int, default=8, help="Batch size for q-MOBO")
    parser.add_argument("--num-initial-samples", type=int, default=16, help="Number of initial random samples")
    parser.add_argument("--num-workers", type=int, default=4, help="Number of parallel workers for ASTRA")
    parser.add_argument("--acquisition", type=str, choices=["qLogNEHVI", "qEHVI"], default="qLogNEHVI", help="Acquisition function")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--output-dir", type=str, default=None, help="Custom output directory")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_unconstrained(args)
