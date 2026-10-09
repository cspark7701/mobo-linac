"""
CLI command handlers for Pareto validation, candidate verification, and robustness auditing:
- run-robustness
- run-verification
- analyze
"""

import argparse
from pathlib import Path

from mobo_linac.utils.logger import get_logger
from mobo_linac.cli.common import add_verbosity_args
from mobo_linac.cli.common import MockEvaluator
from mobo_linac.config import load_config
from mobo_linac.evaluation import create_evaluation_result

logger = get_logger(__name__)


def analyze_run(args: argparse.Namespace) -> None:
    """Summarize a recorded run and export its standard figures."""
    from mobo_linac.io.run_data import read_run_data
    from mobo_linac.plotting import (plot_constraint_diagnostics, plot_hypervolume_progress,
                                     plot_objective_evolution, plot_pareto_front)
    from mobo_linac.plotting.common import figure_scope

    run_dir = Path(args.run_dir)
    run = read_run_data(run_dir)
    results = run.results
    logger.info(f"--- Analysis Summary for {run_dir.name} ---")
    logger.info(f"Total Evaluations: {len(results)}")
    logger.info(f"Valid Simulations: {sum(r.simulation_valid is True for r in results)} / {len(results)}")
    logger.info(f"Feasible Beams: {sum(r.physically_feasible is True for r in results)} / {len(results)}")

    output_dir = Path(args.output_dir) if args.output_dir else run_dir / "figures"
    output_dir.mkdir(parents=True, exist_ok=True)
    with figure_scope():
        plot_hypervolume_progress(run.hypervolume, output_dir / "hypervolume_progress.png")
        plot_pareto_front(results, output_dir / "pareto_front.png", config=run.config)
        plot_objective_evolution(results, output_dir / "objective_evolution.png", config=run.config)
        plot_constraint_diagnostics(results, run.config, output_dir / "constraint_diagnostics.png")
    logger.info(f"Figures exported to: {output_dir.resolve()}")


def run_robustness(args: argparse.Namespace) -> None:
    """Executes robustness analysis over Pareto candidates."""
    from mobo_linac.io.run_data import load_candidates
    from mobo_linac.robustness.workflow import run_robustness_workflow

    config = load_config(getattr(args, "config", None))

    output_dir = Path(getattr(args, "output_dir", "results/robustness"))

    input_path = getattr(args, "history_path", None) or getattr(args, "pareto_csv", None)

    results = load_candidates(input_path, config=config)

    mock = MockEvaluator(output_dir, config=config) if getattr(args, "mock_evaluator", False) else None
    run_robustness_workflow(
        results, config, output_dir,
        num_perturbations=getattr(args, "num_perturbations", 20),
        num_workers=getattr(args, "num_workers", None) or config.execution.max_workers, seed=getattr(args, "seed", 42),
        dry_run=getattr(args, "dry_run", False), evaluator=mock,
    )


def run_verification(args: argparse.Namespace) -> None:
    """Load measured candidates and run the configured verification service."""
    from mobo_linac.io.run_data import load_candidates
    from mobo_linac.verification.verifier import run_verification_pipeline

    config = load_config(getattr(args, "config", None))
    output_dir = Path(getattr(args, "output_dir", "results/verification"))
    input_path = getattr(args, "history_path", None) or getattr(args, "pareto_csv", None) or getattr(args, "input", None)
    results = load_candidates(input_path, config=config)
    if getattr(args, "dry_run", False):
        print("[DRY-RUN] Pareto Verification Plan:")
        print(f"  - Input Candidates: {len(results)}")
        print(f"  - Workers: {getattr(args, 'num_workers', None) or config.execution.max_workers}")
        return
    mock = bool(getattr(args, "mock_evaluator", False))
    if not results and not mock:
        raise ValueError("Verification requires measured candidate history; no input data found")
    evaluator = None
    if mock:
        evaluator = MockEvaluator(output_dir, config=config)
        if not results:
            nominal = [variable.nominal_value for variable in config.design_variables]
            results = [create_evaluation_result(evaluator.respond(nominal, run_id="mock_nominal"), config)]
    records, manifest, table = run_verification_pipeline(
        results, config=config, output_dir=output_dir, evaluator=evaluator,
        num_workers=getattr(args, "num_workers", None), timeout=getattr(args, "timeout", None),
        template_dir=getattr(args, "template_dir", None))
    logger.info(f"Verification produced {len(records)} audit records: {manifest}")


