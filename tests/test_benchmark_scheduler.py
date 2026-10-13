"""Independent campaign scheduling: real spawned processes, resource caps and audit state."""

from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
import json
import multiprocessing
import os
from pathlib import Path
import time

import pandas as pd
import pytest

from mobo_linac.campaigns.benchmark import BenchmarkCampaignRunner
from mobo_linac.campaigns.scheduler import benchmark_lock
from mobo_linac.config import load_config
from mobo_linac.execution.mock import MockEvaluator
from mobo_linac.result_schema import ResultSchema


class ExplodingEvaluator(MockEvaluator):
    def evaluate(self, requests, run_id="test", on_complete=None):
        raise RuntimeError("Injected campaign failure")


class CrashingEvaluator(MockEvaluator):
    def evaluate(self, requests, run_id="test", on_complete=None):
        os._exit(9)


def _nested_evaluation(request, run_id, root):
    started = time.time()
    time.sleep(0.1)
    raw = MockEvaluator(root, fail_eval_ids=[request.eval_id]).respond(request.parameters, run_id, request.eval_id)
    raw["request"] = request.to_dict()
    path = Path(root) / f"{run_id}_{request.eval_id}.json"
    path.write_text(json.dumps({"pid": os.getpid(), "start": started, "end": time.time()}))
    return raw


class NestedPoolEvaluator:
    """Exercise spawned evaluation pools nested inside spawned campaign controllers."""
    def __init__(self, root):
        self.root = str(root)

    def evaluate(self, requests, run_id="test", on_complete=None):
        with ProcessPoolExecutor(max_workers=2, mp_context=multiprocessing.get_context("spawn")) as pool:
            futures = [pool.submit(_nested_evaluation, request, run_id, self.root) for request in requests]
            results = []
            for future in futures:
                result = future.result()
                results.append(result)
                if on_complete is not None:
                    on_complete(result)
        return results


def _runner(root, **options):
    return BenchmarkCampaignRunner(
        load_config("configs/publication_200MeV.yaml"), output_dir=root,
        algorithms=["unconstrained_qlognehvi", "scalarized_bo"], seeds=[7, 8],
        total_eval_budget=5, n_sobol_init=2, batch_size=2, device="cpu", **options,
    )


@pytest.mark.parametrize("option,value", [("max_concurrent_campaigns", 0), ("total_workers", -1),
                                          ("campaign_threads", True)])
def test_invalid_scheduler_limits_fail_before_outputs(tmp_path, option, value):
    with pytest.raises(ValueError, match="positive integer"):
        _runner(tmp_path / "bad", **{option: value})
    assert not (tmp_path / "bad").exists()


def test_worker_cap_is_partitioned_without_changing_budget(tmp_path):
    runner = _runner(tmp_path, num_workers=8, total_workers=8, max_concurrent_campaigns=3)
    frame = runner.execute_benchmark_campaigns(dry_run=True)
    assert runner.concurrent_campaigns == 3
    assert runner.workers_per_campaign == 2
    assert runner.concurrent_campaigns * runner.workers_per_campaign <= runner.total_workers
    assert frame.budget.tolist() == [5] * 4
    assert frame.final_batch_size.tolist() == [1] * 4


