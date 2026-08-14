"""
Unit tests for Config-Driven Dynamic Parameter Mapping & Beamline Element Decoupling (Task 02).
"""

import pytest
from pathlib import Path
from mobo_linac.config import DesignVariableConfig, MoboConfig, load_config
from mobo_linac.astra.runner import apply_parameters_to_astra, PARAMETER_NAMES, AstraRunner, run_astra_eval


def test_apply_parameters_default_fallback():
    """Verify default fallback parameter mapping for standard 6 parameters."""
    mock_sim = {}
    params = [0.28, 5.0, -4.5, 30.0, -15.0, 10.0]

    applied = apply_parameters_to_astra(mock_sim, params, config=None)

    assert applied == PARAMETER_NAMES
    assert mock_sim["solenoid:maxb(1)"] == 0.28
    assert mock_sim["quadrupole:q_grad(1)"] == 5.0
    assert mock_sim["quadrupole:q_grad(2)"] == -4.5
    assert mock_sim["cavity:phi(1)"] == 30.0
    assert mock_sim["cavity:phi(2)"] == -15.0
    assert mock_sim["cavity:phi(3)"] == -15.0  # Coupled ACC1/ACC2
    assert mock_sim["cavity:phi(4)"] == 10.0
    assert mock_sim["cavity:phi(5)"] == 10.0   # Coupled ACC3/ACC4


def test_apply_parameters_from_loaded_config():
    """Verify dynamic mapping using a loaded MoboConfig instance."""
    config = load_config("configs/mobo_200MeV.yaml")
    mock_sim = {}
    params = [0.25, 4.0, -3.0, 25.0, -10.0, 5.0]

    applied = apply_parameters_to_astra(mock_sim, params, config=config)

    assert len(applied) == 6
    assert applied[0] == "solenoid_field_T"
    assert mock_sim["solenoid:maxb(1)"] == 0.25
    assert mock_sim["quadrupole:q_grad(1)"] == 4.0
    assert mock_sim["quadrupole:q_grad(2)"] == -3.0
    assert mock_sim["cavity:phi(1)"] == 25.0
    assert mock_sim["cavity:phi(2)"] == -10.0
    assert mock_sim["cavity:phi(3)"] == -10.0
    assert mock_sim["cavity:phi(4)"] == 5.0
    assert mock_sim["cavity:phi(5)"] == 5.0


def test_apply_parameters_custom_decoupled_cavities():
    """Verify dynamic mapping with custom decoupled cavity phases (7 variables)."""
    custom_dvs = [
        DesignVariableConfig(name="sol", astra_key="solenoid:maxb(1)", unit="T", nominal_value=0.28, ratio=0.1, lower_bound=0.2, upper_bound=0.35),
        DesignVariableConfig(name="q1", astra_key="quadrupole:q_grad(1)", unit="T/m", nominal_value=5.0, ratio=0.1, lower_bound=0.0, upper_bound=10.0),
        DesignVariableConfig(name="q2", astra_key="quadrupole:q_grad(2)", unit="T/m", nominal_value=-5.0, ratio=0.1, lower_bound=-10.0, upper_bound=0.0),
        DesignVariableConfig(name="gun_phi", astra_key="cavity:phi(1)", unit="deg", nominal_value=30.0, ratio=0.1, lower_bound=0.0, upper_bound=60.0),
        DesignVariableConfig(name="acc1_phi", astra_key="cavity:phi(2)", unit="deg", nominal_value=-20.0, ratio=0.1, lower_bound=-40.0, upper_bound=0.0),
        DesignVariableConfig(name="acc2_phi", astra_key="cavity:phi(3)", unit="deg", nominal_value=-15.0, ratio=0.1, lower_bound=-40.0, upper_bound=0.0),
        DesignVariableConfig(name="acc3_4_phi", astra_key="cavity:phi(4,5)", unit="deg", nominal_value=0.0, ratio=0.1, lower_bound=-20.0, upper_bound=20.0, is_coupled=True, coupled_targets=["cavity:phi(4)", "cavity:phi(5)"]),
    ]

    mock_sim = {}
    params = [0.29, 6.0, -4.0, 32.0, -18.0, -12.0, 5.0]

    applied = apply_parameters_to_astra(mock_sim, params, config={"design_variables": custom_dvs})

    assert len(applied) == 7
    assert applied == ["sol", "q1", "q2", "gun_phi", "acc1_phi", "acc2_phi", "acc3_4_phi"]
    assert mock_sim["solenoid:maxb(1)"] == 0.29
    assert mock_sim["quadrupole:q_grad(1)"] == 6.0
    assert mock_sim["quadrupole:q_grad(2)"] == -4.0
    assert mock_sim["cavity:phi(1)"] == 32.0
    assert mock_sim["cavity:phi(2)"] == -18.0  # ACC1 independent
    assert mock_sim["cavity:phi(3)"] == -12.0  # ACC2 independent
    assert mock_sim["cavity:phi(4)"] == 5.0    # Coupled ACC3/ACC4
    assert mock_sim["cavity:phi(5)"] == 5.0


def test_parameter_length_mismatch_raises():
    """Verify ValueError is raised when parameter count does not match config or default."""
    mock_sim = {}

    # Default expects 6
    with pytest.raises(ValueError, match="Expected 6"):
        apply_parameters_to_astra(mock_sim, [0.1, 0.2, 0.3], config=None)

    # Config with 6 variables expects 6
    config = load_config("configs/mobo_200MeV.yaml")
    with pytest.raises(ValueError, match="does not match"):
        apply_parameters_to_astra(mock_sim, [0.1, 0.2], config=config)


def test_astra_runner_config_support():
    """Verify AstraRunner retains and passes config."""
    config = load_config("configs/mobo_200MeV.yaml")
    runner = AstraRunner(run_id="test_run", config=config)
    assert runner.config is config
