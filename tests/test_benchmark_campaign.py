"""
Unit tests for Statistically Rigorous Benchmark Campaign Orchestration and Analysis (Task 06).
"""

from mobo_linac.result_schema import ResultSchema
from mobo_linac.requests import requests_for
import json
from pathlib import Path
import pytest
import numpy as np
import pandas as pd
import torch

from mobo_linac.config import load_config
from mobo_linac.campaigns.analysis import compute_aggregate_benchmark_metrics, compute_bootstrap_ci
from mobo_linac.campaigns.benchmark import BenchmarkCampaignRunner, generate_seed_paired_sobol_samples


def test_seed_paired_sobol_samples():
    """Verify seed-paired Sobol design generation consistency."""
    bounds = torch.tensor([[0.0] * 6, [1.0] * 6], dtype=torch.double)

    # Same seed -> identical samples
    samples_s42_a = generate_seed_paired_sobol_samples(10, seed=42, bounds=bounds)
    samples_s42_b = generate_seed_paired_sobol_samples(10, seed=42, bounds=bounds)
    assert torch.allclose(samples_s42_a, samples_s42_b)

    # Different seed -> distinct samples
    samples_s43 = generate_seed_paired_sobol_samples(10, seed=43, bounds=bounds)
    assert not torch.allclose(samples_s42_a, samples_s43)


def test_bootstrap_ci_calculation():
    """Verify median and 95% bootstrap confidence interval calculation."""
    # 5 seeds, 10 steps
    np.random.seed(42)
    data = np.random.rand(5, 10) + np.arange(10)

    medians, ci_lower, ci_upper = compute_bootstrap_ci(data, confidence_level=0.95, n_bootstraps=500)

    assert len(medians) == 10
    assert len(ci_lower) == 10
    assert len(ci_upper) == 10
    assert np.all(ci_lower <= medians)
    assert np.all(medians <= ci_upper)


def test_aggregate_benchmark_metrics_computation():
    """Verify aggregation of mock per-seed metrics histories across algorithms."""
    seed_histories = {
        "constrained_qlognehvi": {},
        "sobol": {},
    }

    for seed in [42, 43]:
        df_cq = pd.DataFrame({
            "cumulative_astra_evaluations": [10, 20, 30],
            "fixed_ref_all_valid_hv": [1.0, 2.0, 3.0],
            "fixed_ref_feasible_hv": [0.5, 1.5, 2.5],
            "feasible_fraction": [0.5, 0.6, 0.7],
            "first_feasible_eval_index": [1, 1, 1],
            "pareto_set_size": [2, 4, 6],
            "invalid_run_count": [0, 0, 0],
            "total_wallclock_s": [10.0, 20.0, 30.0],
            "total_simulation_runtime_s": [8.0, 16.0, 24.0],
        })
        seed_histories["constrained_qlognehvi"][seed] = df_cq

        df_sob = pd.DataFrame({
            "cumulative_astra_evaluations": [10, 20, 30],
            "fixed_ref_all_valid_hv": [0.5, 1.0, 1.5],
            "fixed_ref_feasible_hv": [0.2, 0.5, 1.0],
            "feasible_fraction": [0.2, 0.3, 0.4],
            "first_feasible_eval_index": [5, 5, 5],
            "pareto_set_size": [1, 2, 3],
            "invalid_run_count": [0, 0, 0],
            "total_wallclock_s": [5.0, 10.0, 15.0],
            "total_simulation_runtime_s": [4.0, 8.0, 12.0],
        })
        seed_histories["sobol"][seed] = df_sob

    from mobo_linac.metrics.reporting import reporting_metadata
    convention = reporting_metadata(load_config("configs/mobo_200MeV.yaml"), [-1.5e-6, -1.5e-6, -1.5e6])
    for histories in seed_histories.values():
        for frame in histories.values():
            frame.attrs["reporting_metadata"] = convention
    agg_df, summary_df = compute_aggregate_benchmark_metrics(seed_histories, n_bootstraps=200)

    assert len(agg_df) == 6  # 2 algorithms * 3 steps
    assert len(summary_df) == 2
    assert "algorithm" in summary_df.columns
    assert "final_median_feasible_hv" in summary_df.columns


