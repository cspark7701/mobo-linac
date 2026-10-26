"""
Unit tests for Result Serialization, DataFrame Conversions, and Checkpoint Management.
"""

from mobo_linac.result_schema import ResultSchema
from pathlib import Path
import pytest
import numpy as np
import pandas as pd

from mobo_linac.evaluation import EvaluationResult, FailureCategory
from mobo_linac.io.checkpoint import (
    CampaignSpec,
    CheckpointState,
    MetricState,
    ProgressState,
    ProposalState,
    RngState,
    load_run_checkpoint,
    migrate_to_v3,
    save_run_checkpoint,
)
from mobo_linac.io.results import load_evaluation_results, results_to_dataframe
from mobo_linac.metrics.exports import save_evaluation_results
import torch
import json

from mobo_linac.io.journal import load_streaming_records, write_streaming_csv
from mobo_linac.io.journal import append_streaming_evaluation, load_streaming_evaluations

from mobo_linac.config import load_config as _load_test_config
TEST_CONFIG = _load_test_config("configs/mobo_200MeV.yaml")


def test_versioned_journal_round_trip_preserves_metadata(tmp_path, sample_results):
    append_streaming_evaluation(tmp_path, sample_results[1], batch_idx=2, candidate_idx=1, config=TEST_CONFIG)
    append_streaming_evaluation(tmp_path, sample_results[0], batch_idx=2, candidate_idx=0, config=TEST_CONFIG)
    (tmp_path / "evaluations_stream.csv").write_text("corrupt csv")
    records = load_streaming_records(tmp_path)
    assert [r.result.to_dict() for r in records] == [r.to_dict() for r in reversed(sample_results)]
    assert [(r.batch_idx, r.candidate_idx) for r in records] == [(2, 1), (2, 0)]
    payload = json.loads((tmp_path / "evaluations_stream.jsonl").read_text().splitlines()[0])
    assert payload["version"] == "1.0"
    assert "batch_idx" not in payload["evaluation"]
    csv_path = write_streaming_csv(tmp_path, config=TEST_CONFIG)
    assert pd.read_csv(csv_path)["evaluation_id"].tolist() == [r.evaluation_id for r in sample_results]


def test_legacy_flat_journal_round_trip_without_csv(tmp_path, sample_results):
    payload = sample_results[0].to_dict()
    payload["batch_idx"] = 3
    (tmp_path / "evaluations_stream.jsonl").write_text(json.dumps(payload) + "\n")
    assert load_streaming_evaluations(tmp_path)[0].to_dict() == sample_results[0].to_dict()
    assert load_streaming_records(tmp_path)[0].batch_idx == 3
    assert not (tmp_path / "evaluations_stream.csv").exists()


@pytest.mark.parametrize("suffix", [b'{"version":', b'{"evaluation": {"run_id": "unfinished',
                                    b'{"evaluation": {"runtime_s": 1e',
                                    b'{"evaluation": {"work_dir": "\\u00'])
def test_truncated_trailing_record_repaired_before_append(tmp_path, sample_results, suffix):
    append_streaming_evaluation(tmp_path, sample_results[0], batch_idx=0, candidate_idx=0, config=TEST_CONFIG)
    journal = tmp_path / "evaluations_stream.jsonl"
    with journal.open("ab") as stream:
        stream.write(suffix)
    with pytest.warns(RuntimeWarning, match="truncated trailing"):
        assert len(load_streaming_records(tmp_path)) == 1
    with pytest.warns(RuntimeWarning, match="truncated trailing"):  # reported again by the repairing append
        append_streaming_evaluation(tmp_path, sample_results[1], batch_idx=0, candidate_idx=1, config=TEST_CONFIG)
    assert len(load_streaming_records(tmp_path)) == 2
    assert len(journal.read_text().splitlines()) == 2


