"""
Unit tests for CLI Workflow Execution, Dry-Run Mode, and Mock-Evaluator (Task 05).
"""

import pytest
import sys
from pathlib import Path
from mobo_linac.cli import main


def test_cli_help(capsys):
    """Verify CLI --help execution for all subcommands."""
    for cmd in ["run-unconstrained", "run-constrained", "run-benchmark", "run-robustness", "run-verification", "resume"]:
        sys.argv = ["mobo-linac", cmd, "--help"]
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert f"usage: mobo-linac {cmd}" in captured.out or f"usage: mobo-linac" in captured.out


def test_cli_dry_run(capsys, tmp_path):
    """Verify --dry-run flag for all workflow subcommands."""
    subcommands = [
        ["run-unconstrained", "--dry-run", "--output-dir", str(tmp_path / "dry_un")],
        ["run-constrained", "--dry-run", "--output-dir", str(tmp_path / "dry_co")],
        ["run-scalarized", "--dry-run", "--output-dir", str(tmp_path / "dry_sc")],
        ["run-benchmark", "--dry-run", "--output-dir", str(tmp_path / "dry_bm")],
        ["run-robustness", "--dry-run", "--output-dir", str(tmp_path / "dry_rob")],
        ["run-verification", "--dry-run", "--output-dir", str(tmp_path / "dry_ver")],
    ]

    for cmd_args in subcommands:
        sys.argv = ["mobo-linac"] + cmd_args
        main()
        captured = capsys.readouterr()
        assert "[DRY-RUN]" in captured.out


def test_cli_mock_evaluator_workflows(tmp_path):
    """Verify full workflow execution using --mock-evaluator."""
    # 1. run-unconstrained
    dir_un = tmp_path / "mock_un"
    sys.argv = ["mobo-linac", "run-unconstrained", "--n-iterations", "1", "-q", "2", "--num-initial-samples", "4", "--output-dir", str(dir_un), "--mock-evaluator"]
    main()
    assert (dir_un / "candidate_history.csv").exists()

    # 2. run-constrained
    dir_co = tmp_path / "mock_co"
    sys.argv = ["mobo-linac", "run-constrained", "--n-iterations", "1", "-q", "2", "--num-initial-samples", "4", "--output-dir", str(dir_co), "--mock-evaluator"]
    main()
    assert (dir_co / "candidate_history.csv").exists()

    # 3. run-robustness
    dir_rob = tmp_path / "mock_rob"
    sys.argv = ["mobo-linac", "run-robustness", "--num-perturbations", "3", "--output-dir", str(dir_rob), "--mock-evaluator"]
    main()
    assert (dir_rob / "robustness_summary.csv").exists()

    # 4. run-verification
    dir_ver = tmp_path / "mock_ver"
    sys.argv = ["mobo-linac", "run-verification", "--output-dir", str(dir_ver), "--mock-evaluator"]
    main()
    assert (dir_ver / "verification_manifest.json").exists()
