"""
Unit tests for Python Package Layout and CLI Entry Points (Task 07).
"""

import subprocess
import sys
import pytest

import mobo_linac
import mobo_linac.acquisition
import mobo_linac.astra
import mobo_linac.config
import mobo_linac.constraints
import mobo_linac.evaluation
import mobo_linac.execution
import mobo_linac.io
import mobo_linac.metrics
import mobo_linac.models
import mobo_linac.objectives
import mobo_linac.plotting


def test_package_version():
    """Verify package version metadata."""
    assert hasattr(mobo_linac, "__version__")
    assert mobo_linac.__version__ == "1.0.0"

    try:
        import importlib.metadata
        installed_ver = importlib.metadata.version("mobo-linac")
        assert installed_ver == "1.0.0"
    except importlib.metadata.PackageNotFoundError:
        pass


def test_subpackage_imports():
    """Verify clean importability of all subpackages."""
    assert mobo_linac.astra.AstraWorkDirManager is not None
    assert mobo_linac.execution.BatchEvaluator is not None
    assert mobo_linac.models.build_gp_models is not None
    assert mobo_linac.acquisition.build_acquisition_function is not None
    assert mobo_linac.metrics.HypervolumeTracker is not None
    assert mobo_linac.io.save_evaluation_results is not None
    assert mobo_linac.plotting.plot_pareto_front is not None


def test_cli_help_execution():
    """Verify mobo-linac CLI command line interface execution."""
    res = subprocess.run(
        [sys.executable, "-m", "mobo_linac.cli", "--help"],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0
    assert "Multi-Objective Bayesian Optimization" in res.stdout
    assert "run" in res.stdout
    assert "resume" in res.stdout
    assert "analyze" in res.stdout


def test_mock_campaign_and_analysis_do_not_initialize_astra(tmp_path):
    """Block external simulator imports and check environment after real mock work."""
    code = r'''
import importlib.abc
import os
import sys
from pathlib import Path
class BlockSimulator(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in ('astra', 'distgen'):
            raise AssertionError('Unexpected simulator initialization: ' + fullname)
sys.meta_path.insert(0, BlockSimulator())
before = dict(os.environ)
from mobo_linac.campaigns.runner import MoboCampaignRunner
from mobo_linac.execution.mock import MockBatchEvaluator
from mobo_linac.execution.candidate_evaluator import CandidateEvaluatorBase
from mobo_linac.io.run_data import read_run_data
from mobo_linac.metrics.publication import campaign_summary
from mobo_linac.astra.runner import resolve_executable_path
assert dict(os.environ) == before
for mode, constrained in [('scalarized_bo', False), ('unconstrained_mobo', False), ('constrained_mobo', True)]:
    root = Path(sys.argv[1]) / mode
    results, tracker, run_dir = MoboCampaignRunner(config='configs/publication_200MeV.yaml',
        output_dir=root, num_initial_samples=2, num_batches=0, seed=42,
        optimization_mode=mode, constrained=constrained, evaluator=MockBatchEvaluator(root),
        export_plots=False, export_env_info=False).run()
    assert len(results) == 2
    assert campaign_summary(read_run_data(run_dir))
from mobo_linac.config import load_config
from mobo_linac.robustness.workflow import run_robustness_workflow
from mobo_linac.verification.verifier import run_verification_pipeline
config = load_config('configs/publication_200MeV.yaml')
run_robustness_workflow(results, config, Path(sys.argv[1]) / 'robustness',
                       num_perturbations=1, batch_evaluator=MockBatchEvaluator(root))
run_verification_pipeline(results, config=config, output_dir=Path(sys.argv[1]) / 'verification',
                          mock_evaluator=MockBatchEvaluator(root))
assert os.environ.get('ASTRA_BIN') == before.get('ASTRA_BIN')
assert os.environ.get('GENERATOR_BIN') == before.get('GENERATOR_BIN')
assert 'astra' not in sys.modules and 'distgen' not in sys.modules
resolve_executable_path('ASTRA_BIN', 'astra')
assert os.environ.get('ASTRA_BIN') == before.get('ASTRA_BIN')
'''
    res = subprocess.run([sys.executable, '-c', code, str(tmp_path)], capture_output=True, text=True)
    assert res.returncode == 0, res.stderr
