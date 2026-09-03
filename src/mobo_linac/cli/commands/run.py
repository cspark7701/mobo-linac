"""
CLI command handlers for starting new optimization campaigns:
- run / run-unconstrained
- run-constrained
- run-scalarized
- run-validation
"""

import argparse
from pathlib import Path

from mobo_linac.cli.common import CliMockEvaluator, add_common_run_args


def run_unconstrained(args: argparse.Namespace) -> None:
    """Executes Phase 2 Unconstrained MOBO campaign."""
    from mobo_linac.campaigns.runner import MoboCampaignRunner

    config_path = args.config if hasattr(args, "config") and args.config else "configs/publication.yaml"
    if not Path(config_path).exists():
        config_path = "configs/mobo_200MeV.yaml"

    if getattr(args, "dry_run", False):
        print("[DRY-RUN] Unconstrained MOBO Campaign Plan:")
        print(f"  - Config: {config_path}")
        print(f"  - Output Directory: {args.output_dir or 'results/unconstrained_<timestamp>'}")
        print(f"  - Initial Samples: {getattr(args, 'num_initial_samples', 16)}")
        print(f"  - Iterations: {getattr(args, 'n_iterations', 20)} (batch size: {getattr(args, 'batch_size', 8)})")
        return

    evaluator = (
        CliMockEvaluator(Path(args.output_dir or "results"))
        if getattr(args, "mock_evaluator", False)
        else None
    )

    runner = MoboCampaignRunner(
        config=config_path,
        run_name="unconstrained",
        output_dir=getattr(args, "output_dir", None),
        num_initial_samples=getattr(args, "num_initial_samples", 16),
        num_batches=getattr(args, "n_iterations", 20),
        batch_size=getattr(args, "batch_size", 8),
        num_workers=getattr(args, "num_workers", None),
        seed=getattr(args, "seed", 42),
        acq_type=getattr(args, "acquisition", "qLogNEHVI"),
        constrained=False,
        export_plots=True,
        evaluator=evaluator,
        device=getattr(args, "device", "auto"),
    )
    runner.run()


def run_constrained(args: argparse.Namespace) -> None:
    """Executes Phase 3 Constrained MOBO campaign."""
    from mobo_linac.campaigns.runner import MoboCampaignRunner

    config_path = args.config if hasattr(args, "config") and args.config else "configs/publication.yaml"
    if not Path(config_path).exists():
        config_path = "configs/mobo_200MeV.yaml"

    if getattr(args, "dry_run", False):
        print("[DRY-RUN] Constrained MOBO Campaign Plan:")
        print(f"  - Config: {config_path}")
        print(f"  - Output Directory: {args.output_dir or 'results/constrained_<timestamp>'}")
        print(f"  - Initial Samples: {getattr(args, 'num_initial_samples', 16)}")
        print(f"  - Iterations: {getattr(args, 'n_iterations', 20)} (batch size: {getattr(args, 'batch_size', 8)})")
        return

    evaluator = (
        CliMockEvaluator(Path(args.output_dir or "results"))
        if getattr(args, "mock_evaluator", False)
        else None
    )

    runner = MoboCampaignRunner(
        config=config_path,
        run_name="constrained",
        output_dir=getattr(args, "output_dir", None),
        num_initial_samples=getattr(args, "num_initial_samples", 16),
        num_batches=getattr(args, "n_iterations", 20),
        batch_size=getattr(args, "batch_size", 8),
        num_workers=getattr(args, "num_workers", None),
        seed=getattr(args, "seed", 42),
        acq_type=getattr(args, "acquisition", "qLogNEHVI"),
        constrained=True,
        export_plots=True,
        evaluator=evaluator,
        device=getattr(args, "device", "auto"),
    )
    runner.run()


