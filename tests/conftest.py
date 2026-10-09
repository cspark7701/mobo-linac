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
    from mobo_linac.config import load_config

    project = tmp_path / 'template'
    project.mkdir()
    template = Path(__file__).resolve().parents[1] / 'astra.in'
    (project / 'astra.in').write_bytes(template.read_bytes())
    for name in load_config('configs/mobo_200MeV.yaml').simulation.static_files:
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
    config.simulation.template_dir = str(project)  # inputs come from configuration, not the cwd
    return project, config


@pytest.fixture
def publication_runs(tmp_path):
    """Temporary explicit-contract runs with feasible, infeasible, and failed evaluations."""
    from mobo_linac.io.artifacts import RunArtifactWriter
    from mobo_linac.metrics.hypervolume import HypervolumeTracker
    from mobo_linac.io.results import get_train_tensors
    import pandas as pd
    config = load_config('configs/mobo_200MeV.yaml')
    directories = []
    for phase in ('phase1', 'phase2', 'phase3'):
        directory = tmp_path / phase
        directory.mkdir()
        config.save_json(directory / 'config.json')
        config.save_yaml(directory / 'config.yaml')
        parameters = [v.nominal_value for v in config.design_variables]
        records = []
        for index, (objectives, valid, feasible) in enumerate([
            ([1e-6, 1.2e-6, .5e6], True, True),
            ([.5e-6, .6e-6, .2e6], True, False), (None, False, False)]):
            records.append(EvaluationResult(evaluation_id=f'eval_{index+1:06d}', run_id=phase,
                x_physical=parameters, objectives_physical=objectives,
                objectives_model=[-v for v in objectives] if objectives else None,
                diagnostics={}, simulation_valid=valid, physically_feasible=feasible,
                failure_category='SUCCESS' if valid else 'ASTRA_EXECUTION_FAILED'))
        tracker = HypervolumeTracker([-3e-6, -3e-6, -2e6], config)
        _, y, feasibility = get_train_tensors(records, config=config)
        tracker.track_iteration(0, y, feasibility)
        writer = RunArtifactWriter(directory, config)
        writer.write(records, tracker)
        directories.append(directory)
    verification = tmp_path / 'verification_summary.csv'
    pd.DataFrame([{'role': 'knee_point', 'stored_emit_x_m_rad': 1e-6,
        'rerun_emit_x_m_rad': 1e-6, 'stored_sigma_energy_eV': .5e6,
        'rerun_sigma_energy_eV': .5e6, 'max_diff_pct': 0., 'verification_status': 'MOCK_VERIFIED'}]).to_csv(verification, index=False)
    return (*directories, verification)
