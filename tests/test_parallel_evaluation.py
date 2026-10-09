"""
Unit and Integration Tests for Process-Safe Parallel ASTRA Evaluation (Task 03).
"""

from mobo_linac.result_schema import ResultSchema
import os
import json
from pathlib import Path
import shutil
import pytest
import numpy as np

from mobo_linac.config import load_config as _load_test_config
TEST_CONFIG = _load_test_config("configs/mobo_200MeV.yaml")


from dataclasses import asdict

from mobo_linac.execution.parallel import (
    ProcessPoolEvaluator,
    WorkerTask,
    run_worker_task,
)
from mobo_linac.execution.requests import EvaluationRequest, requests_for


def evaluate_candidates(candidates, run_id, max_workers, base_results_dir, template_dir=None,
                        eval_ids=None, on_complete=None, config=TEST_CONFIG):
    with ProcessPoolEvaluator(config, base_results_dir=base_results_dir, template_dir=template_dir,
                              max_workers=max_workers) as evaluator:
        return evaluator.evaluate(requests_for(candidates, eval_ids), run_id=run_id, on_complete=on_complete)


def worker_task(parameters, run_id, eval_id, base_results_dir, template_dir, retries=0, config=None,
                clean_on_success=False):
    return WorkerTask(candidate_idx=0, request=EvaluationRequest(eval_id, list(parameters)).to_dict(),
                      run_id=run_id, base_results_dir=str(base_results_dir), template_dir=str(template_dir),
                      retries=retries, clean_on_success=clean_on_success,
                      config=asdict(config) if config is not None else None)


@pytest.mark.parametrize("max_workers", [1, 2])
def test_callback_persistence_errors_propagate_in_serial_and_parallel(tmp_path, monkeypatch, max_workers):
    def worker(**kwargs):
        return {"status": "failed", "error": "simulated beam loss", "objectives": None}

    def callback(result):
        assert result["run_id"] == "durable_run"
        assert result["eval_id"] in ["eval_000009", "eval_000010"]
        assert len(result["parameters"]) == 6
        raise OSError("journal write failed")

    monkeypatch.setattr("mobo_linac.execution.parallel.run_astra_eval", worker)
    with pytest.raises(OSError, match="journal write failed"):
        evaluate_candidates(
            [[0.2, 1, -1, 0, 0, 0], [0.3, 1, -1, 0, 0, 0]],
            run_id="durable_run", eval_ids=["eval_000009", "eval_000010"],
            max_workers=max_workers, base_results_dir=tmp_path, on_complete=callback,
        )



@pytest.fixture
def temp_project(tmp_path):
    """
    Creates a temporary project environment with mock input/field files.
    """
    template_dir = tmp_path / "template"
    template_dir.mkdir()

    (template_dir / "gun.dat").write_text("GUN DATA MOCK")
    (template_dir / "PAL_SOL_A.dat").write_text("SOLENOID DATA MOCK")
    (template_dir / "TWS_Sband.dat").write_text("TWS DATA MOCK")
    (template_dir / "pal_photo2.ini").write_text("PARTICLE DIST MOCK")

    astra_in_content = (
        "&INPUT\n"
        "  solenoid:maxb(1) = 0.20,\n"
        "  quadrupole:q_grad(1) = 1.5,\n"
        "  quadrupole:q_grad(2) = -1.5,\n"
        "  cavity:phi(1) = 0.0,\n"
        "  cavity:phi(2) = 0.0,\n"
        "  cavity:phi(3) = 0.0,\n"
        "  cavity:phi(4) = 0.0,\n"
        "  cavity:phi(5) = 0.0\n"
        "/\n"
    )
    (template_dir / "astra.in").write_text(astra_in_content)

    results_dir = tmp_path / "results"
    results_dir.mkdir()

    return {
        "template_dir": template_dir,
        "results_dir": results_dir,
        "base_dir": tmp_path,
    }


