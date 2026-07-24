"""
Utility functions for MOBO optimization loops.
Refactored to use centralized config, objectives, and constraint evaluations.
"""

from typing import Dict, Tuple
import torch

from mobo_linac.config import load_config
from mobo_linac.constraints import ConstraintEvaluator
from mobo_linac.objectives import extract_physical_objectives, transform_to_model_space
from run_astra import run_astra_simulation, get_objectives, get_diagnostics

# Load centralized config and constraint evaluator
_CONFIG = load_config()
_CONSTRAINT_EVALUATOR = ConstraintEvaluator(_CONFIG.constraints)


def evaluate_objective(params: torch.Tensor, timeout: int = 30) -> Tuple[torch.Tensor, torch.Tensor, Dict[str, float]]:
    """
    Evaluates a candidate parameter set and returns model-space objectives, feasibility, and diagnostics.
    """
    with torch.no_grad():
        values = params.detach().tolist()
        try:
            stats = run_astra_simulation(values, timeout=timeout)
            if stats is None or len(stats.get("norm_emit_x", [])) == 0:
                raise ValueError("ASTRA simulation produced empty or invalid stats.")

            phys_objs = get_objectives(stats)
            diags = get_diagnostics(stats)
            is_feasible = _CONSTRAINT_EVALUATOR.check_feasibility(diags)
        except Exception as e:
            print(f"Simulation error/timeout for params {values}: {e}")
            phys_objs = (1.0e-3, 1.0e-3, 1.0e8)
            diags = {
                "emit_x": 1.0e-3,
                "emit_y": 1.0e-3,
                "sigma_energy": 1.0e8,
                "sigma_x": 999.0,
                "sigma_y": 999.0,
                "sigma_xp": 999.0,
                "sigma_yp": 999.0,
                "sigma_z": 999.0,
                "mean_kinetic_energy": 0.0,
            }
            is_feasible = False

        feasible = torch.tensor(is_feasible, dtype=torch.bool)
        objs_model = transform_to_model_space(phys_objs, _CONFIG)
        return objs_model, feasible, diags


def evaluate_constrained_objective(params: torch.Tensor, timeout: int = 30):
    """
    Evaluates simulation and returns model-space objectives, 9-outcome tensor, feasibility, and diagnostics.
    """
    with torch.no_grad():
        values = params.detach().tolist()
        try:
            stats = run_astra_simulation(values, timeout=timeout)
            if stats is None or len(stats.get("norm_emit_x", [])) == 0:
                raise ValueError("ASTRA simulation produced empty or invalid stats.")

            phys_objs = get_objectives(stats)
            diags = get_diagnostics(stats)
            is_feasible = _CONSTRAINT_EVALUATOR.check_feasibility(diags)
        except Exception as e:
            print(f"Simulation error/timeout for params {values}: {e}")
            phys_objs = (1.0e-3, 1.0e-3, 1.0e8)
            diags = {
                "emit_x": 1.0e-3,
                "emit_y": 1.0e-3,
                "sigma_energy": 1.0e8,
                "sigma_x": 999.0,
                "sigma_y": 999.0,
                "sigma_xp": 999.0,
                "sigma_yp": 999.0,
                "sigma_z": 999.0,
                "mean_kinetic_energy": 0.0,
            }
            is_feasible = False

        feasible = torch.tensor(is_feasible, dtype=torch.bool)
        objs_model = transform_to_model_space(phys_objs, _CONFIG)
        outcomes_9 = torch.tensor(
            [
                objs_model[0].item(),
                objs_model[1].item(),
                objs_model[2].item(),
                diags["sigma_x"],
                diags["sigma_y"],
                diags["sigma_xp"],
                diags["sigma_yp"],
                diags["sigma_z"],
                diags["mean_kinetic_energy"],
            ],
            dtype=torch.double,
        )

        return objs_model, outcomes_9, feasible, diags


def compute_ref_point(train_Y: torch.Tensor) -> torch.Tensor:
    """
    Computes a reference point for Hypervolume calculation in model (maximization) space.
    """
    min_vals_negated = train_Y.min(dim=0).values
    max_vals_negated = train_Y.max(dim=0).values

    ranges_negated = max_vals_negated - min_vals_negated
    epsilon = 1e-6
    offset = 0.05 * (ranges_negated + epsilon)

    ref_point = min_vals_negated - offset
    return ref_point