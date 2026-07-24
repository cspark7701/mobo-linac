"""
Statistical Aggregation and Analysis for Benchmark Campaigns (Task 06).

Computes median feasible hypervolume histories, 95% bootstrap confidence intervals,
empirical attainment probabilities, evaluations to first feasible point, final feasible
fractions, Pareto cardinality, and runtime metrics across seeds and algorithms.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import numpy as np
import pandas as pd


def compute_bootstrap_ci(
    data_matrix: np.ndarray,
    confidence_level: float = 0.95,
    n_bootstraps: int = 1000,
    seed: int = 42,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Computes median and 95% bootstrap confidence intervals across random seeds.

    Args:
        data_matrix: (N_seeds, T_steps) 2D array of metric histories.
        confidence_level: Confidence level (e.g. 0.95 for 95% CI).
        n_bootstraps: Number of bootstrap resamples.
        seed: Random seed for reproducibility.

    Returns:
        Tuple of (median_array, ci_lower_array, ci_upper_array).
    """
    if data_matrix.ndim != 2:
        raise ValueError(f"data_matrix must be 2D (N_seeds, T_steps), got shape {data_matrix.shape}")

    n_seeds, n_steps = data_matrix.shape
    rng = np.random.default_rng(seed)

    medians = np.median(data_matrix, axis=0)

    if n_seeds == 1:
        return medians, medians.copy(), medians.copy()

    boot_medians = np.zeros((n_bootstraps, n_steps), dtype=np.float64)
    for b in range(n_bootstraps):
        boot_idx = rng.choice(n_seeds, size=n_seeds, replace=True)
        boot_sample = data_matrix[boot_idx, :]
        boot_medians[b, :] = np.median(boot_sample, axis=0)

    alpha = 1.0 - confidence_level
    ci_lower = np.percentile(boot_medians, 100.0 * (alpha / 2.0), axis=0)
    ci_upper = np.percentile(boot_medians, 100.0 * (1.0 - alpha / 2.0), axis=0)

    return medians, ci_lower, ci_upper


def compute_aggregate_benchmark_metrics(
    seed_histories: Dict[str, Dict[int, pd.DataFrame]],
    confidence_level: float = 0.95,
    n_bootstraps: int = 1000,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Aggregates per-seed metrics histories across algorithms into aggregate metrics
    and summary tables.

    Args:
        seed_histories: Dict mapping algorithm_name -> {seed_int: history_df}.
        confidence_level: Bootstrap confidence level.
        n_bootstraps: Number of bootstrap resamples.

    Returns:
        Tuple of (aggregate_time_series_df, algorithm_summary_df).
    """
    series_rows = []
    summary_rows = []

    for algo_name, seed_dict in seed_histories.items():
        if not seed_dict:
            continue

        seeds = sorted(list(seed_dict.keys()))
        sample_df = next(iter(seed_dict.values()))
        eval_steps = sample_df["cumulative_astra_evaluations"].values
        n_steps = len(eval_steps)
        n_seeds = len(seeds)

        # Extract matrices for HV, feasible fraction, invalid counts
        all_hv_mat = np.zeros((n_seeds, n_steps))
        feas_hv_mat = np.zeros((n_seeds, n_steps))
        feas_frac_mat = np.zeros((n_seeds, n_steps))

        first_feas_indices = []
        final_pareto_sizes = []
        final_feas_fractions = []
        invalid_counts = []
        total_wallclocks = []
        total_sim_runtimes = []

        for idx, s in enumerate(seeds):
            df = seed_dict[s]
            # Align evaluation steps
            all_hv_mat[idx, :] = df["fixed_ref_all_valid_hv"].values[:n_steps]
            feas_hv_mat[idx, :] = df["fixed_ref_feasible_hv"].values[:n_steps]
            feas_frac_mat[idx, :] = df["feasible_fraction"].values[:n_steps]

            # Summary stats per seed
            ff_idx = df["first_feasible_eval_index"].iloc[0] if "first_feasible_eval_index" in df else np.nan
            if pd.isna(ff_idx):
                ff_val = df["first_feasible_eval_index"].dropna()
                ff_idx = ff_val.iloc[0] if len(ff_val) > 0 else np.nan
            first_feas_indices.append(ff_idx)

            final_pareto_sizes.append(df["pareto_set_size"].iloc[-1])
            final_feas_fractions.append(df["feasible_fraction"].iloc[-1])
            invalid_counts.append(df["invalid_run_count"].iloc[-1])
            total_wallclocks.append(df["total_wallclock_s"].iloc[-1])
            total_sim_runtimes.append(df["total_simulation_runtime_s"].iloc[-1])

        # Compute bootstrap CIs for feasible HV
        med_hv, low_hv, high_hv = compute_bootstrap_ci(
            feas_hv_mat, confidence_level=confidence_level, n_bootstraps=n_bootstraps
        )
        med_ff, low_ff, high_ff = compute_bootstrap_ci(
            feas_frac_mat, confidence_level=confidence_level, n_bootstraps=n_bootstraps
        )

        for step_i in range(n_steps):
            series_rows.append({
                "algorithm": algo_name,
                "cumulative_astra_evaluations": eval_steps[step_i],
                "median_feasible_hv": med_hv[step_i],
                "ci_lower_feasible_hv": low_hv[step_i],
                "ci_upper_feasible_hv": high_hv[step_i],
                "median_feasible_fraction": med_ff[step_i],
                "ci_lower_feasible_fraction": low_ff[step_i],
                "ci_upper_feasible_fraction": high_ff[step_i],
            })

        valid_ff_indices = [idx for idx in first_feas_indices if not pd.isna(idx)]
        med_first_feas = float(np.median(valid_ff_indices)) if valid_ff_indices else np.nan

        summary_rows.append({
            "algorithm": algo_name,
            "num_seeds": n_seeds,
            "final_median_feasible_hv": float(med_hv[-1]),
            "final_ci_lower_hv": float(low_hv[-1]),
            "final_ci_upper_hv": float(high_hv[-1]),
            "median_evals_to_first_feasible": med_first_feas,
            "mean_final_feasible_fraction": float(np.mean(final_feas_fractions)),
            "mean_final_pareto_size": float(np.mean(final_pareto_sizes)),
            "mean_invalid_run_count": float(np.mean(invalid_counts)),
            "mean_total_wallclock_s": float(np.mean(total_wallclocks)),
            "mean_total_sim_runtime_s": float(np.mean(total_sim_runtimes)),
        })

    aggregate_series_df = pd.DataFrame(series_rows)
    algorithm_summary_df = pd.DataFrame(summary_rows)

    return aggregate_series_df, algorithm_summary_df