def test_spawned_campaigns_overlap_and_match_sequential_candidates(tmp_path):
    import matplotlib.pyplot as plt
    open_figures = plt.get_fignums()
    sequential = _runner(tmp_path / "sequential", num_workers=2)
    parallel = _runner(tmp_path / "parallel", num_workers=2, total_workers=4, max_concurrent_campaigns=2)
    evaluator = MockEvaluator(fail_eval_ids=range(1, 6), delay_sec=0.2)
    sequential.execute_benchmark_campaigns(mock_evaluator=evaluator)
    manifest = parallel.execute_benchmark_campaigns(mock_evaluator=evaluator)
    assert manifest.status.tolist() == ["completed"] * 4
    schedule = json.loads((parallel.output_dir / "scheduler.json").read_text())
    events = schedule["completions"]
    assert schedule["start_method"] == "spawn"
    assert len({event["pid"] for event in events}) == 2
    assert os.getpid() not in {event["pid"] for event in events}
    assert any(a["started_at"] < b["finished_at"] and b["started_at"] < a["finished_at"]
               for i, a in enumerate(events) for b in events[i + 1:] if a["pid"] != b["pid"])
    timeline = sorted([(event["started_at"], 1) for event in events]
                      + [(event["finished_at"], -1) for event in events])
    active = 0
    for _, delta in timeline:
        active += delta
        assert active <= 2
    columns = list(ResultSchema.from_config(parallel.config).design_columns)
    initial_by_seed = {}
    for algorithm in parallel.algorithms:
        for seed in parallel.seeds:
            run_dir = parallel.get_run_dir(algorithm, seed)
            observed = pd.read_csv(run_dir / "candidate_history.csv")
            expected = pd.read_csv(sequential.get_run_dir(algorithm, seed) / "candidate_history.csv")
            pd.testing.assert_frame_equal(observed[columns], expected[columns])
            assert len(observed) == 5 and observed.simulation_valid.sum() == 0
            initial = observed[columns].iloc[:2].reset_index(drop=True)
            if seed in initial_by_seed:
                pd.testing.assert_frame_equal(initial, initial_by_seed[seed])
            initial_by_seed[seed] = initial
            state = json.loads((run_dir / "benchmark_state.json").read_text())
            assert state["status"] == "completed" and state["evaluation_count"] == 5
    before = (parallel.output_dir / "scheduler.json").read_bytes()
    parallel.execute_benchmark_campaigns(mock_evaluator=evaluator)
    assert (parallel.output_dir / "scheduler.json").read_bytes() == before
    damaged = parallel.get_run_dir(parallel.algorithms[0], 7) / "candidate_history.csv"
    pd.read_csv(damaged).iloc[:1].to_csv(damaged, index=False)
    with pytest.raises(RuntimeError, match="incomplete"):
        parallel.execute_benchmark_campaigns(mock_evaluator=evaluator)
    assert len(pd.read_csv(damaged)) == 1
    assert plt.get_fignums() == open_figures


@pytest.mark.parametrize("evaluator", [ExplodingEvaluator, CrashingEvaluator])
def test_failure_drains_active_campaigns_without_starting_more(tmp_path, evaluator):
    runner = _runner(tmp_path, num_workers=1, total_workers=2, max_concurrent_campaigns=2)
    with pytest.raises(RuntimeError, match="campaign.*failed"):
        runner.execute_benchmark_campaigns(mock_evaluator=evaluator())
    schedule = json.loads((tmp_path / "scheduler.json").read_text())
    assert len(schedule["completions"]) == 2
    assert all(event["status"] == "failed" for event in schedule["completions"])
    expected_error = "Injected campaign failure" if evaluator is ExplodingEvaluator else "BrokenProcessPool"
    assert all(expected_error in event["error"] for event in schedule["completions"])
    assert runner.run_campaign_manifest().status.tolist() == ["incomplete", "pending", "incomplete", "pending"]
    assert not (tmp_path / "aggregate_metrics.csv").exists()


def test_concurrent_valid_gp_campaigns_publish_complete_scientific_artifacts(tmp_path):
    config = load_config("configs/publication_200MeV.yaml")
    config.execution = replace(config.execution, acqf_num_restarts=2, acqf_raw_samples=16, acqf_maxiter=5)
    runner = BenchmarkCampaignRunner(
        config, output_dir=tmp_path, algorithms=["constrained_qlognehvi", "unconstrained_qlognehvi"],
        seeds=[7], n_sobol_init=2, total_eval_budget=3, batch_size=2, num_workers=2,
        total_workers=4, max_concurrent_campaigns=2, device="cpu",
    )
    manifest = runner.execute_benchmark_campaigns(mock_evaluator=MockEvaluator(config=config))
    assert manifest.status.tolist() == ["completed", "completed"]
    initials = []
    columns = list(ResultSchema.from_config(config).design_columns)
    for algorithm in runner.algorithms:
        run_dir = runner.get_run_dir(algorithm, 7)
        history = pd.read_csv(run_dir / "candidate_history.csv")
        assert len(history) == 3 and history.simulation_valid.all() and history.physically_feasible.all()
        initials.append(history[columns].iloc[:2])
        assert list((run_dir / "gp_checkpoint").glob("*.pt"))
        assert (run_dir / "checkpoints" / "checkpoint.pt").exists()
        assert (run_dir / "evaluations_stream.jsonl").exists()
        source = json.loads((run_dir / "config_source.json").read_text())
        assert str(config.source_path) in str(source)
        metadata = json.loads((run_dir / "reporting_metadata.json").read_text())
        assert metadata["reporting_ref_point_normalized"] == [-1.5, -1.5, -1.5]
    pd.testing.assert_frame_equal(*initials)
    assert (tmp_path / "aggregate_metrics.csv").exists()


