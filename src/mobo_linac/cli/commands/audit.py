"""
CLI command handlers for Pareto validation, candidate verification, and robustness auditing:
- run-robustness
- run-verification
- analyze
"""

import argparse
from pathlib import Path
import pandas as pd

from mobo_linac.cli.common import CliMockEvaluator
from mobo_linac.config import load_config
from mobo_linac.evaluation import create_evaluation_result


def analyze_run(args: argparse.Namespace) -> None:
    """Analyzes results from a completed optimization run."""
    run_dir = Path(args.run_dir)
    history_csv = run_dir / "candidate_history.csv"
    if not history_csv.exists():
        history_csv = run_dir / "evaluations.csv"
    if not history_csv.exists():
        raise FileNotFoundError(f"Candidate history / evaluations CSV not found in: {run_dir}")

    df = pd.read_csv(history_csv)
    print(f"\n--- Analysis Summary for {run_dir.name} ---")
    print(f"Total Evaluations: {len(df)}")
    print(f"Valid Simulations: {df['simulation_valid'].sum()} / {len(df)}")
    print(f"Feasible Beams: {df['physically_feasible'].sum()} / {len(df)}")

    output_dir = Path(args.output_dir) if args.output_dir else run_dir / "figures"
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Figures exported to: {output_dir.resolve()}")


def run_robustness(args: argparse.Namespace) -> None:
    """Executes robustness analysis over Pareto candidates."""
    from mobo_linac.io.results import load_evaluation_results
    from mobo_linac.robustness.workflow import run_robustness_workflow

    config = load_config(getattr(args, "config", None))

    output_dir = Path(getattr(args, "output_dir", "results/robustness"))

    input_path = getattr(args, "history_path", None) or getattr(args, "pareto_csv", None)

    results = []
    if input_path and Path(input_path).exists():
        p = Path(input_path)
        if p.is_dir():
            target = p / "candidate_history.json"
            if not target.exists():
                target = p / "candidate_history.csv"
            if not target.exists():
                target = p / "pareto.csv"
            results = load_evaluation_results(target, config=config)
        else:
            results = load_evaluation_results(p, config=config)
    else:
        results_dir = Path("results")
        cand_files = list(results_dir.glob("**/pareto.csv")) + list(results_dir.glob("**/candidate_history.json"))
        if cand_files:
            latest = max(cand_files, key=lambda f: f.stat().st_mtime)
            print(f"Loading Pareto candidates from {latest} for robustness analysis...")
            results = load_evaluation_results(latest, config=config)

    mock = CliMockEvaluator(output_dir) if getattr(args, "mock_evaluator", False) else None
    run_robustness_workflow(
        results, config, output_dir,
        num_perturbations=getattr(args, "num_perturbations", 20),
        num_workers=getattr(args, "num_workers", 4), seed=getattr(args, "seed", 42),
        dry_run=getattr(args, "dry_run", False), batch_evaluator=mock,
    )


def run_verification(args: argparse.Namespace) -> None:
    """Load measured candidates and run the configured verification service."""
    from mobo_linac.io.results import load_evaluation_results
    from mobo_linac.verification.verifier import run_verification_pipeline

    config = load_config(getattr(args, "config", None))
    output_dir = Path(getattr(args, "output_dir", "results/verification"))
    input_path = getattr(args, "history_path", None) or getattr(args, "pareto_csv", None) or getattr(args, "input", None)
    results = []
    if input_path:
        path = Path(input_path)
        if not path.exists():
            raise FileNotFoundError(f"Verification input not found: {path}")
        if path.is_dir():
            path = next((path / name for name in ("candidate_history.json", "candidate_history.csv", "pareto.csv")
                         if (path / name).is_file()), path / "candidate_history.json")
        results = load_evaluation_results(path, config=config)
    else:
        candidates = list(Path("results").glob("**/candidate_history.json")) + list(Path("results").glob("**/candidate_history.csv"))
        if candidates:
            results = load_evaluation_results(max(candidates, key=lambda path: path.stat().st_mtime), config=config)
    if getattr(args, "dry_run", False):
        print("[DRY-RUN] Pareto Verification Plan:")
        print(f"  - Input Candidates: {len(results)}")
        print(f"  - Workers: {getattr(args, 'num_workers', None) or config.execution.max_workers}")
        return
    mock = bool(getattr(args, "mock_evaluator", False))
    if not results and not mock:
        raise ValueError("Verification requires measured candidate history; no input data found")
    mock_evaluator = None
    if mock:
        evaluator = CliMockEvaluator(output_dir)
        mock_evaluator = evaluator
        if not results:
            nominal = [variable.nominal_value for variable in config.design_variables]
            results = [create_evaluation_result(evaluator(nominal, run_id="mock_nominal"), config)]
    records, manifest, table = run_verification_pipeline(
        results, config=config, output_dir=output_dir, mock_evaluator=mock_evaluator,
        num_workers=getattr(args, "num_workers", None), timeout=getattr(args, "timeout", None),
        template_dir=getattr(args, "template_dir", "."), template_in=getattr(args, "template_in", "astra.in"))
    print(f"Verification produced {len(records)} audit records: {manifest}")


def register_audit_commands(subparsers: argparse._SubParsersAction) -> None:
    """Registers audit, analysis, robustness, and verification subcommands."""
    # Subcommand: analyze
    analyze_parser = subparsers.add_parser("analyze", help="Analyze results from a completed optimization run")
    analyze_parser.add_argument("--run-dir", type=str, required=True, help="Path to run directory")
    analyze_parser.add_argument("--output-dir", type=str, default=None, help="Output directory for figures")
    analyze_parser.set_defaults(handler=analyze_run)

    # Subcommand: run-robustness
    run_rob_parser = subparsers.add_parser(
        "run-robustness", help="Perform robustness and sensitivity analysis over Pareto candidates"
    )
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
        "--num-workers", type=int, default=4, help="Number of parallel worker processes"
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
    run_ver_parser.add_argument("--template-dir", default=".", help="ASTRA template and static input directory")
    run_ver_parser.add_argument("--template-in", default="astra.in", help="ASTRA input template filename")
    run_ver_parser.set_defaults(handler=run_verification)

    # Subcommand: validate-config
    val_cfg_parser = subparsers.add_parser(
        "validate-config", help="Validate YAML/JSON configuration files and export schema/docs"
    )
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
        p = cfg.resolved_path
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
        print(f"✓ JSON Schema exported to: {args.export_schema}")

    if getattr(args, "export_docs", None):
        docs_str = generate_config_markdown_docs(cfg)
        out_docs = Path(args.export_docs)
        out_docs.parent.mkdir(parents=True, exist_ok=True)
        out_docs.write_text(docs_str, encoding="utf-8")
        print(f"✓ Markdown documentation exported to: {out_docs}")