def test_worker_eval_task_mock_failure(temp_project, monkeypatch):
    """Test worker handles failure gracefully and returns structured dict."""
    task = worker_task([0.2, 1.0, -1.0, 0.0, 0.0, 0.0], "test_run", 1, temp_project["results_dir"],
                       temp_project["template_dir"], retries=1)

    # Mock run_astra_eval to simulate failure
    def mock_run_astra_eval(**kwargs):
        return {
            "status": "failed",
            "objectives": None,
            "diagnostics": None,
            "eval_dir": str(temp_project["results_dir"] / "test_run" / "work" / "eval_000001"),
            "manifest_path": None,
            "error": "Simulated ASTRA failure",
        }

    monkeypatch.setattr("mobo_linac.execution.parallel.run_astra_eval", mock_run_astra_eval)

    res = run_worker_task(task)

    assert res["candidate_idx"] == 0
    assert res["status"] == "failed"
    assert res["error"] == "Simulated ASTRA failure"
    assert res["retries_attempted"] == 1


def test_parallel_deterministic_order_and_alignment(temp_project, monkeypatch):
    """Verify that results order strictly matches candidate input order regardless of worker finish time."""
    candidates = [
        [0.20, 1.0, -1.0, 0.0, 0.0, 0.0],
        [0.22, 1.2, -1.2, 5.0, 2.0, 2.0],
        [0.25, 1.5, -1.5, 10.0, 5.0, 5.0],
        [0.28, 1.8, -1.8, 15.0, 8.0, 8.0],
    ]

    def mock_run_astra_eval(parameters, run_id, eval_id, base_results_dir, **kwargs):
        cand_val = parameters[0]
        eval_path = Path(base_results_dir) / run_id / "work" / str(eval_id)
        eval_path.mkdir(parents=True, exist_ok=True)
        return {
            "status": "success",
            "objectives": {"norm_emit_x": cand_val * 1e-6, "norm_emit_y": cand_val * 1e-6, "sigma_energy": 0.01},
            "diagnostics": {"emit_x": cand_val * 1e-6},
            "eval_dir": str(eval_path),
            "manifest_path": str(eval_path / "manifest.json"),
            "error": None,
        }

    monkeypatch.setattr("mobo_linac.execution.parallel.run_astra_eval", mock_run_astra_eval)

    results = evaluate_candidates(candidates, "order_test", 4, temp_project["results_dir"], temp_project["template_dir"])

    assert len(results) == 4
    for i, res in enumerate(results):
        assert res["candidate_idx"] == i
        assert res["manifest"] is not None if "manifest" in res else True
        assert res["objectives"]["norm_emit_x"] == pytest.approx(candidates[i][0] * 1e-6)


def test_partial_failure_resilience(temp_project, monkeypatch):
    """Ensure a single failed candidate does not crash or cancel remaining batch candidates."""
    candidates = [
        [0.20, 1.0, -1.0, 0.0, 0.0, 0.0],  # Success
        [0.99, 9.9, -9.9, 0.0, 0.0, 0.0],  # Fail
        [0.25, 1.5, -1.5, 10.0, 5.0, 5.0], # Success
    ]

    def mock_run_astra_eval(parameters, **kwargs):
        if parameters[0] == 0.99:
            return {
                "status": "failed",
                "objectives": None,
                "diagnostics": None,
                "eval_dir": "/tmp/dummy",
                "manifest_path": None,
                "error": "Simulated divergence error",
            }
        return {
            "status": "success",
            "objectives": {"norm_emit_x": 1e-6, "norm_emit_y": 1e-6, "sigma_energy": 0.01},
            "diagnostics": {"emit_x": 1e-6},
            "eval_dir": "/tmp/dummy",
            "manifest_path": None,
            "error": None,
        }

    monkeypatch.setattr("mobo_linac.execution.parallel.run_astra_eval", mock_run_astra_eval)

    results = evaluate_candidates(candidates, "resilience_test", 2, temp_project["results_dir"], temp_project["template_dir"])

    assert len(results) == 3
    assert results[0]["status"] == "success"
    assert results[1]["status"] == "failed"
    assert results[1]["error"] == "Simulated divergence error"
    assert results[2]["status"] == "success"


