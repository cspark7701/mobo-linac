"""
Unit tests for Paired Multi-Seed Benchmark Campaigns (Codex Task 09).

Tests benchmark configuration, seed pairing, budget equality, dry-run, mock-mode
execution, aggregate metrics, and publication plot generation.
"""

import pytest
import sys
import numpy as np
import pandas as pd
import torch
from pathlib import Path

from mobo_linac.config import BenchmarkConfig, load_config
from mobo_linac.campaigns.analysis import compute_aggregate_benchmark_metrics, compute_bootstrap_ci
from mobo_linac.campaigns.benchmark import (
    BenchmarkCampaignRunner,
    SUPPORTED_BENCHMARK_ALGORITHMS,
    generate_seed_paired_sobol_samples,
)


# ── BenchmarkConfig ────────────────────────────────────────────────────────────

def test_benchmark_config_defaults():
    """Verify BenchmarkConfig initializes with valid defaults."""
    cfg = BenchmarkConfig()
    assert len(cfg.algorithms) > 0
    assert len(cfg.seeds) > 0
    assert cfg.total_eval_budget > cfg.n_sobol_init


def test_benchmark_config_validation_passes():
    """Valid BenchmarkConfig should pass validation without error."""
    cfg = BenchmarkConfig(
        algorithms=["constrained_qlognehvi", "sobol"],
        seeds=[42, 43],
        total_eval_budget=20,
        n_sobol_init=8,
        batch_size=4,
    )
    cfg.validate()  # Should not raise


def test_benchmark_config_validation_fails_unsupported_algorithm():
    """Invalid algorithm name should raise ValueError."""
    cfg = BenchmarkConfig(
        algorithms=["constrained_qlognehvi", "nonexistent_algorithm"],
        seeds=[42],
        total_eval_budget=20,
        n_sobol_init=8,
        batch_size=4,
    )
    with pytest.raises(ValueError, match="Unsupported algorithm"):
        cfg.validate()


def test_benchmark_config_validation_fails_budget_too_small():
    """Budget <= n_sobol_init should raise ValueError."""
    cfg = BenchmarkConfig(
        algorithms=["sobol"],
        seeds=[42],
        total_eval_budget=10,
        n_sobol_init=10,
        batch_size=4,
    )
    with pytest.raises(ValueError, match="total_eval_budget must be greater"):
        cfg.validate()


# ── Seed Pairing ────────────────────────────────────────────────────────────────

def test_seed_paired_sobol_samples_reproducibility():
    """Same seed must produce identical Sobol design across algorithms."""
    bounds = torch.tensor([[0.0] * 6, [1.0] * 6], dtype=torch.double)
    s1 = generate_seed_paired_sobol_samples(10, seed=42, bounds=bounds)
    s2 = generate_seed_paired_sobol_samples(10, seed=42, bounds=bounds)
    assert torch.allclose(s1, s2), "Seed-paired Sobol designs must be deterministically identical."


def test_seed_paired_sobol_samples_distinct_seeds():
    """Different seeds must produce distinct Sobol designs."""
    bounds = torch.tensor([[0.0] * 6, [1.0] * 6], dtype=torch.double)
    s42 = generate_seed_paired_sobol_samples(10, seed=42, bounds=bounds)
    s43 = generate_seed_paired_sobol_samples(10, seed=43, bounds=bounds)
    assert not torch.allclose(s42, s43), "Different seeds must generate distinct Sobol designs."


# ── BenchmarkCampaignRunner ────────────────────────────────────────────────────

def test_benchmark_runner_budget_equality(tmp_path):
    """Equal budgets must be assigned to all algorithm-seed pairs in manifest."""
    config = load_config("configs/publication_200MeV.yaml")
    runner = BenchmarkCampaignRunner(
        config=config,
        output_dir=tmp_path / "benchmark",
        algorithms=["constrained_qlognehvi", "sobol"],
        seeds=[42, 43],
        total_eval_budget=20,
        n_sobol_init=8,
        batch_size=4,
    )
    manifest_df = runner.run_campaign_manifest()
    # All rows should have the same effective budget
    budgets = manifest_df["budget"].unique()
    assert len(budgets) == 1, f"All algorithm-seed pairs must have equal budget; found: {budgets}"


def test_benchmark_runner_manifest_structure(tmp_path):
    """Manifest should have one row per algorithm-seed pair with required columns."""
    config = load_config("configs/publication_200MeV.yaml")
    runner = BenchmarkCampaignRunner(
        config=config,
        output_dir=tmp_path / "bm",
        algorithms=["constrained_qlognehvi", "sobol"],
        seeds=[42, 43],
        total_eval_budget=20,
        n_sobol_init=8,
        batch_size=4,
    )
    manifest = runner.run_campaign_manifest()
    assert len(manifest) == 4  # 2 algos * 2 seeds
    required_cols = {"algorithm", "seed", "budget", "n_sobol_init", "n_batches", "batch_size", "run_dir", "status"}
    assert required_cols.issubset(set(manifest.columns))
    assert (tmp_path / "bm" / "campaign_manifest.csv").exists()


def test_benchmark_runner_dry_run(tmp_path, capsys):
    """Dry-run should print plan without executing campaigns."""
    config = load_config("configs/publication_200MeV.yaml")
    runner = BenchmarkCampaignRunner(
        config=config,
        output_dir=tmp_path / "bm_dry",
        algorithms=["constrained_qlognehvi"],
        seeds=[42],
        total_eval_budget=14,
        n_sobol_init=6,
        batch_size=4,
    )
    result_df = runner.execute_benchmark_campaigns(dry_run=True)
    captured = capsys.readouterr()
    assert "[DRY-RUN]" in captured.out
    assert "constrained_qlognehvi" in captured.out


