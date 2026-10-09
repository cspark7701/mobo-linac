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
    load_perturbation_spec,
)
from mobo_linac.metrics.pareto import select_representative_pareto_candidates

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
    candidates = select_representative_pareto_candidates(sample_pareto_results, TEST_CONFIG)

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
    """The YAML specification declares channels per design variable; legacy flat files still load."""
    yaml_spec = load_perturbation_spec("configs/perturbation_config.yaml")
    by_name = {c.channel: c for c in yaml_spec.lattice + yaml_spec.source}
    assert by_name["gun_phase_error_deg"].std == pytest.approx(0.10)
    assert by_name["gun_phase_error_deg"].kind == "absolute"
    assert by_name["solenoid_field_relative_error"].kind == "relative"
    assert by_name["bunch_charge_relative_jitter"].setting == "bunch_charge_scale"
    assert yaml_spec.seed_policy == "common" and yaml_spec.fragility_threshold == 0.80
    yaml_spec.validate_for(TEST_CONFIG)

    legacy = PerturbationSpecification.from_dict({"perturbations": {
        "gun_phase_error_deg": {"std": 0.25}, "bunch_charge_relative_jitter": {"std": 0.05}}})
    legacy_channels = {c.channel: c.std for c in legacy.lattice + legacy.source}
    assert legacy_channels["gun_phase_error_deg"] == 0.25
    assert legacy_channels["bunch_charge_relative_jitter"] == 0.05
    assert legacy_channels["solenoid_field_relative_error"] == 0.001
    assert [c.channel for c in legacy.lattice] == [c.channel for c in yaml_spec.lattice]


@pytest.mark.parametrize("data, message", [
    ({"perturbations": {"unknown_channel": {"std": 0.1}}}, "Unknown legacy"),
    ({"lattice": [{"channel": "x", "design_variable": "gun_phase_deg", "kind": "absolute", "std": 0.1,
                   "distribution": "uniform"}]}, "distribution"),
    ({"lattice": [], "extra": 1}, "Unknown perturbation specification fields"),
    ({"lattice": [], "seed_policy": "random"}, "seed_policy"),
])
def test_perturbation_specification_rejects_unused_or_invalid_fields(data, message):
    with pytest.raises(ValueError, match=message):
        PerturbationSpecification.from_dict(data)


def test_generate_perturbed_parameters_and_states():
    """Verify full-chain perturbation distributions across all configured channels."""
    nominal = dict(zip([dv.name for dv in TEST_CONFIG.design_variables], [0.194, 1.28, -2.88, 35.6, -39.5, 310.0]))
    num_samples = 4000
    seed = 42
    spec = load_perturbation_spec("configs/perturbation_config.yaml")

    states = generate_perturbed_machine_states(nominal, spec, num_perturbations=num_samples, seed=seed)
    assert len(states) == num_samples
    states_rep = generate_perturbed_machine_states(nominal, spec, num_perturbations=num_samples, seed=seed)
    assert states[0].parameters == states_rep[0].parameters
    assert states[0].source_settings == states_rep[0].source_settings

    for channel, expected in [("solenoid_field_relative_error", 0.001), ("quad1_gradient_relative_error", 0.001),
                              ("gun_phase_error_deg", 0.10), ("cavity_phase_acc12_error_deg", 0.10),
                              ("bunch_charge_relative_jitter", 0.010), ("laser_spot_size_relative_jitter", 0.010),
                              ("laser_pulse_duration_relative_jitter", 0.010)]:
        assert np.std([s.channel_deltas[channel] for s in states]) == pytest.approx(expected, rel=0.10)


def test_perturbed_draws_match_the_historical_six_channel_model():
    """Golden check: the configured 200 MeV channels reproduce the former positional draws."""
    nominal_x = [0.194, 1.28, -2.88, 35.6, -39.5, 310.0]
    names = [dv.name for dv in TEST_CONFIG.design_variables]
    states = generate_perturbed_machine_states(dict(zip(names, nominal_x)), load_perturbation_spec(), 5, seed=42)
    rng = np.random.default_rng(42)
    for state in states:
        sol, q1, q2 = rng.normal(0, 0.001), rng.normal(0, 0.001), rng.normal(0, 0.001)
        gun, acc12, acc34 = rng.normal(0, 0.1), rng.normal(0, 0.1), rng.normal(0, 0.1)
        charge, spot, duration = rng.normal(0, 0.01), rng.normal(0, 0.01), rng.normal(0, 0.01)
        expected = [nominal_x[0] * (1 + sol), nominal_x[1] * (1 + q1), nominal_x[2] * (1 + q2),
                    nominal_x[3] + gun, nominal_x[4] + acc12, nominal_x[5] + acc34]
        assert [state.parameters[name] for name in names] == expected
        assert state.source_settings == {"bunch_charge_scale": 1 + charge, "laser_spot_scale": 1 + spot,
                                         "laser_pulse_duration_scale": 1 + duration}


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


def _perturbed(nominal, objectives, feasible, transmission=1.0, valid=True):
    diagnostics = dict(nominal.diagnostics, transmission_fraction=transmission)
    return EvaluationResult(evaluation_id="p", run_id="test_run", x_physical=nominal.x_physical,
                            objectives_physical=objectives, simulation_valid=valid, physically_feasible=feasible,
                            diagnostics=diagnostics, failure_category="SUCCESS" if feasible else "INFEASIBLE_BEAM")


