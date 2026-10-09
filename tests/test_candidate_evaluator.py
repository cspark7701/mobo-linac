"""
Unit tests for CandidateEvaluatorBase, RobustnessEvaluator, and ParetoVerifier.
"""

from mobo_linac.result_schema import ResultSchema
from pathlib import Path
import numpy as np
import pytest

from mobo_linac.execution import FunctionEvaluator
from tests.evaluators import callable_evaluator

from mobo_linac.evaluation import EvaluationResult
from mobo_linac.execution.candidate_evaluator import (
    CandidateEvaluatorBase,
    EvaluationOutcome,
    EvaluationTask,
    compute_metric_deltas,
)
from mobo_linac.robustness.evaluator import RobustnessEvaluator
from mobo_linac.verification.verifier import ParetoVerifier

from mobo_linac.config import load_config as _load_test_config
TEST_CONFIG = _load_test_config("configs/mobo_200MeV.yaml")


@pytest.fixture
def sample_candidate():
    return EvaluationResult(
        evaluation_id="eval_000001",
        run_id="test_run",
        x_physical=[0.2, 1.0, -1.0, -10.0, -5.0, 0.0],
        objectives_physical=[3.5e-6, 3.6e-6, 0.9e6],
        objectives_model=[-3.5e-6, -3.6e-6, -0.9e6],
        diagnostics={
            "sigma_x_m": 0.5e-3,
            "sigma_y_m": 0.5e-3,
            "sigma_xp_rad": 0.4e-3,
            "sigma_yp_rad": 0.4e-3,
            "sigma_z_m": 0.6e-3,
            "mean_kinetic_energy_eV": 200.0e6,
            "transmission_fraction": 1.0,
        },
        simulation_valid=True,
        physically_feasible=True,
    )


def test_compute_metric_deltas_identical(sample_candidate):
    """Verifies that identical nominal and rerun results yield 0% deltas."""
    deltas = compute_metric_deltas(sample_candidate, sample_candidate, TEST_CONFIG)
    assert deltas["objective_deltas_pct"]["norm_emit_x_m_rad"] == 0.0
    assert deltas["objective_deltas_pct"]["norm_emit_y_m_rad"] == 0.0
    assert deltas["objective_deltas_pct"]["sigma_energy_eV"] == 0.0
    assert deltas["diff_transmission_pct"] == 0.0
    assert deltas["max_diff_pct"] == 0.0


def test_compute_metric_deltas_perturbed(sample_candidate):
    """Verifies correct calculation of percentage metric deltas."""
    perturbed = EvaluationResult(
        evaluation_id="eval_000002",
        run_id="test_run",
        x_physical=[0.2, 1.0, -1.0, -10.0, -5.0, 0.0],
        objectives_physical=[3.85e-6, 3.6e-6, 0.99e6],  # +10% emit_x, +10% sigma_e
        diagnostics={"transmission_fraction": 0.95},      # -5% transmission
        simulation_valid=True,
        physically_feasible=True,
    )
    deltas = compute_metric_deltas(sample_candidate, perturbed, TEST_CONFIG)
    assert pytest.approx(deltas["objective_deltas_pct"]["norm_emit_x_m_rad"], 1e-4) == 10.0
    assert pytest.approx(deltas["objective_deltas_pct"]["norm_emit_y_m_rad"], 1e-4) == 0.0
    assert pytest.approx(deltas["objective_deltas_pct"]["sigma_energy_eV"], 1e-4) == 10.0
    assert pytest.approx(deltas["diff_transmission_pct"], 1e-4) == 5.0
    assert pytest.approx(deltas["max_diff_pct"], 1e-4) == 10.0


def test_robustness_evaluator_plan_and_execution(sample_candidate, tmp_path):
    """Verifies RobustnessEvaluator task plan generation and custom evaluator execution."""
    robust_eval = RobustnessEvaluator(TEST_CONFIG, base_output_dir=tmp_path / "robustness")
    tasks = robust_eval.generate_evaluation_plan([sample_candidate], num_perturbations=5, seed=42)
    assert len(tasks) == 5
    assert tasks[0].nominal_result == sample_candidate
    assert len(tasks[0].parameters) == 6

    def mock_eval(params, run_id, eval_id):
        return {
            "status": "success",
            "eval_id": eval_id,
            "run_id": run_id,
            "parameters": params,
            "objectives": {"norm_emit_x": 3.55e-6, "norm_emit_y": 3.65e-6, "sigma_energy": 0.92e6},
            "diagnostics": {
                "sigma_x_m": 0.5e-3,
                "sigma_y_m": 0.5e-3,
                "sigma_xp_rad": 0.4e-3,
                "sigma_yp_rad": 0.4e-3,
                "sigma_z_m": 0.6e-3,
                "transmission_fraction": 0.98,
                "mean_kinetic_energy_eV": 200.0e6,
            },
        }

    summaries = robust_eval.evaluate_candidates(
        candidates=[sample_candidate],
        num_perturbations=5,
        seed=42,
        evaluator=callable_evaluator(mock_eval, mock=False),
    )
    assert len(summaries) == 1
    assert summaries[0]["probability_of_feasibility"] == 1.0
    assert summaries[0]["robust_score"] > 0.0


