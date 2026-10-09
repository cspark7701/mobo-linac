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

from mobo_linac.config import load_config as _load_test_config
TEST_CONFIG = _load_test_config("configs/mobo_200MeV.yaml")


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

    applied = apply_parameters_to_astra(dummy_sim, params, TEST_CONFIG, namelist_overrides=overrides)
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



def test_complete_plan_reproducibility_zero_jitter_and_reordered_config(sample_pareto_results, tmp_path):
    from dataclasses import fields
    from copy import deepcopy
    from mobo_linac.config import load_config
    from mobo_linac.robustness.evaluator import RobustnessEvaluator

    config = load_config()
    evaluator = RobustnessEvaluator(config=config, base_output_dir=tmp_path)
    first = evaluator.generate_evaluation_plan(sample_pareto_results[:2], num_perturbations=4, seed=91)
    second = evaluator.generate_evaluation_plan(sample_pareto_results[:2], num_perturbations=4, seed=91)
    assert [task.to_request().to_dict() for task in first] == [task.to_request().to_dict() for task in second]
    assert first[0].metadata['seed'] == 91
    assert first[4].metadata['seed'] == 191
    zero = PerturbationSpecification(**{field.name: 0.0 for field in fields(PerturbationSpecification)})
    zero_tasks = RobustnessEvaluator(config=config, spec=zero).generate_evaluation_plan(sample_pareto_results[:1], 3, 91)
    for task in zero_tasks:
        assert task.parameters == sample_pareto_results[0].x_physical
        assert all(scale == 1.0 for scale in task.source_settings.values())
        assert all(delta == 0.0 for delta in task.metadata['channel_deltas'].values())
        assert task.metadata['unsupported_channels'] == {}
        assert task.namelist_overrides is None
    reordered = deepcopy(config)
    reordered.design_variables.reverse()
    candidate = deepcopy(sample_pareto_results[0])
    candidate.x_physical.reverse()
    reordered_task = RobustnessEvaluator(config=reordered).generate_evaluation_plan([candidate], 4, 91)[0]
    assert reordered_task.parameters == list(reversed(first[0].parameters))
    assert reordered_task.source_settings == first[0].source_settings
    assert reordered_task.metadata['channel_deltas'] == first[0].metadata['channel_deltas']


def test_reports_never_claim_unapplied_source_or_mock_jitter(sample_pareto_results, tmp_path):
    import json
    from pathlib import Path
    from mobo_linac.execution.mock import MockBatchEvaluator
    from mobo_linac.robustness.evaluator import RobustnessEvaluator, SOURCE_CHANNELS

    evaluator = RobustnessEvaluator(TEST_CONFIG, base_output_dir=tmp_path)
    mock = MockBatchEvaluator(tmp_path)
    summary = evaluator.evaluate_candidates(sample_pareto_results[:1], 3, seed=31, batch_evaluator=mock)[0]
    assert summary['unsupported_channels'] == sorted(SOURCE_CHANNELS)
    assert summary['execution_kinds'] == ['mock']
    assert summary['evaluated_channels'] == []
    assert summary['full_requested_jitter_evaluated'] is False
    archive = Path(summary['request_manifest_path'])
    payload = json.loads(archive.read_text())
    assert 'config' in payload
    records = payload['records']
    assert len(records) == 3
    for record in records:
        assert record['request']['source_settings']['bunch_charge_scale'] != 1.0
        assert record['applied_perturbations'] == {}
        assert record['request']['metadata']['seed'] == 31
        assert record['request']['metadata']['unsupported_channels']
    original = archive.read_bytes()
    next_summary = evaluator.evaluate_candidates(sample_pareto_results[:1], 3, seed=31, batch_evaluator=mock)[0]
    assert next_summary['request_manifest_path'] != str(archive)
    assert archive.read_bytes() == original


@pytest.mark.parametrize('std', [-0.01, float('nan'), float('inf')])
def test_invalid_jitter_spec_rejected(std):
    with pytest.raises(ValueError, match='finite and nonnegative'):
        generate_perturbed_machine_states([0.2, 1, -1, 0, 0, 0], spec=PerturbationSpecification(gun_phase_std_deg=std))
