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
    assert mobo_linac.__version__ == "0.1.0"


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
