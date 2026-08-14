"""
Unit tests for Machine and Beam Robustness Analysis (Task 07).
"""

import pytest
import numpy as np

from mobo_linac.evaluation import EvaluationResult, FailureCategory
from mobo_linac.astra.runner import apply_parameters_to_astra
from mobo_linac.robustness.evaluator import (
    PerturbationSpecification,
    PerturbedMachineState,
    compute_robustness_summary,
    generate_perturbed_machine_states,
    generate_perturbed_parameters,
    load_perturbation_spec,
    select_representative_pareto_candidates,
)


@pytest.fixture
def sample_pareto_results():
    results = []
    for i in range(1, 6):
        res = EvaluationResult(
            evaluation_id=f"eval_{i}",
            run_id="test_run",
            x_physical=[0.19 + 0.01 * i, 1.2, -2.8, 35.0, -39.0, 310.0],
            objectives_physical=[1.0e-6 * i, 2.0e-6 / i, 0.2e6 * i],
            objectives_model=[-1.0e-6 * i, -2.0e-6 / i, -0.2e6 * i],
            diagnostics={
                "sigma_x_m": 0.5e-3,
                "sigma_y_m": 0.5e-3,
                "sigma_xp_rad": 0.5e-3,
                "sigma_yp_rad": 0.5e-3,
                "sigma_z_m": 0.5e-3,
                "mean_kinetic_energy_eV": 200.0e6,
                "transmission_fraction": 1.0,
            },
            simulation_valid=True,
            physically_feasible=True,
            failure_category=FailureCategory.SUCCESS.value,
        )
        results.append(res)
    return results


def test_select_representative_pareto_candidates(sample_pareto_results):
    """Verify representative Pareto candidate selection."""
    candidates = select_representative_pareto_candidates(sample_pareto_results)

    assert "min_emit_x" in candidates
    assert "min_emit_y" in candidates
    assert "min_sigma_energy" in candidates
    assert "knee_point" in candidates
    assert "balanced" in candidates

    # min_emit_x should be eval_1 (1.0e-6)
    assert candidates["min_emit_x"].evaluation_id == "eval_1"
    # min_sigma_energy should be eval_1 (0.2e6)
    assert candidates["min_sigma_energy"].evaluation_id == "eval_1"
    # min_emit_y should be eval_5 (2.0e-6 / 5 = 0.4e-6)
    assert candidates["min_emit_y"].evaluation_id == "eval_5"


def test_perturbation_specification_loading():
    """Verify loading and defaults of PerturbationSpecification."""
    # 1. Default spec
    default_spec = PerturbationSpecification()
    assert default_spec.gun_phase_std_deg == 0.10
    assert default_spec.bunch_charge_relative_std == 0.010
    assert default_spec.laser_spot_size_relative_std == 0.010

    # 2. From YAML
    yaml_spec = load_perturbation_spec("configs/perturbation_config.yaml")
    assert yaml_spec.gun_phase_std_deg == pytest.approx(0.10)
    assert yaml_spec.solenoid_field_relative_std == pytest.approx(0.001)
    assert yaml_spec.bunch_charge_relative_std == pytest.approx(0.010)
    assert yaml_spec.laser_pulse_duration_relative_std == pytest.approx(0.010)

    # 3. From Dict
    custom_dict = {
        "perturbations": {
            "gun_phase_error_deg": {"std": 0.25},
            "bunch_charge_relative_jitter": {"std": 0.05},
        }
    }
    spec_from_dict = PerturbationSpecification.from_dict(custom_dict)
    assert spec_from_dict.gun_phase_std_deg == 0.25
    assert spec_from_dict.bunch_charge_relative_std == 0.05
    assert spec_from_dict.solenoid_field_relative_std == 0.001  # fallback default


