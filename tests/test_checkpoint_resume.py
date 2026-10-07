"""
Unit tests for Checkpoint Writing, Resuming, and Deterministic Continuation (Task 04).
"""

import pytest
import torch
import numpy as np
from pathlib import Path

from mobo_linac.config import load_config
from mobo_linac.campaigns.runner import MoboCampaignRunner
from mobo_linac.execution import MockBatchEvaluator
from mobo_linac.io.results import load_run_checkpoint, get_train_tensors


@pytest.fixture(autouse=True)
def fast_resume_proposals(monkeypatch):
    """Exercise real checkpoint/proposal flow without repeated expensive GP fitting."""
    import random
    import mobo_linac.campaigns.runner as runner_module
    import mobo_linac.acquisition.mobo as acquisition_module

    class StubPipeline:
        objective_model = None
        constraint_model = None

        def __init__(self, **kwargs):
            # Model construction consumes the same device RNGs a real fit may use.
            torch.rand((), device=kwargs["device"])

        def fit(self, *args):
            return self

    class StubAcquisition(torch.nn.Module):
        pass

    monkeypatch.setattr(runner_module, "SurrogatePipeline", StubPipeline)
    monkeypatch.setattr(runner_module, "build_scalarized_gp_model", lambda **kwargs: torch.nn.Linear(1, 1))
    monkeypatch.setattr(runner_module, "fit_gp_models", lambda model: model)
    monkeypatch.setattr(runner_module, "build_acquisition_function", lambda **kwargs: StubAcquisition())
    monkeypatch.setattr(runner_module, "qLogNoisyExpectedImprovement", lambda **kwargs: StubAcquisition())

    def optimize(**kwargs):
        bounds = kwargs["bounds"]
        samples = torch.rand(kwargs["q"], bounds.shape[1], dtype=torch.double, device=bounds.device)
        samples = (samples + np.random.random() + random.random()) / 3.0
        candidates = bounds[0] + (bounds[1] - bounds[0]) * samples
        return candidates, torch.zeros(1, dtype=torch.double, device=bounds.device)

    monkeypatch.setattr(acquisition_module, "optimize_acqf", optimize)
    return optimize


def test_uninterrupted_vs_resumed_campaign(tmp_path):
    """Verify that a resumed campaign produces identical results to an uninterrupted campaign."""
    config = load_config("configs/publication_200MeV.yaml")

    # 1. Uninterrupted run (8 initial + 3 batches of 2 = 14 evals)
    dir_uninterrupted = tmp_path / "uninterrupted"
    mock_eval_1 = MockBatchEvaluator(dir_uninterrupted)
    runner_full = MoboCampaignRunner(
        config=config,
        output_dir=dir_uninterrupted,
        num_initial_samples=8,
        num_batches=3,
        batch_size=2,
        seed=123,
        evaluator=mock_eval_1,
    )
    res_full, tracker_full, _ = runner_full.run()
    assert len(res_full) == 14

    # 2. Partial run (8 initial + 1 batch of 2 = 10 evals)
    dir_resumed = tmp_path / "resumed"
    mock_eval_2 = MockBatchEvaluator(dir_resumed)
    runner_part1 = MoboCampaignRunner(
        config=config,
        output_dir=dir_resumed,
        num_initial_samples=8,
        num_batches=1,
        batch_size=2,
        seed=123,
        evaluator=mock_eval_2,
    )
    res_part1, _, _ = runner_part1.run()
    assert len(res_part1) == 10

    # 3. Resume partial run up to 3 batches (batches 2 and 3)
    runner_part2 = MoboCampaignRunner(
        config=config,
        output_dir=dir_resumed,
        num_initial_samples=8,
        num_batches=3,
        batch_size=2,
        seed=123,
        resume=True,
        evaluator=mock_eval_2,
    )
    res_resumed, tracker_resumed, _ = runner_part2.run()
    assert len(res_resumed) == 14

    # Verify candidate parameter agreement
    X_full, Y_full, _ = get_train_tensors(res_full)
    X_res, Y_res, _ = get_train_tensors(res_resumed)

    assert torch.allclose(X_full, X_res, atol=1e-8)
    assert torch.allclose(Y_full, Y_res, atol=1e-8)

    # Verify hypervolume history agreement
    hv_full = tracker_full.to_dataframe()["feasible_hypervolume"].tolist()
    hv_res = tracker_resumed.to_dataframe()["feasible_hypervolume"].tolist()
    assert len(hv_full) == len(hv_res)
    assert np.allclose(hv_full, hv_res, atol=1e-8)


def test_missing_checkpoint_raises(tmp_path):
    """Verify FileNotFoundError when attempting to resume without a checkpoint."""
    nonexistent = tmp_path / "nonexistent"
    runner = MoboCampaignRunner(output_dir=nonexistent, resume=True)
    with pytest.raises(FileNotFoundError):
        runner.run()


def test_corrupted_checkpoint_raises(tmp_path):
    """Verify ValueError when attempting to load a corrupted checkpoint file."""
    ckpt_dir = tmp_path / "checkpoints"
    ckpt_dir.mkdir(parents=True)
    bad_file = ckpt_dir / "checkpoint.pt"
    bad_file.write_text("CORRUPTED_CHECKPOINT_DATA", encoding="utf-8")

    with pytest.raises(ValueError):
        load_run_checkpoint(tmp_path)


