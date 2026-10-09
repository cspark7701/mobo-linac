"""
Shared argument mixins and mock evaluators for the mobo_linac CLI.
"""

from mobo_linac.campaign_options import MULTIOBJECTIVE_ACQUISITIONS
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
        default=None,
        help="Path to config file",
    )
    subparser.add_argument(
        "--n-iterations",
        type=int,
        default=None,
        help="BO iterations after the initial design (default: config campaign.num_batches)",
    )
    subparser.add_argument(
        "-b",
        "-q",
        "--batch-size",
        "--batch_size",
        dest="batch_size",
        type=int,
        default=None,
        help="Batch size for q-MOBO candidate proposals (default: config campaign.batch_size)",
    )
    subparser.add_argument(
        "--num-initial-samples",
        type=int,
        default=None,
        help="Initial Sobol samples (default: config campaign.num_initial_samples)",
    )
    subparser.add_argument(
        "--num-workers",
        type=int,
        default=None,
        help="Parallel worker processes (default: config execution.max_workers)",
    )
    subparser.add_argument(
        "-a",
        "--acquisition",
        type=str,
        choices=list(MULTIOBJECTIVE_ACQUISITIONS),
        default=None,
        help="MOBO acquisition (default: config campaign.acquisition; scalarized BO uses qLogNEI)",
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
        default=None,
        help="Random seed (default: config campaign.seed)",
    )
    subparser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Custom output directory",
    )
    subparser.add_argument(
        "--reporting-ref-point", nargs="+", type=float, default=None,
        help="Fixed reporting reference in model-space units, in configured objective order",
    )
    subparser.add_argument(
        "--resume",
        action="store_true",
        help="Resume optimization from the latest checkpoint in output-dir if present",
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
