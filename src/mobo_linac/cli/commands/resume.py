"""
CLI command handler for resuming an optimization campaign from checkpoint.
"""

import argparse
from pathlib import Path

from mobo_linac.cli.common import add_verbosity_args
from mobo_linac.cli.common import MockEvaluator


def resume_optimization(args: argparse.Namespace) -> None:
    """Resumes an existing optimization campaign from checkpoint."""
    from mobo_linac.campaigns.runner import MoboCampaignRunner
    from mobo_linac.io.checkpoint import load_run_checkpoint

    run_dir = Path(getattr(args, "run_dir", getattr(args, "output_dir", "results")))

    if getattr(args, "dry_run", False):
        print("[DRY-RUN] Resume Optimization Plan:")
        print(f"  - Target Run Directory: {run_dir}")
        return

    ckpt_data = load_run_checkpoint(run_dir)
    if not ckpt_data:
        raise FileNotFoundError(f"No valid checkpoint found in: {run_dir}")

    # The checkpoint's configuration and campaign settings are authoritative. The runner
    # validates saved state before it touches any existing artifacts.
    batch_size = getattr(args, "batch_size", None)
    legacy_weights = getattr(args, "legacy_scalar_weights", None)
    if legacy_weights is not None and ckpt_data.migrated_from != "1.0":
        raise ValueError("--legacy-scalar-weights applies only to legacy v1 checkpoints.")

    evaluator = MockEvaluator(run_dir) if getattr(args, "mock_evaluator", False) else None

    runner = MoboCampaignRunner(
        output_dir=run_dir,
        num_batches=getattr(args, "n_iterations", None),
        batch_size=batch_size,
        num_workers=getattr(args, "num_workers", None),
        scalar_weights=legacy_weights,
        resume=True,
        evaluator=evaluator,
        device=getattr(args, "device", "auto"),
    )
    runner.run()


def register_resume_command(subparsers: argparse._SubParsersAction) -> None:
    """Registers resume subcommands."""
    resume_parser = subparsers.add_parser("resume", help="Resume an existing optimization campaign")
    add_verbosity_args(resume_parser)
    resume_parser.add_argument("--run-dir", type=str, required=True, help="Path to run directory")
    resume_parser.add_argument("--n-iterations", type=int, default=None, help="Total BO iterations (default: saved campaign plan)")
    resume_parser.add_argument(
        "-b", "-q", "--batch-size", "--batch_size",
        dest="batch_size",
        type=int,
        default=None,
        help="Batch size for future iterations; completed history is preserved",
    )
    resume_parser.add_argument("--legacy-scalar-weights", nargs="+", type=float, default=None, help="Original weights omitted by a legacy scalarized v1 checkpoint")
    resume_parser.add_argument("--num-workers", type=int, default=None, help="Number of workers (default: saved campaign setting)")
    resume_parser.add_argument("--device", type=str, default="auto", help="Target PyTorch compute device ('auto', 'cuda', 'cuda:0', 'cpu')")
    resume_parser.add_argument("--dry-run", action="store_true", help="Print planned execution details")
    resume_parser.add_argument("--mock-evaluator", action="store_true", help="Use mock evaluator for testing")
    resume_parser.set_defaults(handler=resume_optimization)