def test_intra_batch_streaming_persistence_and_resume(tmp_path):
    """Verify that evaluations_stream.csv/jsonl records individual worker completions in real time."""
    from mobo_linac.io.results import (
        append_streaming_evaluation,
        load_streaming_evaluations,
    )
    from mobo_linac.evaluation import EvaluationResult

    # 1. Direct streaming API tests
    test_dir = tmp_path / "stream_test"
    res1 = EvaluationResult(
        evaluation_id="eval_000001",
        run_id="test_stream",
        x_physical=[0.2, 1.0, -1.0, -10.0, -5.0, 0.0],
        objectives_physical=[3.5e-6, 3.6e-6, 0.9e6],
        objectives_model=[-3.5e-6, -3.6e-6, -0.9e6],
        diagnostics={"sigma_x_m": 0.5e-3, "mean_kinetic_energy_eV": 200.0e6, "transmission_fraction": 1.0},
        simulation_valid=True,
        physically_feasible=True,
    )
    res2 = EvaluationResult(
        evaluation_id="eval_000002",
        run_id="test_stream",
        x_physical=[0.25, 0.9, -0.9, -8.0, -4.0, 1.0],
        objectives_physical=[3.8e-6, 3.9e-6, 1.1e6],
        objectives_model=[-3.8e-6, -3.9e-6, -1.1e6],
        diagnostics={"sigma_x_m": 0.6e-3, "mean_kinetic_energy_eV": 201.0e6, "transmission_fraction": 0.95},
        simulation_valid=True,
        physically_feasible=True,
    )

    csv_path = append_streaming_evaluation(test_dir, res1, batch_idx=0)
    assert csv_path.exists()
    append_streaming_evaluation(test_dir, res2, batch_idx=0)

    loaded = load_streaming_evaluations(test_dir)
    assert len(loaded) == 2
    assert loaded[0].evaluation_id == "eval_000001"
    assert loaded[1].evaluation_id == "eval_000002"
    assert loaded[0].physically_feasible is True

    # 2. Campaign runner streaming verification
    camp_dir = tmp_path / "camp_stream"
    mock_eval = MockBatchEvaluator(camp_dir)
    config = load_config("configs/publication_200MeV.yaml")
    runner = MoboCampaignRunner(
        config=config,
        output_dir=camp_dir,
        num_initial_samples=4,
        num_batches=2,
        batch_size=2,
        seed=42,
        evaluator=mock_eval,
    )
    runner.run()

    streamed_camp = load_streaming_evaluations(camp_dir)
    assert len(streamed_camp) == 8  # 4 initial + 2*2 batches
    assert (camp_dir / "evaluations_stream.csv").exists()
    assert (camp_dir / "evaluations_stream.jsonl").exists()



@pytest.mark.parametrize("mode", ["unconstrained_mobo", "constrained_mobo", "scalarized_bo"])
def test_complete_state_resume_preserves_failures_and_metrics(tmp_path, mode):
    config = load_config("configs/publication_200MeV.yaml")
    weights = [0.6, 0.3, 0.1]
    failed = ["eval_000002", "eval_000005"]
    options = dict(config=config, num_initial_samples=3, batch_size=2, seed=17,
                   optimization_mode=mode, scalar_weights=weights,
                   export_plots=False, export_env_info=False, device="cpu", num_workers=3)
    full_dir = tmp_path / "full"
    full, full_tracker, _ = MoboCampaignRunner(
        **options, output_dir=full_dir, num_batches=3,
        evaluator=MockBatchEvaluator(full_dir, fail_eval_ids=failed),
    ).run()
    split_dir = tmp_path / "split"
    MoboCampaignRunner(
        **options, output_dir=split_dir, num_batches=1,
        evaluator=MockBatchEvaluator(split_dir, fail_eval_ids=failed),
    ).run()
    checkpoint = load_run_checkpoint(split_dir)
    assert checkpoint.version == "2.0"
    assert isinstance(checkpoint.config, dict)
    assert checkpoint.num_initial_samples == 3
    assert checkpoint.initial_design == [r.x_physical for r in checkpoint.results[:3]]
    assert checkpoint.evaluation_batches == [0, 0, 0, 1, 1]
    assert checkpoint.sobol_state["num_generated"] == 3  # Successful BO proposals did not consume Sobol.
    assert checkpoint.num_workers == 3
    resumed_runner = MoboCampaignRunner(
        output_dir=split_dir, resume=True, num_batches=3, device="cpu",
        export_plots=False, export_env_info=False,
        evaluator=MockBatchEvaluator(split_dir, fail_eval_ids=failed),
    )
    resumed, resumed_tracker, _ = resumed_runner.run()
    assert resumed_runner.optimization_mode == mode
    assert resumed_runner.num_initial_samples == 3
    assert resumed_runner.num_workers == 3
    assert resumed_runner.scalar_weights.tolist() == pytest.approx(weights)
    assert [r.x_physical for r in full] == [r.x_physical for r in resumed]
    assert [r.simulation_valid for r in full] == [r.simulation_valid for r in resumed]
    assert full_tracker.history == resumed_tracker.history
    assert resumed_tracker.history[0]["num_valid_points"] == 2
    assert resumed_tracker.history[1]["num_valid_points"] == 3
    assert load_run_checkpoint(split_dir).evaluation_batches == [0, 0, 0, 1, 1, 2, 2, 3, 3]


