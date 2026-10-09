"""
CLI command handlers for starting new optimization campaigns:
- run / run-unconstrained
- run-constrained
- run-scalarized / run-scalarized-suite
- run-validation

Omitted options take the configuration's ``campaign`` defaults (workers:
``execution.max_workers``), the single default source for every entry point.
"""

import argparse
import math
from pathlib import Path

from mobo_linac.campaign_options import normalize_scalar_weights, resolve_campaign_options, validate_campaign_options
from mobo_linac.config import load_config
from mobo_linac.cli.common import MockEvaluator, add_common_run_args

MODES = {
    "unconstrained": ("unconstrained_mobo", "Unconstrained MOBO"),
    "constrained": ("constrained_mobo", "Constrained MOBO"),
    "scalarized": ("scalarized_bo", "Scalarized BO"),
    "validation": ("unconstrained_mobo", "Validation"),
}


def resolve_plan(args, optimization_mode="unconstrained_mobo"):
    """Load the configuration and resolve every campaign option before any side effect."""
    config = load_config(getattr(args, "config", None))
    options = resolve_campaign_options(
        config, num_initial_samples=getattr(args, "num_initial_samples", None),
        num_batches=getattr(args, "n_iterations", None), batch_size=getattr(args, "batch_size", None),
        seed=getattr(args, "seed", None), acquisition=getattr(args, "acquisition", None),
        num_workers=getattr(args, "num_workers", None))
    if optimization_mode == "scalarized_bo" and getattr(args, "acquisition", None) is None:
        options["acquisition"] = "qLogNEI"
    validate_campaign_options(num_initial_samples=options["num_initial_samples"], num_batches=options["num_batches"],
                              batch_size=options["batch_size"], num_workers=options["num_workers"],
                              seed=options["seed"], acq_type=options["acquisition"], optimization_mode=optimization_mode)
    reference = getattr(args, "reporting_ref_point", None)
    if reference is not None and (len(reference) != len(config.objectives)
                                  or not all(math.isfinite(value) for value in reference)):
        raise ValueError("Reporting reference must match finite configured objectives.")
    return config, options


def _print_plan(title, config, options, output_dir, extra=()):
    print(f"[DRY-RUN] {title} Campaign Plan:")
    print(f"  - Config: {config.source_path}")
    print(f"  - Output Directory: {output_dir}")
    print(f"  - Initial Samples: {options['num_initial_samples']}")
    print(f"  - Iterations: {options['num_batches']} (batch size: {options['batch_size']})")
    print(f"  - Workers: {options['num_workers']}; seed: {options['seed']}; acquisition: {options['acquisition']}")
    for line in extra:
        print(f"  - {line}")


def _mock(args, directory, config):
    return MockEvaluator(Path(directory), config=config) if getattr(args, "mock_evaluator", False) else None


def run_campaign_command(args: argparse.Namespace, kind: str) -> None:
    """Shared handler for unconstrained, constrained and single-case scalarized campaigns."""
    from mobo_linac.campaigns.runner import MoboCampaignRunner

    mode, title = MODES[kind]
    config, options = resolve_plan(args, mode)
    weights, case = None, getattr(args, "case", None)
    if kind == "scalarized":
        from mobo_linac.campaigns.scalarized_suite import get_scalarized_case
        weights = get_scalarized_case(config, case).weights if case else getattr(args, "weights", None)
        normalize_scalar_weights(weights, len(config.objectives))
    run_name = f"scalarized_{case}" if case else kind
    if getattr(args, "dry_run", False):
        _print_plan(title, config, options, args.output_dir or f"results/{run_name}_<timestamp>",
                    [f"Case: {case or 'custom'}; weights: {weights}"] if kind == "scalarized" else ())
        return
    MoboCampaignRunner(
        config=config, run_name=run_name, output_dir=getattr(args, "output_dir", None),
        num_initial_samples=options["num_initial_samples"], num_batches=options["num_batches"],
        batch_size=options["batch_size"], num_workers=options["num_workers"], seed=options["seed"],
        acq_type=options["acquisition"], optimization_mode=mode, scalar_weights=weights,
        resume=getattr(args, "resume", False), export_plots=True,
        evaluator=_mock(args, args.output_dir or "results", config),
        reporting_ref_point=getattr(args, "reporting_ref_point", None), device=getattr(args, "device", "auto"),
    ).run()


