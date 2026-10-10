"""
Shared argument mixins and mock evaluators for the mobo_linac CLI.
"""

from mobo_linac.campaign_options import Acquisition
import warnings
import argparse

from mobo_linac.execution.mock import MockEvaluator

__all__ = [
    "MockEvaluator",
    "add_common_run_args",
    "add_input_arg",
    "add_verbosity_args",
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
        choices=[acquisition.value for acquisition in Acquisition],
        default=None,
        help="Acquisition (default: config campaign.acquisition; scalarized BO requires qLogNEI)",
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
    add_verbosity_args(subparser)


class _DeprecatedInputAlias(argparse.Action):
    """Former spellings of ``--input``: store into ``input`` and warn."""

    def __call__(self, parser, namespace, values, option_string=None):
        message = f"{option_string} is deprecated and will be removed in 1.1.0; use --input."
        warnings.warn(message, DeprecationWarning, stacklevel=2)
        from mobo_linac.utils.logger import get_logger
        get_logger(__name__).warning(message)
        setattr(namespace, "input", values)


def add_input_arg(subparser: argparse.ArgumentParser, help_text: str) -> None:
    """One measured-candidate input option (``--history-path``/``--pareto-csv`` are deprecated aliases)."""
    subparser.add_argument("--input", type=str, default=None, help=help_text)
    for alias in ("--history-path", "--pareto-csv"):
        subparser.add_argument(alias, type=str, action=_DeprecatedInputAlias, help=argparse.SUPPRESS)


def add_verbosity_args(subparser: argparse.ArgumentParser) -> None:
    """Console verbosity shared by every subcommand (see ``utils.logger.configure_logging``)."""
    subparser.add_argument("--quiet", "--silent", action="store_true",
                           help="Show warnings and errors only")
    subparser.add_argument("-v", "--verbose", action="store_true",
                           help="Show INFO messages with timestamps")
    subparser.add_argument("--debug", action="store_true", help="Show DEBUG messages")
