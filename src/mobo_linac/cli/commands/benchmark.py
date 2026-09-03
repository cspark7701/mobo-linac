"""
CLI command handlers for multi-algorithm benchmarking:
- run-benchmark
- analyze-benchmark
"""

import argparse
from pathlib import Path

from mobo_linac.cli.common import CliMockEvaluator
from mobo_linac.config import load_config


def run_benchmark(args: argparse.Namespace) -> None:
    """Executes multi-seed paired benchmark campaigns."""
    from mobo_linac.campaigns.benchmark import BenchmarkCampaignRunner

    config = load_config(args.config)
    runner = BenchmarkCampaignRunner(
        config=config,
        output_dir=args.output_dir,
        algorithms=getattr(args, "algorithms", None),
        seeds=args.seeds,
        total_eval_budget=args.budget,
        n_sobol_init=getattr(args, "n_sobol_init", 10),
        batch_size=getattr(args, "batch_size", 4),
        device=getattr(args, "device", "auto"),
    )
    mock_eval = (
        CliMockEvaluator(Path(args.output_dir))
        if getattr(args, "mock_evaluator", False)
        else None
    )
    runner.execute_benchmark_campaigns(dry_run=args.dry_run, mock_evaluator=mock_eval)


def analyze_benchmark(args: argparse.Namespace) -> None:
    """Aggregates and analyzes completed benchmark campaigns."""
    from mobo_linac.campaigns.benchmark import BenchmarkCampaignRunner

    config = load_config("configs/publication_200MeV.yaml")
    runner = BenchmarkCampaignRunner(config=config, output_dir=args.output_dir)
    agg_df, summary_df = runner.analyze_completed_results()
    print(f"Benchmark analysis complete. Aggregate metrics saved in {args.output_dir}")


def register_benchmark_commands(subparsers: argparse._SubParsersAction) -> None:
    """Registers benchmark subcommands."""
    # Subcommand: run-benchmark
    run_bm_parser = subparsers.add_parser(
        "run-benchmark", help="Run a paired multi-seed benchmark campaign"
    )
    run_bm_parser.add_argument(
        "--config", type=str, default="configs/publication_200MeV.yaml", help="Path to config file"
    )
    run_bm_parser.add_argument(
        "--output-dir", type=str, default="results/publication_benchmark", help="Output directory"
    )
    run_bm_parser.add_argument(
        "--algorithms", nargs="+", type=str, default=None, help="Algorithms to benchmark (space-separated)"
    )
    run_bm_parser.add_argument(
        "--seeds", nargs="+", type=int, default=list(range(42, 52)), help="List of random seeds"
    )
    run_bm_parser.add_argument(
        "--budget", type=int, default=40, help="Total evaluation budget per algorithm-seed pair"
    )
    run_bm_parser.add_argument(
        "--n-sobol-init", type=int, default=10, help="Number of initial Sobol samples"
    )
    run_bm_parser.add_argument(
        "-b", "-q", "--batch-size", "--batch_size",
        dest="batch_size",
        type=int,
        default=4,
        help="BO batch size per iteration",
    )
    run_bm_parser.add_argument(
        "--num-workers", type=int, default=4, help="Number of parallel worker processes"
    )
    run_bm_parser.add_argument(
        "--device", type=str, default="auto", help="Target PyTorch compute device ('auto', 'cuda', 'cuda:0', 'cpu')"
    )
    run_bm_parser.add_argument(
        "--dry-run", action="store_true", help="Print planned benchmark plan"
    )
    run_bm_parser.add_argument(
        "--mock-evaluator", action="store_true", help="Use mock evaluator for testing"
    )
    run_bm_parser.set_defaults(handler=run_benchmark)

    # Subcommand: analyze-benchmark
    analyze_bm_parser = subparsers.add_parser(
        "analyze-benchmark", help="Aggregate and analyze completed benchmark campaign results"
    )
    analyze_bm_parser.add_argument(
        "--output-dir", type=str, default="results/publication_benchmark", help="Benchmark campaign directory"
    )
    analyze_bm_parser.set_defaults(handler=analyze_benchmark)