def run_unconstrained(args: argparse.Namespace) -> None:
    """Executes a Phase 2 unconstrained MOBO campaign."""
    run_campaign_command(args, "unconstrained")


def run_constrained(args: argparse.Namespace) -> None:
    """Executes a Phase 3 constrained MOBO campaign."""
    run_campaign_command(args, "constrained")


def run_scalarized(args: argparse.Namespace) -> None:
    """Executes a single scalarized campaign, or the configured suite with --suite/--case all."""
    if getattr(args, "suite", None) == "option2" or getattr(args, "case", None) == "all":
        return run_scalarized_suite_cmd(args)
    run_campaign_command(args, "scalarized")


def run_scalarized_suite_cmd(args: argparse.Namespace) -> None:
    """Executes the configured Phase 1 multi-case scalarized suite."""
    from mobo_linac.campaigns.scalarized_suite import get_scalarized_case, run_scalarized_suite

    config, options = resolve_plan(args, "scalarized_bo")
    cases = getattr(args, "cases", None)
    if cases and "all" in cases:
        cases = None
    if cases is None and getattr(args, "case", None) not in [None, "all"]:
        cases = [args.case]
    for case in (cases or config.scalarized_cases):
        get_scalarized_case(config, case)
    output_dir = getattr(args, "output_dir", None) or "results/full_production/phase1_scalarized"
    if getattr(args, "dry_run", False):
        _print_plan("Scalarized Suite", config, options, output_dir, [f"Cases: {cases or list(config.scalarized_cases)}"])
        return
    run_scalarized_suite(
        config=config, n_iterations=options["num_batches"], batch_size=options["batch_size"],
        num_initial_samples=options["num_initial_samples"], num_workers=options["num_workers"],
        seed=options["seed"], output_dir=output_dir, device=getattr(args, "device", "auto"),
        cases_to_run=cases, resume=getattr(args, "resume", False), evaluator=_mock(args, output_dir, config),
        reporting_ref_point=getattr(args, "reporting_ref_point", None),
    )


def run_validation(args: argparse.Namespace) -> None:
    """Executes a reproducible validation campaign under ``<output-dir>/validation_<timestamp>``."""
    from mobo_linac.campaigns.validation import run_validation_campaign

    config, options = resolve_plan(args)
    base = args.output_dir or "results"
    if getattr(args, "dry_run", False):
        _print_plan("Validation", config, options, f"{base}/validation_<timestamp>")
        return
    run_validation_campaign(config, options, base_results_dir=base, device=getattr(args, "device", "auto"),
                            evaluator=_mock(args, base, config))


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
        "run-scalarized", help="Start a scalarized BO campaign or Option 2 suite"
    )
    add_common_run_args(run_sc_parser)
    run_sc_parser.add_argument(
        "--weights",
        nargs="+",
        type=float,
        default=None,
        help="Nonnegative weights in configured objective order (default: equal weights)",
    )
    run_sc_parser.add_argument(
        "--suite",
        type=str,
        default=None,
        choices=["option2", "custom"],
        help="Predefined multi-case suite to run (e.g. 'option2')",
    )
    run_sc_parser.add_argument(
        "--case",
        type=str,
        default=None,
        help="Configured scalarized case id ('all' runs every configured case)",
    )
    run_sc_parser.set_defaults(handler=run_scalarized)

    # Subcommand: run-scalarized-suite
    run_sc_suite_parser = subparsers.add_parser(
        "run-scalarized-suite", help="Start the Option 2 Phase 1 multi-case Scalarized BO suite"
    )
    add_common_run_args(run_sc_suite_parser)
    run_sc_suite_parser.add_argument(
        "--cases",
        nargs="*",
        default=None,
        help="Subset of configured scalarized cases to run (default: all)",
    )
    run_sc_suite_parser.set_defaults(handler=run_scalarized_suite_cmd)

    # Subcommand: run-validation
    run_val_parser = subparsers.add_parser(
        "run-validation", help="Run a validation campaign"
    )
    add_common_run_args(run_val_parser)
    run_val_parser.set_defaults(handler=run_validation)
