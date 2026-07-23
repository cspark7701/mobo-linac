"""
Unit and Integration Tests for ASTRA Isolated Working Directories (Task 02).
"""

import json
import os
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pytest

from mobo_linac.astra.workdir import AstraWorkDirManager, format_eval_id
from mobo_linac.astra.runner import run_astra_eval, AstraRunner


@pytest.fixture
def temp_project(tmp_path):
    """
    Creates a temporary project structure with mock template files.
    """
    template_dir = tmp_path / "template"
    template_dir.mkdir()

    # Create dummy static files
    (template_dir / "gun.dat").write_text("GUN DATA MOCK")
    (template_dir / "PAL_SOL_A.dat").write_text("SOLENOID DATA MOCK")
    (template_dir / "TWS_Sband.dat").write_text("TWS DATA MOCK")
    (template_dir / "pal_photo2.ini").write_text("PARTICLE DIST MOCK")

    # Create dummy astra.in
    astra_in_content = (
        "&INPUT\n"
        "  solenoid:maxb(1) = 0.20,\n"
        "  quadrupole:q_grad(1) = 1.5,\n"
        "  quadrupole:q_grad(2) = -1.5,\n"
        "  cavity:phi(1) = 0.0,\n"
        "  cavity:phi(2) = 0.0,\n"
        "  cavity:phi(3) = 0.0,\n"
        "  cavity:phi(4) = 0.0,\n"
        "  cavity:phi(5) = 0.0\n"
        "/\n"
    )
    (template_dir / "astra.in").write_text(astra_in_content)

    results_dir = tmp_path / "results"
    results_dir.mkdir()

    return {
        "template_dir": template_dir,
        "results_dir": results_dir,
        "base_dir": tmp_path,
    }


def test_format_eval_id():
    """Verify evaluation ID formatting."""
    assert format_eval_id(1) == "eval_000001"
    assert format_eval_id(42) == "eval_000042"
    assert format_eval_id("eval_000003") == "eval_000003"
    assert format_eval_id("custom_id") == "eval_custom_id"


def test_unique_working_directories(temp_project):
    """Test that distinct evaluation IDs create isolated directories."""
    manager = AstraWorkDirManager(
        base_results_dir=temp_project["results_dir"],
        template_dir=temp_project["template_dir"],
    )

    eval1_dir = manager.prepare_eval_dir(run_id="run_test", eval_id=1)
    eval2_dir = manager.prepare_eval_dir(run_id="run_test", eval_id=2)

    assert eval1_dir != eval2_dir
    assert eval1_dir.exists()
    assert eval2_dir.exists()
    assert eval1_dir.name == "eval_000001"
    assert eval2_dir.name == "eval_000002"
    assert eval1_dir.parent == eval2_dir.parent


def test_file_isolation_and_independence(temp_project):
    """Test that modifying astra.in in one workdir does not affect root or other workdirs."""
    manager = AstraWorkDirManager(
        base_results_dir=temp_project["results_dir"],
        template_dir=temp_project["template_dir"],
    )

    eval1_dir = manager.prepare_eval_dir(run_id="run_test", eval_id=1)
    eval2_dir = manager.prepare_eval_dir(run_id="run_test", eval_id=2)

    root_in = temp_project["template_dir"] / "astra.in"
    eval1_in = eval1_dir / "astra.in"
    eval2_in = eval2_dir / "astra.in"

    # Modify eval1_in
    eval1_in.write_text("MODIFIED EVAL 1 INPUT")

    assert root_in.read_text() != "MODIFIED EVAL 1 INPUT"
    assert eval2_in.read_text() != "MODIFIED EVAL 1 INPUT"
    assert "solenoid:maxb(1)" in root_in.read_text()


def test_manifest_generation(temp_project):
    """Test manifest file writing and structure."""
    manager = AstraWorkDirManager(
        base_results_dir=temp_project["results_dir"],
        template_dir=temp_project["template_dir"],
    )

    eval_dir = manager.prepare_eval_dir(run_id="run_test", eval_id=10)
    manifest_data = {
        "run_id": "run_test",
        "eval_id": "eval_000010",
        "parameters": [0.25, 2.0, -2.0, 10.0, -5.0, 5.0],
        "status": "success",
        "timestamps": {"start_time": "2026-07-23T12:00:00", "end_time": "2026-07-23T12:00:02"},
        "eval_dir": str(eval_dir),
    }

    manifest_path = manager.save_manifest(eval_dir, manifest_data)
    assert manifest_path.exists()

    with open(manifest_path, "r", encoding="utf-8") as f:
        loaded = json.load(f)

    assert loaded["run_id"] == "run_test"
    assert loaded["eval_id"] == "eval_000010"
    assert loaded["parameters"] == [0.25, 2.0, -2.0, 10.0, -5.0, 5.0]


def test_concurrent_workdir_preparation(temp_project):
    """Test preparing multiple workdirs concurrently using ThreadPoolExecutor."""
    manager = AstraWorkDirManager(
        base_results_dir=temp_project["results_dir"],
        template_dir=temp_project["template_dir"],
    )

    def prepare_worker(idx):
        return manager.prepare_eval_dir(run_id="concurrent_run", eval_id=idx)

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(prepare_worker, i) for i in range(1, 17)]
        results = [f.result() for f in futures]

    assert len(results) == 16
    paths = set(results)
    assert len(paths) == 16  # All 16 paths must be unique


def test_cleanup_eval_dir(temp_project):
    """Test cleanup function removes specified workdir."""
    manager = AstraWorkDirManager(
        base_results_dir=temp_project["results_dir"],
        template_dir=temp_project["template_dir"],
    )

    eval_dir = manager.prepare_eval_dir(run_id="run_cleanup", eval_id=1)
    assert eval_dir.exists()

    manager.cleanup_eval_dir(eval_dir)
    assert not eval_dir.exists()


@pytest.mark.integration
def test_real_astra_isolated_run():
    """
    Integration test running real ASTRA simulation in isolated workdirs.
    Checks that two concurrent evaluations produce separate output files.
    """
    root_dir = Path(__file__).resolve().parents[1]
    if not (root_dir / "gun.dat").exists() or not (root_dir / "astra.in").exists():
        pytest.skip("Root ASTRA files not available in repo root")

    with tempfile.TemporaryDirectory() as tmp_results:
        runner = AstraRunner(
            run_id="integration_test_run",
            base_results_dir=tmp_results,
            template_dir=root_dir,
            timeout=30,
        )

        params1 = [0.22, 1.0, -1.0, 0.0, 0.0, 0.0]
        params2 = [0.25, 1.2, -1.2, 5.0, 2.0, 2.0]

        with ThreadPoolExecutor(max_workers=2) as executor:
            fut1 = executor.submit(runner.run, params1, eval_id=1)
            fut2 = executor.submit(runner.run, params2, eval_id=2)

            res1 = fut1.result()
            res2 = fut2.result()

        assert res1["eval_dir"] != res2["eval_dir"]
        assert Path(res1["manifest_path"]).exists()
        assert Path(res2["manifest_path"]).exists()

        assert res1["manifest"]["parameters"] == params1
        assert res2["manifest"]["parameters"] == params2
