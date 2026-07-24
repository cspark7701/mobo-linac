"""
Unit tests for Statistically Rigorous Benchmark Campaign Orchestration and Analysis (Task 06).
"""

import pytest
import numpy as np
import pandas as pd
import torch

from mobo_linac.config import load_config
from mobo_linac.campaigns.analysis import compute_aggregate_benchmark_metrics, compute_bootstrap_ci
from mobo_linac.campaigns.benchmark import BenchmarkCampaignRunner, generate_seed_paired_sobol_samples


def test_seed_paired_sobol_samples():
    """Verify seed-paired Sobol design generation consistency."""
    bounds = torch.tensor([[0.0] * 6, [1.0] * 6], dtype=torch.double)

    # Same seed -> identical samples
    samples_s42_a = generate_seed_paired_sobol_samples(10, seed=42, bounds=bounds)
    samples_s42_b = generate_seed_paired_sobol_samples(10, seed=42, bounds=bounds)
    assert torch.allclose(samples_s42_a, samples_s42_b)

    # Different seed -> distinct samples
    samples_s43 = generate_seed_paired_sobol_samples(10, seed=43, bounds=bounds)
    assert not torch.allclose(samples_s42_a, samples_s43)


def test_bootstrap_ci_calculation():
    """Verify median and 95% bootstrap confidence interval calculation."""
    # 5 seeds, 10 steps
    np.random.seed(42)
    data = np.random.rand(5, 10) + np.arange(10)

    medians, ci_lower, ci_upper = compute_bootstrap_ci(data, confidence_level=0.95, n_bootstraps=500)

    assert len(medians) == 10
    assert len(ci_lower) == 10
    assert len(ci_upper) == 10
    assert np.all(ci_lower <= medians)
    assert np.all(medians <= ci_upper)


def test_aggregate_benchmark_metrics_computation():
    """Verify aggregation of mock per-seed metrics histories across algorithms."""
    seed_histories = {
        "constrained_qlognehvi": {},
        "sobol": {},
    }

    for seed in [42, 43]:
        df_cq = pd.DataFrame({
            "cumulative_astra_evaluations": [10, 20, 30],
            "fixed_ref_all_valid_hv": [1.0, 2.0, 3.0],
            "fixed_ref_feasible_hv": [0.5, 1.5, 2.5],
            "feasible_fraction": [0.5, 0.6, 0.7],
            "first_feasible_eval_index": [1, 1, 1],
            "pareto_set_size": [2, 4, 6],
            "invalid_run_count": [0, 0, 0],
            "total_wallclock_s": [10.0, 20.0, 30.0],
            "total_simulation_runtime_s": [8.0, 16.0, 24.0],
        })
        seed_histories["constrained_qlognehvi"][seed] = df_cq

        df_sob = pd.DataFrame({
            "cumulative_astra_evaluations": [10, 20, 30],
            "fixed_ref_all_valid_hv": [0.5, 1.0, 1.5],
            "fixed_ref_feasible_hv": [0.2, 0.5, 1.0],
            "feasible_fraction": [0.2, 0.3, 0.4],
            "first_feasible_eval_index": [5, 5, 5],
            "pareto_set_size": [1, 2, 3],
            "invalid_run_count": [0, 0, 0],
            "total_wallclock_s": [5.0, 10.0, 15.0],
            "total_simulation_runtime_s": [4.0, 8.0, 12.0],
        })
        seed_histories["sobol"][seed] = df_sob

    agg_df, summary_df = compute_aggregate_benchmark_metrics(seed_histories, n_bootstraps=200)

    assert len(agg_df) == 6  # 2 algorithms * 3 steps
    assert len(summary_df) == 2
    assert "algorithm" in summary_df.columns
    assert "final_median_feasible_hv" in summary_df.columns


def test_benchmark_campaign_manifest_generation(tmp_path):
    """Verify benchmark campaign manifest generation."""
    config = load_config("configs/publication_200mev.yaml")
    runner = BenchmarkCampaignRunner(
        config=config,
        output_dir=tmp_path / "benchmark",
        algorithms=["constrained_qlognehvi", "sobol"],
        seeds=[42, 43],
        total_eval_budget=20,
    )

    manifest_df = runner.run_campaign_manifest()
    assert (tmp_path / "benchmark" / "campaign_manifest.csv").exists()
    assert len(manifest_df) == 4  # 2 algos * 2 seeds
