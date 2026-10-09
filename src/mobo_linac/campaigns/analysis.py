"""
Statistical Aggregation and Analysis for Benchmark Campaigns (Task 06).

Computes median feasible hypervolume histories, 95% bootstrap confidence intervals,
empirical attainment probabilities, evaluations to first feasible point, final feasible
fractions, Pareto cardinality, and runtime metrics across seeds and algorithms.
"""

from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd


def compute_bootstrap_ci(
    data_matrix: np.ndarray,
    confidence_level: float = 0.95,
    n_bootstraps: int = 1000,
    seed: int = 42,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Median and percentile bootstrap confidence intervals of the median across seeds.

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
    n_seeds, _ = data_matrix.shape
    medians = np.median(data_matrix, axis=0)
    if n_seeds == 1:
        return medians, medians.copy(), medians.copy()
    rng = np.random.default_rng(seed)
    # Resample seed indices for every bootstrap at once (same draw sequence as one-by-one choice).
    indices = np.stack([rng.choice(n_seeds, size=n_seeds, replace=True) for _ in range(n_bootstraps)])
    boot_medians = np.median(data_matrix[indices, :], axis=1)
    alpha = 1.0 - confidence_level
    ci_lower = np.percentile(boot_medians, 100.0 * (alpha / 2.0), axis=0)
    ci_upper = np.percentile(boot_medians, 100.0 * (1.0 - alpha / 2.0), axis=0)
    return medians, ci_lower, ci_upper


def feasible_objective_extrema(results, config) -> Dict[str, Optional[float]]:
    """Best feasible measured value per configured objective (direction aware); None if absent."""
    from mobo_linac.metrics.selection import valid_measured
    from mobo_linac.result_schema import ResultSchema
    schema = ResultSchema.from_config(config)
    _, values = valid_measured(results, schema, feasible=True)
    extrema = {}
    for index, (name, sign) in enumerate(zip(schema.physical_columns, schema.signs)):
        column = values[:, index]
        extrema[name] = None if not len(column) else float(column.min() if sign == -1 else column.max())
    return extrema


def _extremum_column(name: str, sign: int) -> str:
    return f"{'min' if sign == -1 else 'max'}_{name}"


def compute_aggregate_benchmark_metrics(
    seed_histories: Dict[str, Dict[int, pd.DataFrame]],
    confidence_level: float = 0.95,
    n_bootstraps: int = 1000,
    bootstrap_seed: int = 42,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Aggregate per-seed metric histories across algorithms.

    Every history must carry ``attrs["reporting_metadata"]`` with a matching convention.
    Histories are aligned on ``cumulative_astra_evaluations``; unequal budgets raise.
    Optional ``attrs["objective_extrema"]`` (best feasible value per objective) feeds the
    direction-aware objective extrema columns, which stay NaN when no history supplies them.

    Returns:
        Tuple of (aggregate_time_series_df, algorithm_summary_df).
    """
    from mobo_linac.metrics.reporting import validate_campaign_compatibility
    convention = None
    for histories in seed_histories.values():
        for frame in histories.values():
            meta = frame.attrs.get("reporting_metadata")
            validate_campaign_compatibility(meta, meta)
            if convention is not None:
                validate_campaign_compatibility(convention, meta)
            convention = meta
    objectives = list(zip(convention["objective_names"], convention["objective_signs"])) if convention else []
    series_rows = []
    summary_rows = []

    for algo_name, seed_dict in seed_histories.items():
        if not seed_dict:
            continue
        seeds = sorted(seed_dict)
        eval_steps = seed_dict[seeds[0]]["cumulative_astra_evaluations"].to_numpy()
        for seed in seeds:
            steps = seed_dict[seed]["cumulative_astra_evaluations"].to_numpy()
            if steps.shape != eval_steps.shape or not np.array_equal(steps, eval_steps):
                raise ValueError(f"Benchmark histories for '{algo_name}' have unequal evaluation steps (seed {seed}).")
        frames = [seed_dict[seed] for seed in seeds]
        feas_hv_mat = np.stack([frame["fixed_ref_feasible_hv"].to_numpy(dtype=float) for frame in frames])
        feas_frac_mat = np.stack([frame["feasible_fraction"].to_numpy(dtype=float) for frame in frames])
        med_hv, low_hv, high_hv = compute_bootstrap_ci(feas_hv_mat, confidence_level, n_bootstraps, bootstrap_seed)
        med_ff, low_ff, high_ff = compute_bootstrap_ci(feas_frac_mat, confidence_level, n_bootstraps, bootstrap_seed)

        for step_i, step in enumerate(eval_steps):
            series_rows.append({
                "algorithm": algo_name,
                "cumulative_astra_evaluations": step,
                "median_feasible_hv": med_hv[step_i],
                "ci_lower_feasible_hv": low_hv[step_i],
                "ci_upper_feasible_hv": high_hv[step_i],
                "median_feasible_fraction": med_ff[step_i],
                "ci_lower_feasible_fraction": low_ff[step_i],
                "ci_upper_feasible_fraction": high_ff[step_i],
            })

        # first_feasible_eval_index is cumulative, so the final row holds the run's value.
        first_feasible = [frame["first_feasible_eval_index"].iloc[-1] for frame in frames]
        first_feasible = [value for value in first_feasible if not pd.isna(value)]
        invalid_counts = [frame["invalid_run_count"].iloc[-1] for frame in frames]
        total_evaluations = float(sum(frame["cumulative_astra_evaluations"].iloc[-1] for frame in frames))
        row = {
            "algorithm": algo_name,
            "num_seeds": len(seeds),
            "final_median_feasible_hv": float(med_hv[-1]),
            "final_ci_lower_hv": float(low_hv[-1]),
            "final_ci_upper_hv": float(high_hv[-1]),
            "median_evals_to_first_feasible": float(np.median(first_feasible)) if first_feasible else np.nan,
            "mean_final_feasible_fraction": float(np.mean([frame["feasible_fraction"].iloc[-1] for frame in frames])),
            "mean_final_pareto_size": float(np.mean([frame["pareto_set_size"].iloc[-1] for frame in frames])),
            "mean_invalid_run_count": float(np.mean(invalid_counts)),
            "failure_rate": float(np.sum(invalid_counts)) / total_evaluations if total_evaluations else np.nan,
            "mean_total_wallclock_s": float(np.mean([frame["total_wallclock_s"].iloc[-1] for frame in frames])),
            "mean_total_sim_runtime_s": float(np.mean([frame["total_simulation_runtime_s"].iloc[-1] for frame in frames])),
            "bootstrap_seed": bootstrap_seed,
        }
        for name, sign in objectives:
            values = [frame.attrs.get("objective_extrema", {}).get(name) for frame in frames]
            values = [value for value in values if value is not None]
            row[_extremum_column(name, sign)] = (min(values) if sign == -1 else max(values)) if values else np.nan
        summary_rows.append(row)

    return pd.DataFrame(series_rows), pd.DataFrame(summary_rows)