def register_audit_commands(subparsers: argparse._SubParsersAction) -> None:
    """Registers audit, analysis, robustness, and verification subcommands."""
    # Subcommand: analyze
    analyze_parser = subparsers.add_parser("analyze", help="Analyze results from a completed optimization run")
    add_verbosity_args(analyze_parser)
    analyze_parser.add_argument("--run-dir", type=str, required=True, help="Path to run directory")
    analyze_parser.add_argument("--output-dir", type=str, default=None, help="Output directory for figures")
    analyze_parser.set_defaults(handler=analyze_run)

    # Subcommand: run-robustness
    run_rob_parser = subparsers.add_parser(
        "run-robustness", help="Perform robustness and sensitivity analysis over Pareto candidates"
    )
    add_verbosity_args(run_rob_parser)
    run_rob_parser.add_argument(
        "--config", type=str, default=None, help="Path to config file"
    )
    run_rob_parser.add_argument(
        "--input", "--history-path", dest="history_path", type=str, default=None, help="Path to Pareto candidates CSV/JSON"
    )
    run_rob_parser.add_argument(
        "--pareto-csv", type=str, default=None, help="Path to pareto.csv file"
    )
    run_rob_parser.add_argument(
        "--output-dir", type=str, default="results/robustness", help="Output directory"
    )
    run_rob_parser.add_argument(
        "--num-perturbations", type=int, default=20, help="Number of perturbations per candidate"
    )
    run_rob_parser.add_argument(
        "--num-workers", type=int, default=None, help="Parallel worker processes (default: config execution.max_workers)"
    )
    run_rob_parser.add_argument(
        "--seed", type=int, default=42, help="Random seed"
    )
    run_rob_parser.add_argument(
        "--dry-run", action="store_true", help="Print planned robustness plan"
    )
    run_rob_parser.add_argument(
        "--mock-evaluator", action="store_true", help="Use mock evaluator for testing"
    )
    run_rob_parser.set_defaults(handler=run_robustness)

    # Subcommand: run-verification
    run_ver_parser = subparsers.add_parser(
        "run-verification", help="Rerun Pareto candidates independently for verification"
    )
    add_verbosity_args(run_ver_parser)
    run_ver_parser.add_argument(
        "--config", type=str, default=None, help="Path to config file"
    )
    run_ver_parser.add_argument(
        "--input", "--history-path", dest="history_path", type=str, default=None, help="Path to Pareto candidates CSV/JSON"
    )
    run_ver_parser.add_argument(
        "--pareto-csv", type=str, default=None, help="Path to pareto.csv file"
    )
    run_ver_parser.add_argument(
        "--output-dir", type=str, default="results/verification", help="Output directory"
    )
    run_ver_parser.add_argument(
        "--dry-run", action="store_true", help="Print planned verification plan"
    )
    run_ver_parser.add_argument(
        "--mock-evaluator", action="store_true", help="Use mock evaluator for testing"
    )
    run_ver_parser.add_argument("--num-workers", type=int, default=None, help="Override configured worker count")
    run_ver_parser.add_argument("--timeout", type=int, default=None, help="Override configured timeout in seconds")
    run_ver_parser.add_argument("--template-dir", default=None, help="ASTRA template and static input directory (default: config execution.template_dir)")
    run_ver_parser.set_defaults(handler=run_verification)

    # Subcommand: validate-config
    val_cfg_parser = subparsers.add_parser(
        "validate-config", help="Validate YAML/JSON configuration files and export schema/docs"
    )
    add_verbosity_args(val_cfg_parser)
    val_cfg_parser.add_argument(
        "--config", type=str, default=None, help="Path to configuration file to validate"
    )
    val_cfg_parser.add_argument(
        "--export-schema", type=str, default=None, help="Export JSON Schema to file path"
    )
    val_cfg_parser.add_argument(
        "--export-docs", type=str, default=None, help="Export Markdown documentation to file path"
    )
    val_cfg_parser.set_defaults(handler=validate_config)


def validate_config(args: argparse.Namespace) -> None:
    """Validates YAML/JSON configuration files and optionally exports docs/schema."""
    import sys
    from mobo_linac.config import export_config_schema, generate_config_markdown_docs, load_config

    p = getattr(args, "config", None)
    try:
        cfg = load_config(p)
        p = cfg.source_path
        print(f"  - Config: {p}")
        print(f"✓ Configuration '{cfg.name}' (v{cfg.version}) is VALID.")
        print(f"  - Design Variables: {len(cfg.design_variables)}")
        print(f"  - Objectives: {len(cfg.objectives)}")
        print(f"  - Max Workers: {cfg.execution.max_workers}")
        print(f"  - Constraints: {cfg.constraints.min_mean_kinetic_energy_eV*1e-6:.1f} - {cfg.constraints.max_mean_kinetic_energy_eV*1e-6:.1f} MeV")
    except Exception as e:
        print(f"✗ Validation FAILED for '{p}': {e}")
        sys.exit(1)

    if getattr(args, "export_schema", None):
        export_config_schema(args.export_schema)
        logger.info(f"✓ JSON Schema exported to: {args.export_schema}")

    if getattr(args, "export_docs", None):
        docs_str = generate_config_markdown_docs(cfg)
        from mobo_linac.utils.durable import atomic_write_text
        out_docs = atomic_write_text(args.export_docs, docs_str)
        logger.info(f"✓ Markdown documentation exported to: {out_docs}")

