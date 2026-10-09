"""
Canonical Constraints Module for mobo_linac.

Evaluates beam quality constraints and feasibility status using centralized
configuration thresholds.
"""

from typing import Dict, Optional, Union
import torch

from mobo_linac.config import ConstraintsConfig, MoboConfig
from mobo_linac.diagnostics import (
    DIAGNOSTIC_CHANNELS, constraint_sides, diagnostic_observations,
    normalize_diagnostics, valid_channel_measurement,
)


class ConstraintEvaluator:
    """
    Evaluates beam quality constraints against configurable thresholds.
    """

    def __init__(self, constraints_config: ConstraintsConfig):
        if not isinstance(constraints_config, ConstraintsConfig):
            raise TypeError("ConstraintEvaluator requires the active ConstraintsConfig.")
        self.config = constraints_config
        self.config.validate()

    def check_feasibility(self, diagnostics: Dict[str, float]) -> bool:
        """
        Check whether an evaluation meets all physical beam quality constraints.

        Args:
            diagnostics: Dictionary containing diagnostic statistics:
                ['sigma_x_m', 'sigma_y_m', 'sigma_xp_rad', 'sigma_yp_rad',
                 'sigma_z_m', 'mean_kinetic_energy_eV', 'transmission_fraction']

        Returns:
            True if all constraints are satisfied, False otherwise.
        """
        observations = diagnostic_observations(diagnostics)
        if observations is None:
            return False
        return all(observations[index] >= threshold if side == "lower"
                   else observations[index] <= threshold
                   for index, side, threshold, _ in constraint_sides(self.config))

    def compute_violations(self, diagnostics: Dict[str, float]) -> Dict[str, float]:
        """
        Computes constraint violation magnitudes (0.0 if satisfied, > 0.0 if violated).

        Args:
            diagnostics: Dictionary containing diagnostic metrics.

        Returns:
            Dictionary of violation amounts for each constraint.
            Missing or invalid measurements have an unknown violation, represented by infinity.
        """
        normalized = normalize_diagnostics(diagnostics)
        violations = {}
        for index, side, threshold, name in constraint_sides(self.config):
            channel = DIAGNOSTIC_CHANNELS[index]
            value = normalized.get(channel.name)
            if not valid_channel_measurement(channel, value):
                violations[name] = float("inf")
            else:
                violations[name] = max(0.0, threshold - value if side == "lower" else value - threshold)
        return violations


def get_botorch_constraint_functions(
    config: Union[ConstraintsConfig, MoboConfig],
    num_objectives: Optional[int] = None,
) -> list:
    """
    Dynamically constructs a list of BoTorch tensor constraint functions c_i(Y) <= 0
    from configuration thresholds.

    Args:
        config: MoboConfig or ConstraintsConfig instance.
        num_objectives: Actual objective output count; defaults to the configured count
            and is required with a bare ConstraintsConfig.

    Returns:
        List of callable constraint functions returning Tensors where <= 0 indicates feasibility.
    """
    if isinstance(config, MoboConfig):
        c_config = config.constraints
    elif isinstance(config, ConstraintsConfig):
        c_config = config
    else:
        raise TypeError("Constraint functions require a MoboConfig or ConstraintsConfig.")

    c_config.validate()
    offset = num_objectives if num_objectives is not None else (
        len(config.objectives) if isinstance(config, MoboConfig) else None)
    if offset is None:
        raise ValueError("num_objectives is required when only constraint thresholds are supplied.")
    if type(offset) is not int or offset < 1:
        raise ValueError("num_objectives must be a positive integer.")

    functions = []
    for index, side, threshold, _ in constraint_sides(c_config):
        def constraint(Y, index=index, side=side, threshold=threshold):
            if Y.shape[-1] != offset + len(DIAGNOSTIC_CHANNELS):
                raise ValueError("Acquisition outcomes do not match objective/diagnostic layout.")
            value = Y[..., offset + index]
            residual = threshold - value if side == "lower" else value - threshold
            return torch.where(torch.isfinite(value), residual, torch.full_like(value, float("inf")))
        functions.append(constraint)
    return functions