@pytest.mark.parametrize("bad_record", ['not json\n', 'not json', '{bad}\n', '{bad}', '{"version": "99", "evaluation": {}}\n', '{}\n'])
def test_malformed_or_invalid_journal_is_not_hidden_by_csv(tmp_path, sample_results, bad_record):
    append_streaming_evaluation(tmp_path, sample_results[0], batch_idx=0, config=TEST_CONFIG)
    journal = tmp_path / "evaluations_stream.jsonl"
    journal.write_text(journal.read_text() + bad_record)
    before = journal.read_bytes()
    with pytest.raises(ValueError, match="journal"):
        load_streaming_evaluations(tmp_path)
    with pytest.raises(ValueError, match="journal"):
        append_streaming_evaluation(tmp_path, sample_results[1], batch_idx=0, config=TEST_CONFIG)
    assert journal.read_bytes() == before


def test_duplicate_journal_records_are_idempotent_and_conflicts_rejected(tmp_path, sample_results):
    first = sample_results[0]
    append_streaming_evaluation(tmp_path, first, batch_idx=0, candidate_idx=0, config=TEST_CONFIG)
    journal = tmp_path / "evaluations_stream.jsonl"
    original_line = journal.read_text()
    append_streaming_evaluation(tmp_path, first, batch_idx=0, candidate_idx=0, config=TEST_CONFIG)
    assert journal.read_text() == original_line
    journal.write_text(original_line + original_line)
    assert len(load_streaming_records(tmp_path)) == 1
    payload = json.loads(original_line)
    payload["evaluation"]["work_dir"] = "conflicting attempt"
    journal.write_text(original_line + json.dumps(payload) + "\n")
    with pytest.raises(ValueError, match="Conflicting duplicate"):
        load_streaming_records(tmp_path)


def test_valid_unterminated_journal_record_gets_delimited_on_append(tmp_path, sample_results):
    append_streaming_evaluation(tmp_path, sample_results[0], batch_idx=0, config=TEST_CONFIG)
    journal = tmp_path / "evaluations_stream.jsonl"
    journal.write_text(journal.read_text().rstrip("\n"))
    assert len(load_streaming_records(tmp_path)) == 1
    append_streaming_evaluation(tmp_path, sample_results[1], batch_idx=0, config=TEST_CONFIG)
    assert len(load_streaming_records(tmp_path)) == 2


def test_csv_write_failure_preserves_authoritative_journal(tmp_path, sample_results, monkeypatch):
    def fail_csv(*args, **kwargs):
        raise OSError("CSV view unavailable")
    with monkeypatch.context() as patch:
        patch.setattr("mobo_linac.io.journal.write_streaming_csv", fail_csv)
        with pytest.raises(OSError, match="CSV view unavailable"):
            append_streaming_evaluation(tmp_path, sample_results[0], batch_idx=0, config=TEST_CONFIG)
    assert len(load_streaming_records(tmp_path)) == 1
    append_streaming_evaluation(tmp_path, sample_results[0], batch_idx=0, config=TEST_CONFIG)
    assert len(load_streaming_records(tmp_path)) == 1
    assert len(pd.read_csv(tmp_path / "evaluations_stream.csv")) == 1


@pytest.fixture
def sample_results():
    res1 = EvaluationResult(
        evaluation_id="eval_000001",
        run_id="run_001",
        x_physical=[0.20, 1.2, -1.2, 0.0, 0.0, 0.0],
        objectives_physical=[1.2e-6, 1.2e-6, 5.0e4],
        objectives_model=[-1.2e-6, -1.2e-6, -5.0e4],
        diagnostics={"sigma_x": 0.8e-3, "mean_kinetic_energy": 200.0e6},
        simulation_valid=True,
        physically_feasible=True,
        failure_category=FailureCategory.SUCCESS.value,
        runtime_s=2.5,
        work_dir="/tmp/work/eval_1",
    )
    res2 = EvaluationResult(
        evaluation_id="eval_000002",
        run_id="run_001",
        x_physical=[0.25, 1.5, -1.5, 5.0, 2.0, 2.0],
        objectives_physical=[2.5e-6, 2.5e-6, 6.0e4],
        objectives_model=[-2.5e-6, -2.5e-6, -6.0e4],
        diagnostics={"sigma_x": 1.2e-3, "mean_kinetic_energy": 200.0e6},
        simulation_valid=True,
        physically_feasible=False,
        failure_category=FailureCategory.INFEASIBLE_BEAM.value,
        failure_reason="Beam diagnostics violated constraint thresholds",
        runtime_s=2.7,
        work_dir="/tmp/work/eval_2",
    )
    return [res1, res2]