def test_compute_robustness_summary(sample_pareto_results):
    """Verify calculation of robustness statistics and fragile classification."""
    nominal = sample_pareto_results[0]
    perturbed_list = [_perturbed(nominal, [1.05e-6, 1.05e-6, 0.21e6] if i < 8 else [2.5e-6, 2.5e-6, 0.5e6], i < 8)
                      for i in range(10)]

    summary = compute_robustness_summary("knee_point", nominal, perturbed_list, TEST_CONFIG)

    assert summary["candidate_label"] == "knee_point"
    assert summary["probability_of_feasibility"] == pytest.approx(0.80)
    assert summary["mean_norm_emit_x_m_rad"] > 0
    for column in ("norm_emit_x_m_rad", "norm_emit_y_m_rad", "sigma_energy_eV"):
        assert {f"{stat}_{column}" for stat in ("nominal", "mean", "std", "p5", "p95")} <= set(summary)
    assert summary["is_fragile"] is False
    assert summary["summary_issues"] == []
    # Every configured channel contributes a normalized margin (0.5 mm against a 1.0 mm limit).
    assert summary["constraint_margins"]["sigma_x_m:upper"] == pytest.approx(0.5)
    assert summary["constraint_margins"]["transmission_fraction:lower"] == pytest.approx(0.1 / 0.9)


def test_robustness_margins_follow_the_active_constraint_profile(sample_pareto_results):
    from copy import deepcopy
    nominal = sample_pareto_results[0]
    perturbed = [_perturbed(nominal, [1.05e-6, 1.05e-6, 0.21e6], True, transmission=0.95) for _ in range(4)]
    stringent = deepcopy(TEST_CONFIG)
    stringent.constraints.min_transmission = 0.9999
    nominal_summary = compute_robustness_summary("knee", nominal, perturbed, TEST_CONFIG)
    stringent_summary = compute_robustness_summary("knee", nominal, perturbed, stringent)
    assert nominal_summary["constraint_margins"]["transmission_fraction:lower"] > 0
    assert stringent_summary["worst_constraint_margin"] < 0
    assert stringent_summary["worst_constraint_channel"] == "transmission_fraction:lower"


def test_missing_nominal_or_transmission_is_unknown_not_substituted(sample_pareto_results):
    from copy import deepcopy
    nominal = deepcopy(sample_pareto_results[0])
    nominal.objectives_physical = None
    perturbed = [_perturbed(sample_pareto_results[0], [1e-6, 1e-6, 0.2e6], True)]
    del perturbed[0].diagnostics["transmission_fraction"]
    summary = compute_robustness_summary("knee", nominal, perturbed, TEST_CONFIG)
    assert np.isnan(summary["nominal_norm_emit_x_m_rad"])
    assert np.isnan(summary["robust_score"]) and np.isnan(summary["worst_constraint_margin"])
    assert "nominal objectives missing or nonfinite" in summary["summary_issues"]
    assert "constraint margins incomplete" in summary["summary_issues"]


def test_complete_plan_reproducibility_zero_jitter_and_reordered_config(sample_pareto_results, tmp_path):
    from copy import deepcopy
    from mobo_linac.config import load_config
    from mobo_linac.robustness.evaluator import RobustnessEvaluator

    config = load_config()
    offset = load_perturbation_spec()
    offset = PerturbationSpecification(offset.lattice, offset.source, seed_policy="candidate_offset")
    evaluator = RobustnessEvaluator(config=config, base_output_dir=tmp_path, spec=offset)
    first = evaluator.generate_evaluation_plan(sample_pareto_results[:2], num_perturbations=4, seed=91)
    second = evaluator.generate_evaluation_plan(sample_pareto_results[:2], num_perturbations=4, seed=91)
    assert [task.to_request().to_dict() for task in first] == [task.to_request().to_dict() for task in second]
    assert first[0].metadata['seed'] == 91
    assert first[4].metadata['seed'] == 191
    zero = offset.with_stds(**{channel: 0.0 for channel in offset.channels})
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
    reordered_task = RobustnessEvaluator(config=reordered, spec=offset).generate_evaluation_plan([candidate], 4, 91)[0]
    common = RobustnessEvaluator(config=config).generate_evaluation_plan(sample_pareto_results[:2], 4, 91)
    assert common[4].metadata['seed'] == 91 and common[4].metadata['seed_policy'] == 'common'
    assert reordered_task.parameters == list(reversed(first[0].parameters))
    assert reordered_task.source_settings == first[0].source_settings
    assert reordered_task.metadata['channel_deltas'] == first[0].metadata['channel_deltas']


def test_reports_never_claim_unapplied_source_or_mock_jitter(sample_pareto_results, tmp_path):
    import json
    from pathlib import Path
    from mobo_linac.execution.mock import MockEvaluator
    from mobo_linac.robustness.evaluator import RobustnessEvaluator

    evaluator = RobustnessEvaluator(TEST_CONFIG, base_output_dir=tmp_path)
    mock = MockEvaluator(tmp_path)
    summary = evaluator.evaluate_candidates(sample_pareto_results[:1], 3, seed=31, evaluator=mock)[0]
    assert summary['unsupported_channels'] == sorted(c.channel for c in evaluator.spec.source)
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
    next_summary = evaluator.evaluate_candidates(sample_pareto_results[:1], 3, seed=31, evaluator=mock)[0]
    assert next_summary['request_manifest_path'] != str(archive)
    assert archive.read_bytes() == original


@pytest.mark.parametrize('std', [-0.01, float('nan'), float('inf')])
def test_invalid_jitter_spec_rejected(std):
    with pytest.raises(ValueError, match='finite and nonnegative'):
        load_perturbation_spec().with_stds(gun_phase_error_deg=std)


def test_unknown_design_variable_channels_are_rejected():
    spec = PerturbationSpecification.from_dict({"lattice": [
        {"channel": "x", "design_variable": "not_configured", "kind": "absolute", "std": 0.1}]})
    with pytest.raises(ValueError, match="unknown design variables"):
        spec.validate_for(TEST_CONFIG)
