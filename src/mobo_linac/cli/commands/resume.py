"""
CLI command handler for resuming an optimization campaign from checkpoint.
"""

import argparse
from pathlib import Path

from mobo_linac.cli.common import CliMockEvaluator


def resume_optimization(args: argparse.Namespace) -> None:
    """Resumes an existing optimization campaign from checkpoint."""
    from mobo_linac.campaigns.runner import MoboCampaignRunner
    from mobo_linac.io.results import load_run_checkpoint

    run_dir = Path(getattr(args, "run_dir", getattr(args, "output_dir", "results")))

    if getattr(args, "dry_run", False):
        print("[DRY-RUN] Resume Optimization Plan:")
        print(f"  - Target Run Directory: {run_dir}")
        return

    ckpt_data = load_run_checkpoint(run_dir)
    if not ckpt_data:
        raise FileNotFoundError(f"No valid checkpoint found in: {run_dir}")

    config_path = run_dir / "config.yaml"
    if not config_path.exists():
        config_path = run_dir / "config.json"
    if not config_path.exists():
        config_path = getattr(args, "config", "configs/publication.yaml")

    acq_type = ckpt_data.get("acquisition_mode", getattr(args, "acquisition", "qLogNEHVI"))
    constrained = ckpt_data.get("constrained", False)
    seed = ckpt_data.get("seed", getattr(args, "seed", 42))
    batch_size = getattr(args, "batch_size", None) or ckpt_data.get("batch_size", 4)

    evaluator = CliMockEvaluator(run_dir) if getattr(args, "mock_evaluator", False) else None

    runner = MoboCampaignRunner(
        config=config_path,
        output_dir=run_dir,
        num_batches=getattr(args, "n_iterations", 6),
        batch_size=batch_size,
        num_workers=getattr(args, "num_workers", None),
        seed=seed,
        acq_type=acq_type,
        constrained=constrained,
        resume=True,
        evaluator=evaluator,
        device=getattr(args, "device", "auto"),
    )
    runner.run()


def register_resume_command(subparsers: argparse._SubParsersAction) -> None:
    """Registers resume subcommands."""
    resume_parser = subparsers.add_parser("resume", help="Resume an existing optimization campaign")
    resume_parser.add_argument("--run-dir", type=str, required=True, help="Path to run directory")
    resume_parser.add_argument("--n-iterations", type=int, default=300, help="Total BO iterations")
    resume_parser.add_argument(
        "-b", "-q", "--batch-size", "--batch_size",
        dest="batch_size",
        type=int,
        default=None,
        help="Batch size override for resumed iterations",
    )
    resume_parser.add_argument("--num-workers", type=int, default=4, help="Number of parallel worker processes")
    resume_parser.add_argument("--device", type=str, default="auto", help="Target PyTorch compute device ('auto', 'cuda', 'cuda:0', 'cpu')")
    resume_parser.add_argument("--dry-run", action="store_true", help="Print planned execution details")
    resume_parser.add_argument("--mock-evaluator", action="store_true", help="Use mock evaluator for testing")
    resume_parser.set_defaults(handler=resume_optimization)