def test_results_to_dataframe(sample_results):
    """Test converting EvaluationResult list to Pandas DataFrame."""
    df = results_to_dataframe(sample_results, config=TEST_CONFIG)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert "evaluation_id" in df.columns
    assert "simulation_valid" in df.columns
    assert "physically_feasible" in df.columns
    assert df.loc[0, "simulation_valid"] == True
    assert df.loc[0, "physically_feasible"] == True
    assert df.loc[1, "physically_feasible"] == False


def test_save_and_load_evaluation_results(sample_results, tmp_path):
    """Test saving and restoring evaluation results to/from JSON and CSV."""
    paths = save_evaluation_results(sample_results, tmp_path, config=TEST_CONFIG, reporting_ref_point=ResultSchema.from_config(TEST_CONFIG).empty_reference)
    assert paths["json"].exists()
    assert paths["csv"].exists()

    loaded_json = load_evaluation_results(paths["json"], config=TEST_CONFIG)
    assert len(loaded_json) == 2
    assert loaded_json[0].evaluation_id == "eval_000001"
    assert loaded_json[0].simulation_valid is True
    assert loaded_json[1].physically_feasible is False

    loaded_csv = load_evaluation_results(paths["csv"], config=TEST_CONFIG)
    assert len(loaded_csv) == 2
    assert loaded_csv[0].evaluation_id == "eval_000001"
    assert loaded_csv[0].simulation_valid is True


@pytest.mark.parametrize("legacy_header", [False, True])
def test_csv_round_trip_preserves_float_bits_without_warnings(tmp_path, sample_results, legacy_header):
    from dataclasses import replace
    import warnings

    values = [0.2804161877670514, -1.2345678901234567, np.nextafter(1.0, 2.0),
              np.nextafter(0.0, 1.0), -0.0, 2.2250738585072014e-308]
    objectives = [1.2345678901234567e-6, 2.3456789012345678e-6, 1234567.8901234567]
    result = replace(sample_results[0], x_physical=values, objectives_physical=objectives,
                     objectives_model=[-value for value in objectives],
                     diagnostics={"sigma_x_m": 0.00012345678901234567},
                     runtime_s=1.2345678901234567)
    path = tmp_path / "precise.csv"
    text = results_to_dataframe([result], TEST_CONFIG).to_csv(index=False)
    path.write_text(("# " if legacy_header else "") + text)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        restored, = load_evaluation_results(path, TEST_CONFIG)
    for field in ("x_physical", "objectives_physical", "objectives_model"):
        assert [float(value).hex() for value in getattr(restored, field)] == [float(value).hex() for value in getattr(result, field)]
    assert restored.runtime_s.hex() == result.runtime_s.hex()
    assert restored.diagnostics == result.diagnostics
    assert restored.evaluation_id == result.evaluation_id
    assert restored.simulation_valid is True and restored.physically_feasible is True


def make_checkpoint_state(iteration, results, hypervolumes, acquisition_mode="qLogNEHVI", seed=42):
    """A complete typed snapshot of a small unconstrained campaign."""
    return CheckpointState(
        iteration=iteration, results=list(results), config=None,
        campaign=CampaignSpec(run_id="test_run", optimization_mode="unconstrained_mobo",
                              acquisition_mode=acquisition_mode, constrained=False, seed=seed,
                              scalar_weights=[1 / 3] * 3, num_initial_samples=len(results), batch_size=1,
                              planned_num_batches=iteration, num_workers=1, total_eval_budget=None, device="cpu"),
        rng=RngState.capture(),
        progress=ProgressState(initial_design=[r.x_physical for r in results], sobol_state=None,
                               evaluation_batches=[0] * len(results), elapsed_wall_time_s=None,
                               evaluation_elapsed_s=None),
        metrics=MetricState(reporting_ref_point=None, reporting_scales=None, metric_history=[],
                            hypervolumes=list(hypervolumes)),
        proposals=ProposalState(proposal_history=[], pending_proposal=None),
    )


