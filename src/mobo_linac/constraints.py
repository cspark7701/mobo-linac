"""
Canonical Constraints Module for mobo_linac.

Evaluates beam quality constraints and feasibility status using centralized
configuration thresholds.
"""

from typing import Dict, Optional, Tuple, Union
import torch

from mobo_linac.config import ConstraintsConfig, MoboConfig


class ConstraintEvaluator:
    """
    Evaluates beam quality constraints against configurable thresholds.
    """

    def __init__(self, constraints_config: Optional[ConstraintsConfig] = None):
        if constraints_config is None:
            self.config = ConstraintsConfig()
        else:
            self.config = constraints_config
        self.config.validate()

    def check_feasibility(self, diagnostics: Dict[str, float]) -> bool:
        """
        Check whether an evaluation meets all physical beam quality constraints.

        Args:
            diagnostics: Dictionary containing diagnostic statistics:
                ['sigma_x'/'sigma_x_m', 'sigma_y'/'sigma_y_m', 'sigma_xp'/'sigma_xp_rad',
                 'sigma_yp'/'sigma_yp_rad', 'sigma_z'/'sigma_z_m',
                 'mean_kinetic_energy'/'mean_kinetic_energy_eV']

        Returns:
            True if all constraints are satisfied, False otherwise.
        """
        if not diagnostics:
            return False

        sigma_x = diagnostics.get("sigma_x", diagnostics.get("sigma_x_m", 999.0))
        sigma_y = diagnostics.get("sigma_y", diagnostics.get("sigma_y_m", 999.0))
        sigma_xp = diagnostics.get("sigma_xp", diagnostics.get("sigma_xp_rad", 999.0))
        sigma_yp = diagnostics.get("sigma_yp", diagnostics.get("sigma_yp_rad", 999.0))
        sigma_z = diagnostics.get("sigma_z", diagnostics.get("sigma_z_m", 999.0))
        energy = diagnostics.get("mean_kinetic_energy", diagnostics.get("mean_kinetic_energy_eV", 0.0))
        transmission = diagnostics.get("transmission", 1.0)

        is_feasible = (
            (sigma_x <= self.config.max_sigma_x_m)
            and (sigma_y <= self.config.max_sigma_y_m)
            and (sigma_xp <= self.config.max_sigma_xp_rad)
            and (sigma_yp <= self.config.max_sigma_yp_rad)
            and (sigma_z <= self.config.max_sigma_z_m)
            and (energy >= self.config.min_mean_kinetic_energy_eV)
            and (energy <= self.config.max_mean_kinetic_energy_eV)
            and (transmission >= self.config.min_transmission)
        )
        return bool(is_feasible)

    def compute_violations(self, diagnostics: Dict[str, float]) -> Dict[str, float]:
        """
        Computes constraint violation magnitudes (0.0 if satisfied, > 0.0 if violated).

        Args:
            diagnostics: Dictionary containing diagnostic metrics.

        Returns:
            Dictionary of violation amounts for each constraint.
        """
        sigma_x = diagnostics.get("sigma_x", diagnostics.get("sigma_x_m", 999.0))
        sigma_y = diagnostics.get("sigma_y", diagnostics.get("sigma_y_m", 999.0))
        sigma_xp = diagnostics.get("sigma_xp", diagnostics.get("sigma_xp_rad", 999.0))
        sigma_yp = diagnostics.get("sigma_yp", diagnostics.get("sigma_yp_rad", 999.0))
        sigma_z = diagnostics.get("sigma_z", diagnostics.get("sigma_z_m", 999.0))
        energy = diagnostics.get("mean_kinetic_energy", diagnostics.get("mean_kinetic_energy_eV", 0.0))
        transmission = diagnostics.get("transmission", 1.0)

        return {
            "sigma_x_m": max(0.0, sigma_x - self.config.max_sigma_x_m),
            "sigma_y_m": max(0.0, sigma_y - self.config.max_sigma_y_m),
            "sigma_xp_rad": max(0.0, sigma_xp - self.config.max_sigma_xp_rad),
            "sigma_yp_rad": max(0.0, sigma_yp - self.config.max_sigma_yp_rad),
            "sigma_z_m": max(0.0, sigma_z - self.config.max_sigma_z_m),
            "energy_lower_eV": max(0.0, self.config.min_mean_kinetic_energy_eV - energy),
            "energy_upper_eV": max(0.0, energy - self.config.max_mean_kinetic_energy_eV),
            "transmission": max(0.0, self.config.min_transmission - transmission),
        }