def test_pareto_verifier_plan_and_execution(sample_candidate, tmp_path):
    """Verifies ParetoVerifier task plan generation and verification pipeline."""
    verifier = ParetoVerifier(TEST_CONFIG, base_output_dir=tmp_path / "verification")
    tasks = verifier.generate_evaluation_plan([sample_candidate], roles=["knee_point"])
    assert len(tasks) == 1
    assert tasks[0].role == "knee_point"

    def mock_eval(params, run_id, eval_id):
        return {
            "status": "success",
            "eval_id": eval_id,
            "run_id": run_id,
            "parameters": params,
            "objectives": {"norm_emit_x": 3.5001e-6, "norm_emit_y": 3.6001e-6, "sigma_energy": 0.9001e6},
            "diagnostics": dict(sample_candidate.diagnostics),
        }

    cands_dict = {"knee_point": sample_candidate}
    records, manifest_p, tex_p = verifier.verify_candidates(cands_dict, evaluator=callable_evaluator(mock_eval))
    assert len(records) == 1
    assert records[0]["verification_status"] == "MOCK_VERIFIED"
    assert manifest_p.exists()
    assert tex_p.exists()
    original_manifest = manifest_p.read_bytes()
    _, next_manifest, next_tex = verifier.verify_candidates(cands_dict, evaluator=callable_evaluator(mock_eval))
    assert next_manifest != manifest_p
    assert manifest_p.read_bytes() == original_manifest
    assert next_tex.exists()


@pytest.mark.parametrize('workers', [1, 2])
def test_complete_requests_reach_serial_and_process_backend(sample_candidate, recording_astra_project, tmp_path, workers):
    import json

    project, config = recording_astra_project
    evaluator = RobustnessEvaluator(config=config, base_output_dir=tmp_path / 'results', num_workers=workers)
    tasks = evaluator.generate_evaluation_plan([sample_candidate], num_perturbations=3, seed=73)
    for index, task in enumerate(tasks):
        task.namelist_overrides = {'charge:nrad': index + 10}
    outcomes = evaluator.evaluate_plan_parallel(tasks)
    assert len(outcomes) == len(tasks)
    for task, outcome in zip(tasks, outcomes):
        raw = outcome.execution_details
        assert raw['status'] == 'SUCCESS', raw['error']
        manifest = json.loads(Path(raw['manifest_path']).read_text())
        assert manifest['source_settings'] == task.source_settings
        assert manifest['request_metadata'] == task.metadata
        assert manifest['requested_perturbations'] == task.metadata['channel_deltas']
        assert manifest['applied_namelist_overrides'] == task.namelist_overrides
        assigned = manifest['applied_namelist_values']
        assert assigned['solenoid:maxb(2)'] == task.parameters[0]
        assert assigned['cavity:phi(6)'] == task.parameters[4]
        assert assigned['cavity:phi(4)'] == task.parameters[5]
        assert 'solenoid:maxb(1)' not in assigned
        assert assigned['charge:nrad'] == task.namelist_overrides['charge:nrad']
        supported = set(task.metadata['channel_targets'])
        assert set(manifest['applied_perturbations']) == supported
        assert all(value == 'unsupported' for value in manifest['source_application'].values())
        assert not Path(raw['eval_dir']).exists()
        inputs = Path(raw['manifest_path']).parent / 'inputs'
        assert "Distribution = 'pal_photo2.ini'" in (inputs / 'astra.in').read_text()
        assert (inputs / 'pal_photo2.ini').read_bytes() == (project / 'pal_photo2.ini').read_bytes()


def test_override_failure_is_not_silently_applied(sample_candidate, recording_astra_project, tmp_path):
    import json
    project, config = recording_astra_project
    evaluator = RobustnessEvaluator(config=config, base_output_dir=tmp_path)
    tasks = evaluator.generate_evaluation_plan([sample_candidate], num_perturbations=1)
    tasks[0].namelist_overrides = {'charge:unsupported_test_key': 1}
    outcome = evaluator.evaluate_plan_parallel(tasks)[0]
    raw = outcome.execution_details
    assert raw['status'] == 'UNHANDLED_EXCEPTION'
    assert 'unsupported namelist override' in raw['error']
    manifest = json.loads(Path(raw['manifest_path']).read_text())
    assert manifest['applied_namelist_overrides'] == {}
    assert manifest['applied_perturbations'] == {}
    assert Path(raw['eval_dir']).exists()