def test_save_and_load_checkpoint(sample_results, tmp_path):
    """Typed snapshots round-trip through the v3 payload."""
    ckpt_path = tmp_path / "checkpoint.pt"
    hypervolumes = [0.0, 1.5e-10, 2.1e-10]
    save_run_checkpoint(ckpt_path, make_checkpoint_state(5, sample_results, hypervolumes))
    ckpt = load_run_checkpoint(ckpt_path)
    assert isinstance(ckpt, CheckpointState) and ckpt.version == "3.0" and ckpt.migrated_from is None
    assert ckpt.iteration == 5
    assert ckpt.metrics.hypervolumes == hypervolumes
    assert len(ckpt.results) == 2
    assert ckpt.results[0].evaluation_id == "eval_000001"
    assert ckpt.results[0].simulation_valid is True
    assert ckpt.rng.torch_rng_state is not None and ckpt.rng.numpy_rng_state is not None
    assert not hasattr(ckpt, "__getitem__") and not hasattr(ckpt, "get")


def test_checkpoint_state_schema_validation(sample_results):
    """Construction requires every record field; decoding rejects malformed or unknown structures."""
    state = make_checkpoint_state(3, sample_results, [0.1, 0.2], acquisition_mode="qLogEHVI")
    d = state.to_dict()
    assert d["iteration"] == 3 and d["version"] == "3.0"
    assert len(d["results_serialized"]) == 2
    restored = CheckpointState.from_dict(d)
    assert restored.campaign.acquisition_mode == "qLogEHVI"
    assert len(restored.results) == 2
    assert restored.campaign.seed == 42

    with pytest.raises(TypeError):
        CampaignSpec(run_id="r", optimization_mode="unconstrained_mobo", acquisition_mode="qLogNEHVI",
                     constrained=False, seed=1, scalar_weights=[1.0], num_initial_samples=1, batch_size=1,
                     planned_num_batches=1, num_workers=1, total_eval_budget=None)  # device omitted
    with pytest.raises(ValueError, match="must be a dictionary"):
        CheckpointState.from_dict("not_a_dict")  # type: ignore
    with pytest.raises(ValueError, match="missing required 'iteration' field"):
        CheckpointState.from_dict({"hypervolumes": [0.1]})
    with pytest.raises(ValueError, match="Unknown checkpoint fields"):
        CheckpointState.from_dict({**d, "surprise": 1})
    with pytest.raises(ValueError, match="campaign"):
        CheckpointState.from_dict({**d, "campaign": {**d["campaign"], "typo_seed": 1}})
    with pytest.raises(ValueError, match="Unknown legacy checkpoint fields"):
        CheckpointState.from_dict({"version": "2.0", "iteration": 0, "typo_seed": 1})


def test_v1_and_v2_payloads_migrate_to_identical_v3_states(sample_results):
    """An archived v1 payload and its v2 migration decode to the same typed state."""
    v1 = {"iteration": 1, "results_serialized": [r.to_dict() for r in sample_results], "hypervolumes": [0.0, 0.1],
          "acquisition_mode": "qLogNEHVI", "reporting_ref_point": [-1.0, -1.0, -1.0], "seed": 7, "batch_size": 1,
          "constrained": False, "torch_rng_state": torch.get_rng_state(), "numpy_rng_state": np.random.get_state(),
          "config": None}
    from mobo_linac.io.checkpoint import migrate_v1_to_v2
    v2 = migrate_v1_to_v2(v1)
    from_v1, from_v2 = CheckpointState.from_dict(v1), CheckpointState.from_dict(v2)
    assert from_v1.migrated_from == "1.0" and from_v2.migrated_from == "2.0"
    from_v2.migrated_from = from_v1.migrated_from
    assert repr(from_v1) == repr(from_v2)
    assert from_v1.campaign.num_initial_samples == 1 and from_v1.progress.evaluation_batches == [0, 1]
    assert migrate_to_v3(v1)["version"] == "3.0"


