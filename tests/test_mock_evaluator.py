"""
Unit tests for Canonical Mock Evaluator Infrastructure (Task 19).
"""

from pathlib import Path
import pytest

from mobo_linac.execution.mock import MockEvaluator
from mobo_linac.execution.requests import requests_for


def test_mock_batch_evaluator_callable(tmp_path):
    """Verify MockEvaluator callable interface produces valid dictionary."""
    evaluator = MockEvaluator(run_dir=tmp_path)
    res = evaluator.respond([0.2, 1.0, -1.0, 0.0, 0.0, 0.0], run_id="test_run", eval_id=1)

    assert res["status"] == "SUCCESS"
    assert res["eval_id"] == "eval_000001"
    assert res["run_id"] == "test_run"
    assert "norm_emit_x" in res["objectives"]
    assert "sigma_energy" in res["objectives"]
    assert res["diagnostics"]["transmission_fraction"] == 1.0
    assert res["diagnostics"]["mean_kinetic_energy_eV"] == 200.0e6


def test_mock_batch_evaluator_batch_and_callback(tmp_path):
    """Verify batch evaluation and real-time streaming callback triggering."""
    evaluator = MockEvaluator(run_dir=tmp_path)
    cands = [
        [0.2, 1.0, -1.0, 0.0, 0.0, 0.0],
        [0.25, 0.9, -0.9, 1.0, 1.0, 0.0],
        [0.18, 1.1, -1.1, -1.0, -1.0, 0.0],
    ]

    callback_records = []

    def on_done(res):
        callback_records.append(res["eval_id"])

    results = evaluator.evaluate(requests_for(cands, eval_ids=[10, 20, 30]), run_id="stream_test",
                                 on_complete=on_done)

    assert len(results) == 3
    assert len(callback_records) == 3
    assert results[0]["eval_id"] == "eval_000010"
    assert results[1]["eval_id"] == "eval_000020"
    assert results[2]["eval_id"] == "eval_000030"
    assert callback_records == ["eval_000010", "eval_000020", "eval_000030"]


def test_mock_batch_evaluator_failure_injection(tmp_path):
    """Verify targeted failure injection on specific evaluation IDs."""
    evaluator = MockEvaluator(run_dir=tmp_path, fail_eval_ids=["eval_000002"])
    results = evaluator.evaluate(requests_for([[0.2, 1.0, -1.0, 0.0, 0.0, 0.0], [0.25, 0.9, -0.9, 1.0, 1.0, 0.0]]),
                                 run_id="fail_test")

    assert results[0]["status"] == "SUCCESS"
    assert results[1]["status"] == "RUN_FAILED"
    assert results[1]["error"] is not None


def test_request_contract_streams_once_and_preserves_full_request(tmp_path):
    from mobo_linac.config import load_config
    from mobo_linac.execution.contracts import evaluate_requests
    from mobo_linac.execution.requests import EvaluationRequest
    config = load_config('configs/publication_200MeV.yaml')
    requests = [EvaluationRequest('candidate_a', [0.2, 1, -1, 0, 0, 0],
                {'charge:nrad': 8}, {'bunch_charge_scale': 1.1}, {'seed': 73})]
    done = []
    out = evaluate_requests(MockEvaluator(tmp_path), requests, run_id='study', config=config,
                            on_complete=done.append)
    assert len(done) == len(out) == 1
    assert out[0].result.evaluation_id == 'eval_candidate_a'
    assert done[0].details['request'] == requests[0].to_dict()
    assert done[0].details['execution_kind'] == 'mock'


def test_request_contract_reorders_completions_from_returning_backends():
    from mobo_linac.config import load_config
    from mobo_linac.execution.contracts import evaluate_requests
    from mobo_linac.execution.requests import EvaluationRequest
    config = load_config('configs/publication_200MeV.yaml')
    requests = [EvaluationRequest(i, [0.2, 1, -1, 0, 0, 0]) for i in [1, 2]]
    class Legacy:
        # A backend that only returns its completions (never calls on_complete).
        def evaluate(self, requests, run_id, on_complete=None):
            return [dict(status='failed', run_id=run_id, eval_id=r.eval_id, parameters=r.parameters,
                         error='beam loss') for r in reversed(list(requests))]
    done = []
    out = evaluate_requests(Legacy(), requests, run_id='legacy', config=config, on_complete=done.append)
    assert [c.result.evaluation_id for c in done] == ['eval_000002', 'eval_000001']
    assert [c.result.evaluation_id for c in out] == ['eval_000001', 'eval_000002']
    with pytest.raises(ValueError, match='Duplicate'):
        evaluate_requests(Legacy(), [requests[0], requests[0]], run_id='legacy', config=config)


@pytest.mark.parametrize('fault', ['identity', 'parameters', 'missing', 'conflict'])
def test_request_contract_rejects_corrupt_completions(fault):
    from mobo_linac.config import load_config
    from mobo_linac.execution.contracts import evaluate_requests
    from mobo_linac.execution.requests import EvaluationRequest
    request = EvaluationRequest(1, [0.2, 1, -1, 0, 0, 0])
    class Backend:
        def evaluate(self, requests, run_id, on_complete=None):
            raw = dict(status='failed', run_id=run_id, eval_id=1, parameters=request.parameters,
                       error='beam loss')
            if fault == 'identity': raw['eval_id'] = 99
            if fault == 'parameters': raw['parameters'] = [0.3, 1, -1, 0, 0, 0]
            if fault == 'missing': return []
            on_complete(raw)
            if fault == 'conflict': raw['error'] = 'different failure'
            return [raw]
    with pytest.raises(ValueError):
        evaluate_requests(Backend(), [request], run_id='corrupt', config=load_config())


def test_mock_answers_any_configured_layout():
    """Objectives follow the configuration; every registered channel gets an in-limit value."""
    from mobo_linac.diagnostics import DIAGNOSTIC_CHANNELS
    from mobo_linac.evaluation import create_evaluation_result
    from tests.test_configuration_boundaries import noncanonical_config
    config = noncanonical_config()
    raw = MockEvaluator(config=config).respond([v.nominal_value for v in config.design_variables], "layout", 1)
    assert set(raw["objectives"]) == {obj.name for obj in config.objectives}
    assert set(raw["diagnostics"]) == {channel.name for channel in DIAGNOSTIC_CHANNELS}
    assert create_evaluation_result(raw, config).simulation_valid is True


def test_execution_code_has_no_capability_probing():
    import re
    from pathlib import Path
    root = Path(__file__).resolve().parents[1] / "src" / "mobo_linac" / "execution"
    offenders = [path.name for path in root.glob("*.py")
                 if re.search(r"(hasattr|getattr)\(\s*(evaluator|backend|self\.evaluator)", path.read_text())]
    assert offenders == []
