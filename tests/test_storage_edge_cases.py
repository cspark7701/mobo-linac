"""Corrupt journals, mismatched reporting conventions and audit evidence fail closed."""

from dataclasses import replace
from pathlib import Path
import json

import numpy as np
import pandas as pd
import pytest
import torch

from mobo_linac.evaluation import EvaluationResult, create_evaluation_result
from mobo_linac.io import checkpoint, journal, artifacts, results, run_data
from mobo_linac.astra.runner import run_astra_eval
from mobo_linac.verification.audit import audit_attempt
from mobo_linac.result_schema import ResultSchema


@pytest.mark.parametrize(
    "marker", [{}, {"schema_version": 1, "status": "completed", "artifacts": {"../escape": "digest"}}]
)
def test_completion_rejects_invalid_or_escaping_markers(tmp_path, marker):
    (tmp_path / "run_complete.json").write_text(json.dumps(marker))
    assert not artifacts.validate_run_completion(tmp_path)


@pytest.mark.parametrize("fault", ["object", "envelope", "position", "identity"])
def test_journal_invalid_records(fault):
    result = EvaluationResult("one", "run", []).to_dict()
    payload = {"version": "1.0", "evaluation": result}
    if fault == "object":
        payload = []
    if fault == "envelope":
        payload["extra"] = 1
    if fault == "position":
        payload["batch_idx"] = -1
    if fault == "identity":
        result["run_id"] = 123
    with pytest.raises(ValueError):
        journal._decode(payload)


def test_incomplete_unicode_and_journal_result_view(tmp_path, sample_config):
    data = b"\xe2\x82"
    try:
        data.decode()
    except UnicodeDecodeError as error:
        assert journal._incomplete_tail(data, error)
    assert journal.EvaluationJournal(tmp_path, sample_config).results == []


def test_checkpoint_storage_boundaries(tmp_path, monkeypatch):
    with pytest.raises(TypeError):
        checkpoint.save_run_checkpoint(tmp_path / "x.pt", {})
    with pytest.raises(ValueError):
        torch.save([], tmp_path / "bad.pt")
        checkpoint.load_run_checkpoint(tmp_path / "bad.pt")
    directory = tmp_path / "checkpoints"
    directory.mkdir()
    path = directory / "checkpoint_iter_01.pt"
    path.touch()
    assert checkpoint.find_checkpoint(tmp_path) == path
    assert checkpoint._float_list(torch.tensor([1.0, 2.0])) == [1.0, 2.0]
    rng = checkpoint.RngState.capture()
    rng.cuda_rng_states = [torch.tensor([], dtype=torch.uint8)]
    with pytest.raises(ValueError, match="CUDA RNG"):
        rng.validate()
    rng.cuda_rng_states = [torch.zeros(2, dtype=torch.uint8)]
    seen = []
    monkeypatch.setattr(torch.cuda, "set_rng_state_all", seen.append)
    rng.restore()
    assert len(seen) == 1


def test_training_reader_missing_invalid_and_duplicate_rows(sample_config, tmp_path):
    schema = ResultSchema.from_config(sample_config)
    row = EvaluationResult(
        "one", "run", sample_config.get_nominal_parameters(), objectives_model=[-1.0] * 3, simulation_valid=True
    )
    assert (
        results.get_training_observations([replace(row, objectives_model=None)], config=sample_config).train_X.shape[0]
        == 0
    )
    with pytest.raises(ValueError, match="width"):
        results.get_training_observations([replace(row, x_physical=[1])], config=sample_config)
    with pytest.raises(ValueError, match="Duplicate"):
        results.get_training_observations([row, row], config=sample_config)
    with pytest.raises(FileNotFoundError):
        results.load_evaluation_results(tmp_path / "missing.csv", sample_config)
    path = tmp_path / "history.txt"
    path.write_text("data")
    with pytest.raises(ValueError, match="extension"):
        results.load_evaluation_results(path, sample_config)
    frame = results.results_to_dataframe([row], sample_config)
    frame["simulation_valid"] = "not_boolean"
    path = tmp_path / "bad.csv"
    frame.to_csv(path, index=False)
    with pytest.raises(ValueError, match="boolean"):
        results.load_evaluation_results(path, sample_config)
    raw = {
        "status": "success",
        "parameters": row.x_physical,
        "objectives": dict(zip(schema.physical_columns, [1e-6, 1e-6, 5e5])),
        "diagnostics": {},
        "stats": {"z": [1.0]},
    }
    assert create_evaluation_result(raw, sample_config).failure_category == "PREMATURE_BEAM_LOSS"


