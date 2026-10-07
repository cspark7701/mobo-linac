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
    parser.addoption("--phase1-dir", default=None, help="Phase 1 run directory (for paper output tests)")
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


@pytest.fixture
def recording_astra_project(tmp_path, monkeypatch):
    """A recording simulator with the real template and disposable fake field files."""
    import json
    import os
    from mobo_linac.astra.workdir import DEFAULT_STATIC_FILES
    from mobo_linac.config import load_config

    project = tmp_path / 'template'
    project.mkdir()
    template = Path(__file__).resolve().parents[1] / 'astra.in'
    (project / 'astra.in').write_bytes(template.read_bytes())
    for name in DEFAULT_STATIC_FILES:
        (project / name).write_text('fixed input bytes')
    executable = project / 'stub_astra'
    executable.write_bytes(b'recording executable')
    monkeypatch.setenv('ASTRA_BIN', str(executable))
    monkeypatch.chdir(project)
    class RecordingAstra:
        particles = []
        def __init__(self, input_file, workdir, **kwargs):
            self.directory = Path(workdir)
            self.template = Path(input_file).read_text()
            self.values = {}
            self.command = os.environ['ASTRA_BIN']
            self.output = {}
        def __setitem__(self, key, value):
            if key == 'charge:unsupported_test_key':
                raise ValueError('unsupported namelist override')
            self.values[key] = value
        def write_input(self):
            (self.directory / 'astra.in').write_text(self.template + '\n' + json.dumps(self.values, sort_keys=True) + '\n' + json.dumps({'timeout_sec': self.timeout, 'pid': os.getpid()}))
        def run(self):
            (self.directory / 'applied.json').write_text(json.dumps(self.values, sort_keys=True))
            self.output = {'stats': {key: [value] for key, value in {
                'norm_emit_x': 1e-6, 'norm_emit_y': 1e-6, 'sigma_energy': 0.5e6,
                'sigma_x': 0.5e-3, 'sigma_y': 0.5e-3, 'sigma_xp': 0.4e-3,
                'sigma_yp': 0.4e-3, 'sigma_z': 0.5e-3,
                'mean_kinetic_energy': 200e6, 'transmission_fraction': 1.0, 'z': 16.2,
            }.items()}}
    monkeypatch.setattr('mobo_linac.astra.runner.Astra', RecordingAstra)
    config = load_config(template.parents[0] / 'configs/publication_200MeV.yaml')
    # Use a different configured key and coupled targets, without changing jitter units.
    config.design_variables[0].astra_key = 'solenoid:maxb(2)'
    config.design_variables[4].coupled_targets = ['cavity:phi(2)', 'cavity:phi(6)']
    config.execution.clean_on_success = True
    return project, config