def run_scalarized(args: argparse.Namespace) -> None:
    """Executes Scalarized BO campaign (weighted sum scalarization)."""
    from mobo_linac.campaigns.runner import MoboCampaignRunner

    config_path = args.config if hasattr(args, "config") and args.config else "configs/publication.yaml"
    if not Path(config_path).exists():
        config_path = "configs/mobo_200MeV.yaml"

    if getattr(args, "dry_run", False):
        print("[DRY-RUN] Scalarized BO Campaign Plan:")
        print(f"  - Config: {config_path}")
        print(f"  - Output Directory: {args.output_dir or 'results/scalarized_<timestamp>'}")
        print(f"  - Weights: {getattr(args, 'weights', [1.0, 1.0, 1.0])}")
        print(f"  - Initial Samples: {getattr(args, 'num_initial_samples', 16)}")
        print(f"  - Iterations: {getattr(args, 'n_iterations', 20)} (batch size: {getattr(args, 'batch_size', 8)})")
        return

    evaluator = (
        CliMockEvaluator(Path(args.output_dir or "results"))
        if getattr(args, "mock_evaluator", False)
        else None
    )

    runner = MoboCampaignRunner(
        config=config_path,
        run_name="scalarized",
        output_dir=getattr(args, "output_dir", None),
        num_initial_samples=getattr(args, "num_initial_samples", 16),
        num_batches=getattr(args, "n_iterations", 20),
        batch_size=getattr(args, "batch_size", 8),
        num_workers=getattr(args, "num_workers", None),
        seed=getattr(args, "seed", 42),
        optimization_mode="scalarized_bo",
        scalar_weights=getattr(args, "weights", [1.0, 1.0, 1.0]),
        export_plots=True,
        evaluator=evaluator,
        device=getattr(args, "device", "auto"),
    )
    runner.run()


def run_validation(args: argparse.Namespace) -> None:
    """Executes full reproducible validation campaign."""
    config_path = args.config if args.config else "configs/publication.yaml"
    if not Path(config_path).exists():
        config_path = "configs/mobo_200MeV.yaml"

    if getattr(args, "dry_run", False):
        print("[DRY-RUN] Validation Campaign Plan:")
        print(f"  - Config: {config_path}")
        print(f"  - Output Directory: {args.output_dir or 'results/validation_<timestamp>'}")
        return

    from scripts.run_validation_campaign import run_campaign

    run_campaign(
        config_path=config_path,
        num_initial_samples=args.num_initial_samples,
        num_batches=args.n_iterations,
        batch_size=args.batch_size,
        num_workers=args.num_workers,
        seed=args.seed,
        base_results_dir=args.output_dir or "results",
        device=getattr(args, "device", "auto"),
    )


def register_run_commands(subparsers: argparse._SubParsersAction) -> None:
    """Registers optimization execution subcommands."""
    # Subcommand: run
    run_parser = subparsers.add_parser(
        "run", help="Start a new MOBO optimization campaign (unconstrained)"
    )
    add_common_run_args(run_parser)
    run_parser.set_defaults(handler=run_unconstrained)

    # Subcommand: run-unconstrained
    run_un_parser = subparsers.add_parser(
        "run-unconstrained", help="Start an unconstrained MOBO campaign"
    )
    add_common_run_args(run_un_parser)
    run_un_parser.set_defaults(handler=run_unconstrained)

    # Subcommand: run-constrained
    run_co_parser = subparsers.add_parser(
        "run-constrained", help="Start a constraint-aware MOBO campaign"
    )
    add_common_run_args(run_co_parser)
    run_co_parser.set_defaults(handler=run_constrained)

    # Subcommand: run-scalarized
    run_sc_parser = subparsers.add_parser(
        "run-scalarized", help="Start a scalarized BO campaign"
    )
    add_common_run_args(run_sc_parser)
    run_sc_parser.add_argument(
        "--weights",
        nargs=3,
        type=float,
        default=[1.0, 1.0, 1.0],
        help="Weights for 3 objectives",
    )
    run_sc_parser.set_defaults(handler=run_scalarized)

    # Subcommand: run-validation
    run_val_parser = subparsers.add_parser(
        "run-validation", help="Run a validation campaign"
    )
    add_common_run_args(run_val_parser)
    run_val_parser.set_defaults(handler=run_validation)