def test_atomic_checkpoint_save(sample_results, tmp_path):
    """Atomic checkpoint writes leave no temporary files; iteration snapshots refresh checkpoint.pt."""
    ckpt_path = tmp_path / "checkpoints" / "checkpoint_iter_02.pt"
    saved_path = save_run_checkpoint(ckpt_path, make_checkpoint_state(2, sample_results, [0.0, 1.2e-10]))
    assert saved_path.exists()
    latest_path = tmp_path / "checkpoints" / "checkpoint.pt"
    assert latest_path.exists()
    assert list(tmp_path.glob("**/*.tmp*")) == []
    assert load_run_checkpoint(saved_path).iteration == load_run_checkpoint(latest_path).iteration == 2
    assert len(load_run_checkpoint(latest_path).results) == 2


def test_checkpoint_discovery_order(sample_results, tmp_path):
    from mobo_linac.io.checkpoint import find_checkpoint, run_directory
    state = make_checkpoint_state(1, sample_results, [0.0])
    pending = save_run_checkpoint(tmp_path / "checkpoints" / "pending_batch.pt", state)
    assert find_checkpoint(tmp_path) == pending
    iteration = save_run_checkpoint(tmp_path / "checkpoints" / "checkpoint_iter_01.pt", state)
    assert find_checkpoint(tmp_path) == tmp_path / "checkpoints" / "checkpoint.pt"
    assert run_directory(iteration) == run_directory(tmp_path) == tmp_path
    assert find_checkpoint(tmp_path / "missing") is None


def test_dynamic_config_column_binding(tmp_path):
    """Verify dynamic column header binding from custom MoboConfig."""
    from mobo_linac.config import ConstraintsConfig, DesignVariableConfig, MoboConfig, ObjectiveConfig

    dvs = [
        DesignVariableConfig("var_a", "key_a", "T", 1.0, 0.1, 0.5, 1.5),
        DesignVariableConfig("var_b", "key_b", "T", 2.0, 0.1, 1.0, 3.0),
        DesignVariableConfig("var_c", "key_c", "T", 3.0, 0.1, 2.0, 4.0),
        DesignVariableConfig("var_d", "key_d", "T", 4.0, 0.1, 3.0, 5.0),
    ]
    objs = [
        ObjectiveConfig("custom_emit", "custom_emit_m", "m", "minimize", -1),
        ObjectiveConfig("custom_energy", "custom_energy_eV", "eV", "minimize", -1),
    ]
    custom_cfg = MoboConfig(
        version="2.0",
        description="Custom 4D 2-Obj Config",
        design_variables=dvs,
        objectives=objs,
        constraints=ConstraintsConfig(),
    )

    custom_res = [
        EvaluationResult(
            evaluation_id="eval_000001",
            run_id="custom_run",
            x_physical=[1.1, 2.2, 3.3, 4.4],
            objectives_physical=[1.0e-6, 2.0e5],
            objectives_model=[-1.0e-6, -2.0e5],
            diagnostics={"sigma_x_m": 0.5e-3, "mean_kinetic_energy_eV": 200.0e6, "transmission_fraction": 1.0},
            simulation_valid=True,
            physically_feasible=True,
        )
    ]

    df = results_to_dataframe(custom_res, config=custom_cfg)
    assert "var_a" in df.columns
    assert "var_d" in df.columns
    assert "custom_emit_m" in df.columns
    assert "model_custom_emit_neg" in df.columns
    assert df.loc[0, "var_a"] == 1.1
    assert df.loc[0, "var_d"] == 4.4

    paths = save_evaluation_results(custom_res, tmp_path / "custom_run", config=custom_cfg, reporting_ref_point=ResultSchema.from_config(custom_cfg).empty_reference)
    loaded_csv = load_evaluation_results(paths["csv"], config=custom_cfg)

    assert len(loaded_csv) == 1
    assert loaded_csv[0].x_physical == [1.1, 2.2, 3.3, 4.4]
    assert loaded_csv[0].objectives_physical == [1.0e-6, 2.0e5]
    assert loaded_csv[0].objectives_model == [-1.0e-6, -2.0e5]