def test_benchmark_lock_excludes_competing_writers(tmp_path):
    runner = _runner(tmp_path)
    with benchmark_lock(tmp_path):
        for operation in (runner.run_campaign_manifest, runner.analyze_completed_results,
                          runner.execute_benchmark_campaigns):
            with pytest.raises(RuntimeError, match="Another benchmark"):
                operation()
    runner.execute_benchmark_campaigns(dry_run=True)


def test_unserializable_evaluator_fails_before_reserving_runs(tmp_path):
    runner = _runner(tmp_path, total_workers=2, max_concurrent_campaigns=2)
    with pytest.raises(ValueError, match="serializable"):
        runner.execute_benchmark_campaigns(mock_evaluator=lambda: None)
    assert not (tmp_path / "per_seed").exists()


def test_campaign_processes_can_spawn_bounded_evaluation_pools(tmp_path):
    runner = BenchmarkCampaignRunner(
        load_config("configs/publication_200MeV.yaml"), output_dir=tmp_path / "campaigns",
        algorithms=["unconstrained_qlognehvi"], seeds=[7, 8], total_eval_budget=3,
        n_sobol_init=2, batch_size=1, num_workers=2, total_workers=4,
        max_concurrent_campaigns=2, device="cpu",
    )
    manifest = runner.execute_benchmark_campaigns(mock_evaluator=NestedPoolEvaluator(tmp_path))
    assert manifest.status.tolist() == ["completed", "completed"]
    events = [json.loads(path.read_text()) for path in tmp_path.glob("*.json")]
    assert len(events) == 6
    controllers = {event["pid"] for event in json.loads((runner.output_dir / "scheduler.json").read_text())["completions"]}
    assert not controllers.intersection({event["pid"] for event in events})
    active = peak = 0
    for _, delta in sorted([(event["start"], 1) for event in events] + [(event["end"], -1) for event in events]):
        active += delta
        peak = max(peak, active)
    assert peak <= 4


def test_campaign_loop_explicitly_closes_default_evaluator(tmp_path, monkeypatch):
    """Verify CampaignLoop.run closes default ProcessPoolEvaluator in its finally block."""
    from mobo_linac.campaigns.runner import MoboCampaignRunner
    from mobo_linac.execution.parallel import ProcessPoolEvaluator

    closed = []
    original_close = ProcessPoolEvaluator.close

    def tracking_close(self):
        closed.append(self)
        original_close(self)

    monkeypatch.setattr(ProcessPoolEvaluator, "close", tracking_close)

    def mock_evaluate(self, requests, run_id="test", on_complete=None):
        evaluator = MockEvaluator()
        results = []
        for r in requests:
            res = evaluator.respond(r.parameters, run_id, r.eval_id)
            res["request"] = r.to_dict()
            results.append(res)
            if on_complete:
                on_complete(res)
        return results

    monkeypatch.setattr(ProcessPoolEvaluator, "evaluate", mock_evaluate)

    config = load_config("configs/publication_200MeV.yaml")
    runner = MoboCampaignRunner(
        config=config,
        output_dir=tmp_path / "test_closure_run",
        num_initial_samples=2,
        num_batches=1,
        batch_size=1,
        total_eval_budget=3,
        num_workers=1,
        device="cpu",
    )
    runner.run()
    assert len(closed) == 1