def test_request_evaluator_receives_full_state_and_config(sample_candidate, tmp_path):
    from mobo_linac.config import load_config
    from mobo_linac.requests import EvaluationRequest

    config = load_config()
    evaluator = RobustnessEvaluator(config=config, base_output_dir=tmp_path)
    tasks = evaluator.generate_evaluation_plan([sample_candidate], num_perturbations=2)
    tasks[0].namelist_overrides = {'charge:nrad': 16}
    captured = []
    def recording(request, run_id):
        assert isinstance(request, EvaluationRequest)
        captured.append((request.to_dict(), run_id))
        return sample_candidate
    outcomes = evaluator.evaluate_plan_parallel(tasks, evaluator=FunctionEvaluator(recording), run_id="study")
    assert [record for record, _ in captured] == [task.to_request().to_dict() for task in tasks]
    assert all(run_id == "study" for _, run_id in captured)
    assert [o.evaluated_result.run_id for o in outcomes] == ["study"] * len(tasks)


def test_lattice_override_is_recorded_without_claiming_original_jitter(sample_candidate, recording_astra_project, tmp_path):
    project, config = recording_astra_project
    evaluator = RobustnessEvaluator(config=config, base_output_dir=tmp_path)
    tasks = evaluator.generate_evaluation_plan([sample_candidate], num_perturbations=1)
    tasks[0].namelist_overrides = {'solenoid:maxb(2)': 0.7}
    from mobo_linac.astra.workdir import read_evaluation_manifest
    manifest = read_evaluation_manifest(evaluator.evaluate_plan_parallel(tasks)[0].execution_details['manifest_path'])
    assert manifest['applied_namelist_values']['solenoid:maxb(2)'] == 0.7
    assert manifest['requested_perturbations']['solenoid_field_relative_error'] != 0
    assert 'solenoid_field_relative_error' not in manifest['applied_perturbations']


def test_cli_and_script_honor_config_through_shared_workflow(sample_candidate, recording_astra_project, tmp_path):
    import argparse
    import json
    from dataclasses import asdict
    from mobo_linac.cli.commands.audit import run_robustness
    from mobo_linac.metrics.exports import save_evaluation_results
    from scripts.run_robustness_analysis import run_robustness_analysis

    project, config = recording_astra_project
    import yaml
    config_file = tmp_path / 'custom_config.yaml'
    config_file.write_text(yaml.safe_dump(asdict(config)))
    history = tmp_path / 'nominal_history'
    save_evaluation_results([sample_candidate], history, config=config, reporting_ref_point=ResultSchema.from_config(config).empty_reference)
    # Use the complete candidate-history schema, including observed feasibility.
    input_file = history / 'candidate_history.csv'
    outputs = [tmp_path / 'cli', tmp_path / 'script']
    common = {'config': str(config_file), 'num_workers': 1, 'num_perturbations': 2,
              'seed': 17, 'pareto_csv': str(input_file), 'mock_evaluator': False, 'dry_run': False}
    run_robustness(argparse.Namespace(**common, output_dir=str(outputs[0]), history_path=str(input_file)))
    run_robustness_analysis(argparse.Namespace(**common, output_dir=str(outputs[1])))
    requests_by_entry = []
    for output in outputs:
        archives = list(output.glob('robustness_runs/*/robustness_requests.json'))
        assert archives
        captured = []
        for archive in archives:
            payload = json.loads(archive.read_text())
            assert payload['config']['design_variables'][0]['astra_key'] == 'solenoid:maxb(2)'
            for record in payload['records']:
                request = record['request']
                assert record['applied_namelist_values']['solenoid:maxb(2)'] == request['parameters'][0]
                assert record['applied_namelist_values']['cavity:phi(6)'] == request['parameters'][4]
                assert record['result']['simulation_valid'] is True
                assert request['metadata']['seed'] == 17
                captured.append(request)
        requests_by_entry.append(sorted(captured, key=lambda request: request['eval_id']))
        assert (output / 'robustness_summary.csv').exists()
        assert 'unsupported' in (output / 'robustness_table.tex').read_text()
    assert requests_by_entry[0] == requests_by_entry[1]


def test_analysis_streams_typed_results_and_returns_request_order(tmp_path, monkeypatch):
    from mobo_linac.config import load_config
    from mobo_linac.execution.mock import MockEvaluator
    from mobo_linac.execution.candidate_evaluator import CandidateEvaluatorBase, EvaluationTask
    from mobo_linac.evaluation import create_evaluation_result
    config = load_config('configs/publication_200MeV.yaml')
    class Analysis(CandidateEvaluatorBase):
        def generate_evaluation_plan(self, candidates): return []
    class TypedBackend:
        def evaluate(self, requests, run_id, on_complete=None):
            raw = MockEvaluator(tmp_path).evaluate(requests, run_id)
            results = [create_evaluation_result(row, config) for row in reversed(raw)]
            for result in results:
                on_complete(result)
            return results
    monkeypatch.setattr(CandidateEvaluatorBase, 'default_evaluator', lambda self: TypedBackend())
    tasks = [EvaluationTask(name, name, [0.2, 1, -1, 0, 0, 0]) for name in ['first', 'second']]
    done = []
    out = Analysis(config=config, base_output_dir=tmp_path).evaluate_plan_parallel(tasks, on_task_complete=done.append)
    assert [row.task.task_id for row in done] == ['second', 'first']
    assert [row.task.task_id for row in out] == ['first', 'second']
    assert all(row.evaluated_result.simulation_valid for row in out)
