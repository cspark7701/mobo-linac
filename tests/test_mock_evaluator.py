"""
Unit tests for Canonical Mock Evaluator Infrastructure (Task 19).
"""

from pathlib import Path
import pytest

from mobo_linac.execution.mock import MockBatchEvaluator


def test_mock_batch_evaluator_callable(tmp_path):
    """Verify MockBatchEvaluator callable interface produces valid dictionary."""
    evaluator = MockBatchEvaluator(run_dir=tmp_path)
    res = evaluator([0.2, 1.0, -1.0, 0.0, 0.0, 0.0], run_id="test_run", eval_id=1)

    assert res["status"] == "success"
    assert res["eval_id"] == "eval_000001"
    assert res["run_id"] == "test_run"
    assert "norm_emit_x" in res["objectives"]
    assert "sigma_energy" in res["objectives"]
    assert res["diagnostics"]["transmission_fraction"] == 1.0
    assert res["diagnostics"]["mean_kinetic_energy_eV"] == 200.0e6


def test_mock_batch_evaluator_batch_and_callback(tmp_path):
    """Verify batch evaluation and real-time streaming callback triggering."""
    evaluator = MockBatchEvaluator(run_dir=tmp_path)
    cands = [
        [0.2, 1.0, -1.0, 0.0, 0.0, 0.0],
        [0.25, 0.9, -0.9, 1.0, 1.0, 0.0],
        [0.18, 1.1, -1.1, -1.0, -1.0, 0.0],
    ]

    callback_records = []

    def on_done(res):
        callback_records.append(res["eval_id"])

    results = evaluator.evaluate_batch(
        cands,
        run_id="stream_test",
        eval_ids=[10, 20, 30],
        on_evaluation_complete=on_done,
    )

    assert len(results) == 3
    assert len(callback_records) == 3
    assert results[0]["eval_id"] == "eval_000010"
    assert results[1]["eval_id"] == "eval_000020"
    assert results[2]["eval_id"] == "eval_000030"
    assert callback_records == ["eval_000010", "eval_000020", "eval_000030"]


def test_mock_batch_evaluator_failure_injection(tmp_path):
    """Verify targeted failure injection on specific evaluation IDs."""
    evaluator = MockBatchEvaluator(run_dir=tmp_path, fail_eval_ids=["eval_000002"])
    results = evaluator.evaluate_batch(
        [[0.2, 1.0, -1.0, 0.0, 0.0, 0.0], [0.25, 0.9, -0.9, 1.0, 1.0, 0.0]],
        run_id="fail_test",
        eval_ids=[1, 2],
    )

    assert results[0]["status"] == "success"
    assert results[1]["status"] == "failed"
    assert results[1]["error"] is not None


def test_request_contract_streams_once_and_preserves_full_request(tmp_path):
    from mobo_linac.config import load_config
    from mobo_linac.execution.contracts import evaluate_requests
    from mobo_linac.execution.requests import EvaluationRequest
    config = load_config('configs/publication_200MeV.yaml')
    requests = [EvaluationRequest('candidate_a', [0.2, 1, -1, 0, 0, 0],
                {'charge:nrad': 8}, {'bunch_charge_scale': 1.1}, {'seed': 73})]
    done = []
    out = evaluate_requests(MockBatchEvaluator(tmp_path), requests, run_id='study', config=config,
                            on_complete=done.append)
    assert len(done) == len(out) == 1
    assert out[0].result.evaluation_id == 'eval_candidate_a'
    assert done[0].details['request'] == requests[0].to_dict()
    assert done[0].details['execution_kind'] == 'mock'


def test_request_contract_reorders_completions_and_adapts_legacy():
    from mobo_linac.config import load_config
    from mobo_linac.execution.contracts import evaluate_requests
    from mobo_linac.execution.requests import EvaluationRequest
    config = load_config('configs/publication_200MeV.yaml')
    requests = [EvaluationRequest(i, [0.2, 1, -1, 0, 0, 0]) for i in [1, 2]]
    class Legacy:
        # Deliberately no callback argument or advertised capability.
        def evaluate_batch(self, candidates, run_id, eval_ids):
            return [dict(status='failed', run_id=run_id, eval_id=i, parameters=x,
                         error='beam loss') for i, x in reversed(list(zip(eval_ids, candidates)))]
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
        supports_completion_callback = True
        def evaluate_requests(self, requests, run_id, on_evaluation_complete):
            raw = dict(status='failed', run_id=run_id, eval_id=1, parameters=request.parameters,
                       error='beam loss')
            if fault == 'identity': raw['eval_id'] = 99
            if fault == 'parameters': raw['parameters'] = [0.3, 1, -1, 0, 0, 0]
            if fault == 'missing': return []
            on_evaluation_complete(raw)
            if fault == 'conflict': raw['error'] = 'different failure'
            return [raw]
    with pytest.raises(ValueError):
        evaluate_requests(Backend(), [request], run_id='corrupt', config=load_config())
