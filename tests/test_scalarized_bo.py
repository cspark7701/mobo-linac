"""
Unit tests for Phase 1 Scalarized Bayesian Optimization workflow.
"""

import argparse
import pytest
from pathlib import Path
import torch

from mobo_linac.config import load_config
from mobo_linac.cli import run_scalarized


def test_scalarized_bo_argument_parser():
    from scripts.run_scalarized_bo import parse_args
    test_args = ["--n-iterations", "5", "--batch-size", "2", "--weights", "0.5", "0.3", "0.2"]
    import sys
    sys.argv = ["run_scalarized_bo.py"] + test_args
    args = parse_args()
    assert args.n_iterations == 5
    assert args.batch_size == 2
    assert args.weights == [0.5, 0.3, 0.2]


def test_scalarized_bo_execution(tmp_path, monkeypatch):
    """Test scalarized BO execution with mock ASTRA evaluation via CLI."""
    config_path = Path("configs/mobo_200MeV.yaml")
    assert config_path.exists()

    target_dir = tmp_path / "scalarized_test_run"

    class DummyArgs:
        config = str(config_path)
        n_iterations = 1
        batch_size = 2
        num_initial_samples = 4
        num_workers = 2
        weights = [1.0, 1.0, 1.0]
        seed = 42
        output_dir = str(target_dir)

    def mock_evaluate_batch(self, parameter_sets, run_id="default_run", eval_ids=None):
        results = []
        for i, p in enumerate(parameter_sets):
            results.append({
                "eval_id": eval_ids[i] if eval_ids else i + 1,
                "status": "success",
                "parameters": list(p),
                "objectives": {
                    "norm_emit_x": 0.35e-6,
                    "norm_emit_y": 0.38e-6,
                    "sigma_energy": 0.12e6,
                },
                "diagnostics": {
                    "sigma_x_m": 0.8e-3,
                    "sigma_y_m": 0.8e-3,
                    "sigma_xp_rad": 0.8e-3,
                    "sigma_yp_rad": 0.8e-3,
                    "sigma_z_m": 0.8e-3,
                    "mean_kinetic_energy_eV": 200.0e6,
                    "transmission_fraction": 1.0,
                    "z_final_m": 16.2,
                },
                "error": None,
            })
        return results

    from mobo_linac.execution.parallel import BatchEvaluator
    monkeypatch.setattr(BatchEvaluator, "evaluate_batch", mock_evaluate_batch)

    args = DummyArgs()
    run_scalarized(args)

    assert target_dir.exists()
    assert (target_dir / "config.json").exists()
    assert (target_dir / "hypervolume.csv").exists()
    assert (target_dir / "figures" / "pareto_front.png").exists()


def test_mobo_campaign_runner_scalarized_mode(tmp_path):
    """Test MoboCampaignRunner direct execution with optimization_mode='scalarized_bo'."""
    from mobo_linac.campaigns.runner import MoboCampaignRunner
    from mobo_linac.cli import CliMockEvaluator

    target_dir = tmp_path / "runner_scalarized_test"
    evaluator = CliMockEvaluator(target_dir)

    runner = MoboCampaignRunner(
        config="configs/mobo_200MeV.yaml",
        run_name="test_scalarized",
        output_dir=target_dir,
        num_initial_samples=4,
        num_batches=1,
        batch_size=2,
        seed=123,
        optimization_mode="scalarized_bo",
        scalar_weights=[0.5, 0.3, 0.2],
        evaluator=evaluator,
    )

    results, tracker, run_dir = runner.run()

    assert runner.optimization_mode == "scalarized_bo"
    assert len(results) == 6  # 4 initial + 2 in batch 1
    assert (target_dir / "checkpoints" / "checkpoint_iter_01.pt").exists()
    assert (target_dir / "hypervolume.csv").exists()

