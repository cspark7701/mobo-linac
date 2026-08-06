"""
Statistically Rigorous Benchmark Campaign Orchestrator for Linac MOBO (Task 09).

Executes multi-seed, multi-algorithm benchmark comparisons with seed-paired initial
Sobol sampling, equal evaluation budgets, checkpoint resume capabilities, and
publication-ready aggregate metrics and plots.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import numpy as np
import pandas as pd
import torch
from torch.quasirandom import SobolEngine

from mobo_linac.config import BenchmarkConfig, MoboConfig, load_config
from mobo_linac.evaluation import EvaluationResult, create_evaluation_result
from mobo_linac.io.results import load_run_checkpoint, save_evaluation_results, save_run_checkpoint
from mobo_linac.metrics.reporting import (
    DEFAULT_REPORTING_REF_POINT_MODEL_NORM,
    compute_campaign_metrics_history,
)
from mobo_linac.campaigns.analysis import compute_aggregate_benchmark_metrics

SUPPORTED_BENCHMARK_ALGORITHMS = [
    "constrained_qlognehvi",
    "unconstrained_qlognehvi",
    "qlogehvi",
    "scalarized_bo",
    "nsga2",
    "sobol",
]


def generate_seed_paired_sobol_samples(
    n_samples: int,
    seed: int,
    bounds: torch.Tensor,
) -> torch.Tensor:
    """
    Generates deterministic, seed-paired initial Sobol design points within bounds.

    All algorithms sharing the same seed receive the same initial Sobol design,
    enforcing fair, seed-paired benchmark comparisons.

    Args:
        n_samples: Number of initial Sobol samples to generate.
        seed: Random seed.
        bounds: (2, D) PyTorch double tensor of design variable bounds.

    Returns:
        (n_samples, D) PyTorch double tensor of design variable parameters.
    """
    dim = bounds.shape[1]
    sobol = SobolEngine(dimension=dim, scramble=True, seed=seed)
    unit_samples = sobol.draw(n_samples).to(dtype=torch.double)
    lower = bounds[0]
    upper = bounds[1]
    scaled_samples = lower + (upper - lower) * unit_samples
    return scaled_samples


class BenchmarkCampaignRunner:
    """
    Orchestrates paired multi-seed benchmark optimization campaigns across algorithms.

    Enforces equal total ASTRA evaluation budgets across all algorithms within each seed.
    All algorithms within the same seed receive the same initial Sobol design.
    """

    def __init__(
        self,
        config: MoboConfig,
        output_dir: Union[str, Path] = "results/publication_benchmark",
        algorithms: Optional[List[str]] = None,
        seeds: Optional[List[int]] = None,
        total_eval_budget: int = 40,
        n_sobol_init: int = 10,
        batch_size: int = 4,
        benchmark_config: Optional[BenchmarkConfig] = None,
    ):
        self.config = config

        # If BenchmarkConfig provided, it takes precedence over individual args
        if benchmark_config is not None:
            benchmark_config.validate()
            self.output_dir = Path(benchmark_config.output_dir)
            self.algorithms = benchmark_config.algorithms
            self.seeds = benchmark_config.seeds
            self.total_eval_budget = benchmark_config.total_eval_budget
            self.n_sobol_init = benchmark_config.n_sobol_init
            self.batch_size = benchmark_config.batch_size
            self.benchmark_config = benchmark_config
        else:
            self.output_dir = Path(output_dir)
            self.algorithms = algorithms or SUPPORTED_BENCHMARK_ALGORITHMS
            self.seeds = seeds or list(range(42, 52))
            self.total_eval_budget = total_eval_budget
            self.n_sobol_init = n_sobol_init
            self.batch_size = batch_size
            self.benchmark_config = BenchmarkConfig(
                algorithms=self.algorithms,
                seeds=self.seeds,
                total_eval_budget=self.total_eval_budget,
                n_sobol_init=self.n_sobol_init,
                batch_size=self.batch_size,
            )

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_rows: List[Dict[str, Any]] = []

        # Validate budget
        n_batches = (self.total_eval_budget - self.n_sobol_init) // self.batch_size
        if n_batches < 1:
            raise ValueError(
                f"total_eval_budget ({self.total_eval_budget}) - n_sobol_init ({self.n_sobol_init}) "
                f"must be >= batch_size ({self.batch_size})."
            )

    @property
    def n_batches(self) -> int:
        return max(1, (self.total_eval_budget - self.n_sobol_init) // self.batch_size)

    def get_run_dir(self, algorithm: str, seed: int) -> Path:
        """Returns isolated run directory for algorithm and seed."""
        return self.output_dir / "per_seed" / f"{algorithm}_seed_{seed}"

    def run_campaign_manifest(self) -> pd.DataFrame:
        """Generates campaign manifest DataFrame."""
        self.manifest_rows = []
        for algo in self.algorithms:
            for s in self.seeds:
                run_path = self.get_run_dir(algo, s)
                completed = (run_path / "candidate_history.csv").exists()
                effective_budget = self.n_sobol_init + self.n_batches * self.batch_size
                self.manifest_rows.append({
                    "algorithm": algo,
                    "seed": s,
                    "budget": effective_budget,
                    "n_sobol_init": self.n_sobol_init,
                    "n_batches": self.n_batches,
                    "batch_size": self.batch_size,
                    "run_dir": str(run_path),
                    "status": "completed" if completed else "pending",
                })
        manifest_df = pd.DataFrame(self.manifest_rows)
        manifest_df.to_csv(self.output_dir / "campaign_manifest.csv", index=False)
        return manifest_df

    def analyze_completed_results(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Analyzes all completed seed results and exports aggregate metrics and summary tables.
        Also generates publication-ready comparison plots.

        Returns:
            Tuple of (aggregate_series_df, summary_df).
        """
        from mobo_linac.plotting.visualizations import (
            plot_benchmark_comparison,
            plot_benchmark_feasibility_comparison,
        )

        seed_histories: Dict[str, Dict[int, pd.DataFrame]] = {algo: {} for algo in self.algorithms}

        for algo in self.algorithms:
            for s in self.seeds:
                run_path = self.get_run_dir(algo, s)
                history_csv = run_path / "metrics_history.csv"
                if history_csv.exists():
                    seed_histories[algo][s] = pd.read_csv(history_csv)

        agg_df, summary_df = compute_aggregate_benchmark_metrics(seed_histories)

        tables_dir = self.output_dir / "tables"
        tables_dir.mkdir(parents=True, exist_ok=True)
        figures_dir = self.output_dir / "figures"
        figures_dir.mkdir(parents=True, exist_ok=True)

        agg_df.to_csv(self.output_dir / "aggregate_metrics.csv", index=False)
        summary_df.to_csv(tables_dir / "benchmark_summary_table.csv", index=False)

        if not agg_df.empty:
            plot_benchmark_comparison(agg_df, output_path=figures_dir / "benchmark_hv_comparison.pdf")
            plot_benchmark_feasibility_comparison(agg_df, output_path=figures_dir / "benchmark_feasibility_comparison.pdf")

        return agg_df, summary_df

    def execute_benchmark_campaigns(
        self,
        dry_run: bool = False,
        mock_evaluator: Optional[Any] = None,
    ) -> pd.DataFrame:
        """
        Executes or previews benchmark campaigns across configured algorithms and seeds.

        Enforces equal evaluation budget and seed-paired initial Sobol design
        across all algorithm-seed combinations.
        """
        self.run_campaign_manifest()

        total_runs = len(self.algorithms) * len(self.seeds)
        effective_budget = self.n_sobol_init + self.n_batches * self.batch_size

        if dry_run:
            print(f"[DRY-RUN] Benchmark Campaign Plan:")
            print(f"  - Output Directory: {self.output_dir.resolve()}")
            print(f"  - Algorithms ({len(self.algorithms)}): {self.algorithms}")
            print(f"  - Seeds ({len(self.seeds)}): {self.seeds}")
            print(f"  - Total Runs: {total_runs}")
            print(f"  - Per-run Budget: {effective_budget} evals ({self.n_sobol_init} Sobol + {self.n_batches} x {self.batch_size} batches)")
            print(f"  - Total Planned Evaluations: {total_runs * effective_budget}")
            return pd.DataFrame(self.manifest_rows)

        from mobo_linac.campaigns.runner import MoboCampaignRunner

        for s in self.seeds:
            for algo in self.algorithms:
                run_dir = self.get_run_dir(algo, s)
                if (run_dir / "candidate_history.csv").exists():
                    print(f"Skipping already completed benchmark run: {algo} seed {s}")
                    continue

                print(f"Executing Benchmark Run: algorithm='{algo}', seed={s}...")
                constrained = "constrained" in algo
                if "nehvi" in algo:
                    acq_type = "qLogNEHVI"
                elif "ehvi" in algo:
                    acq_type = "qEHVI"
                else:
                    acq_type = "qLogNEHVI"

                runner = MoboCampaignRunner(
                    config=self.config,
                    output_dir=run_dir,
                    num_initial_samples=self.n_sobol_init,
                    num_batches=self.n_batches,
                    batch_size=self.batch_size,
                    seed=s,
                    acq_type=acq_type,
                    constrained=constrained,
                    evaluator=mock_evaluator,
                )
                results, tracker, _ = runner.run()

                metrics_df = compute_campaign_metrics_history(results, tracker.reporting_ref_point, self.config)
                metrics_df.to_csv(run_dir / "metrics_history.csv", index=False)

        self.analyze_completed_results()
        return self.run_campaign_manifest()