def test_benchmark_campaign_manifest_generation(tmp_path):
    """Verify benchmark campaign manifest generation."""
    config = load_config("configs/publication_200MeV.yaml")
    runner = BenchmarkCampaignRunner(
        config=config,
        output_dir=tmp_path / "benchmark",
        algorithms=["constrained_qlognehvi", "unconstrained_qlognehvi"],
        seeds=[42, 43],
        total_eval_budget=20,
    )

    manifest_df = runner.run_campaign_manifest()
    assert (tmp_path / "benchmark" / "campaign_manifest.csv").exists()
    assert len(manifest_df) == 4  # 2 algos * 2 seeds


@pytest.mark.parametrize("algorithm,mode,acquisition,constrained", [
    ("constrained_qlognehvi", "constrained_mobo", "qLogNEHVI", True),
    ("unconstrained_qlognehvi", "unconstrained_mobo", "qLogNEHVI", False),
    ("qlogehvi", "unconstrained_mobo", "qLogEHVI", False),
    ("scalarized_bo", "scalarized_bo", "qLogNEI", False),
])
def test_explicit_algorithm_dispatch(tmp_path, monkeypatch, algorithm, mode, acquisition, constrained):
    from mobo_linac.execution import MockEvaluator
    from mobo_linac.evaluation import create_evaluation_result
    from mobo_linac.metrics.exports import save_evaluation_results
    import mobo_linac.campaigns.runner as campaign_module
    import mobo_linac.campaigns.strategies as strategies_module
    import mobo_linac.campaigns.benchmark as benchmark_module

    captured = {}

    class RecordingRunner:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        def run(self):
            candidates = generate_seed_paired_sobol_samples(
                captured["total_eval_budget"], captured["seed"],
                captured["config"].get_parameter_bounds_tensor(),
            )
            raw = MockEvaluator(tmp_path).evaluate(requests_for(candidates.tolist()))
            results = [create_evaluation_result(r, captured["config"]) for r in raw]
            # A complete test double publishes the same artifact contract as the real runner.
            from mobo_linac.metrics.exports import RunArtifactWriter
            from mobo_linac.metrics.hypervolume import HypervolumeTracker
            from mobo_linac.io.results import get_train_tensors
            config, run_dir = captured["config"], Path(captured["output_dir"])
            tracker = HypervolumeTracker(captured["reporting_ref_point"], config)
            _, y, feasible = get_train_tensors(results, config=config)
            tracker.track_iteration(0, y, feasible)
            writer = RunArtifactWriter(run_dir, config)
            writer.write(results, tracker, reference_policy="explicit")
            config.save_json(run_dir / "config.json")
            config.save_yaml(run_dir / "config.yaml")
            writer.complete(len(results), None, ["config.json", "config.yaml"])
            return results, None, captured["output_dir"]

    monkeypatch.setattr("mobo_linac.campaigns.runner.MoboCampaignRunner", RecordingRunner)
    monkeypatch.setattr(BenchmarkCampaignRunner, "analyze_completed_results", lambda self: None)
    runner = BenchmarkCampaignRunner(
        config=load_config("configs/publication_200MeV.yaml"), output_dir=tmp_path,
        algorithms=[algorithm], seeds=[42], n_sobol_init=2, total_eval_budget=5,
        batch_size=2, num_workers=3, device="cpu",
    )
    manifest = runner.execute_benchmark_campaigns()
    assert captured["optimization_mode"] == mode
    assert captured["acq_type"] == acquisition
    assert captured["constrained"] is constrained
    assert captured["num_workers"] == 3
    assert captured["total_eval_budget"] == 5
    assert captured["num_initial_samples"] == 2
    assert captured["num_batches"] == 2
    metadata = json.loads((runner.get_run_dir(algorithm, 42) / "reporting_metadata.json").read_text())
    assert metadata["objective_scales"] == [1e-6, 1e-6, 1e6]
    assert metadata["reporting_ref_point_normalized"] == [-1.5, -1.5, -1.5]
    assert manifest.iloc[0]["status"] == "completed"
    assert manifest.iloc[0]["requested_budget"] == manifest.iloc[0]["effective_budget"] == 5
    assert manifest.iloc[0]["final_batch_size"] == 1
    captured.clear()
    runner.execute_benchmark_campaigns()
    assert not captured, "A verified completed run should be skipped"


