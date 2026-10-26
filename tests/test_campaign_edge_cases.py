"""Campaign boundaries reject incompatible plans and damaged durable state."""

from copy import deepcopy
from dataclasses import asdict, replace
import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest
import torch

from mobo_linac.campaigns import runner as campaigns, recovery, state, scheduler, scalarized_suite as suites
from mobo_linac.campaigns.benchmark import BenchmarkCampaignRunner
from mobo_linac.execution.mock import MockEvaluator
from mobo_linac.io.checkpoint import save_run_checkpoint
from test_resume_edge_cases import original_checkpoint as original_checkpoint, snapshot as snapshot


@pytest.mark.parametrize(
    "kwargs",
    [
        {"num_initial_samples": 2, "batch_size": 2, "num_batches": 1, "total_eval_budget": 5},
        {"optimization_mode": "scalarized_bo", "constrained": True},
    ],
)
def test_inconsistent_campaign_plans_fail_before_output(sample_config, tmp_path, kwargs):
    with pytest.raises(ValueError):
        campaigns.MoboCampaignRunner(config=sample_config, output_dir=tmp_path / "never", **kwargs)
    assert not (tmp_path / "never").exists()


def test_measured_noise_requires_explicit_values(sample_config, tmp_path):
    sample_config.model.noise_mode = "measured_fixed"
    with pytest.raises(ValueError, match="fixed noise"):
        campaigns.MoboCampaignRunner(config=sample_config, output_dir=tmp_path / "never", num_batches=1)


def test_generated_run_path_and_existing_journal(sample_config, tmp_path):
    r = campaigns.MoboCampaignRunner(
        config=sample_config, base_results_dir=tmp_path, run_name="generated", num_batches=0
    )
    assert r.run_dir.name.startswith("generated_")
    (r.run_dir / "evaluations_stream.jsonl").write_text("")
    with pytest.raises(ValueError, match="requires resume"):
        r.run()
    with pytest.raises(FileNotFoundError):
        campaigns.MoboCampaignRunner(output_dir=r.run_dir, resume=True, acq_type="qLogNEI").run()


def test_final_evaluator_cleanup_and_completion_guards(sample_config, tmp_path, monkeypatch, caplog):
    class BrokenClose(MockEvaluator):
        def close(self):
            raise OSError("close failure")

    monkeypatch.setattr(campaigns.MoboCampaignRunner, "build_evaluator", lambda self: BrokenClose(config=sample_config))
    r = campaigns.MoboCampaignRunner(
        config=sample_config,
        output_dir=tmp_path / "close",
        num_initial_samples=2,
        num_batches=0,
        export_plots=False,
        device="cpu",
    )
    assert len(r.run()[0]) == 2
    assert "Failed to close evaluator" in caplog.text
    monkeypatch.setattr(campaigns, "evaluate_requests", lambda *a, **k: [])
    r = campaigns.MoboCampaignRunner(
        config=sample_config,
        output_dir=tmp_path / "incomplete",
        num_initial_samples=2,
        num_batches=0,
        export_plots=False,
        device="cpu",
    )
    with pytest.raises(ValueError, match="every submitted"):
        r.run()


def test_loop_reference_and_pending_candidate_guards(snapshot, tmp_path):
    saved, config = snapshot
    r = campaigns.MoboCampaignRunner(config=config, output_dir=tmp_path, export_plots=False)
    loop = campaigns.CampaignLoop(r, saved)
    r._requested_reporting_ref = [1]
    with pytest.raises(ValueError, match="finite configured"):
        loop.prepare_outputs()
    r._requested_reporting_ref = [1, 1, 1]
    with pytest.raises(ValueError, match="resume reporting"):
        loop.prepare_outputs()
    saved.proposals.pending_proposal = {"batch_idx": 1, "candidates": [config.get_nominal_parameters()]}
    with pytest.raises(ValueError, match="Recovery candidates"):
        loop.evaluate([[0] * 6], 1)


