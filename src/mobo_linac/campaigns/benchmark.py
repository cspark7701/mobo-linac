"""
Statistically Rigorous Benchmark Campaign Orchestrator for Linac MOBO (Task 09).

Executes multi-seed, multi-algorithm benchmark comparisons with seed-paired initial
Sobol sampling, exact evaluation budgets, completion-state validation, and
publication-ready aggregate metrics and plots.
"""

from dataclasses import asdict, replace
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Dict, List, Optional, Tuple, Union
import pandas as pd
import torch
from torch.quasirandom import SobolEngine

from mobo_linac.benchmark_algorithms import (
    SUPPORTED_BENCHMARK_ALGORITHMS,
    get_benchmark_algorithm,
)
from mobo_linac.config import BenchmarkConfig, MoboConfig
from mobo_linac.metrics.reporting import (
    compute_campaign_metrics_history,
    reporting_metadata, validate_campaign_compatibility,
)
from mobo_linac.result_schema import ResultSchema
from mobo_linac.io.artifacts import atomic_json, RunArtifactWriter, validate_run_completion
from mobo_linac.campaigns.analysis import compute_aggregate_benchmark_metrics


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
        self.benchmark_config = benchmark_config or BenchmarkConfig(
            algorithms=list(SUPPORTED_BENCHMARK_ALGORITHMS) if algorithms is None else algorithms,
            seeds=list(range(42, 52)) if seeds is None else seeds,
            total_eval_budget=total_eval_budget,
            n_sobol_init=n_sobol_init,
            batch_size=batch_size,
            output_dir=str(output_dir),
        )
        self.benchmark_config.validate()
        if len(self.benchmark_config.reporting_ref_point) != len(config.objectives):
            raise ValueError("Benchmark reporting reference must match configured objectives.")
        self.config = replace(
            config, constraints=config.get_constraint_profile(self.benchmark_config.constraint_profile)
        )
        if hasattr(config, "resolved_path"):
            self.config.resolved_path = config.resolved_path
        self.output_dir = Path(self.benchmark_config.output_dir)
        self.algorithms = list(self.benchmark_config.algorithms)
        self.seeds = list(self.benchmark_config.seeds)
        self.total_eval_budget = self.benchmark_config.total_eval_budget
        self.n_sobol_init = self.benchmark_config.n_sobol_init
        self.batch_size = self.benchmark_config.batch_size
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_rows: List[Dict[str, Any]] = []

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
            "reporting_ref_point_physical_norm": self.benchmark_config.reporting_ref_point,
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
            "reporting_ref_point_physical_norm": self.benchmark_config.reporting_ref_point,
        }
        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", dir=run_dir, delete=False) as stream:
                temporary_path = Path(stream.name)
                json.dump(data, stream, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary_path, run_dir / "benchmark_state.json")
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()

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
            seed_histories.setdefault(algo, {})[seed] = frame

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
        self.evaluation_kind = "mock" if mock_evaluator is not None else "astra"
        self.run_campaign_manifest()

        total_runs = len(self.algorithms) * len(self.seeds)
        effective_budget = self.total_eval_budget

        if dry_run:
            print(f"[DRY-RUN] Benchmark Campaign Plan:")
            print(f"  - Output Directory: {self.output_dir.resolve()}")
            print(f"  - Algorithms ({len(self.algorithms)}): {self.algorithms}")
            print(f"  - Seeds ({len(self.seeds)}): {self.seeds}")
            print(f"  - Total Runs: {total_runs}")
            print(f"  - Per-run Budget: {effective_budget} evals ({self.n_sobol_init} Sobol + {self.n_batches} batches, final q={self.final_batch_size})")
            print(f"  - Total Planned Evaluations: {total_runs * effective_budget}")
            return pd.DataFrame(self.manifest_rows)

        from mobo_linac.campaigns.runner import MoboCampaignRunner

        for s in self.seeds:
            for algo in self.algorithms:
                run_dir = self.get_run_dir(algo, s)
                status = self._run_status(algo, s)
                if status == "completed":
                    print(f"Skipping already completed benchmark run: {algo} seed {s}")
                    continue
                if status != "pending":
                    raise RuntimeError(
                        f"Benchmark run {run_dir} is {status}; preserve its artifacts and "
                        "select a new output directory. Automatic recovery requires the complete resume-state refactor."
                    )

                print(f"\nExecuting Benchmark Run: algorithm='{algo}', seed={s}...")
                spec = get_benchmark_algorithm(algo)
                self._save_run_state(algo, s, "running", 0)
                runner = MoboCampaignRunner(
                    config=self.config,
                    output_dir=run_dir,
                    num_initial_samples=self.n_sobol_init,
                    num_batches=self.n_batches,
                    batch_size=self.batch_size,
                    seed=s,
                    acq_type=spec.acquisition,
                    optimization_mode=spec.optimization_mode,
                    constrained=spec.constrained,
                    num_workers=self.num_workers,
                    total_eval_budget=self.total_eval_budget,
                    evaluator=mock_evaluator,
                    reporting_ref_point=[value * sign * scale for value, sign, scale in zip(self.benchmark_config.reporting_ref_point, ResultSchema.from_config(self.config).signs, ResultSchema.from_config(self.config).scales)],
                    device=self.device,
                )
                results, _, _ = runner.run()

                if len(results) != self.total_eval_budget:
                    raise RuntimeError(f"Benchmark returned {len(results)} evaluations; expected {self.total_eval_budget}.")
                metric_path = run_dir / "metrics_history.csv"
                # Real campaigns already wrote metrics using this explicit reference.
                # Alternate/test runners may return records without derived artifacts.
                if not metric_path.exists():
                    schema = ResultSchema.from_config(self.config)
                    norm_ref = [value * sign for value, sign in zip(self.benchmark_config.reporting_ref_point, schema.signs)]
                    metrics_df = compute_campaign_metrics_history(results=results, scales=list(schema.scales), reporting_ref_point_norm=norm_ref)
                    metrics_df.to_csv(metric_path, index=False)
                    atomic_json(run_dir / "reporting_metadata.json", reporting_metadata(self.config, [value * scale for value, scale in zip(norm_ref, schema.scales)], "explicit"))
                else:
                    meta = json.loads((run_dir / "reporting_metadata.json").read_text())
                    schema = ResultSchema.from_config(self.config)
                    expected = reporting_metadata(self.config, [value * sign * scale for value, sign, scale in zip(self.benchmark_config.reporting_ref_point, schema.signs, schema.scales)], "explicit")
                    validate_campaign_compatibility(meta, expected)
                if not (run_dir / "run_complete.json").exists() and (run_dir / "candidate_history.csv").exists():
                    # Record-returning backend adapters must also publish a concrete artifact marker.
                    self.config.save_json(run_dir / "config.json")
                    self.config.save_yaml(run_dir / "config.yaml")
                    adapter_writer = RunArtifactWriter(run_dir, self.config)
                    adapter_writer.required = [name for name in ("candidate_history.json", "candidate_history.csv", "evaluations.csv", "train_X.csv", "train_Y.csv", "pareto.csv", "pareto_all.csv", "pareto_feasible.csv", "constraints.csv", "failures.csv", "objectives_physical.csv", "objectives_model.csv", "metrics_history.csv", "hypervolume.csv", "reporting_metadata.json", "config.json", "config.yaml")]
                    adapter_writer.complete(len(results), None)
                self._save_run_state(algo, s, "completed", len(results))
                if self._run_status(algo, s) != "completed":
                    self._save_run_state(algo, s, "incomplete", len(results))
                    raise RuntimeError(f"Benchmark run {run_dir} has incomplete persisted evaluation or metric history.")

        self.analyze_completed_results()
        return self.run_campaign_manifest()
