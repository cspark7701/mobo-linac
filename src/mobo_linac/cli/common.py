"""
Shared argument mixins and mock evaluators for the mobo_linac CLI.
"""

import argparse
from pathlib import Path

from mobo_linac.execution.mock import (
    CliMockEvaluator,
    MockBatchEvaluator,
)

__all__ = [
    "CliMockEvaluator",
    "MockBatchEvaluator",
    "add_common_run_args",
]


def add_common_run_args(subparser: argparse.ArgumentParser) -> None:
    """Adds standard Bayesian optimization execution arguments to a subparser."""
    subparser.add_argument(
        "--config",
        type=str,
        default="configs/publication.yaml",
        help="Path to config file",
    )
    subparser.add_argument(
        "--n-iterations",
        type=int,
        default=300,
        help="Total BO iterations",
    )
    subparser.add_argument(
        "-b",
        "-q",
        "--batch-size",
        "--batch_size",
        dest="batch_size",
        type=int,
        default=8,
        help="Batch size for q-MOBO candidate proposals",
    )
    subparser.add_argument(
        "--num-initial-samples",
        type=int,
        default=16,
        help="Initial random Sobol samples",
    )
    subparser.add_argument(
        "--num-workers",
        type=int,
        default=4,
        help="Number of parallel worker processes",
    )
    subparser.add_argument(
        "-a",
        "--acquisition",
        type=str,
        choices=["qLogNEHVI", "qLogEHVI", "qEHVI", "qNEHVI"],
        default="qLogNEHVI",
        help="Acquisition function ('qLogNEHVI', 'qLogEHVI', 'qEHVI', 'qNEHVI')",
    )
    subparser.add_argument(
        "--device",
        type=str,
        default="auto",
        help="Target PyTorch compute device ('auto', 'cuda', 'cuda:0', 'cpu')",
    )
    subparser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed",
    )
    subparser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Custom output directory",
    )
    subparser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned execution details without running ASTRA",
    )
    subparser.add_argument(
        "--mock-evaluator",
        action="store_true",
        help="Use fast mock evaluator for testing without ASTRA binary",
    )
    subparser.add_argument(
        "--quiet",
        "--silent",
        action="store_true",
        help="Suppress non-critical console outputs",
    )
    subparser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output logging",
    )
    subparser.add_argument(
        "--debug",
        action="store_true",
        help="Enable detailed debug logging",
    )