@pytest.mark.parametrize("algorithm", ["nsga2", "sobol", "unknown"])
def test_unavailable_algorithms_fail_before_creating_outputs(tmp_path, algorithm):
    destination = tmp_path / "benchmark"
    with pytest.raises(ValueError, match="no implemented executor|Unsupported algorithm"):
        BenchmarkCampaignRunner(
            config=load_config("configs/publication_200MeV.yaml"),
            output_dir=destination, algorithms=[algorithm], seeds=[42],
        )
    assert not destination.exists()


@pytest.mark.parametrize("algorithms,seeds,initial,batch", [
    ([], [42], 2, 2),
    (["scalarized_bo", "scalarized_bo"], [42], 2, 2),
    (["scalarized_bo"], [], 2, 2),
    (["scalarized_bo"], [42, 42], 2, 2),
    (["scalarized_bo"], [42], 0, 2),
    (["scalarized_bo"], [42], 2, 0),
])
def test_invalid_benchmark_settings(tmp_path, algorithms, seeds, initial, batch):
    with pytest.raises(ValueError):
        BenchmarkCampaignRunner(
            config=load_config("configs/publication_200MeV.yaml"), output_dir=tmp_path / "bad",
            algorithms=algorithms, seeds=seeds, n_sobol_init=initial, batch_size=batch,
        )
    assert not (tmp_path / "bad").exists()


def test_mock_campaign_exact_budget_pairing_and_completion(tmp_path, monkeypatch):
    import json
    from mobo_linac.execution import MockEvaluator
    from mobo_linac.benchmark_algorithms import SUPPORTED_BENCHMARK_ALGORITHMS
    from mobo_linac.campaigns.runner import MoboCampaignRunner

    # Failed evaluations still count toward the exact budget and bypass expensive GP fitting.
    class RecordingEvaluator(MockEvaluator):
        def __init__(self):
            super().__init__(tmp_path, fail_eval_ids=[f"eval_{i:06d}" for i in range(1, 7)])
            self.batches = []

        def evaluate(self, requests, run_id, on_complete=None):
            self.batches.append((run_id, [r.parameters for r in requests]))
            return super().evaluate(requests, run_id, on_complete)

    evaluator = RecordingEvaluator()
    original_init = MoboCampaignRunner.__init__

    def no_plot_init(self, **kwargs):
        original_init(self, **{**kwargs, "export_plots": False, "export_env_info": False})

    monkeypatch.setattr(MoboCampaignRunner, "__init__", no_plot_init)
    runner = BenchmarkCampaignRunner(
        config=load_config("configs/publication_200MeV.yaml"), output_dir=tmp_path,
        algorithms=SUPPORTED_BENCHMARK_ALGORITHMS, seeds=[42],
        n_sobol_init=2, total_eval_budget=5, batch_size=2, device="cpu",
    )
    manifest = runner.execute_benchmark_campaigns(mock_evaluator=evaluator)
    assert manifest["status"].tolist() == ["completed"] * 4
    assert [len(candidates) for _, candidates in evaluator.batches] == [2, 2, 1] * 4
    initial_designs = [torch.tensor(evaluator.batches[i][1]) for i in range(0, 12, 3)]
    assert all(torch.equal(initial_designs[0], design) for design in initial_designs)
    for algorithm in SUPPORTED_BENCHMARK_ALGORITHMS:
        run_dir = runner.get_run_dir(algorithm, 42)
        metrics = pd.read_csv(run_dir / "metrics_history.csv")
        assert len(metrics) == 5
        assert metrics.iloc[-1]["cumulative_astra_evaluations"] == 5
        assert metrics.iloc[-1]["invalid_run_count"] == 5
        state = json.loads((run_dir / "benchmark_state.json").read_text())
        assert state["status"] == "completed"
        assert state["evaluation_count"] == 5
    assert (tmp_path / "aggregate_metrics.csv").exists()
    assert (tmp_path / "figures" / "benchmark_hv_comparison.pdf").exists()

    # A truncated persisted history invalidates completion and must never be silently skipped.
    damaged_dir = runner.get_run_dir("scalarized_bo", 42)
    history_path = damaged_dir / "candidate_history.csv"
    pd.read_csv(history_path).iloc[:2].to_csv(history_path, index=False)
    assert runner._run_status("scalarized_bo", 42) == "incomplete"
    with pytest.raises(RuntimeError, match="is incomplete"):
        runner.execute_benchmark_campaigns(mock_evaluator=evaluator)
    assert len(pd.read_csv(history_path)) == 2


