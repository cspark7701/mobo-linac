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

