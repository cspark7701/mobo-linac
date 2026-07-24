"""
Robustness and Sensitivity Analysis Evaluator for Linac MOBO (Task 07).

Evaluates machine and beam perturbation sensitivity across representative Pareto candidates,
computing mean, standard deviation, percentile intervals, probability of feasibility,
worst constraint margins, and identifying robust operating points.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import numpy as np
import pandas as pd
import torch
import yaml

from mobo_linac.config import MoboConfig, load_config
from mobo_linac.evaluation import EvaluationResult, create_evaluation_result
from mobo_linac.metrics.reporting import normalize_objectives_physical


def select_representative_pareto_candidates(
    results: List[EvaluationResult],
) -> Dict[str, EvaluationResult]:
    """
    Selects representative Pareto candidates:
    - min_emit_x: Objective extreme for horizontal emittance
    - min_emit_y: Objective extreme for vertical emittance
    - min_sigma_energy: Objective extreme for energy spread
    - knee_point: Solution closest to origin in normalized objective space
    - balanced: Solution closest to centroid of Pareto set

    Args:
        results: List of EvaluationResult objects.

    Returns:
        Dict mapping candidate label -> EvaluationResult.
    """
    feasible_results = [res for res in results if res.simulation_valid and res.physically_feasible and res.objectives_physical]
    if not feasible_results:
        raise ValueError("No physically feasible candidates available for robustness analysis.")

    # 1. Objective extremes
    min_emit_x_res = min(feasible_results, key=lambda r: r.objectives_physical[0])
    min_emit_y_res = min(feasible_results, key=lambda r: r.objectives_physical[1])
    min_sigma_e_res = min(feasible_results, key=lambda r: r.objectives_physical[2])

    # Extract all physical objective vectors
    objs_arr = np.array([r.objectives_physical for r in feasible_results])
    norm_objs = objs_arr / np.array([1.0e-6, 1.0e-6, 1.0e6])

    # 2. Knee point (closest to ideal minimum [0, 0, 0] in normalized space)
    dist_to_ideal = np.linalg.norm(norm_objs, axis=1)
    knee_idx = int(np.argmin(dist_to_ideal))
    knee_res = feasible_results[knee_idx]

    # 3. Balanced point (closest to centroid of Pareto set)
    centroid = np.mean(norm_objs, axis=0)
    dist_to_centroid = np.linalg.norm(norm_objs - centroid, axis=1)
    balanced_idx = int(np.argmin(dist_to_centroid))
    balanced_res = feasible_results[balanced_idx]

    return {
        "min_emit_x": min_emit_x_res,
        "min_emit_y": min_emit_y_res,
        "min_sigma_energy": min_sigma_e_res,
        "knee_point": knee_res,
        "balanced": balanced_res,
    }


def generate_perturbed_parameters(
    nominal_x: List[float],
    num_perturbations: int = 50,
    seed: int = 42,
    phase_std_deg: float = 0.10,
    field_relative_std: float = 0.001,
) -> List[List[float]]:
    """
    Generates perturbed parameter vectors around a nominal design vector.

    Args:
        nominal_x: Nominal 6D design vector.
        num_perturbations: Number of perturbed samples to generate.
        seed: Random seed.
        phase_std_deg: Phase jitter standard deviation (degrees).
        field_relative_std: Relative field jitter standard deviation (dimensionless).

    Returns:
        List of 6D perturbed parameter vectors.
    """
    rng = np.random.default_rng(seed)
    nominal_arr = np.array(nominal_x, dtype=np.float64)

    # 6D design vector: [solenoid, quad1, quad2, gun_phase, acc1_2_phase, acc3_4_phase]
    rel_stds = np.array([
        field_relative_std,  # solenoid
        field_relative_std,  # quad 1
        field_relative_std,  # quad 2
        0.0,                 # gun phase (absolute std added below)
        0.0,                 # acc1_2 phase
        0.0,                 # acc3_4 phase
    ])

    abs_stds = np.array([
        0.0,
        0.0,
        0.0,
        phase_std_deg,
        phase_std_deg,
        phase_std_deg,
    ])

    perturbed_samples = []
    for _ in range(num_perturbations):
        rel_noise = rng.normal(loc=0.0, scale=rel_stds)
        abs_noise = rng.normal(loc=0.0, scale=abs_stds)

        perturbed_x = nominal_arr * (1.0 + rel_noise) + abs_noise
        perturbed_samples.append(perturbed_x.tolist())

    return perturbed_samples


def compute_robustness_summary(
    candidate_label: str,
    nominal_result: EvaluationResult,
    perturbed_results: List[EvaluationResult],
) -> Dict[str, Any]:
    """
    Computes statistical robustness metrics for a Pareto candidate across perturbed runs.

    Args:
        candidate_label: Candidate name (e.g. 'knee_point').
        nominal_result: Nominal EvaluationResult.
        perturbed_results: List of perturbed EvaluationResult records.

    Returns:
        Dictionary of robustness metrics.
    """
    total_evals = len(perturbed_results)
    valid_results = [r for r in perturbed_results if r.simulation_valid and r.objectives_physical]
    feasible_results = [r for r in valid_results if r.physically_feasible]

    prob_feasibility = float(len(feasible_results)) / float(total_evals) if total_evals > 0 else 0.0

    if valid_results:
        emit_x_vals = [r.objectives_physical[0] for r in valid_results]
        emit_y_vals = [r.objectives_physical[1] for r in valid_results]
        sigma_e_vals = [r.objectives_physical[2] for r in valid_results]

        mean_emit_x = float(np.mean(emit_x_vals))
        std_emit_x = float(np.std(emit_x_vals))
        p5_emit_x = float(np.percentile(emit_x_vals, 5))
        p95_emit_x = float(np.percentile(emit_x_vals, 95))

        mean_emit_y = float(np.mean(emit_y_vals))
        std_emit_y = float(np.std(emit_y_vals))

        mean_sigma_e = float(np.mean(sigma_e_vals))
        std_sigma_e = float(np.std(sigma_e_vals))
    else:
        mean_emit_x = std_emit_x = p5_emit_x = p95_emit_x = np.nan
        mean_emit_y = std_emit_y = np.nan
        mean_sigma_e = std_sigma_e = np.nan

    # Robust score: feasibility probability divided by normalized emittance growth factor
    nom_objs = nominal_result.objectives_physical if nominal_result.objectives_physical else [1e-6, 1e-6, 1e6]
    growth_x = mean_emit_x / nom_objs[0] if not np.isnan(mean_emit_x) and nom_objs[0] > 0 else 2.0
    robust_score = float(prob_feasibility / max(1.0, growth_x))

    return {
        "candidate_label": candidate_label,
        "evaluation_id": nominal_result.evaluation_id,
        "probability_of_feasibility": prob_feasibility,
        "robust_score": robust_score,
        "nominal_emit_x": nom_objs[0],
        "mean_emit_x": mean_emit_x,
        "std_emit_x": std_emit_x,
        "p5_emit_x": p5_emit_x,
        "p95_emit_x": p95_emit_x,
        "nominal_emit_y": nom_objs[1],
        "mean_emit_y": mean_emit_y,
        "std_emit_y": std_emit_y,
        "nominal_sigma_energy": nom_objs[2],
        "mean_sigma_energy": mean_sigma_e,
        "std_sigma_energy": std_sigma_e,
        "is_fragile": prob_feasibility < 0.80,
    }