def test_interrupted_history_is_not_completed_or_overwritten(tmp_path):
    runner = BenchmarkCampaignRunner(
        config=load_config("configs/publication_200MeV.yaml"), output_dir=tmp_path,
        algorithms=["unconstrained_qlognehvi"], seeds=[42],
        n_sobol_init=2, total_eval_budget=5, batch_size=2,
    )
    run_dir = runner.get_run_dir("unconstrained_qlognehvi", 42)
    run_dir.mkdir(parents=True)
    history = run_dir / "candidate_history.csv"
    history.write_text("evaluation_id\neval_000001\n")
    assert runner.run_campaign_manifest().iloc[0]["status"] == "incomplete"
    with pytest.raises(RuntimeError, match="is incomplete"):
        runner.execute_benchmark_campaigns()
    assert history.read_text() == "evaluation_id\neval_000001\n"


def test_reporting_settings_in_state_and_metrics(tmp_path, monkeypatch):
    from mobo_linac.config import BenchmarkConfig
    from mobo_linac.execution import MockEvaluator
    from mobo_linac.campaigns.runner import MoboCampaignRunner
    import json

    original_run = MoboCampaignRunner.run

    def fast_run(self):
        self.export_plots = False
        return original_run(self)

    monkeypatch.setattr(MoboCampaignRunner, "run", fast_run)
    runner = BenchmarkCampaignRunner(
        config=load_config("configs/publication_200MeV.yaml"),
        benchmark_config=BenchmarkConfig(
            output_dir=str(tmp_path), algorithms=["unconstrained_qlognehvi"], seeds=[42],
            n_sobol_init=1, total_eval_budget=2, batch_size=4,
            reporting_ref_point=[2.0, 3.0, 4.0],
        ), device="cpu",
    )
    runner.execute_benchmark_campaigns(mock_evaluator=MockEvaluator(tmp_path))
    run_dir = runner.get_run_dir("unconstrained_qlognehvi", 42)
    state = json.loads((run_dir / "benchmark_state.json").read_text())
    assert state["reporting_ref_point_physical_norm"] == [2.0, 3.0, 4.0]
    metrics = pd.read_csv(run_dir / "metrics_history.csv")
    assert metrics.iloc[-1]["fixed_ref_feasible_hv"] > 0
    runner.benchmark_config.reporting_ref_point = [1.0, 1.0, 1.0]
    assert runner._run_status("unconstrained_qlognehvi", 42) == "incompatible"
    with pytest.raises(RuntimeError, match="is incompatible"):
        runner.execute_benchmark_campaigns()


@pytest.mark.parametrize("algorithm", [
    "constrained_qlognehvi", "unconstrained_qlognehvi", "qlogehvi", "scalarized_bo",
])
def test_partial_final_batch_reaches_acquisition_proposal(tmp_path, monkeypatch, algorithm):
    from mobo_linac.execution import MockEvaluator
    import mobo_linac.campaigns.runner as campaign_module
    import mobo_linac.campaigns.strategies as strategies_module

    class StubPipeline:
        @classmethod
        def from_config(cls, config, bounds, device=None):
            return cls(bounds=bounds, device=device)

        objective_model = None
        constraint_model = None

        def __init__(self, **kwargs):
            pass

        def fit(self, *args):
            return self

        def save_artifact(self, path, **kwargs):
            path.parent.mkdir(parents=True, exist_ok=True)
            torch.save({"test_stub": True}, path)

    proposed_sizes = []

    def propose(**kwargs):
        size = kwargs["batch_size"]
        proposed_sizes.append(size)
        bounds = kwargs["bounds"]
        from mobo_linac.acquisition.mobo import ProposalResult
        return ProposalResult(bounds.mean(dim=0).repeat(size, 1), torch.zeros(size), None)

    monkeypatch.setattr(strategies_module, "SurrogatePipeline", StubPipeline)
    monkeypatch.setattr(strategies_module, "build_output_gp", lambda *args, **kwargs: None)
    monkeypatch.setattr(strategies_module, "fit_gp_models", lambda model: model)
    monkeypatch.setattr(campaign_module, "save_model_artifact", lambda model, path, **kwargs: StubPipeline().save_artifact(path))
    monkeypatch.setattr(strategies_module, "qLogNoisyExpectedImprovement", lambda **kwargs: None)
    monkeypatch.setattr(strategies_module, "build_acquisition_function", lambda **kwargs: None)
    monkeypatch.setattr(strategies_module, "generate_next_candidates", propose)
    original_init = campaign_module.MoboCampaignRunner.__init__

    def no_plot_init(self, **kwargs):
        original_init(self, **{**kwargs, "export_plots": False})

    monkeypatch.setattr(campaign_module.MoboCampaignRunner, "__init__", no_plot_init)
    monkeypatch.setattr(BenchmarkCampaignRunner, "analyze_completed_results", lambda self: None)
    runner = BenchmarkCampaignRunner(
        config=load_config("configs/publication_200MeV.yaml"), output_dir=tmp_path,
        algorithms=[algorithm], seeds=[42], n_sobol_init=2,
        total_eval_budget=5, batch_size=2, device="cpu",
    )
    manifest = runner.execute_benchmark_campaigns(mock_evaluator=MockEvaluator(tmp_path))
    assert proposed_sizes == [2, 1]
    assert manifest.iloc[0]["status"] == "completed"