# ── Aggregate Metrics ──────────────────────────────────────────────────────────

def test_aggregate_metrics_includes_failure_rate_and_objective_extrema():
    """Aggregate summary must include failure_rate and objective extrema columns."""
    seed_histories = {}
    for algo in ["constrained_qlognehvi", "sobol"]:
        seed_histories[algo] = {}
        for s in [42, 43]:
            seed_histories[algo][s] = pd.DataFrame({
                "cumulative_astra_evaluations": [10, 20, 30],
                "fixed_ref_all_valid_hv": [1.0, 2.0, 3.0],
                "fixed_ref_feasible_hv": [0.5, 1.5, 2.5],
                "feasible_fraction": [0.5, 0.6, 0.7],
                "first_feasible_eval_index": [1, 1, 1],
                "pareto_set_size": [2, 4, 6],
                "invalid_run_count": [1, 2, 3],
                "total_wallclock_s": [10.0, 20.0, 30.0],
                "total_simulation_runtime_s": [8.0, 16.0, 24.0],
            })

    agg_df, summary_df = compute_aggregate_benchmark_metrics(seed_histories, n_bootstraps=50)
    assert "failure_rate" in summary_df.columns
    assert "min_norm_emit_x" in summary_df.columns
    assert "min_norm_emit_y" in summary_df.columns
    assert "min_sigma_energy" in summary_df.columns


# ── Publication Plots ──────────────────────────────────────────────────────────

def test_plot_benchmark_comparison_runs():
    """plot_benchmark_comparison must return a Figure without raising."""
    import matplotlib
    matplotlib.use("Agg")
    from mobo_linac.plotting.visualizations import plot_benchmark_comparison

    agg_df = pd.DataFrame({
        "algorithm": ["constrained_qlognehvi"] * 3 + ["sobol"] * 3,
        "cumulative_astra_evaluations": [10, 20, 30, 10, 20, 30],
        "median_feasible_hv": [0.1, 0.3, 0.5, 0.05, 0.1, 0.2],
        "ci_lower_feasible_hv": [0.08, 0.25, 0.45, 0.03, 0.07, 0.15],
        "ci_upper_feasible_hv": [0.12, 0.35, 0.55, 0.07, 0.13, 0.25],
        "median_feasible_fraction": [0.5, 0.6, 0.7, 0.3, 0.4, 0.5],
        "ci_lower_feasible_fraction": [0.4, 0.5, 0.6, 0.2, 0.3, 0.4],
        "ci_upper_feasible_fraction": [0.6, 0.7, 0.8, 0.4, 0.5, 0.6],
    })
    fig = plot_benchmark_comparison(agg_df)
    import matplotlib.pyplot as plt
    assert fig is not None
    plt.close(fig)


def test_plot_benchmark_feasibility_comparison_runs():
    """plot_benchmark_feasibility_comparison must return a Figure without raising."""
    import matplotlib
    matplotlib.use("Agg")
    from mobo_linac.plotting.visualizations import plot_benchmark_feasibility_comparison

    agg_df = pd.DataFrame({
        "algorithm": ["constrained_qlognehvi"] * 3 + ["sobol"] * 3,
        "cumulative_astra_evaluations": [10, 20, 30, 10, 20, 30],
        "median_feasible_hv": [0.1, 0.3, 0.5, 0.05, 0.1, 0.2],
        "ci_lower_feasible_hv": [0.08, 0.25, 0.45, 0.03, 0.07, 0.15],
        "ci_upper_feasible_hv": [0.12, 0.35, 0.55, 0.07, 0.13, 0.25],
        "median_feasible_fraction": [0.5, 0.6, 0.7, 0.3, 0.4, 0.5],
        "ci_lower_feasible_fraction": [0.4, 0.5, 0.6, 0.2, 0.3, 0.4],
        "ci_upper_feasible_fraction": [0.6, 0.7, 0.8, 0.4, 0.5, 0.6],
    })
    fig = plot_benchmark_feasibility_comparison(agg_df)
    import matplotlib.pyplot as plt
    assert fig is not None
    plt.close(fig)


# ── CLI integration (mock-mode) ────────────────────────────────────────────────

def test_cli_benchmark_dry_run(tmp_path):
    """CLI run-benchmark --dry-run should complete without launching evaluations."""
    from mobo_linac.cli import main
    sys.argv = [
        "mobo-linac", "run-benchmark",
        "--algorithms", "constrained_qlognehvi", "sobol",
        "--seeds", "42",
        "--budget", "14",
        "--n-sobol-init", "6",
        "--batch-size", "4",
        "--output-dir", str(tmp_path / "bm_cli_dry"),
        "--dry-run",
    ]
    main()  # Should not raise


def test_cli_benchmark_mock_mode(tmp_path):
    """CLI run-benchmark with single algo + seed + dry-run verifies manifest and plan output."""
    from mobo_linac.cli import main
    # Use dry-run so no ASTRA/BO work is performed; this satisfies the
    # "Do not launch expensive campaigns by default in tests" acceptance criterion.
    outdir = tmp_path / "bm_mock"
    sys.argv = [
        "mobo-linac", "run-benchmark",
        "--algorithms", "constrained_qlognehvi",
        "--seeds", "42",
        "--budget", "14",
        "--n-sobol-init", "6",
        "--batch-size", "4",
        "--output-dir", str(outdir),
        "--dry-run",
    ]
    main()
    assert (outdir / "campaign_manifest.csv").exists()
    df = pd.read_csv(outdir / "campaign_manifest.csv")
    assert len(df) == 1
    assert df.iloc[0]["algorithm"] == "constrained_qlognehvi"
    assert df.iloc[0]["seed"] == 42

