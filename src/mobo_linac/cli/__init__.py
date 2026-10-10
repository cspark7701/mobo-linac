"""
Command Line Interface (CLI) Package for mobo_linac.

Provides console commands:
    mobo-linac run-unconstrained --config configs/publication_200MeV.yaml
    mobo-linac run-constrained --config configs/publication_200MeV.yaml
    mobo-linac run-scalarized --config configs/publication_200MeV.yaml
    mobo-linac run-validation --config configs/publication_200MeV.yaml
    mobo-linac resume --run-dir results/<run_id>
    mobo-linac analyze --run-dir results/<run_id>
    mobo-linac run-benchmark --config configs/publication_200MeV.yaml
    mobo-linac analyze-benchmark --output-dir results/publication_benchmark
    mobo-linac run-robustness --input results/<run_id>
    mobo-linac run-verification --input results/<run_id>
    mobo-linac compare --phase2-dir <run> --phase3-dir <run> --output-dir <analysis>
    mobo-linac paper-figures --phase2-dir <run> --phase3-dir <run>
"""

import argparse
from typing import Optional, Sequence

from mobo_linac import __version__
from mobo_linac.cli.commands.audit import (
    analyze_run,
    register_audit_commands,
    run_robustness,
    run_verification,
    validate_config,
)
from mobo_linac.cli.commands.benchmark import (
    analyze_benchmark,
    register_benchmark_commands,
    run_benchmark,
)
from mobo_linac.cli.commands.reports import register_report_commands
from mobo_linac.cli.commands.resume import (
    register_resume_command,
    resume_optimization,
)
from mobo_linac.cli.commands.run import (
    register_run_commands,
    run_constrained,
    run_scalarized,
    run_scalarized_suite_cmd,
    run_unconstrained,
    run_validation,
)


def build_parser() -> argparse.ArgumentParser:
    """Constructs the master argument parser with all registered subcommands."""
    parser = argparse.ArgumentParser(
        prog="mobo-linac",
        description="Multi-Objective Bayesian Optimization framework for 200 MeV Electron Injector Linac",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Register subcommand groups
    register_run_commands(subparsers)
    register_resume_command(subparsers)
    register_benchmark_commands(subparsers)
    register_audit_commands(subparsers)
    register_report_commands(subparsers)

    return parser


def main(args: Optional[Sequence[str]] = None) -> Optional[int]:
    """Main CLI entry point; returns the subcommand's exit code (``None`` means success)."""
    parser = build_parser()
    parsed_args = parser.parse_args(args)

    from mobo_linac.utils.logger import configure_logging

    quiet = getattr(parsed_args, "quiet", False)
    verbose = getattr(parsed_args, "verbose", False)
    debug = getattr(parsed_args, "debug", False)
    configure_logging(quiet=quiet, verbose=verbose, debug=debug)

    return parsed_args.handler(parsed_args)


if __name__ == "__main__":
    main()
