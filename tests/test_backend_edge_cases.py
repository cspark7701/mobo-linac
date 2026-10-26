"""Simulator adapter boundaries and worker failures retain explicit identities and provenance."""

from dataclasses import asdict, replace
from pathlib import Path
import sys
from types import SimpleNamespace, ModuleType

import pytest

from mobo_linac.astra import runner, workdir
from mobo_linac.astra.parser import AstraOutputParser
from mobo_linac.execution import parallel, contracts
from mobo_linac.execution.candidate_evaluator import CandidateEvaluatorBase, compute_metric_deltas
from mobo_linac.execution.mock import _in_limit_value
from mobo_linac.evaluation import EvaluationResult
from mobo_linac.requests import EvaluationRequest


@pytest.mark.parametrize("fault", ["output", "objective", "diagnostic", "particle_attr", "counts_empty", "counts", "z"])
def test_parser_corruption_is_explicit(sample_config, fault):
    stats = {
        "norm_emit_x": [1e-6],
        "norm_emit_y": [1e-6],
        "sigma_energy": [5e5],
        "sigma_x": [0.0005],
        "sigma_y": [0.0005],
        "sigma_xp": [0.0005],
        "sigma_yp": [0.0005],
        "sigma_z": [0.0005],
        "mean_kinetic_energy": [2e8],
        "transmission": [1.0],
        "z": [16.2],
    }
    sim = SimpleNamespace(output={"stats": stats}, particles=[])
    if fault == "output":
        sim.output = None
    if fault == "objective":
        stats["norm_emit_x"] = []
    if fault == "diagnostic":
        stats["sigma_x"] = ["invalid"]
    if fault == "particle_attr":
        sim.particles = [object(), object()]
    if fault == "counts_empty":
        stats["landf_n_particles"] = []
    if fault == "counts":
        stats["landf_n_particles"] = [100, 99]
    if fault == "z":
        stats["z"] = [float("nan")]
    result = AstraOutputParser(config=sample_config).parse_astra_simulation(sim)
    assert result.simulation_valid is (fault in ("particle_attr", "counts_empty", "counts"))


def test_parser_logs_are_optional_and_read_errors_are_nonfatal(tmp_path, sample_config, monkeypatch):
    parser = AstraOutputParser(config=sample_config)
    assert parser.parse_log_dir(None) == {}
    (tmp_path / "run.log").write_text("\n".join(map(str, range(15))))
    assert parser.parse_log_dir(tmp_path)["log_summary"].splitlines() == list(map(str, range(5, 15)))
    monkeypatch.setattr(Path, "read_text", lambda *a, **k: (_ for _ in ()).throw(OSError("unreadable")))
    assert parser.parse_log_dir(tmp_path) == {}


def test_lazy_runtime_compatibility_and_parameter_provenance(monkeypatch, sample_config):
    distgen = ModuleType("distgen")
    sub = ModuleType("distgen.generator")
    sub.Generator = object()
    astra = ModuleType("astra")
    astra.Astra = object()
    monkeypatch.setitem(sys.modules, "distgen", distgen)
    monkeypatch.setitem(sys.modules, "distgen.generator", sub)
    monkeypatch.setitem(sys.modules, "astra", astra)
    monkeypatch.setattr(runner, "Astra", None)
    assert runner.initialize_astra_backend() is astra.Astra
    assert distgen.Generator is sub.Generator
    monkeypatch.setitem(sys.modules, "distgen", None)
    runner._install_distgen_compatibility()
    sample_config.simulation.template_dir = None
    with pytest.raises(ValueError, match="template_dir"):
        runner.resolve_template_dir(sample_config)
    values = sample_config.get_nominal_parameters()
    v = sample_config.design_variables[0]
    applied = runner.applied_lattice_perturbations(
        values,
        sample_config,
        {v.astra_key: values[0]},
        {"field": 0.1, "source": 0.2},
        {"field": v.name, "source": "unknown"},
    )
    assert applied == {"field": 0.1}
    with pytest.raises(TypeError):
        runner.run_astra_eval(values, "run", 1, config=None)
    with pytest.raises(ValueError, match="timeout"):
        runner.run_astra_eval(values, "run", 1, config=sample_config, timeout=0)


def test_workdir_invariants(tmp_path):
    manager = workdir.AstraWorkDirManager(tmp_path / "results", tmp_path / "template")
    assert workdir.format_eval_id("12") == "eval_000012"
    manifest = tmp_path / "manifest.json"
    manifest.write_text('{"schema_version":99}')
    with pytest.raises(ValueError, match="schema"):
        workdir.read_evaluation_manifest(manifest)
    with pytest.raises(FileNotFoundError):
        manager.prepare_eval_dir("run", 1)
    attempt = manager.get_eval_dir("run", 1) / "attempt_a"
    attempt.mkdir(parents=True)
    with pytest.raises(FileExistsError):
        manager.reserve_attempt("run", 1, "attempt_a")
    with pytest.raises(ValueError):
        manager.cleanup_eval_dir(tmp_path / "results" / "invalid")
    manager.cleanup_eval_dir(manager.get_eval_dir("run", 2))
    with pytest.raises(ValueError, match="provenance"):
        manager.cleanup_eval_dir(attempt)
    source = tmp_path / "inputs"
    source.mkdir()
    (source / "astra.in").write_text("input")
    (source / "folder").mkdir()
    (tmp_path / "provenance").mkdir()
    assert manager.snapshot_inputs(source, tmp_path / "provenance")


