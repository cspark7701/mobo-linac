"""
CLI command handlers for cross-campaign reports:
- compare: phase comparison report with audited verification of the last phase
- paper-figures: manuscript figures and LaTeX tables from recorded runs
"""

import argparse
from pathlib import Path

from mobo_linac.cli.common import MockEvaluator, add_verbosity_args
from mobo_linac.utils.logger import get_logger

logger = get_logger(__name__)


def compare_phases(args: argparse.Namespace) -> int:
    """Compare recorded phases and write ``comparison_report.md`` under ``--output-dir``."""
    from mobo_linac.config import load_config
    from mobo_linac.reporting.comparison import run_phase_comparison
    config = load_config(args.config)
    phases = [Path(path) for path in (args.phase1_dir, args.phase2_dir, args.phase3_dir) if path is not None]
    evaluator = MockEvaluator(Path(args.output_dir), config=config) if args.mock_evaluator else None
    run_phase_comparison(phases, args.output_dir, config, num_workers=args.num_workers, evaluator=evaluator)
    return 0


def paper_figures(args: argparse.Namespace) -> int:
    """Generate (or only check) the manuscript figures and tables; returns a process exit code."""
    from mobo_linac.reporting.paper import check_manuscript_consistency, generate_paper_artifacts
    for path, flag in ((args.phase1_dir, "--phase1-dir"), (args.phase2_dir, "--phase2-dir"), (args.phase3_dir, "--phase3-dir")):
        if path is not None and not path.is_dir():
            logger.error(f"{flag} directory does not exist: {path}")
            return 1
    if args.check_only:
        ok = check_manuscript_consistency(args.phase2_dir, args.phase3_dir, args.output_dir, args.tables_dir,
                                          args.verification_csv, phase1_dir=args.phase1_dir)
        return 0 if ok else 1
    stats = generate_paper_artifacts(args.phase2_dir, args.phase3_dir, args.verification_csv, args.output_dir,
                                     args.tables_dir, phase1_dir=args.phase1_dir)
    for key, value in stats.items():
        logger.info(f"{key}: {value:.6f}")
    return 0


def register_report_commands(subparsers: argparse._SubParsersAction) -> None:
    compare = subparsers.add_parser("compare", help="Compare recorded campaign phases and verify the last one")
    add_verbosity_args(compare)
    compare.add_argument("--config", type=str, default=None, help="Path to config file")
    compare.add_argument("--phase1-dir", type=str, default=None, help="Phase 1 run directory (optional)")
    compare.add_argument("--phase2-dir", type=str, required=True, help="Phase 2 run directory")
    compare.add_argument("--phase3-dir", type=str, required=True, help="Phase 3 run directory")
    compare.add_argument("--output-dir", type=str, required=True, help="Analysis output directory")
    compare.add_argument("--num-workers", type=int, default=None, help="Verification workers (default: configuration)")
    compare.add_argument("--mock-evaluator", action="store_true", help="Verify with the mock evaluator")
    compare.set_defaults(handler=compare_phases)

    paper = subparsers.add_parser("paper-figures", help="Generate manuscript figures and LaTeX tables from runs")
    add_verbosity_args(paper)
    paper.add_argument("--phase1-dir", type=Path, default=None, help="Phase 1 (scalarized) run directory")
    paper.add_argument("--phase2-dir", type=Path, required=True, help="Phase 2 (unconstrained) run directory")
    paper.add_argument("--phase3-dir", type=Path, required=True, help="Phase 3 (constrained) run directory")
    paper.add_argument("--verification-csv", type=Path, default=Path("results/verification/verification_summary.csv"),
                       help="verification_summary.csv of the audited reruns")
    paper.add_argument("--output-dir", type=Path, default=Path("docs/paper/figures"), help="Figure output directory")
    paper.add_argument("--tables-dir", type=Path, default=Path("docs/paper"), help="LaTeX table output directory")
    paper.add_argument("--check-only", action="store_true", help="Only run the manuscript consistency check")
    paper.set_defaults(handler=paper_figures)