def test_legacy_resume_requires_inferable_base(snapshot):
    saved, config = snapshot
    saved.campaign.seed = None
    with pytest.raises(ValueError, match="infer"):
        state.migrate_legacy_v1_state(saved, config, None)
    saved.campaign.seed = 42
    saved.campaign.optimization_mode = "scalarized_bo"
    with pytest.raises(ValueError, match="Legacy scalar weights"):
        state.migrate_legacy_v1_state(saved, config, [-1, 1, 1])
    saved.campaign.optimization_mode = "unconstrained_mobo"
    saved.campaign.num_initial_samples = 1
    saved.progress.evaluation_batches = [0, 1]
    saved.iteration = 1
    saved.metrics.reporting_ref_point = None
    saved.migration_notes = ["legacy test"]
    with pytest.warns(RuntimeWarning, match="best effort"):
        state.migrate_legacy_v1_state(saved, config, None)
    assert saved.progress.sobol_state["num_generated"] == 2


@pytest.mark.parametrize("fault", ["missing", "no_base", "ahead"])
def test_pending_checkpoint_selection_rejects_corruption(snapshot, tmp_path, monkeypatch, fault):
    saved, _ = snapshot
    pending = deepcopy(saved)
    pending.proposals.pending_proposal = {"batch_idx": 1}
    (tmp_path / "checkpoints").mkdir()
    (tmp_path / "checkpoints/pending_batch.pt").touch()
    if fault == "missing":
        pending.proposals.pending_proposal = None
    if fault == "ahead":
        pending.iteration = 1
    completed = None if fault == "no_base" else saved
    monkeypatch.setattr(
        recovery, "load_run_checkpoint", lambda path: pending if Path(path).name == "pending_batch.pt" else completed
    )
    with pytest.raises(ValueError):
        recovery.load_resume_candidate(tmp_path)


@pytest.mark.parametrize("fault", ["configuration", "history", "journal_run", "journal_record"])
def test_recovery_rejects_conflicting_records(snapshot, tmp_path, monkeypatch, fault):
    saved, config = snapshot
    pending = None
    completed = None
    record = SimpleNamespace(result=deepcopy(saved.results[0]), batch_idx=0, candidate_idx=0)
    records = []
    if fault == "configuration":
        completed = deepcopy(saved)
        pending = deepcopy(saved)
        pending.config["name"] = "display_only_change"
    if fault == "history":
        completed = deepcopy(saved)
        pending = deepcopy(saved)
        pending.results[0].failure_reason = "different retained result"
    if fault == "journal_run":
        record.result.run_id = "other"
        records = [record]
    if fault == "journal_record":
        record.candidate_idx = 99
        records = [record]
    monkeypatch.setattr(recovery, "load_streaming_records", lambda directory: records)
    with pytest.raises(ValueError):
        recovery.reconcile_resume(saved, completed, pending, config, tmp_path)


def test_scheduler_close_is_best_effort(sample_config, tmp_path, monkeypatch):
    class Backend:
        def close(self):
            raise RuntimeError("cleanup failed")

    job = scheduler.CampaignJob(
        asdict(sample_config),
        None,
        "unconstrained_qlognehvi",
        42,
        str(tmp_path),
        2,
        1,
        1,
        3,
        1,
        "cpu",
        [-1, -1, -1],
        Backend(),
        1,
        20,
    )
    called = []
    monkeypatch.setattr(torch, "set_num_threads", called.append)
    monkeypatch.setattr(
        scheduler, "campaign_runner", lambda *a, **k: SimpleNamespace(run=lambda: ([1, 2, 3], None, tmp_path))
    )
    result = scheduler.run_campaign_job(job)
    assert called == [1] and result["evaluation_count"] == 3