def test_configured_empty_shapes_headers_and_csv_unknown_status(tmp_path):
    from mobo_linac.config import load_config
    from mobo_linac.io.results import get_train_tensors
    config = load_config("configs/mobo_200MeV.yaml")
    config.design_variables = config.design_variables[:2]
    config.objectives = [config.objectives[2], config.objectives[0]]
    x, y, feasible = get_train_tensors([], config=config)
    assert x.shape == (0, 2) and y.shape == (0, 2) and feasible.shape == (0,)
    paths = save_evaluation_results([], tmp_path, config=config, reporting_ref_point=ResultSchema.from_config(config).empty_reference)
    assert load_evaluation_results(paths["json"], config) == []
    assert load_evaluation_results(paths["csv"], config) == []
    assert list(pd.read_csv(tmp_path / "train_X.csv").columns) == [v.name for v in config.design_variables]
    assert list(pd.read_csv(tmp_path / "train_Y.csv").columns) == ["model_sigma_energy_neg", "model_emit_x_neg"]
    columns = [v.name for v in config.design_variables] + [o.explicit_name for o in config.objectives]
    path = tmp_path / "pareto_legacy.csv"
    pd.DataFrame([[0.1, 0.2, 1e5, 1e-6]], columns=columns).to_csv(path, index=False)
    result = load_evaluation_results(path, config)[0]
    assert result.objectives_model == [-1e5, -1e-6]
    assert result.simulation_valid is None and result.physically_feasible is None
    path.write_text("a,b,c,d\n1,2,3,4\n")
    with pytest.raises(ValueError, match="named design"):
        load_evaluation_results(path, config)


def test_named_legacy_model_headers_and_unknown_status_are_preserved(tmp_path):
    from mobo_linac.io.results import get_train_tensors
    path = tmp_path / "pareto.csv"
    columns = ["solenoid_field_T", "quad_1_gradient_T_m", "quad_2_gradient_T_m", "gun_phase_deg", "acc1_acc2_phase_deg", "acc3_acc4_phase_deg", "model_norm_emit_x_neg", "model_norm_emit_y_neg", "model_sigma_energy_neg"]
    pd.DataFrame([[0.1] * 6 + [-1e-6, -2e-6, -3e5]], columns=columns).to_csv(path, index=False)
    result = load_evaluation_results(path, config=TEST_CONFIG)[0]
    assert result.objectives_physical == [1e-6, 2e-6, 3e5]
    assert result.physically_feasible is None and result.simulation_valid is None
    assert get_train_tensors([result], config=TEST_CONFIG)[0].shape == (0, 6)
    assert get_train_tensors([result], exclude_invalid=False, config=TEST_CONFIG)[2].tolist() == [False]


def test_artifact_writer_keeps_pareto_semantics_and_clears_stale_rows(tmp_path, sample_results):
    from mobo_linac.io.artifacts import validate_run_completion
    from mobo_linac.metrics.exports import RunArtifactWriter
    from mobo_linac.config import load_config
    from mobo_linac.metrics.hypervolume import HypervolumeTracker
    from copy import deepcopy
    config = load_config("configs/mobo_200MeV.yaml")
    records = deepcopy(sample_results)
    records[1].objectives_physical = [0.1e-6, 0.1e-6, 1e4]
    records[1].objectives_model = [-0.1e-6, -0.1e-6, -1e4]
    tracker = HypervolumeTracker([-1e-5, -1e-5, -1e6], config)
    writer = RunArtifactWriter(tmp_path, config)
    writer.write(records, tracker)
    assert pd.read_csv(tmp_path / "pareto.csv").iloc[0].norm_emit_x_m_rad == 0.1e-6
    assert pd.read_csv(tmp_path / "pareto_feasible.csv").iloc[0].norm_emit_x_m_rad == records[0].objectives_physical[0]
    assert (tmp_path / "pareto.csv").read_bytes() == (tmp_path / "pareto_all.csv").read_bytes()
    headers = {name: (tmp_path / name).read_text().splitlines()[0] for name in writer.required if name.endswith(".csv")}
    writer.complete(2, 1.0)
    assert validate_run_completion(tmp_path)
    writer.write([], tracker)
    assert not (tmp_path / "run_complete.json").exists()
    for name, header in headers.items():
        assert (tmp_path / name).read_text().splitlines()[0] == header
        assert pd.read_csv(tmp_path / name).empty
    writer.complete(0, 2.0)
    assert validate_run_completion(tmp_path)
    (tmp_path / "pareto_all.csv").write_text("broken")
    assert not validate_run_completion(tmp_path)


