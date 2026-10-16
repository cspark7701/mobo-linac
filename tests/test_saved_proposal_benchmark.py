"""Saved proposal timing must preserve budgets and report device failures."""

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest
import torch

from mobo_linac.acquisition.mobo import ProposalResult
from mobo_linac.config import load_config
from mobo_linac.result_schema import ResultSchema


def module():
    path = Path(__file__).resolve().parents[1] / "tools/benchmark_saved_proposal.py"
    spec = importlib.util.spec_from_file_location("saved_proposal_benchmark", path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def test_saved_proposal_retains_budget_and_identity(tmp_path, monkeypatch):
    tool = module()
    config = load_config(Path(__file__).resolve().parents[1] / "configs/publication_200MeV.yaml")
    schema = ResultSchema.from_config(config)
    (tmp_path / "model.pt").write_bytes(b"saved-model")
    rows = []
    for i in range(2):
        rows.append(dict(run_id="run", evaluation_id=f"eval_{i}", physically_feasible=bool(i),
                         **{key: .5 for key in schema.design_columns},
                         **{key: -1. for key in schema.model_columns}))
    pd.DataFrame(rows).to_csv(tmp_path / "evaluations.csv", index=False)
    (tmp_path / "proposal_history.json").write_text(json.dumps([{
        "batch_idx": 18, "metadata": {"attempts": [{"num_restarts": 10, "raw_samples": 1024,
            "options": {"batch_limit": 5, "maxiter": 200}}],
            "acquisition_reference": {"point_model": [-2., -2., -2.]}}}]))
    pipeline = SimpleNamespace(training_ids=[("run", "eval_0"), ("run", "eval_1")],
        campaign_metadata={"proposal_iteration": 18}, objective_model=object(), constraint_model=None,
        bounds=torch.tensor([[0.] * 6, [1.] * 6], dtype=torch.double))
    monkeypatch.setattr(tool, "load_config", lambda _: config)
    monkeypatch.setattr(tool.SurrogatePipeline, "load_artifact", lambda *a, **kw: pipeline)
    seen = {}

    def build(model, X, Y, reference, feasible, **kwargs):
        assert X.dtype == Y.dtype == reference.dtype == torch.double
        assert X.shape == (2, 6)
        assert feasible.tolist() == [False, True]
        return SimpleNamespace(sampler=SimpleNamespace(sample_shape=torch.Size([128])))

    def propose(*args, **kwargs):
        seen.update(kwargs)
        return ProposalResult(torch.full((8, 6), .5, dtype=torch.double), torch.tensor(0.), {"method": "primary"})

    monkeypatch.setattr(tool, "build_acquisition_function", build)
    monkeypatch.setattr(tool, "generate_next_candidates", propose)
    tool.benchmark(SimpleNamespace(input=str(tmp_path), output=str(tmp_path), device="cpu",
                                   threads=1, seed=42, batch_limit=1))
    assert (seen["batch_size"], seen["num_restarts"], seen["raw_samples"], seen["maxiter"]) == (8, 10, 1024, 200)
    assert seen["retry_on_failure"] is False
    assert seen["options"] == {"batch_limit": 1, "maxiter": 200}
    result = json.loads((tmp_path / "cpu_result.json").read_text())
    assert result["status"] == "completed"
    assert result["training_count"] == 2
    assert result["mc_sample_shape"] == [128]


def test_unavailable_gpu_records_failure_without_cpu_fallback(tmp_path, monkeypatch):
    tool = module()
    (tmp_path / "model.pt").write_bytes(b"saved-model")
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    with pytest.raises(RuntimeError, match="CUDA is unavailable"):
        tool.benchmark(SimpleNamespace(input=str(tmp_path), output=str(tmp_path), device="cuda:0",
                                       threads=1, seed=42, batch_limit=1))
    result = json.loads((tmp_path / "cuda_0_result.json").read_text())
    assert result["status"] == "failed"
    assert result["device"] == "cuda:0"


@pytest.mark.parametrize("failed", [False, True])
def test_primary_cleanup_requires_both_benchmarks_to_succeed(tmp_path, monkeypatch, failed):
    tool = module()
    monkeypatch.setattr(tool, "__file__", str(tmp_path / "tools/benchmark_saved_proposal.py"))
    production = tmp_path / "results/paper_production"
    primary = production / "04_primary"
    primary.mkdir(parents=True)
    (primary / "old_result").write_text("old")
    screening = production / "03_screening"
    screening.mkdir()
    (production / "status").mkdir()
    (production / "status/04_primary.failed").write_text("old")
    (production / "logs").mkdir()
    (production / "logs/04_primary_old.log").write_text("old")
    output = production / "device_benchmark"

    class Child:
        pid = 123

        def __init__(self, command, **kwargs):
            self.device = command[command.index("--device") + 1]
            result = dict(device=self.device, status="completed", elapsed_s=3.,
                          construction_s=1., optimization_s=2., model_sha256="same", dtype="float64",
                          training_count=152, batch_size=8, num_restarts=10, raw_samples=1024,
                          options={"batch_limit": 1, "maxiter": 200}, mc_sample_shape=[128])
            if failed and self.device == "cuda:0":
                result["status"] = "failed"
            (output / f"{self.device.replace(':', '_')}_result.json").write_text(json.dumps(result))

        def wait(self):
            return int(failed and self.device == "cuda:0")

    monkeypatch.setattr(tool.subprocess, "Popen", Child)
    monkeypatch.setattr(tool.subprocess, "run", lambda *a, **kw: SimpleNamespace(stdout=""))
    args = SimpleNamespace(input=str(output / "input"), output=str(output), threads=1,
                           seed=42, batch_limit=1, remove_primary=True, task_record=None)
    if failed:
        with pytest.raises(RuntimeError, match="primary results retained"):
            tool.compare(args)
    else:
        tool.compare(args)
    assert primary.exists() is failed
    assert (production / "status/04_primary.failed").exists() is failed
    assert (production / "logs/04_primary_old.log").exists() is failed
    assert screening.exists()
    record = json.loads((output / "comparison.json").read_text())
    assert record["primary_removed"] is not failed
