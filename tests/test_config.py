"""
Unit tests for Centralized Configuration System (Task 04).
"""

import json
from pathlib import Path
import pytest
import torch

from mobo_linac.config import (
    ConstraintsConfig,
    DesignVariableConfig,
    ExecutionConfig,
    MoboConfig,
    ObjectiveConfig,
    load_config,
)


def test_load_default_yaml_config():
    """Verify loading default YAML configuration file."""
    config = load_config("configs/mobo_200MeV.yaml")
    assert config.version == "1.0"
    assert len(config.design_variables) == 6
    assert len(config.objectives) == 3
    assert config.constraints.max_sigma_x_m == 1.0e-3
    assert config.constraints.min_mean_kinetic_energy_eV == 195.0e6


def test_bounds_ordering_negative_parameters():
    """Verify that bounds for negative parameters are ordered lower_bound <= upper_bound."""
    config = load_config("configs/mobo_200MeV.yaml")
    bounds_tensor = config.get_parameter_bounds_tensor()

    assert bounds_tensor.shape == (2, 6)
    lower = bounds_tensor[0]
    upper = bounds_tensor[1]

    # Every lower bound must be <= upper bound
    for i, (l, u) in enumerate(zip(lower, upper)):
        assert l <= u, f"Variable {config.design_variables[i].name} has invalid bounds ordering: {l} > {u}"

    # Specifically check quad 2 (negative value)
    quad2 = config.design_variables[2]
    assert quad2.nominal_value < 0
    assert quad2.lower_bound < quad2.nominal_value < quad2.upper_bound


def test_coupled_phase_mapping():
    """Verify that coupled cavity phases are explicitly declared."""
    config = load_config("configs/mobo_200MeV.yaml")

    acc1_2 = config.design_variables[4]
    assert acc1_2.is_coupled is True
    assert acc1_2.coupled_targets == ["cavity:phi(2)", "cavity:phi(3)"]

    acc3_4 = config.design_variables[5]
    assert acc3_4.is_coupled is True
    assert acc3_4.coupled_targets == ["cavity:phi(4)", "cavity:phi(5)"]


def test_invalid_bounds_rejected():
    """Verify that validation rejects lower_bound > upper_bound."""
    invalid_var = DesignVariableConfig(
        name="bad_var",
        astra_key="dummy",
        unit="T",
        nominal_value=1.0,
        ratio=0.5,
        lower_bound=5.0,
        upper_bound=1.0,
    )
    with pytest.raises(ValueError, match="lower_bound"):
        invalid_var.validate()


def test_config_serialization(tmp_path):
    """Verify JSON and YAML serialization and deserialization."""
    config = load_config("configs/mobo_200MeV.yaml")

    json_path = tmp_path / "config.json"
    config.save_json(json_path)
    assert json_path.exists()

    with open(json_path, "r", encoding="utf-8") as f:
        loaded_dict = json.load(f)

    assert loaded_dict["version"] == "1.0"
    assert len(loaded_dict["design_variables"]) == 6

    yaml_path = tmp_path / "config.yaml"
    config.save_yaml(yaml_path)
    assert yaml_path.exists()