def test_worker_exception_retry_and_in_process_mode(tmp_path, sample_config, monkeypatch):
    calls = []

    def fail(**kwargs):
        calls.append(kwargs)
        raise OSError("worker dependency failed")

    monkeypatch.setattr(parallel, "run_astra_eval", fail)
    task = parallel.WorkerTask(
        0,
        EvaluationRequest(1, sample_config.get_nominal_parameters()).to_dict(),
        "run",
        str(tmp_path),
        str(tmp_path),
        retries=1,
        config=asdict(sample_config),
    )
    result = parallel.run_worker_task(task)
    assert result["status"] == "UNHANDLED_EXCEPTION" and len(calls) == 2
    assert len(result["attempt_history"]) == 2
    evaluator = parallel.ProcessPoolEvaluator(config=sample_config, base_results_dir=tmp_path, in_process=True)
    assert (
        evaluator.evaluate([EvaluationRequest(1, sample_config.get_nominal_parameters())], "debug")[0]["status"]
        == "UNHANDLED_EXCEPTION"
    )
    for kwargs in (
        {"config": None},
        {"config": sample_config, "retries": -1},
        {"config": sample_config, "max_workers": 0},
    ):
        with pytest.raises((ValueError, TypeError)):
            parallel.ProcessPoolEvaluator(**kwargs)


def test_evaluator_identity_fallbacks_and_empty_batches(sample_config):
    requests = [EvaluationRequest(1, sample_config.get_nominal_parameters())]

    class Backend:
        def evaluate(self, requests, run_id, on_complete=None):
            return [{"status": "failed", "candidate_idx": 0, "error": "failed"}]

    assert contracts.evaluate_requests(Backend(), [], run_id="r", config=sample_config) == []
    out = contracts.evaluate_requests(Backend(), requests, run_id="r", config=sample_config)
    assert out[0].result.evaluation_id == "eval_000001"
    with pytest.raises(ValueError, match="stable candidate"):
        contracts._decode_completion({}, ["eval_000001"], {"eval_000001": requests[0]}, "r", sample_config)

    class Foreign:
        def evaluate(self, requests, run_id, on_complete=None):
            return [EvaluationResult("foreign", run_id, requests[0].parameters)]

    with pytest.raises(ValueError, match="unexpected"):
        contracts.evaluate_requests(Foreign(), requests, run_id="r", config=sample_config)
    assert _in_limit_value(SimpleNamespace(lower_default=None, upper_default=None)) == 1


def test_candidate_contract_errors_and_overflow(sample_config, tmp_path):
    class Candidate(CandidateEvaluatorBase):
        def generate_evaluation_plan(self, candidates):
            return super().generate_evaluation_plan(candidates)

    with pytest.raises(TypeError):
        Candidate(config=None)
    with pytest.raises(ValueError):
        Candidate(config=sample_config, num_workers=0)
    instance = Candidate(config=sample_config, base_output_dir=tmp_path)
    with pytest.raises(NotImplementedError):
        instance.generate_evaluation_plan([])
    assert instance.evaluate_plan_parallel([]) == []
    before = EvaluationResult("b", "r", [], objectives_physical=[1e-300] * 3, diagnostics={"transmission_fraction": 1})
    after = replace(before, objectives_physical=[1e300] * 3)
    result = compute_metric_deltas(before, after, sample_config)
    assert "nonfinite_relative_error" in result["comparison_issues"].values()


def test_partial_input_snapshot_cannot_be_claimed_complete(tmp_path):
    root = tmp_path / "work"
    root.mkdir()
    provenance = tmp_path / "provenance"
    (provenance / "inputs").mkdir(parents=True)
    attempt = runner._Attempt("run", "eval_1", "attempt_1", 0, root, provenance, [], "", None, {}, {}, [])
    runner.capture_provenance(attempt, SimpleNamespace())
    assert attempt.status.value == "PROVENANCE_ERROR" and "partial provenance" in attempt.provenance_error
    manager = workdir.AstraWorkDirManager(tmp_path / "results", root)
    (tmp_path / "other").mkdir()
    assert manager.snapshot_inputs(root, tmp_path / "other", names=["absent"]) == {}


def test_missing_future_completion_fails_instead_of_dropping_candidate(tmp_path, sample_config, monkeypatch):
    monkeypatch.setattr(parallel, "as_completed", lambda futures: [])
    pool = SimpleNamespace(submit=lambda *a: object())
    evaluator = parallel.ProcessPoolEvaluator(config=sample_config, base_results_dir=tmp_path)
    monkeypatch.setattr(evaluator, "_pool", lambda: pool)
    with pytest.raises(RuntimeError, match="lost"):
        evaluator.evaluate([EvaluationRequest(1, sample_config.get_nominal_parameters())], "lost")