def test_serial_and_parallel_agreement(temp_project, monkeypatch):
    """Verify that serial execution (max_workers=1) and parallel execution return identical results."""
    candidates = [
        [0.20, 1.0, -1.0, 0.0, 0.0, 0.0],
        [0.22, 1.2, -1.2, 5.0, 2.0, 2.0],
    ]

    def mock_run_astra_eval(parameters, eval_id, **kwargs):
        return {
            "status": "success",
            "objectives": {"norm_emit_x": parameters[0], "norm_emit_y": parameters[1], "sigma_energy": 0.01},
            "diagnostics": {},
            "eval_dir": f"/tmp/eval_{eval_id}",
            "manifest_path": None,
            "error": None,
        }

    monkeypatch.setattr("mobo_linac.execution.parallel.run_astra_eval", mock_run_astra_eval)

    serial_res = evaluate_candidates(candidates, "test_serial", 1, temp_project["results_dir"], temp_project["template_dir"])

    parallel_res = evaluate_candidates(candidates, "test_parallel", 2, temp_project["results_dir"], temp_project["template_dir"])

    assert len(serial_res) == len(parallel_res)
    for s, p in zip(serial_res, parallel_res):
        assert s["status"] == p["status"]
        assert s["objectives"] == p["objectives"]
        assert s["candidate_idx"] == p["candidate_idx"]


def test_batch_evaluator_class(temp_project, monkeypatch):
    """Test BatchEvaluator class encapsulation."""
    evaluator = ProcessPoolEvaluator(
        TEST_CONFIG,
        base_results_dir=temp_project["results_dir"],
        template_dir=temp_project["template_dir"],
        max_workers=2,
        timeout=15,
    )

    def mock_run_astra_eval(parameters, **kwargs):
        return {
            "status": "success",
            "objectives": {"norm_emit_x": 1.0, "norm_emit_y": 1.0, "sigma_energy": 0.01},
            "diagnostics": {},
            "eval_dir": "/tmp/dummy",
            "manifest_path": None,
            "error": None,
        }

    monkeypatch.setattr("mobo_linac.execution.parallel.run_astra_eval", mock_run_astra_eval)

    candidates = [[0.20, 1.0, -1.0, 0.0, 0.0, 0.0]]
    results = evaluator.evaluate(requests_for(candidates), run_id="batch_class_test")
    evaluator.close()
    assert len(results) == 1
    assert results[0]["status"] == "success"


@pytest.mark.integration
def test_real_parallel_astra_evaluations():
    """
    Integration test executing multiple real ASTRA simulations in parallel processes.
    """
    root_dir = Path(__file__).resolve().parents[1]
    if not (root_dir / "gun.dat").exists() or not (root_dir / "astra.in").exists():
        pytest.skip("Root ASTRA files not present")

    astra_bin = os.environ.get("ASTRA_BIN", str(root_dir / "bin" / "astra"))
    if not Path(astra_bin).is_file() and not shutil.which("astra"):
        pytest.skip(f"ASTRA executable not available at {astra_bin} or on PATH")

    candidates = [
        [0.21, 1.1, -1.1, 0.0, 0.0, 0.0],
        [0.24, 1.3, -1.3, 4.0, 1.0, 1.0],
    ]

    with ProcessPoolEvaluator(TEST_CONFIG, base_results_dir="results", template_dir=root_dir,
                              max_workers=2, timeout=300) as evaluator:
        results = evaluator.evaluate(requests_for(candidates), run_id="integration_parallel_run")

    assert len(results) == 2
    for idx, res in enumerate(results):
        assert res["candidate_idx"] == idx
        assert res["status"] == "success", f"Candidate {idx} failed: {res.get('error')}"
        assert res["objectives"] is not None
        assert "norm_emit_x" in res["objectives"]
        assert Path(res["manifest_path"]).exists()