@pytest.mark.parametrize("bad", ["version", "identity", "budget", "json", "counts"])
def test_benchmark_completion_state_corruption(sample_config, publication_runs, tmp_path, monkeypatch, bad):
    benchmark = BenchmarkCampaignRunner(
        sample_config,
        output_dir=tmp_path / "benchmark",
        algorithms=["unconstrained_qlognehvi"],
        seeds=[42],
        total_eval_budget=3,
        n_sobol_init=2,
        batch_size=1,
    )
    run = benchmark.get_run_dir("unconstrained_qlognehvi", 42)
    run.mkdir(parents=True)
    status = {
        "version": 1,
        "algorithm": "unconstrained_qlognehvi",
        "seed": 42,
        "effective_budget": 3,
        "status": "completed",
        "evaluation_count": 3,
    }
    if bad == "version":
        status["version"] = 99
    if bad == "identity":
        status["seed"] = 99
    if bad == "budget":
        status["effective_budget"] = 0
    path = run / "benchmark_state.json"
    path.write_text("bad" if bad == "json" else json.dumps(status))
    if bad == "counts":
        monkeypatch.setattr("mobo_linac.campaigns.benchmark.validate_run_completion", lambda run: True)
        for name in ["reporting_metadata.json", "candidate_history.csv", "metrics_history.csv"]:
            (run / name).write_bytes((publication_runs[0] / name).read_bytes())
        pd.DataFrame({"evaluation_id": ["duplicate"] * 3}).to_csv(run / "candidate_history.csv", index=False)
    assert benchmark._run_status("unconstrained_qlognehvi", 42, require_signature=False) in (
        "incomplete",
        "incompatible",
    )
    with pytest.raises(RuntimeError, match="expected"):
        benchmark._complete_job(None, {"evaluation_count": 0})


def test_benchmark_empty_analysis_and_invalid_workers(sample_config, tmp_path):
    with pytest.raises(ValueError):
        BenchmarkCampaignRunner(sample_config, output_dir=tmp_path, num_workers=0)
    with pytest.raises(FileNotFoundError):
        BenchmarkCampaignRunner.from_output_dir(tmp_path)
    benchmark = BenchmarkCampaignRunner(
        sample_config,
        output_dir=tmp_path,
        algorithms=["unconstrained_qlognehvi"],
        seeds=[42],
        total_eval_budget=3,
        n_sobol_init=2,
        batch_size=1,
    )
    aggregate, summary = benchmark.analyze_completed_results()
    assert aggregate.empty and summary.empty


def test_suite_preflight_and_explicit_aggregation(sample_config, tmp_path, monkeypatch):
    with pytest.raises(ValueError):
        suites.case_seed(sample_config, "balanced", 42, 0, "bad")
    with pytest.raises(ValueError):
        suites._recorded_case(tmp_path)
    for config, options in [
        (replace(sample_config, scalarized_cases={}), {}),
        (sample_config, {"seed": 2**32 - 1}),
        (sample_config, {"reporting_ref_point": [1]}),
    ]:
        with pytest.raises(ValueError):
            suites.run_scalarized_suite(config=config, output_dir=tmp_path / "invalid", **options)
    root = tmp_path / "invalid_meta"
    root.mkdir()
    (root / "evaluations.csv").touch()
    with pytest.raises(ValueError, match="metadata"):
        suites.aggregate_scalarized_cases(root, case_dirs=[root])
    (root / "reporting_metadata.json").write_text("{}")
    with pytest.raises(ValueError, match="completed"):
        suites.aggregate_scalarized_cases(root)
    output = tmp_path / "suite"
    suites.run_scalarized_suite(
        config=sample_config,
        n_iterations=0,
        num_initial_samples=2,
        cases_to_run=["balanced"],
        output_dir=output,
        evaluator=MockEvaluator(config=sample_config),
        device="cpu",
        export_paper_table_dir=tmp_path / "table",
        reporting_ref_point=[-1e-5, -1e-5, -2e6],
    )
    assert (tmp_path / "table/phase1_cases_table.tex").exists()
    assert suites.aggregate_scalarized_cases(output, case_dirs=[output / "balanced"])["num_cases"] == 1


def pending_snapshot(saved, config):
    saved.campaign.batch_size = 1
    saved.campaign.planned_num_batches = 1
    saved.proposals.pending_proposal = {
        "version": "1.0",
        "batch_idx": 1,
        "candidates": [config.get_nominal_parameters()],
        "evaluation_ids": ["eval_000003"],
        "metadata": {},
    }
    saved.proposals.proposal_history.append({"batch_idx": 1, "metadata": {}})
    return saved