def test_generate_perturbed_parameters_and_states():
    """Verify full-chain perturbation distributions across all 7 channels."""
    nominal_x = [0.194, 1.28, -2.88, 35.6, -39.5, 310.0]
    num_samples = 4000
    seed = 42

    spec = PerturbationSpecification(
        gun_phase_std_deg=0.10,
        cavity_phase_std_deg=0.10,
        solenoid_field_relative_std=0.001,
        quad_gradient_relative_std=0.001,
        bunch_charge_relative_std=0.010,
        laser_spot_size_relative_std=0.010,
        laser_pulse_duration_relative_std=0.010,
    )

    states = generate_perturbed_machine_states(nominal_x, num_perturbations=num_samples, seed=seed, spec=spec)
    assert len(states) == num_samples

    # Check reproducibility
    states_rep = generate_perturbed_machine_states(nominal_x, num_perturbations=num_samples, seed=seed, spec=spec)
    assert states[0].parameters == states_rep[0].parameters
    assert states[0].bunch_charge_scale == states_rep[0].bunch_charge_scale

    # Check 7 channels standard deviations
    sol_rel = [s.channel_deltas["solenoid_field_relative_error"] for s in states]
    q1_rel = [s.channel_deltas["quad1_gradient_relative_error"] for s in states]
    gun_dphi = [s.channel_deltas["gun_phase_error_deg"] for s in states]
    acc12_dphi = [s.channel_deltas["cavity_phase_acc12_error_deg"] for s in states]
    charge_rel = [s.channel_deltas["bunch_charge_relative_jitter"] for s in states]
    spot_rel = [s.channel_deltas["laser_spot_size_relative_jitter"] for s in states]
    dur_rel = [s.channel_deltas["laser_pulse_duration_relative_jitter"] for s in states]

    assert np.std(sol_rel) == pytest.approx(0.001, rel=0.10)
    assert np.std(q1_rel) == pytest.approx(0.001, rel=0.10)
    assert np.std(gun_dphi) == pytest.approx(0.10, rel=0.10)
    assert np.std(acc12_dphi) == pytest.approx(0.10, rel=0.10)
    assert np.std(charge_rel) == pytest.approx(0.010, rel=0.10)
    assert np.std(spot_rel) == pytest.approx(0.010, rel=0.10)
    assert np.std(dur_rel) == pytest.approx(0.010, rel=0.10)

    # Verify generate_perturbed_parameters list output
    param_list = generate_perturbed_parameters(nominal_x, num_perturbations=10, seed=seed, spec=spec)
    assert len(param_list) == 10
    assert len(param_list[0]) == 6


def test_apply_parameters_with_namelist_overrides():
    """Verify apply_parameters_to_astra applies namelist overrides properly."""
    dummy_sim = {}
    params = [0.194, 1.28, -2.88, 35.6, -39.5, 310.0]
    overrides = {"charge:q_total": 0.202, "charge:lspch": True}

    applied = apply_parameters_to_astra(dummy_sim, params, namelist_overrides=overrides)
    assert len(applied) == 6
    assert dummy_sim["charge:q_total"] == 0.202
    assert dummy_sim["charge:lspch"] is True
    assert dummy_sim["solenoid:maxb(1)"] == 0.194


def test_compute_robustness_summary(sample_pareto_results):
    """Verify calculation of robustness statistics and fragile classification."""
    nominal = sample_pareto_results[0]
    perturbed_list = []

    # 8 feasible, 2 infeasible
    for i in range(10):
        is_feas = i < 8
        res = EvaluationResult(
            evaluation_id=f"pert_{i}",
            run_id="test_run",
            x_physical=nominal.x_physical,
            objectives_physical=[1.05e-6, 1.05e-6, 0.21e6] if is_feas else [2.5e-6, 2.5e-6, 0.5e6],
            simulation_valid=True,
            physically_feasible=is_feas,
            failure_category=FailureCategory.SUCCESS.value if is_feas else FailureCategory.INFEASIBLE_BEAM.value,
        )
        perturbed_list.append(res)

    summary = compute_robustness_summary("knee_point", nominal, perturbed_list)

    assert summary["candidate_label"] == "knee_point"
    assert summary["probability_of_feasibility"] == pytest.approx(0.80)
    assert summary["mean_emit_x"] > 0
    assert summary["is_fragile"] is False

