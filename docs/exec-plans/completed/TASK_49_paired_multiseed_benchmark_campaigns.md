# Task 49 Summary: Paired Multi-Seed Benchmark Campaigns (Codex Task 09)

## Summary

Task 49 built complete paired multi-seed benchmark campaign infrastructure suitable for publication figures and tables. All algorithms within the same seed receive the identical initial Sobol design, and all algorithm-seed combinations are guaranteed equal total ASTRA evaluation budgets.

## Key Implementation & Enhancements

### 1. `BenchmarkConfig` Dataclass ([`src/mobo_linac/config.py`](file:///home/cspark/Work/projects/mobo_linac/src/mobo_linac/config.py))
Added `BenchmarkConfig` dataclass with:
- `algorithms`: List of algorithm identifiers (supports `constrained_qlognehvi`, `unconstrained_qlognehvi`, `qlogehvi`, `scalarized_bo`, `nsga2`, `sobol`)
- `seeds`: List of random seeds (default 42–51, 10 seeds)
- `total_eval_budget`: Equal ASTRA evaluation budget per algorithm-seed pair
- `n_sobol_init`: Initial Sobol design size (shared across all algorithms within a seed)
- `batch_size`: BO batch size per iteration
- `reporting_ref_point`: Fixed reporting reference point $[1.5, 1.5, 1.5]$
- `constraint_profile`: Named constraint sensitivity profile
- `validate()`: Checks algorithm names, budget feasibility, batch size, and seed list

### 2. Seed-Paired Initial Design Enforcement ([`src/mobo_linac/campaigns/benchmark.py`](file:///home/cspark/Work/projects/mobo_linac/src/mobo_linac/campaigns/benchmark.py))
- `generate_seed_paired_sobol_samples()`: Deterministic Sobol samples shared across all algorithms within the same seed.
- `BenchmarkCampaignRunner.__init__()`: Accepts optional `BenchmarkConfig`; validates budget constraint `(total_eval_budget - n_sobol_init) / batch_size >= 1`.
- Outer loop iterates over **seeds first**, then algorithms — guaranteeing shared Sobol initialization before any BO iteration.
- `run_campaign_manifest()` now resets manifest rows on each call and includes `n_batches` column.
- `analyze_completed_results()` now auto-generates publication plots after aggregation.

### 3. Extended Aggregate Metrics ([`src/mobo_linac/campaigns/analysis.py`](file:///home/cspark/Work/projects/mobo_linac/src/mobo_linac/campaigns/analysis.py))
Added to algorithm summary:
- `failure_rate`: Ratio of invalid ASTRA runs across total planned evaluations.
- `min_norm_emit_x`, `min_norm_emit_y`, `min_sigma_energy`: Objective extrema across seeds (best-of-best per algorithm).

### 4. Publication-Ready Comparison Plots ([`src/mobo_linac/plotting/visualizations.py`](file:///home/cspark/Work/projects/mobo_linac/src/mobo_linac/plotting/visualizations.py))
- `plot_benchmark_comparison()`: Median feasible hypervolume vs cumulative ASTRA evaluations with 95% bootstrap CI shading for all algorithms.
- `plot_benchmark_feasibility_comparison()`: Median feasible fraction vs cumulative evaluations with 95% bootstrap CI shading.

### 5. CLI Flags for `run-benchmark` ([`src/mobo_linac/cli.py`](file:///home/cspark/Work/projects/mobo_linac/src/mobo_linac/cli.py))
Added new arguments:
- `--algorithms`: Space-separated list of algorithm names to benchmark.
- `--n-sobol-init`: Number of initial Sobol samples (default 10).
- `--batch-size`: BO batch size per iteration (default 4).

### 6. Unit Test Suite ([`tests/test_benchmark.py`](file:///home/cspark/Work/projects/mobo_linac/tests/test_benchmark.py))
Tests added:
- `test_benchmark_config_defaults`: Validates default `BenchmarkConfig` initialization.
- `test_benchmark_config_validation_passes`: Valid config passes validation.
- `test_benchmark_config_validation_fails_unsupported_algorithm`: Unsupported algorithm raises `ValueError`.
- `test_benchmark_config_validation_fails_budget_too_small`: Budget ≤ `n_sobol_init` raises `ValueError`.
- `test_seed_paired_sobol_samples_reproducibility`: Same seed → identical Sobol design.
- `test_seed_paired_sobol_samples_distinct_seeds`: Different seeds → distinct designs.
- `test_benchmark_runner_budget_equality`: All algorithm-seed manifest rows have equal budget.
- `test_benchmark_runner_manifest_structure`: Manifest has correct columns and row count.
- `test_benchmark_runner_dry_run`: Dry-run prints plan without launching campaigns.
- `test_aggregate_metrics_includes_failure_rate_and_objective_extrema`: Summary includes new columns.
- `test_plot_benchmark_comparison_runs`: `plot_benchmark_comparison()` returns a Figure.
- `test_plot_benchmark_feasibility_comparison_runs`: `plot_benchmark_feasibility_comparison()` returns a Figure.
- `test_cli_benchmark_dry_run`: CLI `run-benchmark --dry-run` completes without evaluation.
- `test_cli_benchmark_mock_mode`: CLI `run-benchmark --dry-run` writes manifest with correct structure.

**18/18 benchmark tests passed in 7.73s. No expensive campaigns launched in CI.**

## Status

**Completed**. Paired multi-seed benchmark campaign infrastructure is production-ready. Summary saved to `docs/exec-plans/completed/TASK_49_paired_multiseed_benchmark_campaigns.md`.