@pytest.mark.parametrize('cleanup', [False, True])
def test_retry_isolates_stale_outputs_and_retains_provenance(temp_project, monkeypatch, cleanup):
    from mobo_linac.astra.workdir import file_sha256, read_evaluation_manifest
    from mobo_linac.evaluation import create_evaluation_result
    from mobo_linac.config import load_config
    from mobo_linac.io.journal import append_streaming_evaluation, load_streaming_evaluations
    from mobo_linac.io.checkpoint import CheckpointState
    from mobo_linac.io.results import save_evaluation_results, load_evaluation_results

    executable = temp_project['base_dir'] / 'stub_astra'
    executable.write_bytes(b'stub executable bytes')
    directories = []
    class StubAstra:
        command = str(executable)
        particles = []
        def __init__(self, input_file, workdir, **kwargs):
            self.directory = Path(workdir)
            self.values = {}
            self.output = {}
            directories.append(self.directory)
        def __setitem__(self, name, value):
            self.values[name] = value
        def write_input(self):
            (self.directory / 'astra.in').write_text(json.dumps(self.values, sort_keys=True))
        def run(self):
            assert not (self.directory / 'stale.out').exists()
            if len(directories) == 1:
                (self.directory / 'stale.out').write_text('failed attempt output')
                raise RuntimeError('transient simulation failure')
            (self.directory / 'beam.out').write_text('fresh beam output')
            self.output = {'stats': {key: [value] for key, value in {
                'norm_emit_x': 1e-6, 'norm_emit_y': 1e-6, 'sigma_energy': 0.5e6,
                'sigma_x': 0.5e-3, 'sigma_y': 0.5e-3, 'sigma_xp': 0.5e-3,
                'sigma_yp': 0.5e-3, 'sigma_z': 0.5e-3,
                'mean_kinetic_energy': 200e6, 'transmission_fraction': 1.0, 'z': 16.2,
            }.items()}}
    monkeypatch.setattr('mobo_linac.astra.runner.Astra', StubAstra)
    config = load_config()
    result = run_worker_task(worker_task([0.2, 1, -1, 0, 0, 0], 'retry', 1, temp_project['results_dir'],
                                         temp_project['template_dir'], retries=1, config=config,
                                         clean_on_success=cleanup))
    assert result['status'] == 'SUCCESS', result['error']
    history = result['attempt_history']
    assert [entry['status'] for entry in history] == ['UNHANDLED_EXCEPTION', 'SUCCESS']
    assert [entry['retried'] for entry in history] == [True, False]
    assert len({entry['attempt_id'] for entry in history}) == 2
    assert directories[0] != directories[1]
    manifests = [read_evaluation_manifest(entry['manifest_path']) for entry in history]
    assert 'stale.out' in manifests[0]['output_hashes']
    assert 'stale.out' not in manifests[1]['output_hashes']
    assert 'beam.out' in manifests[1]['output_hashes']
    for entry, manifest in zip(history, manifests):
        archive = Path(entry['manifest_path']).parent
        assert manifest['executable']['sha256'] == file_sha256(executable)
        for name, digest in manifest['input_hashes'].items():
            assert file_sha256(archive / 'inputs' / name) == digest
        assert 'solenoid:maxb(1)' in (archive / 'inputs' / 'astra.in').read_text()
    assert directories[0].exists()
    assert directories[1].exists() is (not cleanup)
    accepted = create_evaluation_result(result, config)
    assert accepted.attempt_id == history[-1]['attempt_id']
    assert accepted.manifest_path == history[-1]['manifest_path']
    record_dir = temp_project['base_dir'] / 'records'
    append_streaming_evaluation(record_dir, accepted, batch_idx=0, config=TEST_CONFIG)
    assert load_streaming_evaluations(record_dir)[0].to_dict() == accepted.to_dict()
    save_evaluation_results([accepted], record_dir, config=config, reporting_ref_point=ResultSchema.from_config(config).empty_reference)
    for name in ['candidate_history.json', 'candidate_history.csv']:
        loaded = load_evaluation_results(record_dir / name, config)[0]
        assert loaded.attempt_id == accepted.attempt_id
        assert loaded.manifest_path == accepted.manifest_path
        assert loaded.attempt_history == history
    assert CheckpointState.from_dict({'iteration': 1, 'results_serialized': [accepted.to_dict()]}).results[0].attempt_id == accepted.attempt_id


