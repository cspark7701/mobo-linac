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
    """Test scalarized BO execution with mock ASTRA evaluation."""
    config_path = Path("configs/mobo_200mev.yaml")
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
                "diagnostics": {
                    "emittance_x": 0.35e-6,
                    "emittance_y": 0.38e-6,
                    "energy_spread": 0.12,
                    "sigma_x": 0.8e-3,
                    "sigma_y": 0.8e-3,
                    "sigma_xp": 0.8e-3,
                    "sigma_yp": 0.8e-3,
                    "sigma_z": 0.8e-3,
                    "average_energy": 200.0e6,
                    "transmission": 1.0,
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