@pytest.mark.parametrize(
    "fault", ["configuration", "history", "columns", "nonfinite", "counts", "ref_parse", "ref_mismatch", "ref_valid"]
)
def test_run_reader_corrupt_reporting(publication_runs, fault):
    root = publication_runs[0]
    if fault == "configuration":
        (root / "config.json").unlink()
        (root / "config.yaml").unlink()
    if fault == "history":
        (root / "candidate_history.json").unlink()
        (root / "candidate_history.csv").unlink()
        (root / "evaluations.csv").unlink()
    frame = pd.read_csv(root / "hypervolume.csv")
    if fault == "columns":
        frame = frame.drop(columns=["num_valid_points"])
    if fault == "nonfinite":
        frame["feasible_hypervolume"] = np.nan
    if fault == "counts":
        frame["num_feasible_points"] = -1
    if fault.startswith("ref_"):
        ref = json.loads((root / "reporting_metadata.json").read_text())["reporting_ref_point"]
        frame["reporting_ref_point_model"] = (
            repr(ref) if fault == "ref_valid" else "garbage" if fault == "ref_parse" else "[0,0,0]"
        )
    frame.to_csv(root / "hypervolume.csv", index=False)
    if fault == "ref_valid":
        assert run_data.read_run_data(root).results
    else:
        with pytest.raises((ValueError, FileNotFoundError)):
            run_data.read_run_data(root)


def test_candidate_selection_without_history_and_legacy_join(publication_runs, tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(FileNotFoundError):
        run_data.discover_candidate_source(empty)
    child = empty / "nested"
    child.mkdir()
    (child / "candidate_history.json").write_text("[]")
    assert run_data.discover_candidate_source(empty) == child / "candidate_history.json"
    root = publication_runs[0]
    config = run_data.read_run_data(root).config
    source = pd.read_csv(root / "pareto.csv")
    source = source.drop(columns=["evaluation_id", "run_id"])
    source.to_csv(root / "pareto.csv", index=False)
    assert run_data.load_candidates(root / "pareto.csv", config)
    source.iloc[0, source.columns.get_loc(config.design_variables[0].name)] = 999
    source.to_csv(root / "pareto.csv", index=False)
    with pytest.raises(ValueError, match="do not match"):
        run_data.load_candidates(root / "pareto.csv", config)


@pytest.mark.parametrize(
    "fault",
    [
        "attempt",
        "inputs",
        "after",
        "after_hash",
        "objectives",
        "diagnostics",
        "executable_missing",
        "executable_hash",
        "parameters",
        "status",
        "legacy",
    ],
)
def test_audit_each_provenance_mismatch(recording_astra_project, tmp_path, fault):
    _, config = recording_astra_project
    raw = run_astra_eval(
        config.get_nominal_parameters(), "audit", 1, base_results_dir=tmp_path / "results", config=config
    )
    result = create_evaluation_result(raw, config)
    path = Path(result.manifest_path)
    manifest = json.loads(path.read_text())
    if fault == "attempt":
        manifest["attempt_id"] = "other"
    if fault == "inputs":
        manifest["input_hashes"] = {}
    if fault == "after":
        manifest["input_hashes_after_execution"] = {}
    if fault == "after_hash":
        manifest["input_hashes_after_execution"]["astra.in"] = "incorrect"
    if fault == "objectives":
        manifest["objectives"]["norm_emit_x"] *= 2
    if fault == "diagnostics":
        manifest["diagnostics"] = {}
    if fault == "executable_missing":
        manifest["executable"] = {}
    if fault == "executable_hash":
        manifest["executable"]["sha256"] = "incorrect"
    if fault == "parameters":
        manifest["parameters"] = [999]
    if fault == "status":
        manifest["status"] = "TIMEOUT"
    if fault == "legacy":
        manifest["schema_version"] = 0
    path.write_text(json.dumps(manifest))
    audit = audit_attempt(result, config=config)
    assert audit["issues"]
    assert audit["audit_status"] == ("UNKNOWN" if fault == "legacy" else "FAILED")


@pytest.mark.parametrize("fault", ["parameters", "feasibility"])
def test_identified_pareto_must_match_history(publication_runs, fault):
    root = publication_runs[0]
    config = run_data.read_run_data(root).config
    frame = pd.read_csv(root / "pareto.csv")
    if fault == "parameters":
        frame.iloc[0, frame.columns.get_loc(config.design_variables[0].name)] = 999
    path = root / ("pareto.csv" if fault == "parameters" else "pareto_feasible.csv")
    frame.to_csv(path, index=False)
    with pytest.raises(ValueError):
        run_data.load_candidates(path, config)