@pytest.mark.parametrize("fault", ["metadata", "uncovered", "future_iteration"])
def test_stale_proposal_cannot_be_discarded(snapshot, tmp_path, monkeypatch, fault):
    saved, config = snapshot
    pending = pending_snapshot(deepcopy(saved), config)
    saved.campaign.batch_size = 1
    saved.campaign.planned_num_batches = 1
    completed = saved if fault == "metadata" else None
    if fault != "metadata":
        pending.proposals.proposal_history = None
    if fault == "future_iteration":
        saved.results.append(
            replace(saved.results[0], evaluation_id="eval_000003", x_physical=config.get_nominal_parameters())
        )
        saved.progress.evaluation_batches.append(0)
    monkeypatch.setattr(recovery, "load_streaming_records", lambda directory: [])
    with pytest.raises(ValueError):
        recovery.reconcile_resume(saved, completed, pending, config, tmp_path)


def test_initial_pending_state_and_metadata_corruption(snapshot):
    saved, config = snapshot
    pending_snapshot(saved, config)
    saved.proposals.proposal_history.pop()
    with pytest.raises(ValueError, match="metadata"):
        state.validate_consistency(saved, config)
    saved.iteration = -1
    saved.results = []
    saved.progress.evaluation_batches = []
    saved.metrics.metric_history = []
    saved.metrics.hypervolumes = []
    with pytest.raises(ValueError, match="initial pending"):
        state.validate_consistency(saved, config)


def test_missing_legacy_simulation_paths_are_reported(snapshot, tmp_path):
    saved, config = snapshot
    saved.config["simulation"]["template_dir"] = None
    root = tmp_path / saved.campaign.run_id
    root.mkdir()
    save_run_checkpoint(root / "checkpoints/checkpoint.pt", saved)
    r = campaigns.MoboCampaignRunner(output_dir=root, resume=True, num_batches=0, export_plots=False)
    try:
        r._prepare_resume()
    except ValueError as error:
        assert "configuration" in str(error)
    assert r.config.simulation.template_dir is not None


def test_budget_limit_stops_extra_iterations(sample_config, tmp_path, monkeypatch):
    r = campaigns.MoboCampaignRunner(
        config=sample_config,
        output_dir=tmp_path,
        num_initial_samples=1,
        num_batches=1,
        batch_size=1,
        total_eval_budget=2,
        evaluator=MockEvaluator(config=sample_config),
        export_plots=False,
    )
    r.num_batches = 2
    assert len(r.run()[0]) == 2


def test_benchmark_rejects_mixed_execution_kinds(publication_runs, tmp_path, monkeypatch):
    config = __import__("mobo_linac.config", fromlist=["load_config"]).load_config("configs/publication_200MeV.yaml")
    benchmark = BenchmarkCampaignRunner(
        config,
        output_dir=tmp_path / "mixed",
        algorithms=["unconstrained_qlognehvi"],
        seeds=[42, 43],
        total_eval_budget=3,
        n_sobol_init=2,
        batch_size=1,
    )
    for seed, kind in [(42, "mock"), (43, "astra")]:
        root = benchmark.get_run_dir("unconstrained_qlognehvi", seed)
        root.mkdir(parents=True)
        for name in ["reporting_metadata.json", "metrics_history.csv"]:
            (root / name).write_bytes((publication_runs[0] / name).read_bytes())
        (root / "benchmark_state.json").write_text(json.dumps({"evaluation_kind": kind}))
    monkeypatch.setattr(benchmark, "_run_status", lambda *a, **k: "completed")
    from mobo_linac.io.run_data import read_run_data

    run = read_run_data(publication_runs[0])
    monkeypatch.setattr("mobo_linac.campaigns.benchmark.read_run_data", lambda root: run)
    with pytest.raises(ValueError, match="evaluation kinds"):
        benchmark.analyze_completed_results()
