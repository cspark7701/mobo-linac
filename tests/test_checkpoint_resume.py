"""
Unit tests for Checkpoint Writing, Resuming, and Deterministic Continuation (Task 04).
"""

import pytest
import torch
import numpy as np
from pathlib import Path

from mobo_linac.config import load_config
from mobo_linac.campaigns.runner import MoboCampaignRunner
from mobo_linac.io.results import load_run_checkpoint, get_train_tensors


class MockEvaluator:
    """Mock batch evaluator for fast, deterministic unit testing without ASTRA binary."""

    def __init__(self, run_dir: Path):
        self.run_dir = run_dir

    def evaluate_batch(self, candidates, run_id, eval_ids=None):
        raw_results = []
        for idx, cand in enumerate(candidates):
            eval_id_str = f"eval_{eval_ids[idx]:06d}" if eval_ids and idx < len(eval_ids) else f"eval_{idx+1:06d}"
            raw_results.append({
                "status": "success",
                "eval_id": eval_id_str,
                "run_id": run_id,
                "parameters": cand,
                "objectives": {
                    "norm_emit_x": float(0.1e-6 + 0.01e-6 * (sum(cand) % 5)),
                    "norm_emit_y": float(0.1e-6 + 0.01e-6 * (sum(cand) % 7)),
                    "sigma_energy": float(0.5e6 + 0.05e6 * (sum(cand) % 3)),
                },
                "diagnostics": {
                    "sigma_x_m": 0.5e-3,
                    "sigma_y_m": 0.5e-3,
                    "sigma_xp_rad": 0.5e-3,
                    "sigma_yp_rad": 0.5e-3,
                    "sigma_z_m": 0.5e-3,
                    "mean_kinetic_energy_eV": 200.0e6,
                    "transmission_fraction": 1.0,
                },
                "timestamps": {"duration_sec": 0.1},
                "eval_dir": str(self.run_dir / eval_id_str),
            })
        return raw_results


def test_uninterrupted_vs_resumed_campaign(tmp_path):
    """Verify that a resumed campaign produces identical results to an uninterrupted campaign."""
    config = load_config("configs/publication_200MeV.yaml")

    # 1. Uninterrupted run (8 initial + 3 batches of 2 = 14 evals)
    dir_uninterrupted = tmp_path / "uninterrupted"
    mock_eval_1 = MockEvaluator(dir_uninterrupted)
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
    mock_eval_2 = MockEvaluator(dir_resumed)
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