def test_real_acquisition_fallback_restores_sobol_position(tmp_path, monkeypatch):
    import mobo_linac.acquisition.mobo as acquisition_module

    def fail_optimizer(**kwargs):
        # Retries consume global RNG state; the final fallback consumes the campaign Sobol stream.
        torch.rand(3)
        np.random.random()
        raise RuntimeError("Forced optimizer fallback")

    monkeypatch.setattr(acquisition_module, "optimize_acqf", fail_optimizer)
    full_dir = tmp_path / "full"
    split_dir = tmp_path / "split"
    options = dict(num_initial_samples=3, batch_size=2, seed=31, device="cpu",
                   export_plots=False, export_env_info=False)
    full, full_tracker, _ = MoboCampaignRunner(
        **options, output_dir=full_dir, num_batches=3, evaluator=MockBatchEvaluator(full_dir),
    ).run()
    MoboCampaignRunner(
        **options, output_dir=split_dir, num_batches=1, evaluator=MockBatchEvaluator(split_dir),
    ).run()
    checkpoint = load_run_checkpoint(split_dir)
    assert checkpoint.sobol_state["num_generated"] == 5
    resumed, tracker, _ = MoboCampaignRunner(
        output_dir=split_dir, resume=True, num_batches=3, evaluator=MockBatchEvaluator(split_dir),
        device="cpu", export_plots=False, export_env_info=False,
    ).run()
    assert [r.x_physical for r in full] == [r.x_physical for r in resumed]
    assert full_tracker.history == tracker.history
    assert load_run_checkpoint(split_dir).sobol_state["num_generated"] == 9


def test_low_data_sobol_resume_with_invalid_initial_evaluations(tmp_path):
    options = dict(num_initial_samples=3, batch_size=2, seed=11, device="cpu",
                   export_plots=False, export_env_info=False)
    failed = [f"eval_{i:06d}" for i in range(1, 10)]
    full_dir, split_dir = tmp_path / "full", tmp_path / "split"
    full, full_tracker, _ = MoboCampaignRunner(
        **options, output_dir=full_dir, num_batches=3,
        evaluator=MockBatchEvaluator(full_dir, fail_eval_ids=failed),
    ).run()
    MoboCampaignRunner(
        **options, output_dir=split_dir, num_batches=1,
        evaluator=MockBatchEvaluator(split_dir, fail_eval_ids=failed),
    ).run()
    resumed, tracker, _ = MoboCampaignRunner(
        output_dir=split_dir, resume=True, num_batches=3, device="cpu",
        export_plots=False, export_env_info=False,
        evaluator=MockBatchEvaluator(split_dir, fail_eval_ids=failed),
    ).run()
    assert [r.x_physical for r in full] == [r.x_physical for r in resumed]
    assert full_tracker.history == tracker.history


