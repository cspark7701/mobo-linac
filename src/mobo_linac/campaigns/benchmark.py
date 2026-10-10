"""
Statistically Rigorous Benchmark Campaign Orchestrator for Linac MOBO (Task 09).

Executes multi-seed, multi-algorithm benchmark comparisons with seed-paired initial
Sobol sampling, exact evaluation budgets, completion-state validation, and
publication-ready aggregate metrics and plots.
"""

from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import pandas as pd
import torch
from torch.quasirandom import SobolEngine

from mobo_linac.benchmark_algorithms import (
    get_benchmark_algorithm,
)
from mobo_linac.config import BenchmarkConfig, MoboConfig
from mobo_linac.conventions import reporting_metadata, validate_campaign_compatibility
from mobo_linac.result_schema import ResultSchema
from mobo_linac.io.artifacts import validate_run_completion
from mobo_linac.utils.durable import atomic_csv, atomic_json
from mobo_linac.campaigns.analysis import compute_aggregate_benchmark_metrics, feasible_objective_extrema
from mobo_linac.io.run_data import read_run_data

from mobo_linac.utils.logger import get_logger
from mobo_linac.campaigns.runner import campaign_runner
from mobo_linac.config import load_config

logger = get_logger(__name__)


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
        output_dir: Optional[Union[str, Path]] = None,
        algorithms: Optional[List[str]] = None,
        seeds: Optional[List[int]] = None,
        total_eval_budget: Optional[int] = None,
        n_sobol_init: Optional[int] = None,
        batch_size: Optional[int] = None,
        device: str = "auto",
        benchmark_config: Optional[BenchmarkConfig] = None,
        num_workers: Optional[int] = None,
    ):
        config.validate()
        self.device = device
        self.evaluation_kind = "astra"
        self.num_workers = config.execution.max_workers if num_workers is None else num_workers
        if type(self.num_workers) is not int or self.num_workers < 1:
            raise ValueError("num_workers must be >= 1.")
        if benchmark_config is None:
            # Explicit arguments override the configuration's benchmark section, then defaults.
            requested = dict(algorithms=algorithms, seeds=seeds, total_eval_budget=total_eval_budget,
                             n_sobol_init=n_sobol_init, batch_size=batch_size,
                             output_dir=None if output_dir is None else str(output_dir))
            benchmark_config = replace(config.benchmark or BenchmarkConfig(),
                                       **{name: value for name, value in requested.items() if value is not None})
        self.benchmark_config = benchmark_config
        self.benchmark_config.validate()
        self.benchmark_config.resolved_reporting_ref_point(len(config.objectives))
        self.config = replace(
            config, constraints=config.get_constraint_profile(self.benchmark_config.constraint_profile)
        )
        self.config.source_path = config.source_path  # provenance is not a dataclass field
        self.output_dir = Path(self.benchmark_config.output_dir)
        self.algorithms = list(self.benchmark_config.algorithms)
        self.seeds = list(self.benchmark_config.seeds)
        self.total_eval_budget = self.benchmark_config.total_eval_budget
        self.n_sobol_init = self.benchmark_config.n_sobol_init
        self.batch_size = self.benchmark_config.batch_size
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_rows: List[Dict[str, Any]] = []

    @property
    def reporting_ref_point_norm(self) -> List[float]:
        """Normalized physical reporting reference for the configured objectives."""
        return self.benchmark_config.resolved_reporting_ref_point(len(self.config.objectives))

    @classmethod
    def from_output_dir(cls, output_dir: Union[str, Path]) -> "BenchmarkCampaignRunner":
        """Analysis-only runner using the configuration recorded by the benchmark's runs."""
        configs = sorted(Path(output_dir).glob("per_seed/*/config.json"))
        if not configs:
            raise FileNotFoundError(f"No recorded benchmark run configuration under {output_dir}")
        return cls(load_config(configs[0]), output_dir=output_dir)

    @property
    def model_reporting_ref_point(self) -> List[float]:
        """Signed, scaled model-space equivalent of the normalized benchmark reference."""
        schema = ResultSchema.from_config(self.config)
        return [value * sign * scale for value, sign, scale
                in zip(self.reporting_ref_point_norm, schema.signs, schema.scales)]

    @property
    def n_batches(self) -> int:
        remaining = self.total_eval_budget - self.n_sobol_init
        return (remaining + self.batch_size - 1) // self.batch_size

    @property
    def final_batch_size(self) -> int:
        return self.total_eval_budget - self.n_sobol_init - (self.n_batches - 1) * self.batch_size

    def _run_signature(self, algorithm: str, seed: int) -> str:
        payload = {
            "config": asdict(self.config),
            "algorithm": algorithm,
            "evaluation_kind": self.evaluation_kind,
            "definition": asdict(get_benchmark_algorithm(algorithm)),
            "seed": seed,
            "budget": self.total_eval_budget,
            "n_sobol_init": self.n_sobol_init,
            "batch_size": self.batch_size,
            "reporting_scales": list(ResultSchema.from_config(self.config).scales),
            "reporting_ref_point_physical_norm": self.reporting_ref_point_norm,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    def _run_status(self, algorithm: str, seed: int, require_signature: bool = True) -> str:
        run_dir = self.get_run_dir(algorithm, seed)
        state_path = run_dir / "benchmark_state.json"
        if not run_dir.exists() or not any(run_dir.iterdir()):
            return "pending"
        if not state_path.exists():
            return "incomplete"
        try:
            state = json.loads(state_path.read_text())
            if not isinstance(state, dict) or state.get("version") != 1:
                return "incomplete"
            if state.get("algorithm") != algorithm or state.get("seed") != seed:
                return "incompatible"
            if require_signature and state.get("signature") != self._run_signature(algorithm, seed):
                return "incompatible"
            expected_budget = self.total_eval_budget if require_signature else state.get("effective_budget")
            if not isinstance(expected_budget, int) or expected_budget < 1:
                return "incomplete"
            if state.get("status") != "completed" or state.get("evaluation_count") != expected_budget:
                return "incomplete"
            if not validate_run_completion(run_dir):
                return "incomplete"
            metadata = json.loads((run_dir / "reporting_metadata.json").read_text())
            validate_campaign_compatibility(metadata, metadata)
            history = pd.read_csv(run_dir / "candidate_history.csv")
            metrics = pd.read_csv(run_dir / "metrics_history.csv")
            if (len(history) != expected_budget or len(metrics) != expected_budget
                    or history["evaluation_id"].nunique() != expected_budget
                    or int(metrics.iloc[-1]["cumulative_astra_evaluations"]) != expected_budget):
                return "incomplete"
        except (OSError, ValueError, KeyError, TypeError, IndexError):
            return "incomplete"
        return "completed"

    def _save_run_state(self, algorithm: str, seed: int, status: str, evaluation_count: int) -> None:
        run_dir = self.get_run_dir(algorithm, seed)
        run_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "version": 1,
            "algorithm": algorithm,
            "evaluation_kind": self.evaluation_kind,
            "seed": seed,
            "status": status,
            "signature": self._run_signature(algorithm, seed),
            "requested_budget": self.total_eval_budget,
            "effective_budget": self.total_eval_budget,
            "evaluation_count": evaluation_count,
            "reporting_scales": list(ResultSchema.from_config(self.config).scales),
            "reporting_ref_point_physical_norm": self.reporting_ref_point_norm,
        }
        atomic_json(run_dir / "benchmark_state.json", data)

    def get_run_dir(self, algorithm: str, seed: int) -> Path:
        """Returns isolated run directory for algorithm and seed."""
        return self.output_dir / "per_seed" / f"{algorithm}_seed_{seed}"

    def run_campaign_manifest(self) -> pd.DataFrame:
        """Generates campaign manifest DataFrame."""
        self.manifest_rows = []
        for algo in self.algorithms:
            for s in self.seeds:
                run_path = self.get_run_dir(algo, s)
                status = self._run_status(algo, s)
                effective_budget = self.total_eval_budget
                self.manifest_rows.append({
                    "algorithm": algo,
                    "seed": s,
                    "budget": effective_budget,
                    "requested_budget": self.total_eval_budget,
                    "effective_budget": effective_budget,
                    "final_batch_size": self.final_batch_size,
                    "n_sobol_init": self.n_sobol_init,
                    "n_batches": self.n_batches,
                    "batch_size": self.batch_size,
                    "run_dir": str(run_path),
                    "status": status,
                })
        manifest_df = pd.DataFrame(self.manifest_rows)
        atomic_csv(self.output_dir / "campaign_manifest.csv", manifest_df)
        return manifest_df

    def analyze_completed_results(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Analyzes all completed seed results and exports aggregate metrics and summary tables.
        Also generates publication-ready comparison plots.

        Returns:
            Tuple of (aggregate_series_df, summary_df).
        """
        from mobo_linac.plotting import (
            plot_benchmark_comparison,
            plot_benchmark_feasibility_comparison,
        )

        seed_histories: Dict[str, Dict[int, pd.DataFrame]] = {}
        manifest_path = self.output_dir / "campaign_manifest.csv"
        if manifest_path.exists():
            pairs = pd.read_csv(manifest_path)[["algorithm", "seed"]].itertuples(index=False, name=None)
        else:
            pairs = ((algo, seed) for algo in self.algorithms for seed in self.seeds)
        reporting_metadata = None
        for algo, seed in pairs:
            get_benchmark_algorithm(algo)
            seed = int(seed)
            if self._run_status(algo, seed, require_signature=False) != "completed":
                continue
            run_path = self.get_run_dir(algo, seed)
            state = json.loads((run_path / "benchmark_state.json").read_text())
            metadata = json.loads((run_path / "reporting_metadata.json").read_text())
            metadata["evaluation_kind"] = state["evaluation_kind"]
            if reporting_metadata is not None:
                validate_campaign_compatibility(reporting_metadata, metadata)
                if reporting_metadata["evaluation_kind"] != metadata["evaluation_kind"]:
                    raise ValueError("Completed benchmark runs have incompatible evaluation kinds.")
            reporting_metadata = metadata
            frame = pd.read_csv(run_path / "metrics_history.csv")
            frame.attrs["reporting_metadata"] = metadata
            run = read_run_data(run_path)
            frame.attrs["objective_extrema"] = feasible_objective_extrema(run.results, run.config)
            seed_histories.setdefault(algo, {})[seed] = frame

        agg_df, summary_df = compute_aggregate_benchmark_metrics(seed_histories)

        tables_dir = self.output_dir / "tables"
        tables_dir.mkdir(parents=True, exist_ok=True)
        figures_dir = self.output_dir / "figures"
        figures_dir.mkdir(parents=True, exist_ok=True)

        atomic_csv(self.output_dir / "aggregate_metrics.csv", agg_df)
        atomic_csv(tables_dir / "benchmark_summary_table.csv", summary_df)

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
        self.evaluation_kind = "mock" if mock_evaluator is not None else "astra"
        self.run_campaign_manifest()

        total_runs = len(self.algorithms) * len(self.seeds)
        effective_budget = self.total_eval_budget

        if dry_run:
            logger.info("[DRY-RUN] Benchmark Campaign Plan:")
            logger.info(f"  - Output Directory: {self.output_dir.resolve()}")
            logger.info(f"  - Algorithms ({len(self.algorithms)}): {self.algorithms}")
            logger.info(f"  - Seeds ({len(self.seeds)}): {self.seeds}")
            logger.info(f"  - Total Runs: {total_runs}")
            logger.info(f"  - Per-run Budget: {effective_budget} evals ({self.n_sobol_init} Sobol + {self.n_batches} batches, final q={self.final_batch_size})")
            logger.info(f"  - Total Planned Evaluations: {total_runs * effective_budget}")
            return pd.DataFrame(self.manifest_rows)


        for s in self.seeds:
            for algo in self.algorithms:
                run_dir = self.get_run_dir(algo, s)
                status = self._run_status(algo, s)
                if status == "completed":
                    logger.info(f"Skipping already completed benchmark run: {algo} seed {s}")
                    continue
                if status != "pending":
                    raise RuntimeError(
                        f"Benchmark run {run_dir} is {status}; preserve its artifacts and "
                        "select a new output directory. Automatic recovery requires the complete resume-state refactor."
                    )

                logger.info(f"\nExecuting Benchmark Run: algorithm='{algo}', seed={s}...")
                spec = get_benchmark_algorithm(algo)
                self._save_run_state(algo, s, "running", 0)
                options = {"num_initial_samples": self.n_sobol_init, "num_batches": self.n_batches,
                           "batch_size": self.batch_size, "num_workers": self.num_workers, "seed": s,
                           "acquisition": spec.acquisition}
                runner = campaign_runner(self.config, options, optimization_mode=spec.optimization_mode,
                                         output_dir=run_dir, constrained=spec.constrained,
                                         total_eval_budget=self.total_eval_budget, evaluator=mock_evaluator,
                                         reporting_ref_point=self.model_reporting_ref_point, device=self.device)
                results, _, _ = runner.run()

                if len(results) != self.total_eval_budget:
                    raise RuntimeError(f"Benchmark returned {len(results)} evaluations; expected {self.total_eval_budget}.")
                # The campaign runner publishes the complete artifact contract; nothing is
                # reconstructed here, so a run without it can never be marked complete.
                metadata_path = run_dir / "reporting_metadata.json"
                if metadata_path.exists():
                    expected = reporting_metadata(self.config, self.model_reporting_ref_point, "explicit")
                    validate_campaign_compatibility(json.loads(metadata_path.read_text()), expected)
                self._save_run_state(algo, s, "completed", len(results))
                if self._run_status(algo, s) != "completed":
                    self._save_run_state(algo, s, "incomplete", len(results))
                    raise RuntimeError(f"Benchmark run {run_dir} has incomplete persisted evaluation or metric history.")

        self.analyze_completed_results()
        return self.run_campaign_manifest()
