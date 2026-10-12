"""Step-by-step paper production scripts (scripts/production): syntax, guards and helpers."""

import importlib.util
import json
import os
import subprocess
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
PRODUCTION = ROOT / "scripts" / "production"
STEPS = sorted(PRODUCTION.glob("0*.sh"))


def _tools():
    spec = importlib.util.spec_from_file_location("production_tools", PRODUCTION / "production_tools.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_steps_are_numbered_executable_and_parse():
    assert [p.name[:2] for p in STEPS] == ["01", "02", "03", "04", "05", "06", "07"]
    for script in STEPS:
        assert os.access(script, os.X_OK), script
        subprocess.run(["bash", "-n", str(script)], check=True)


@pytest.mark.parametrize("script", STEPS, ids=lambda p: p.name)
def test_help_describes_the_step_without_side_effects(script, tmp_path):
    env = dict(os.environ, PRODUCTION_ROOT=str(tmp_path / "root"))
    result = subprocess.run([str(script), "--help"], capture_output=True, text=True, env=env, check=True)
    assert result.stdout.startswith(f"Step {int(script.name[:2])} - ")
    assert not (tmp_path / "root").exists()


def test_mock_evaluator_refuses_the_paper_root():
    env = dict(os.environ, MOCK_EVALUATOR="1")
    env.pop("PRODUCTION_ROOT", None)
    result = subprocess.run([str(PRODUCTION / "01_preflight.sh"), "--skip-tests", "--skip-astra"],
                            capture_output=True, text=True, env=env)
    assert result.returncode != 0
    assert "MOCK_EVALUATOR=1 needs PRODUCTION_ROOT" in result.stderr


def test_steps_require_their_predecessor(tmp_path):
    env = dict(os.environ, PRODUCTION_ROOT=str(tmp_path))
    result = subprocess.run([str(PRODUCTION / "04_primary.sh")], capture_output=True, text=True, env=env)
    assert result.returncode != 0
    assert "Step 03_screening has not completed" in result.stderr


def test_forecast_uses_pilot_runtime_and_disk(tmp_path, capsys):
    summary = tmp_path / "pilot_summary.json"
    summary.write_text(json.dumps({"measured": {"median_runtime_s": 300.0, "bytes_per_evaluation": 2e6}}))
    disk = tmp_path / "disk"
    # Primary experiment: 30 runs of 16 Sobol + 18 batches of 8 with 4 workers = 40 rounds per run.
    assert _tools().main(["forecast", "--pilot-summary", str(summary), "--runs", "30", "--initial", "16",
                          "--iterations", "18", "--batch", "8", "--workers", "4", "--disk-output", str(disk)]) == 0
    out = capsys.readouterr().out
    assert "4800 ASTRA evaluations" in out and "100.0 h" in out
    assert disk.read_text().strip() == "12"  # 4800 x 2 MB x 1.25


def test_forecast_partitions_global_workers_across_campaigns(tmp_path, capsys):
    summary = tmp_path / "pilot_summary.json"
    summary.write_text(json.dumps({"measured": {"median_runtime_s": 300.0, "bytes_per_evaluation": 2e6}}))
    disk = tmp_path / "disk"
    assert _tools().main(["forecast", "--pilot-summary", str(summary), "--runs", "30", "--initial", "16",
                          "--iterations", "18", "--batch", "8", "--workers", "8", "--concurrent-campaigns", "2",
                          "--disk-output", str(disk)]) == 0
    out = capsys.readouterr().out
    assert "4800 ASTRA evaluations" in out and "50.0 h" in out
    assert "2 campaigns, 4 workers each" in out
    assert disk.read_text().strip() == "12"


@pytest.mark.parametrize("step", ["03_screening.sh", "04_primary.sh"])
def test_benchmark_steps_forward_global_scheduler_limits(step):
    source = (PRODUCTION / step).read_text()
    assert '--max-concurrent-campaigns "$MAX_CONCURRENT_CAMPAIGNS" --total-workers "$WORKERS"' in source
    assert '--campaign-threads "$CAMPAIGN_THREADS"' in source
    assert '--concurrent-campaigns "$MAX_CONCURRENT_CAMPAIGNS"' in source


def _run(path, feasible, complete=True):
    path.mkdir(parents=True)
    pd.DataFrame({"simulation_valid": [True, True, False], "physically_feasible": [feasible, False, False],
                  "failure_category": [None, None, "TIMEOUT"], "runtime_s": [280.0, 300.0, 2000.0]}
                 ).to_csv(path / "evaluations.csv", index=False)
    (path / "work").mkdir()
    (path / "work" / "evaluations.csv").write_text("ignored copy inside a work directory\n")
    if complete:
        (path / "run_complete.json").write_text("{}")


def test_summary_gate_requires_complete_runs_with_feasible_candidates(tmp_path):
    tools = _tools()
    _run(tmp_path / "ok" / "a", feasible=True)
    assert tools.main(["summarize", str(tmp_path / "ok"), "--gate", "feasible",
                       "--output", str(tmp_path / "ok.json")]) == 0
    measured = json.loads((tmp_path / "ok.json").read_text())["measured"]
    assert (measured["runs"], measured["evaluations"], measured["valid"], measured["feasible"]) == (1, 3, 2, 1)
    assert measured["median_runtime_s"] == 300.0

    _run(tmp_path / "bad" / "a", feasible=False, complete=False)
    assert tools.main(["summarize", str(tmp_path / "bad"), "--gate", "feasible",
                       "--output", str(tmp_path / "bad.json")]) == 2
    problems = json.loads((tmp_path / "bad.json").read_text())["gate_problems"]
    assert len(problems) == 2


def test_summary_counts_case_runs_not_their_aggregate(tmp_path):
    suite = tmp_path / "phase1_scalarized"
    _run(suite / "balanced", feasible=True)
    _run(suite / "emittance", feasible=True)
    pd.DataFrame({"simulation_valid": [True]}).to_csv(suite / "evaluations.csv", index=False)
    assert [run.name for run in _tools().find_runs([tmp_path])] == ["balanced", "emittance"]