@pytest.mark.parametrize("change", ["order", "bounds", "mapping", "objective", "sign", "constraint", "model", "exit_plane", "proposal_budget"])
def test_same_dimension_incompatible_config_rejected_before_writes(tmp_path, change):
    from copy import deepcopy
    import hashlib

    config = load_config("configs/publication_200MeV.yaml")
    MoboCampaignRunner(
        config=config, output_dir=tmp_path, num_initial_samples=3, num_batches=1,
        batch_size=2, device="cpu", export_plots=False, evaluator=MockBatchEvaluator(tmp_path),
    ).run()
    changed = deepcopy(config)
    if change == "order":
        changed.design_variables[0], changed.design_variables[1] = changed.design_variables[1], changed.design_variables[0]
    elif change == "bounds":
        changed.design_variables[0].lower_bound *= 0.99
    elif change == "mapping":
        changed.design_variables[0].astra_key = "solenoid:maxb(2)"
    elif change == "objective":
        changed.objectives[0].name = "alternative_emittance"
    elif change == "sign":
        changed.objectives[0].model_sign = 1
        changed.objectives[0].physical_direction = "maximize"
    elif change == "constraint":
        changed.constraints.min_transmission = 0.95
    elif change == "model":
        changed.model.covar_type = "rbf"
    elif change == "exit_plane":
        changed.execution.z_stop_m += 0.1
    else:
        changed.execution.acqf_maxiter += 1
    def snapshot():
        return {str(p.relative_to(tmp_path)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in tmp_path.rglob("*") if p.is_file()}
    before = snapshot()
    with pytest.raises(ValueError, match="Incompatible checkpoint configuration"):
        MoboCampaignRunner(
            config=changed, output_dir=tmp_path, resume=True, num_batches=2,
            evaluator=MockBatchEvaluator(tmp_path), device="cpu",
        ).run()
    assert snapshot() == before


def test_batch_size_override_keeps_completed_membership(tmp_path):
    MoboCampaignRunner(
        output_dir=tmp_path, num_initial_samples=3, num_batches=1, batch_size=2,
        evaluator=MockBatchEvaluator(tmp_path), device="cpu", export_plots=False,
    ).run()
    previous_history = load_run_checkpoint(tmp_path).metric_history
    runner = MoboCampaignRunner(
        output_dir=tmp_path, resume=True, num_batches=3, batch_size=1,
        evaluator=MockBatchEvaluator(tmp_path), device="cpu", export_plots=False,
    )
    results, tracker, _ = runner.run()
    assert len(results) == 7
    assert tracker.history[:2] == previous_history
    checkpoint = load_run_checkpoint(tmp_path)
    assert checkpoint.batch_size == 1
    assert checkpoint.evaluation_batches == [0, 0, 0, 1, 1, 2, 3]


def test_saved_budget_restored_and_replans_for_batch_override(tmp_path):
    class InterruptedEvaluator(MockBatchEvaluator):
        def evaluate_batch(self, candidates, **kwargs):
            if (kwargs.get("eval_ids") or [0])[0] == "eval_000005":
                raise RuntimeError("interrupted before second batch")
            return super().evaluate_batch(candidates, **kwargs)

    with pytest.raises(RuntimeError, match="interrupted"):
        MoboCampaignRunner(
            output_dir=tmp_path, num_initial_samples=2, num_batches=3, batch_size=2,
            total_eval_budget=7, evaluator=InterruptedEvaluator(tmp_path), device="cpu", export_plots=False,
        ).run()
    checkpoint = load_run_checkpoint(tmp_path)
    assert checkpoint.iteration == 1
    assert checkpoint.planned_num_batches == 3
    runner = MoboCampaignRunner(
        output_dir=tmp_path, resume=True, batch_size=3, evaluator=MockBatchEvaluator(tmp_path),
        device="cpu", export_plots=False,
    )
    results, _, _ = runner.run()
    assert len(results) == 7
    assert runner.total_eval_budget == 7
    assert runner.num_batches == 3  # The durable second proposal retains its original size.
    assert load_run_checkpoint(tmp_path).evaluation_batches == [0, 0, 1, 1, 2, 2, 3]


def test_legacy_completed_checkpoint_migration(tmp_path):
    MoboCampaignRunner(
        output_dir=tmp_path, num_initial_samples=3, num_batches=1, batch_size=2,
        evaluator=MockBatchEvaluator(tmp_path), device="cpu", export_plots=False,
    ).run()
    path = tmp_path / "checkpoints" / "checkpoint.pt"
    state = load_run_checkpoint(path)
    legacy_fields = {"version", "iteration", "results_serialized", "hypervolumes", "acquisition_mode",
                     "reporting_ref_point", "seed", "batch_size", "constrained", "torch_rng_state",
                     "numpy_rng_state", "config"}
    payload = {k: v for k, v in state.to_dict().items() if k in legacy_fields}
    payload["version"] = "1.0"
    torch.save(payload, path)
    migrated = load_run_checkpoint(path)
    assert migrated.version == "1.0"
    assert migrated.num_initial_samples == 3
    assert migrated.evaluation_batches == [0, 0, 0, 1, 1]
    with pytest.warns(RuntimeWarning, match="Legacy v1"):
        resumed, _, _ = MoboCampaignRunner(
            output_dir=tmp_path, resume=True, num_batches=2, evaluator=MockBatchEvaluator(tmp_path),
            device="cpu", export_plots=False,
        ).run()
    assert len(resumed) == 7
    assert load_run_checkpoint(tmp_path).version == "2.0"


def test_legacy_scalarized_weights_require_explicit_input(tmp_path):
    MoboCampaignRunner(
        output_dir=tmp_path, num_initial_samples=3, num_batches=1, batch_size=2,
        optimization_mode="scalarized_bo", scalar_weights=[0.6, 0.3, 0.1],
        evaluator=MockBatchEvaluator(tmp_path), device="cpu", export_plots=False,
    ).run()
    path = tmp_path / "checkpoints" / "checkpoint.pt"
    payload = load_run_checkpoint(path).to_dict()
    payload["version"] = "1.0"
    payload.pop("scalar_weights")
    torch.save(payload, path)
    with pytest.raises(ValueError, match="omitted weights"):
        MoboCampaignRunner(output_dir=tmp_path, resume=True, num_batches=2, device="cpu").run()
    with pytest.warns(RuntimeWarning, match="Legacy v1"):
        runner = MoboCampaignRunner(
            output_dir=tmp_path, resume=True, num_batches=2, scalar_weights=[0.6, 0.3, 0.1],
            evaluator=MockBatchEvaluator(tmp_path), device="cpu", export_plots=False,
        )
        runner.run()
    assert runner.scalar_weights.tolist() == pytest.approx([0.6, 0.3, 0.1])


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA unavailable")
def test_cuda_rng_continuation(tmp_path):
    options = dict(num_initial_samples=3, num_batches=1, batch_size=2, seed=9,
                   device="cuda", export_plots=False, export_env_info=False)
    MoboCampaignRunner(output_dir=tmp_path, evaluator=MockBatchEvaluator(tmp_path), **options).run()
    checkpoint = load_run_checkpoint(tmp_path)
    assert len(checkpoint.cuda_rng_states) == torch.cuda.device_count()
    expected = torch.rand(4, device="cuda")
    torch.rand(50, device="cuda")
    runner = MoboCampaignRunner(
        output_dir=tmp_path, resume=True, evaluator=MockBatchEvaluator(tmp_path),
        device="cuda", export_plots=False, export_env_info=False,
    )
    runner.run()  # Saved target is already complete: restore without new proposal draws.
    actual = torch.rand(4, device="cuda")
    assert torch.equal(actual, expected)


@pytest.mark.parametrize("field", ["evaluation_batches", "metric_history", "reporting_scales", "reporting_ref_point", "torch_rng_state", "version"])
def test_corrupted_campaign_state_rejected_without_overwriting_metadata(tmp_path, field):
    MoboCampaignRunner(
        output_dir=tmp_path, num_initial_samples=3, num_batches=1, batch_size=2,
        evaluator=MockBatchEvaluator(tmp_path), device="cpu", export_plots=False,
    ).run()
    path = tmp_path / "checkpoints" / "checkpoint.pt"
    payload = load_run_checkpoint(path).to_dict()
    if field == "evaluation_batches":
        payload[field] = [0] * len(payload["results_serialized"])
    elif field == "metric_history":
        payload[field][0]["num_valid_points"] += 1
    elif field == "reporting_scales":
        payload[field] = [1e-3, 1e-3, 1e6]
    elif field == "reporting_ref_point":
        payload[field][0] -= 1.0
    elif field == "torch_rng_state":
        payload[field] = torch.ones(1, dtype=torch.uint8)
    else:
        payload[field] = "99.0"
    torch.save(payload, path)
    before = {str(p.relative_to(tmp_path)): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    with pytest.raises(ValueError):
        MoboCampaignRunner(output_dir=tmp_path, resume=True, num_batches=2, device="cpu").run()
    after = {str(p.relative_to(tmp_path)): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert before == after


def test_resume_from_checkpoint_uses_original_directory(tmp_path):
    MoboCampaignRunner(
        output_dir=tmp_path, num_initial_samples=3, num_batches=1, batch_size=2,
        evaluator=MockBatchEvaluator(tmp_path), device="cpu", export_plots=False,
    ).run()
    runner = MoboCampaignRunner(
        resume_from=tmp_path / "checkpoints" / "checkpoint.pt", num_batches=2,
        evaluator=MockBatchEvaluator(tmp_path), device="cpu", export_plots=False,
    )
    results, _, run_dir = runner.run()
    assert run_dir == tmp_path
    assert len(results) == 7


def test_resume_cannot_fork_into_new_directory(tmp_path):
    source = tmp_path / "source"
    MoboCampaignRunner(
        output_dir=source, num_initial_samples=3, num_batches=1, batch_size=2,
        evaluator=MockBatchEvaluator(source), device="cpu", export_plots=False,
    ).run()
    destination = tmp_path / "fork"
    with pytest.raises(ValueError, match="original run identity"):
        MoboCampaignRunner(
            resume_from=source, output_dir=destination, num_batches=2, device="cpu",
        ).run()
    assert not destination.exists()


def test_resume_rejects_explicit_device_change_even_without_cuda(tmp_path):
    MoboCampaignRunner(
        output_dir=tmp_path, num_initial_samples=1, num_batches=0,
        evaluator=MockBatchEvaluator(tmp_path), device="cpu", export_plots=False,
    ).run()
    original_config = (tmp_path / "config.yaml").read_bytes()
    with pytest.raises(ValueError, match="device differs"):
        MoboCampaignRunner(output_dir=tmp_path, resume=True, device="cuda").run()
    assert (tmp_path / "config.yaml").read_bytes() == original_config


class InterruptingStreamEvaluator(MockBatchEvaluator):
    """Complete one chosen candidate out of order, then interrupt the parent."""

    def __init__(self, run_dir, interrupt_batch=None, completion_position=1, **kwargs):
        super().__init__(run_dir, **kwargs)
        self.interrupt_batch = interrupt_batch
        self.completion_position = completion_position
        self.submissions = []

    def evaluate_batch(self, candidates, run_id="mock", eval_ids=None, on_evaluation_complete=None):
        self.submissions.append((list(eval_ids), candidates))
        if len(self.submissions) - 1 == self.interrupt_batch:
            position = self.completion_position
            result = self._generate_candidate_result(candidates[position], run_id, eval_ids[position])
            on_evaluation_complete(result)
            raise RuntimeError("Injected parent interruption")
        return super().evaluate_batch(candidates, run_id, eval_ids, on_evaluation_complete)


@pytest.mark.parametrize("mode", ["unconstrained_mobo", "constrained_mobo", "scalarized_bo"])
@pytest.mark.parametrize("interrupted_batch", [0, 1])
def test_partial_batch_recovery_matches_uninterrupted_campaign(tmp_path, mode, interrupted_batch):
    from mobo_linac.io.journal import load_streaming_records

    options = dict(num_initial_samples=3, num_batches=3, batch_size=3, seed=101,
                   optimization_mode=mode, scalar_weights=[0.6, 0.3, 0.1], device="cpu",
                   export_plots=False, export_env_info=False)
    failed = ["eval_000002", "eval_000005"]
    full_dir = tmp_path / "full"
    full, full_tracker, _ = MoboCampaignRunner(
        **options, output_dir=full_dir, evaluator=MockBatchEvaluator(full_dir, fail_eval_ids=failed),
    ).run()
    interrupted_dir = tmp_path / "interrupted"
    evaluator = InterruptingStreamEvaluator(interrupted_dir, interrupted_batch, fail_eval_ids=failed)
    with pytest.raises(RuntimeError, match="parent interruption"):
        MoboCampaignRunner(**options, output_dir=interrupted_dir, evaluator=evaluator).run()
    pending = load_run_checkpoint(interrupted_dir / "checkpoints" / "pending_batch.pt")
    assert pending.pending_proposal["batch_idx"] == interrupted_batch
    ids = pending.pending_proposal["evaluation_ids"]
    completed_id = ids[1]
    if interrupted_batch == 0:
        assert not (interrupted_dir / "checkpoints" / "checkpoint.pt").exists()
    # A stale CSV must never override the exact journal.
    (interrupted_dir / "evaluations_stream.csv").write_text("stale,csv\n")
    resumed_evaluator = InterruptingStreamEvaluator(interrupted_dir, fail_eval_ids=failed)
    resumed, tracker, _ = MoboCampaignRunner(
        output_dir=interrupted_dir, resume=True, evaluator=resumed_evaluator,
        device="cpu", export_plots=False, export_env_info=False,
    ).run()
    assert resumed_evaluator.submissions[0][0] == [identity for identity in ids if identity != completed_id]
    assert [r.x_physical for r in resumed] == [r.x_physical for r in full]
    assert [r.evaluation_id for r in resumed] == [r.evaluation_id for r in full]
    assert [r.simulation_valid for r in resumed] == [r.simulation_valid for r in full]
    assert tracker.history == full_tracker.history
    assert len(load_streaming_records(interrupted_dir)) == len(full)
    assert not (interrupted_dir / "checkpoints" / "pending_batch.pt").exists()
    idle_evaluator = InterruptingStreamEvaluator(interrupted_dir)
    again, again_tracker, _ = MoboCampaignRunner(
        output_dir=interrupted_dir, resume=True, evaluator=idle_evaluator, device="cpu",
        export_plots=False, export_env_info=False,
    ).run()
    assert idle_evaluator.submissions == []
    assert len(again) == len(full)
    assert again_tracker.history == tracker.history


def test_repeated_initial_batch_interruptions_preserve_completed_work(tmp_path):
    from mobo_linac.io.journal import load_streaming_records

    with pytest.raises(RuntimeError, match="parent interruption"):
        MoboCampaignRunner(
            output_dir=tmp_path, num_initial_samples=3, num_batches=0, device="cpu",
            evaluator=InterruptingStreamEvaluator(tmp_path, 0, completion_position=2),
            export_plots=False, export_env_info=False,
        ).run()
    evaluator = InterruptingStreamEvaluator(tmp_path, 0, completion_position=1)
    with pytest.raises(RuntimeError, match="parent interruption"):
        MoboCampaignRunner(output_dir=tmp_path, resume=True, evaluator=evaluator, device="cpu",
                           export_plots=False, export_env_info=False).run()
    assert evaluator.submissions[0][0] == ["eval_000001", "eval_000002"]
    final_evaluator = InterruptingStreamEvaluator(tmp_path)
    results, _, _ = MoboCampaignRunner(
        output_dir=tmp_path, resume=True, evaluator=final_evaluator, device="cpu",
        export_plots=False, export_env_info=False,
    ).run()
    assert final_evaluator.submissions[0][0] == ["eval_000001"]
    assert [r.evaluation_id for r in results] == ["eval_000001", "eval_000002", "eval_000003"]
    assert len(load_streaming_records(tmp_path)) == 3


@pytest.mark.parametrize("after_commit", [False, True])
@pytest.mark.parametrize("interrupted_iteration", [0, 1])
def test_checkpoint_commit_interruption_does_not_repeat_completed_batch(tmp_path, monkeypatch, after_commit, interrupted_iteration):
    import mobo_linac.campaigns.runner as runner_module

    original_save = runner_module.save_run_checkpoint

    def interrupt_save(**kwargs):
        target = Path(kwargs["checkpoint_path"])
        if target.name == f"checkpoint_iter_{interrupted_iteration:02d}.pt":
            if after_commit:
                original_save(**kwargs)
            raise RuntimeError("Injected checkpoint interruption")
        return original_save(**kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(runner_module, "save_run_checkpoint", interrupt_save)
        with pytest.raises(RuntimeError, match="checkpoint interruption"):
            MoboCampaignRunner(
                output_dir=tmp_path, num_initial_samples=3, num_batches=interrupted_iteration, batch_size=2,
                evaluator=MockBatchEvaluator(tmp_path), device="cpu", export_plots=False,
            ).run()
    evaluator = InterruptingStreamEvaluator(tmp_path)
    results, tracker, _ = MoboCampaignRunner(
        output_dir=tmp_path, resume=True, evaluator=evaluator, device="cpu", export_plots=False,
    ).run()
    assert evaluator.submissions == []
    assert len(results) == 3 + interrupted_iteration * 2
    assert len(tracker.history) == interrupted_iteration + 1
    assert not (tmp_path / "checkpoints" / "pending_batch.pt").exists()


@pytest.mark.parametrize("swallow_callback_error", [False, True])
def test_campaign_callback_persistence_failure_is_observable(tmp_path, monkeypatch, swallow_callback_error):
    import mobo_linac.campaigns.runner as runner_module

    def fail_append(*args, **kwargs):
        raise OSError("Injected journal disk failure")

    class SwallowingEvaluator(MockBatchEvaluator):
        def evaluate_batch(self, candidates, run_id, eval_ids, on_evaluation_complete):
            results = super().evaluate_batch(candidates, run_id, eval_ids)
            for result in results:
                try:
                    on_evaluation_complete(result)
                except OSError:
                    pass
            return results

    evaluator = SwallowingEvaluator(tmp_path) if swallow_callback_error else MockBatchEvaluator(tmp_path)
    with monkeypatch.context() as patch:
        patch.setattr(runner_module, "append_streaming_evaluation", fail_append)
        with pytest.raises(OSError, match="journal disk failure"):
            MoboCampaignRunner(
                output_dir=tmp_path, num_initial_samples=2, num_batches=0, evaluator=evaluator,
                device="cpu", export_plots=False,
            ).run()
    assert (tmp_path / "checkpoints" / "pending_batch.pt").exists()
    assert not (tmp_path / "checkpoints" / "checkpoint.pt").exists()
    recovered, _, _ = MoboCampaignRunner(
        output_dir=tmp_path, resume=True, evaluator=MockBatchEvaluator(tmp_path),
        device="cpu", export_plots=False,
    ).run()
    assert len(recovered) == 2


def test_pending_batch_size_override_applies_after_recovered_batch(tmp_path):
    options = dict(output_dir=tmp_path, num_initial_samples=3, num_batches=3, batch_size=2,
                   total_eval_budget=8, device="cpu", export_plots=False, export_env_info=False)
    with pytest.raises(RuntimeError, match="parent interruption"):
        MoboCampaignRunner(**options, evaluator=InterruptingStreamEvaluator(tmp_path, 1)).run()
    evaluator = InterruptingStreamEvaluator(tmp_path)
    runner = MoboCampaignRunner(output_dir=tmp_path, resume=True, batch_size=3, device="cpu",
                                evaluator=evaluator, export_plots=False, export_env_info=False)
    results, tracker, _ = runner.run()
    assert evaluator.submissions[0][0] == ["eval_000004"]
    assert len(evaluator.submissions[1][0]) == 3
    assert runner.num_batches == 2
    assert len(results) == 8
    assert len(tracker.history) == 3


def test_inflight_fallback_recovery_restores_post_proposal_rng(tmp_path, monkeypatch):
    import random
    import mobo_linac.acquisition.mobo as acquisition_module

    def fail_optimizer(**kwargs):
        torch.rand(3)
        np.random.random()
        random.random()
        raise RuntimeError("Forced fallback")

    monkeypatch.setattr(acquisition_module, "optimize_acqf", fail_optimizer)
    options = dict(num_initial_samples=3, num_batches=3, batch_size=2, seed=85,
                   device="cpu", export_plots=False, export_env_info=False)
    full_dir, split_dir = tmp_path / "full", tmp_path / "split"
    full, full_tracker, _ = MoboCampaignRunner(
        **options, output_dir=full_dir, evaluator=MockBatchEvaluator(full_dir),
    ).run()
    with pytest.raises(RuntimeError, match="parent interruption"):
        MoboCampaignRunner(**options, output_dir=split_dir,
                           evaluator=InterruptingStreamEvaluator(split_dir, 1)).run()
    pending = load_run_checkpoint(split_dir / "checkpoints" / "pending_batch.pt")
    assert pending.sobol_state["num_generated"] == 5
    # Disturb all parent RNGs before recovery.
    torch.rand(100)
    np.random.random(100)
    random.random()
    resumed, tracker, _ = MoboCampaignRunner(
        output_dir=split_dir, resume=True, evaluator=MockBatchEvaluator(split_dir),
        device="cpu", export_plots=False, export_env_info=False,
    ).run()
    assert [r.x_physical for r in resumed] == [r.x_physical for r in full]
    assert tracker.history == full_tracker.history
    assert load_run_checkpoint(split_dir).sobol_state == load_run_checkpoint(full_dir).sobol_state


@pytest.mark.parametrize("corruption", ["interior_json", "unknown_identity", "candidate", "batch", "pending_ids", "pending_metrics"])
def test_recovery_conflicts_fail_before_writes(tmp_path, corruption):
    import json

    with pytest.raises(RuntimeError, match="parent interruption"):
        MoboCampaignRunner(
            output_dir=tmp_path, num_initial_samples=3, num_batches=2, batch_size=2,
            evaluator=InterruptingStreamEvaluator(tmp_path, 1), device="cpu", export_plots=False,
        ).run()
    journal = tmp_path / "evaluations_stream.jsonl"
    pending_path = tmp_path / "checkpoints" / "pending_batch.pt"
    if corruption.startswith("pending"):
        payload = load_run_checkpoint(pending_path).to_dict()
        if corruption == "pending_ids":
            payload["pending_proposal"]["evaluation_ids"][0] = "eval_999999"
        else:
            payload["metric_history"][0]["feasible_hypervolume"] += 1
            payload["hypervolumes"][0] += 1
        torch.save(payload, pending_path)
    else:
        lines = journal.read_text().splitlines()
        record = json.loads(lines[-1])
        if corruption == "interior_json":
            lines.insert(1, "malformed interior record")
        else:
            if corruption == "unknown_identity":
                record["evaluation"]["evaluation_id"] = "eval_999999"
            elif corruption == "candidate":
                record["evaluation"]["x_physical"][0] += 1
            else:
                record["batch_idx"] = 0
            lines[-1] = json.dumps(record)
        journal.write_text("\n".join(lines) + "\n")
    before = {str(p.relative_to(tmp_path)): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    evaluator = InterruptingStreamEvaluator(tmp_path)
    with pytest.raises(ValueError):
        MoboCampaignRunner(output_dir=tmp_path, resume=True, evaluator=evaluator,
                           device="cpu", export_plots=False).run()
    assert evaluator.submissions == []
    assert before == {str(p.relative_to(tmp_path)): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}


def test_resume_pending_file_repairs_truncated_tail_and_retains_completed_work(tmp_path):
    from mobo_linac.io.journal import load_streaming_records

    with pytest.raises(RuntimeError, match="parent interruption"):
        MoboCampaignRunner(
            output_dir=tmp_path, num_initial_samples=3, num_batches=0,
            evaluator=InterruptingStreamEvaluator(tmp_path, 0), device="cpu", export_plots=False,
        ).run()
    with (tmp_path / "evaluations_stream.jsonl").open("ab") as stream:
        stream.write(b'{"evaluation":')
    evaluator = InterruptingStreamEvaluator(tmp_path)
    with pytest.warns(RuntimeWarning, match="truncated trailing"):
        results, _, _ = MoboCampaignRunner(
            resume_from=tmp_path / "checkpoints" / "pending_batch.pt", evaluator=evaluator,
            device="cpu", export_plots=False,
        ).run()
    assert evaluator.submissions[0][0] == ["eval_000001", "eval_000003"]
    assert len(results) == len(load_streaming_records(tmp_path)) == 3


@pytest.mark.parametrize("mode", ["unconstrained_mobo", "constrained_mobo", "scalarized_bo"])
def test_configured_two_variable_mixed_objective_campaign(tmp_path, mode):
    import pandas as pd
    from mobo_linac.io.results import load_evaluation_results
    config = load_config("configs/mobo_200MeV.yaml")
    config.design_variables = config.design_variables[:2]
    config.objectives = [config.objectives[2], config.objectives[0]]
    config.objectives[1].physical_direction = "maximize"
    config.objectives[1].model_sign = 1
    config.objectives[0].reporting_scale = 2e6
    directory = tmp_path / mode
    runner = MoboCampaignRunner(config=config, output_dir=directory, num_initial_samples=2,
                                num_batches=1, batch_size=1, device="cpu", export_plots=True,
                                optimization_mode=mode, evaluator=MockBatchEvaluator(directory))
    results, tracker, _ = runner.run()
    x, y, feasible = get_train_tensors(results, config=config)
    assert x.shape == (3, 2) and y.shape == (3, 2)
    assert runner.scalar_weights.tolist() == [0.5, 0.5]
    for extension in ("csv", "json"):
        restored = load_evaluation_results(directory / f"candidate_history.{extension}", config)
        assert [r.objectives_physical for r in restored] == [r.objectives_physical for r in results]
        assert [r.objectives_model for r in restored] == [r.objectives_model for r in results]
        assert [r.x_physical for r in restored] == [r.x_physical for r in results]
    stream = pd.read_csv(directory / "evaluations_stream.csv")
    assert "model_norm_emit_x_pos" in stream and "gun_phase_deg" not in stream
    pareto = pd.read_csv(directory / "pareto_all.csv", float_precision="round_trip")
    assert set(pareto.norm_emit_x_m_rad) <= {r.objectives_physical[1] for r in results}
    assert set(pareto.sigma_energy_eV) <= {r.objectives_physical[0] for r in results}
    assert tracker.history[0]["reporting_ref_point_physical"][1] == tracker.reporting_ref_point[1]
    assert load_run_checkpoint(directory).reporting_scales == [2e6, 1e-6]
    resumed = MoboCampaignRunner(output_dir=directory, resume=True, num_batches=2,
                                 export_plots=False, device="cpu", evaluator=MockBatchEvaluator(directory))
    continued, _, _ = resumed.run()
    assert len(continued) == 4
    assert list(pd.read_csv(directory / "evaluations_stream.csv").columns) == list(stream.columns)


def test_configured_all_failed_campaign_exports_empty_headers(tmp_path):
    import pandas as pd
    config = load_config("configs/mobo_200MeV.yaml")
    config.design_variables = config.design_variables[:2]
    config.objectives = [config.objectives[2], config.objectives[0]]
    runner = MoboCampaignRunner(config=config, output_dir=tmp_path, num_initial_samples=1,
                                num_batches=0, export_plots=False, device="cpu",
                                evaluator=MockBatchEvaluator(tmp_path, failure_rate=1.0))
    results, _, _ = runner.run()
    assert not results[0].simulation_valid
    assert pd.read_csv(tmp_path / "objectives_model.csv").shape == (0, 2)
    assert pd.read_csv(tmp_path / "pareto_feasible.csv").shape == (0, 4)


@pytest.mark.parametrize("weights", [[1.0], [0.0, 0.0], [1.0, -1.0], [float("nan"), 1.0]])
def test_scalar_weights_require_configured_finite_nonnegative_values(tmp_path, weights):
    config = load_config("configs/mobo_200MeV.yaml")
    config.objectives = config.objectives[:2]
    with pytest.raises(ValueError, match="Scalar weights"):
        MoboCampaignRunner(config=config, output_dir=tmp_path, scalar_weights=weights)


def test_parallel_batch_elapsed_time_is_distinct_from_sum_of_worker_runtimes(tmp_path, monkeypatch):
    import json
    import pandas as pd
    import mobo_linac.campaigns.runner as runner_module
    clock = [0.0]
    monkeypatch.setattr(runner_module.time, "perf_counter", lambda: clock[0])
    class ParallelTimingEvaluator(MockBatchEvaluator):
        def evaluate_batch(self, *args, **kwargs):
            # Four workers each report five seconds; their batch completes in six seconds.
            clock[0] += 6.0
            return super().evaluate_batch(*args, **kwargs)
        def _generate_candidate_result(self, *args, **kwargs):
            record = super()._generate_candidate_result(*args, **kwargs)
            record["timestamps"]["duration_sec"] = 5.0
            return record
    runner = MoboCampaignRunner(output_dir=tmp_path, num_initial_samples=4, num_batches=0,
                                evaluator=ParallelTimingEvaluator(tmp_path), export_plots=False, device="cpu")
    runner.run()
    metrics = pd.read_csv(tmp_path / "metrics_history.csv")
    assert metrics.total_wallclock_s.iloc[-1] == 6.0
    assert metrics.total_simulation_runtime_s.iloc[-1] == 20.0
    assert json.loads((tmp_path / "run_complete.json").read_text())["elapsed_wall_time_s"] == 6.0


def test_requested_plot_failure_prevents_final_completion(tmp_path, monkeypatch):
    import mobo_linac.campaigns.runner as runner_module
    def fail_plot(*args, **kwargs):
        raise OSError("Injected figure failure")
    monkeypatch.setattr(runner_module, "plot_hypervolume_progress", fail_plot)
    runner = MoboCampaignRunner(output_dir=tmp_path, num_initial_samples=1, num_batches=0,
                                evaluator=MockBatchEvaluator(tmp_path), export_plots=True, device="cpu")
    with pytest.raises(OSError, match="figure failure"):
        runner.run()
    assert (tmp_path / "checkpoints/checkpoint.pt").exists()
    assert not (tmp_path / "run_complete.json").exists()