def test_analysis_uses_persisted_manifest_for_custom_settings(tmp_path, monkeypatch):
    from mobo_linac.execution import MockEvaluator
    from mobo_linac.campaigns.runner import MoboCampaignRunner

    original_run = MoboCampaignRunner.run

    def no_plots(self):
        self.export_plots = False
        return original_run(self)

    monkeypatch.setattr(MoboCampaignRunner, "run", no_plots)
    config = load_config("configs/publication_200MeV.yaml")
    runner = BenchmarkCampaignRunner(
        config=config, output_dir=tmp_path, algorithms=["scalarized_bo"], seeds=[7],
        n_sobol_init=1, total_eval_budget=2, batch_size=4, device="cpu",
    )
    runner.execute_benchmark_campaigns(mock_evaluator=MockEvaluator(tmp_path))
    analysis_runner = BenchmarkCampaignRunner(config=config, output_dir=tmp_path)
    aggregate, summary = analysis_runner.analyze_completed_results()
    assert aggregate["algorithm"].unique().tolist() == ["scalarized_bo"]
    assert len(aggregate) == 2
    assert len(summary) == 1
    with pytest.raises(RuntimeError, match="is incompatible"):
        runner.execute_benchmark_campaigns()  # Production must not reuse a mock run.


def test_mock_interruption_leaves_incomplete_state(tmp_path):
    import json
    from mobo_linac.execution import MockEvaluator

    class InterruptingEvaluator(MockEvaluator):
        def evaluate(self, requests, run_id, on_complete=None):
            raise RuntimeError("Injected interruption")

    runner = BenchmarkCampaignRunner(
        config=load_config("configs/publication_200MeV.yaml"), output_dir=tmp_path,
        algorithms=["unconstrained_qlognehvi"], seeds=[42],
        n_sobol_init=1, total_eval_budget=2, batch_size=2, device="cpu",
    )
    with pytest.raises(RuntimeError, match="Injected interruption"):
        runner.execute_benchmark_campaigns(mock_evaluator=InterruptingEvaluator(tmp_path))
    run_dir = runner.get_run_dir("unconstrained_qlognehvi", 42)
    state = json.loads((run_dir / "benchmark_state.json").read_text())
    assert state["status"] == "running"
    assert runner.run_campaign_manifest().iloc[0]["status"] == "incomplete"
    with pytest.raises(RuntimeError, match="is incomplete"):
        runner.execute_benchmark_campaigns(mock_evaluator=MockEvaluator(tmp_path))
    assert not (run_dir / "candidate_history.csv").exists()


def test_missing_persisted_history_cannot_complete(tmp_path, monkeypatch):
    from mobo_linac.execution import MockEvaluator
    from mobo_linac.evaluation import create_evaluation_result
    import mobo_linac.campaigns.runner as campaign_module
    import mobo_linac.campaigns.strategies as strategies_module

    class MissingArtifactRunner:
        def __init__(self, **kwargs):
            self.config = kwargs["config"]

        def run(self):
            raw = MockEvaluator(tmp_path).evaluate(requests_for([[0.0] * 6] * 2))
            return [create_evaluation_result(r, self.config) for r in raw], None, None

    monkeypatch.setattr("mobo_linac.campaigns.runner.MoboCampaignRunner", MissingArtifactRunner)
    runner = BenchmarkCampaignRunner(
        config=load_config("configs/publication_200MeV.yaml"), output_dir=tmp_path,
        algorithms=["unconstrained_qlognehvi"], seeds=[42],
        n_sobol_init=1, total_eval_budget=2, batch_size=2,
    )
    with pytest.raises(RuntimeError, match="incomplete persisted"):
        runner.execute_benchmark_campaigns()
    assert runner.run_campaign_manifest().iloc[0]["status"] == "incomplete"


