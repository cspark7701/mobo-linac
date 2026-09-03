"""
Unit tests for Centralized Configuration System & Strict Schema Validation (Task 17).
"""

import json
from pathlib import Path
import pytest
import sys
import torch

from mobo_linac.config import (
    ConstraintsConfig,
    DesignVariableConfig,
    ExecutionConfig,
    GpModelConfig,
    MoboConfig,
    ObjectiveConfig,
    export_config_schema,
    generate_config_markdown_docs,
    load_config,
)
from mobo_linac.cli import main


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


def test_invalid_coupled_variable_rejected():
    """Verify that coupled variables without targets are rejected."""
    bad_coupled = DesignVariableConfig(
        name="bad_coupled",
        astra_key="dummy",
        unit="deg",
        nominal_value=0.0,
        ratio=0.1,
        lower_bound=-10.0,
        upper_bound=10.0,
        is_coupled=True,
        coupled_targets=None,
    )
    with pytest.raises(ValueError, match="coupled_targets"):
        bad_coupled.validate()


def test_invalid_objective_direction_and_sign():
    """Verify objective validation fails for invalid direction or sign mismatch."""
    with pytest.raises(ValueError, match="physical_direction"):
        ObjectiveConfig(
            name="obj1",
            explicit_name="Objective 1",
            unit="m",
            physical_direction="sideways",
            model_sign=-1,
        ).validate()

    with pytest.raises(ValueError, match="model_sign"):
        ObjectiveConfig(
            name="obj2",
            explicit_name="Objective 2",
            unit="m",
            physical_direction="minimize",
            model_sign=1,  # Minimization must be -1
        ).validate()


def test_invalid_constraints_rejected():
    """Verify constraint validation fails on non-physical thresholds."""
    with pytest.raises(ValueError, match="kinetic energy constraints"):
        ConstraintsConfig(
            min_mean_kinetic_energy_eV=220.0e6,
            max_mean_kinetic_energy_eV=200.0e6,
        ).validate()

    with pytest.raises(ValueError, match="min_transmission"):
        ConstraintsConfig(min_transmission=1.5).validate()

    with pytest.raises(ValueError, match="Beam size constraints"):
        ConstraintsConfig(max_sigma_x_m=-1.0).validate()


def test_duplicate_design_variable_rejected():
    """Verify MoboConfig rejects duplicate design variable names."""
    dv1 = DesignVariableConfig("var1", "key1", "T", 1.0, 0.1, 0.5, 1.5)
    dv2 = DesignVariableConfig("var1", "key2", "T", 1.0, 0.1, 0.5, 1.5)
    obj = ObjectiveConfig("obj1", "Explicit Obj", "m", "minimize", -1)

    cfg = MoboConfig(
        version="1.0",
        description="Test",
        design_variables=[dv1, dv2],
        objectives=[obj],
        constraints=ConstraintsConfig(),
    )
    with pytest.raises(ValueError, match="Duplicate design variable"):
        cfg.validate()


def test_export_config_schema(tmp_path):
    """Verify JSON Schema export."""
    schema_path = tmp_path / "schema.json"
    schema = export_config_schema(schema_path)

    assert schema["$schema"] == "http://json-schema.org/draft-07/schema#"
    assert "design_variables" in schema["properties"]
    assert schema_path.exists()

    with open(schema_path, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded["title"] == "MoboConfig"


def test_generate_config_markdown_docs():
    """Verify Markdown documentation generator."""
    config = load_config("configs/mobo_200MeV.yaml")
    docs = generate_config_markdown_docs(config)

    assert "# Linac MOBO Configuration:" in docs
    assert "## 1. Design Variables (Decision Space)" in docs
    assert "## 2. Optimization Objectives" in docs
    assert "## 3. Physical Beam & Diagnostic Constraints" in docs
    assert "| `solenoid_field_T` |" in docs
    assert "| `norm_emit_x` |" in docs


def test_cli_validate_config(capsys, tmp_path):
    """Verify CLI validate-config subcommand execution and exports."""
    schema_p = tmp_path / "schema.json"
    docs_p = tmp_path / "config_docs.md"

    sys.argv = [
        "mobo-linac",
        "validate-config",
        "--config", "configs/publication.yaml",
        "--export-schema", str(schema_p),
        "--export-docs", str(docs_p),
    ]
    main()

    captured = capsys.readouterr()
    assert "is VALID" in captured.out
    assert schema_p.exists()
    assert docs_p.exists()


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