def test_export_failure_cannot_leave_completion_marker(tmp_path, sample_results, monkeypatch):
    from mobo_linac.metrics.exports import RunArtifactWriter
    from mobo_linac.metrics.hypervolume import HypervolumeTracker
    writer = RunArtifactWriter(tmp_path, TEST_CONFIG)
    tracker = HypervolumeTracker([-1e-4, -1e-4, -1e7], TEST_CONFIG)
    writer.write(sample_results, tracker)
    writer.complete(2, 1.0)
    def fail_csv(*args, **kwargs):
        raise OSError("Injected CSV failure")
    monkeypatch.setattr(pd.DataFrame, "to_csv", fail_csv)
    with pytest.raises(OSError, match="Injected"):
        writer.write(sample_results, tracker)
    assert not (tmp_path / "run_complete.json").exists()


def _synthetic_results(count):
    return [EvaluationResult(evaluation_id=f"eval_{i + 1:06d}", run_id="synthetic",
                             x_physical=[0.1 * i, 1.0, -1.0, 0.0, 2.0, 3.0],
                             objectives_physical=[1e-6 + 1e-9 * (i % 7), 2e-6 - 1e-9 * (i % 5), 1e5 + i],
                             objectives_model=[-(1e-6 + 1e-9 * (i % 7)), -(2e-6 - 1e-9 * (i % 5)), -(1e5 + i)],
                             diagnostics={}, simulation_valid=True, physically_feasible=i % 3 != 0,
                             failure_category="SUCCESS", failure_reason=None, runtime_s=1.0, work_dir="")
            for i in range(count)]


def test_journal_appends_are_constant_time_without_rereading(tmp_path, monkeypatch):
    """5,000 appends never re-read the journal; the identity index replaces the scan."""
    import time
    import mobo_linac.io.journal as journal_module
    from mobo_linac.io.journal import EvaluationJournal
    journal = EvaluationJournal(tmp_path, TEST_CONFIG)
    reads = []
    original = journal_module._read
    monkeypatch.setattr(journal_module, "_read", lambda *a: reads.append(1) or original(*a))
    def append_without_fsync(path, line):  # isolate CPU cost from disk fsync
        with Path(path).open("a", encoding="utf-8") as stream:
            stream.write(line + "\n")

    monkeypatch.setattr(journal_module, "append_line_durable", append_without_fsync)
    records = _synthetic_results(5000)
    start = time.perf_counter()
    for index, result in enumerate(records):
        journal.append(result, batch_idx=index // 8, candidate_idx=index % 8)
    assert time.perf_counter() - start < 30.0
    assert reads == []
    assert journal.append(records[0], batch_idx=0, candidate_idx=0) is False  # idempotent duplicate
    with pytest.raises(ValueError, match="Conflicting"):
        journal.append(records[0], batch_idx=1, candidate_idx=0)
    monkeypatch.setattr(journal_module, "_read", original)
    assert len(EvaluationJournal(tmp_path, TEST_CONFIG)) == 5000


def test_incremental_artifact_export_matches_full_rebuild(tmp_path):
    """Exports reusing cached conversions are byte-identical to a fresh full rebuild."""
    from mobo_linac.metrics.exports import RunArtifactWriter
    from mobo_linac.metrics.hypervolume import HypervolumeTracker
    results = _synthetic_results(30)
    tracker = HypervolumeTracker([-3e-6, -3e-6, -2e5], TEST_CONFIG)
    incremental = RunArtifactWriter(tmp_path / "incremental", TEST_CONFIG)
    for end in (5, 17, 30):
        incremental.write(results[:end], tracker)
    full = RunArtifactWriter(tmp_path / "full", TEST_CONFIG)
    full.write(results, tracker)
    assert incremental.required == full.required
    for name in full.required:
        assert (tmp_path / "incremental" / name).read_bytes() == (tmp_path / "full" / name).read_bytes(), name
    assert (tmp_path / "full" / "pareto.csv").read_bytes() == (tmp_path / "full" / "pareto_all.csv").read_bytes()