@pytest.mark.parametrize("submission_crash", [False, True])
def test_worker_crash_retains_serializable_request_and_order(tmp_path, monkeypatch, submission_crash):
    import pickle
    from concurrent.futures import Future
    from mobo_linac.execution.requests import EvaluationRequest
    import mobo_linac.execution.parallel as parallel
    captured = []
    class Pool:
        def __init__(self, **kwargs): pass
        def submit(self, worker, task):
            captured.append(pickle.loads(pickle.dumps(task)))
            if submission_crash:
                raise RuntimeError("broken pool during submission")
            future = Future()
            future.set_exception(RuntimeError('simulated process crash'))
            return future
        def shutdown(self, **kwargs): pass
    monkeypatch.setattr(parallel, 'ProcessPoolExecutor', Pool)
    requests = [EvaluationRequest(f'candidate_{i}', [0.2, 1, -1, 0, 0, 0],
                                 {'charge:nrad': i + 1}, metadata={'index': i}) for i in range(2)]
    out = ProcessPoolEvaluator(TEST_CONFIG, base_results_dir=tmp_path, max_workers=2).evaluate(requests, run_id='crash')
    assert [row['eval_id'] for row in out] == [request.eval_id for request in requests]
    assert all(row['status'] == 'WORKER_CRASH' and 'Worker process crashed' in row['error'] for row in out)
    assert [row['request'] for row in out] == [request.to_dict() for request in requests]
    assert [task.request for task in captured] == [request.to_dict() for request in requests]


@pytest.mark.parametrize("final_z, expected_attempts, expected_status", [
    (8.0, 1, "PREMATURE_LOSS"),      # deterministic physics outcome: never retried
    (None, 3, "TIMEOUT"),            # infrastructure outcome: retried up to the budget
])
def test_retries_follow_simulation_status_policy(temp_project, monkeypatch, final_z, expected_attempts, expected_status):
    import subprocess
    from mobo_linac.config import load_config
    attempts = []

    class StubAstra:
        command = "stub"
        particles = []
        def __init__(self, input_file, workdir, **kwargs):
            self.output = {}
            attempts.append(workdir)
        def __setitem__(self, name, value):
            pass
        def run(self):
            if final_z is None:
                raise subprocess.TimeoutExpired("astra", 1)
            self.output = {"stats": {key: [value] for key, value in {
                "norm_emit_x": 1e-6, "norm_emit_y": 1e-6, "sigma_energy": 0.5e6,
                "sigma_x": 0.5e-3, "sigma_y": 0.5e-3, "sigma_xp": 0.5e-3, "sigma_yp": 0.5e-3,
                "sigma_z": 0.5e-3, "mean_kinetic_energy": 200e6, "transmission_fraction": 1.0,
                "z": final_z}.items()}}

    monkeypatch.setattr("mobo_linac.astra.runner.Astra", StubAstra)
    result = run_worker_task(worker_task([0.2, 1, -1, 0, 0, 0], "policy", 1, temp_project["results_dir"],
                                         temp_project["template_dir"], retries=2,
                                         config=load_config("configs/mobo_200MeV.yaml")))
    assert result["status"] == expected_status
    assert len(attempts) == expected_attempts
    assert len(result["attempt_history"]) == expected_attempts


def test_single_worker_crash_is_reported_like_a_pooled_crash(tmp_path, monkeypatch):
    """One worker still runs out of process: a crashing worker is a WORKER_CRASH, not a parent failure."""
    import os
    def crash(**kwargs):
        os._exit(17)
    monkeypatch.setattr("mobo_linac.execution.parallel.run_astra_eval", crash)
    for workers in (1, 2):
        out = evaluate_candidates([[0.2, 1, -1, 0, 0, 0]], f"crash_{workers}", workers, tmp_path)
        assert [row["status"] for row in out] == ["WORKER_CRASH"]
        assert "Worker process crashed" in out[0]["error"]
