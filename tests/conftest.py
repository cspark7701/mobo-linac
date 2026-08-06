"""
Shared pytest fixtures and mock ASTRA outputs for unit testing without ASTRA binary.
"""

import math
from pathlib import Path
import pytest
import torch

from mobo_linac.config import MoboConfig, load_config
from mobo_linac.constraints import ConstraintEvaluator
from mobo_linac.evaluation import EvaluationResult, FailureCategory, create_evaluation_result


# ---------------------------------------------------------------------------
# CLI options for test_paper_outputs.py
# ---------------------------------------------------------------------------

def pytest_addoption(parser):
    """Allow passing campaign directories as pytest CLI arguments."""
    parser.addoption("--phase2-dir", default=None, help="Phase 2 run directory (for paper output tests)")
    parser.addoption("--phase3-dir", default=None, help="Phase 3 run directory (for paper output tests)")
    parser.addoption("--verification-csv", default=None, help="Verification summary CSV (for paper output tests)")
    parser.addoption("--figures-dir", default="docs/paper/figures", help="Figures output dir (for paper output tests)")
    parser.addoption("--tables-dir", default="docs/paper", help="Tables output dir (for paper output tests)")


@pytest.fixture
def sample_config() -> MoboConfig:
    """Fixture providing loaded canonical MoboConfig instance."""
    return load_config("configs/mobo_200MeV.yaml")


@pytest.fixture
def sample_constraint_evaluator(sample_config) -> ConstraintEvaluator:
    """Fixture providing ConstraintEvaluator instance."""
    return ConstraintEvaluator(sample_config.constraints)


@pytest.fixture
def mock_valid_feasible_stats():
    """Mock ASTRA output statistics for a valid, physically feasible simulation."""
    return {
        "norm_emit_x": [1.0e-6, 1.2e-6],
        "norm_emit_y": [1.0e-6, 1.1e-6],
        "sigma_energy": [1.0e4, 5.0e4],
        "sigma_x": [0.5e-3, 0.8e-3],
        "sigma_y": [0.5e-3, 0.8e-3],
        "sigma_xp": [0.5e-3, 0.8e-3],
        "sigma_yp": [0.5e-3, 0.8e-3],
        "sigma_z": [0.5e-3, 0.8e-3],
        "mean_kinetic_energy": [190.0e6, 200.0e6],
        "transmission": [1.0, 1.0],
    }


@pytest.fixture
def mock_valid_infeasible_stats():
    """Mock ASTRA output statistics for a valid simulation with violated beam size (> 1mm)."""
    return {
        "norm_emit_x": [1.0e-6, 2.5e-6],
        "norm_emit_y": [1.0e-6, 2.5e-6],
        "sigma_energy": [1.0e4, 6.0e4],
        "sigma_x": [0.5e-3, 1.5e-3],  # Violated > 1mm
        "sigma_y": [0.5e-3, 0.8e-3],
        "sigma_xp": [0.5e-3, 0.8e-3],
        "sigma_yp": [0.5e-3, 0.8e-3],
        "sigma_z": [0.5e-3, 0.8e-3],
        "mean_kinetic_energy": [190.0e6, 200.0e6],
        "transmission": [1.0, 1.0],
    }


@pytest.fixture
def mock_timeout_output():
    """Mock worker execution output for a timed out ASTRA simulation."""
    return {
        "eval_id": "eval_000099",
        "run_id": "mock_run",
        "parameters": [0.2, 1.0, -1.0, 0.0, 0.0, 0.0],
        "status": "timeout",
        "error": "ASTRA execution timed out after 30 seconds",
        "eval_dir": "/tmp/mock_work/eval_000099",
        "execution_time_sec": 30.0,
    }


@pytest.fixture
def mock_missing_output():
    """Mock worker execution output for missing simulation output."""
    return {
        "eval_id": "eval_000100",
        "run_id": "mock_run",
        "parameters": [0.2, 1.0, -1.0, 0.0, 0.0, 0.0],
        "status": "failed",
        "error": "ASTRA output dictionary missing 'stats'",
        "eval_dir": "/tmp/mock_work/eval_000100",
        "execution_time_sec": 0.5,
    }


@pytest.fixture
def mock_nan_output():
    """Mock worker output containing NaN values in diagnostics."""
    return {
        "eval_id": "eval_000101",
        "run_id": "mock_run",
        "parameters": [0.2, 1.0, -1.0, 0.0, 0.0, 0.0],
        "status": "success",
        "objectives": {"norm_emit_x": math.nan, "norm_emit_y": 1.2e-6, "sigma_energy": 5.0e4},
        "diagnostics": {"sigma_x": 0.8e-3, "mean_kinetic_energy": 200.0e6},
        "eval_dir": "/tmp/mock_work/eval_000101",
        "execution_time_sec": 1.2,
    }
