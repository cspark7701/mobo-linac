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

    # 3. run-scalarized
    dir_sc = tmp_path / "mock_sc"
    sys.argv = ["mobo-linac", "run-scalarized", "--n-iterations", "1", "-q", "2", "--num-initial-samples", "4", "--output-dir", str(dir_sc), "--mock-evaluator"]
    main()
    assert (dir_sc / "candidate_history.csv").exists()

    # 4. run-robustness
    dir_rob = tmp_path / "mock_rob"
    sys.argv = ["mobo-linac", "run-robustness", "--input", str(dir_un), "--num-perturbations", "2", "--output-dir", str(dir_rob), "--mock-evaluator"]
    main()
    assert (dir_rob / "robustness_summary.csv").exists()

    # 5. run-verification
    dir_ver = tmp_path / "mock_ver"
    sys.argv = ["mobo-linac", "run-verification", "--input", str(dir_un), "--output-dir", str(dir_ver), "--mock-evaluator"]
    main()
    assert (dir_ver / "verification_manifest.json").exists()


def test_benchmark_cli_forwards_workers_and_algorithm_settings(tmp_path, monkeypatch):
    from mobo_linac.campaigns.benchmark import BenchmarkCampaignRunner

    captured = {}

    class RecordingBenchmarkRunner:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        def execute_benchmark_campaigns(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(
        "mobo_linac.campaigns.benchmark.BenchmarkCampaignRunner", RecordingBenchmarkRunner
    )
    main([
        "run-benchmark", "--algorithms", "scalarized_bo", "qlogehvi",
        "--seeds", "7", "8", "--num-workers", "3", "--budget", "5",
        "--n-sobol-init", "2", "-q", "2", "--device", "cpu",
        "--output-dir", str(tmp_path), "--mock-evaluator",
    ])
    assert captured["num_workers"] == 3
    assert captured["algorithms"] == ["scalarized_bo", "qlogehvi"]
    assert captured["seeds"] == [7, 8]
    assert captured["total_eval_budget"] == 5
    assert captured["batch_size"] == 2
    assert captured["device"] == "cpu"
    assert captured["mock_evaluator"] is not None


@pytest.mark.parametrize("algorithm", ["nsga2", "sobol"])
def test_benchmark_cli_rejects_unimplemented_algorithms(tmp_path, algorithm):
    with pytest.raises(ValueError, match="no implemented executor"):
        main([
            "run-benchmark", "--algorithms", algorithm, "--seeds", "42",
            "--output-dir", str(tmp_path / "unsupported"), "--dry-run",
        ])
    assert not (tmp_path / "unsupported").exists()
