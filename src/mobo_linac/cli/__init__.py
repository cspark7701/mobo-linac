"""
Command Line Interface (CLI) Package for mobo_linac.

Provides console commands:
    mobo-linac run-unconstrained --config configs/publication.yaml
    mobo-linac run-constrained --config configs/publication.yaml
    mobo-linac run-scalarized --config configs/publication.yaml
    mobo-linac run-validation --config configs/publication.yaml
    mobo-linac resume --run-dir results/<run_id>
    mobo-linac analyze --run-dir results/<run_id>
    mobo-linac run-benchmark --config configs/publication_200MeV.yaml
    mobo-linac analyze-benchmark --output-dir results/publication_benchmark
    mobo-linac run-robustness --input results/<run_id>
    mobo-linac run-verification --input results/<run_id>
"""

import argparse
from typing import Optional, Sequence

from mobo_linac import __version__
from mobo_linac.cli.commands.audit import (
    analyze_run,
    register_audit_commands,
    run_robustness,
    run_verification,
)
from mobo_linac.cli.commands.benchmark import (
    analyze_benchmark,
    register_benchmark_commands,
    run_benchmark,
)
from mobo_linac.cli.commands.resume import (
    register_resume_command,
    resume_optimization,
)
from mobo_linac.cli.commands.run import (
    register_run_commands,
    run_constrained,
    run_scalarized,
    run_unconstrained,
    run_validation,
)
from mobo_linac.cli.common import CliMockEvaluator


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

    return parser


def main(args: Optional[Sequence[str]] = None) -> None:
    """Main CLI entry point."""
    parser = build_parser()
    parsed_args = parser.parse_args(args)

    if hasattr(parsed_args, "handler") and callable(parsed_args.handler):
        parsed_args.handler(parsed_args)
    else:
        # Fallback manual dispatch if handler attribute is missing
        dispatch_table = {
            "run": run_unconstrained,
            "run-unconstrained": run_unconstrained,
            "run-constrained": run_constrained,
            "run-scalarized": run_scalarized,
            "run-validation": run_validation,
            "resume": resume_optimization,
            "analyze": analyze_run,
            "run-benchmark": run_benchmark,
            "analyze-benchmark": analyze_benchmark,
            "run-robustness": run_robustness,
            "run-verification": run_verification,
        }
        cmd = getattr(parsed_args, "command", None)
        if cmd in dispatch_table:
            dispatch_table[cmd](parsed_args)
        else:
            parser.print_help()


if __name__ == "__main__":
    main()