def test_aggregate_metrics_require_reporting_evidence():
    with pytest.raises(ValueError, match="explicit convention"):
        compute_aggregate_benchmark_metrics({"algorithm": {42: pd.DataFrame()}})


def _history(steps, convention, extrema=None):
    frame = pd.DataFrame({
        "cumulative_astra_evaluations": steps, "fixed_ref_all_valid_hv": [1.0] * len(steps),
        "fixed_ref_feasible_hv": [0.5] * len(steps), "feasible_fraction": [0.5] * len(steps),
        "first_feasible_eval_index": [np.nan] + [2] * (len(steps) - 1), "pareto_set_size": [1] * len(steps),
        "invalid_run_count": [0] * len(steps), "total_wallclock_s": [1.0] * len(steps),
        "total_simulation_runtime_s": [1.0] * len(steps)})
    frame.attrs["reporting_metadata"] = convention
    if extrema is not None:
        frame.attrs["objective_extrema"] = extrema
    return frame


def test_aggregation_rejects_unequal_histories_and_reports_feasible_extrema():
    from mobo_linac.metrics.reporting import reporting_metadata
    convention = reporting_metadata(load_config("configs/mobo_200MeV.yaml"), [-1.5e-6, -1.5e-6, -1.5e6])
    with pytest.raises(ValueError, match="unequal evaluation steps"):
        compute_aggregate_benchmark_metrics({"a": {1: _history([1, 2, 3], convention), 2: _history([1, 2], convention)}})
    extrema = [{"norm_emit_x_m_rad": 2e-6, "norm_emit_y_m_rad": 1e-6, "sigma_energy_eV": 3e5},
               {"norm_emit_x_m_rad": 1e-6, "norm_emit_y_m_rad": None, "sigma_energy_eV": 4e5}]
    _, summary = compute_aggregate_benchmark_metrics(
        {"a": {seed: _history([1, 2, 3], convention, value) for seed, value in enumerate(extrema)}}, n_bootstraps=20)
    row = summary.iloc[0]
    assert row["min_norm_emit_x_m_rad"] == 1e-6 and row["min_norm_emit_y_m_rad"] == 1e-6
    assert row["min_sigma_energy_eV"] == 3e5
    assert row["median_evals_to_first_feasible"] == 2.0


def test_vectorized_bootstrap_matches_reference_loop():
    data = np.random.default_rng(0).random((6, 5))
    medians, lower, upper = compute_bootstrap_ci(data, n_bootstraps=300, seed=9)
    rng = np.random.default_rng(9)
    boot = np.array([np.median(data[rng.choice(6, size=6, replace=True)], axis=0) for _ in range(300)])
    np.testing.assert_array_equal(lower, np.percentile(boot, 2.5, axis=0))
    np.testing.assert_array_equal(upper, np.percentile(boot, 97.5, axis=0))


def test_benchmark_summary_reads_extrema_from_candidate_history(tmp_path, monkeypatch):
    from mobo_linac.execution import MockEvaluator
    from mobo_linac.campaigns.runner import MoboCampaignRunner
    original_run = MoboCampaignRunner.run

    def no_plots(self):
        self.export_plots = False
        return original_run(self)

    monkeypatch.setattr(MoboCampaignRunner, "run", no_plots)
    config = load_config("configs/publication_200MeV.yaml")
    runner = BenchmarkCampaignRunner(config=config, output_dir=tmp_path, algorithms=["scalarized_bo"], seeds=[7],
                                     n_sobol_init=2, total_eval_budget=3, batch_size=4, device="cpu")
    runner.execute_benchmark_campaigns(mock_evaluator=MockEvaluator(tmp_path, config=config))
    _, summary = BenchmarkCampaignRunner.from_output_dir(tmp_path).analyze_completed_results()
    assert np.isfinite(summary.iloc[0][["min_norm_emit_x_m_rad", "min_norm_emit_y_m_rad", "min_sigma_energy_eV"]].astype(float)).all()
