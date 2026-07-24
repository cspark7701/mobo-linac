"""
Canonical Constraints Module for mobo_linac.

Evaluates beam quality constraints and feasibility status using centralized
configuration thresholds.
"""

import math
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
                ['sigma_x_m', 'sigma_y_m', 'sigma_xp_rad', 'sigma_yp_rad',
                 'sigma_z_m', 'mean_kinetic_energy_eV', 'transmission_fraction']

        Returns:
            True if all constraints are satisfied, False otherwise.
        """
        if not diagnostics:
            return False

        # Require explicit or alias transmission field
        if "transmission_fraction" not in diagnostics and "transmission" not in diagnostics:
            return False

        transmission = diagnostics.get("transmission_fraction", diagnostics.get("transmission"))
        if transmission is None or math.isnan(transmission) or math.isinf(transmission):
            return False

        sigma_x = diagnostics.get("sigma_x_m", diagnostics.get("sigma_x", 999.0))
        sigma_y = diagnostics.get("sigma_y_m", diagnostics.get("sigma_y", 999.0))
        sigma_xp = diagnostics.get("sigma_xp_rad", diagnostics.get("sigma_xp", 999.0))
        sigma_yp = diagnostics.get("sigma_yp_rad", diagnostics.get("sigma_yp", 999.0))
        sigma_z = diagnostics.get("sigma_z_m", diagnostics.get("sigma_z", 999.0))
        energy = diagnostics.get("mean_kinetic_energy_eV", diagnostics.get("mean_kinetic_energy", 0.0))

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
        transmission = diagnostics.get("transmission_fraction", diagnostics.get("transmission", 0.0))
        sigma_x = diagnostics.get("sigma_x_m", diagnostics.get("sigma_x", 999.0))
        sigma_y = diagnostics.get("sigma_y_m", diagnostics.get("sigma_y", 999.0))
        sigma_xp = diagnostics.get("sigma_xp_rad", diagnostics.get("sigma_xp", 999.0))
        sigma_yp = diagnostics.get("sigma_yp_rad", diagnostics.get("sigma_yp", 999.0))
        sigma_z = diagnostics.get("sigma_z_m", diagnostics.get("sigma_z", 999.0))
        energy = diagnostics.get("mean_kinetic_energy_eV", diagnostics.get("mean_kinetic_energy", 0.0))

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
