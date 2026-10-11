"""
Unit and Integration Tests for ASTRA Isolated Working Directories.
"""

import json
import os
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pytest

from mobo_linac.astra.workdir import AstraWorkDirManager, format_eval_id
from mobo_linac.astra.runner import run_astra_eval

from mobo_linac.config import load_config as _load_test_config
TEST_CONFIG = _load_test_config("configs/mobo_200MeV.yaml")


@pytest.fixture
def temp_project(tmp_path, astra_stub_executable):
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
def test_real_astra_isolated_run(astra_timeout):
    """
    Integration test running real ASTRA simulation in isolated workdirs.
    Checks that two concurrent evaluations produce separate output files.
    """
    root_dir = Path(__file__).resolve().parents[1]
    if not (root_dir / "gun.dat").exists() or not (root_dir / "astra.in").exists():
        pytest.skip("Root ASTRA files not available in repo root")

    astra_bin = os.environ.get("ASTRA_BIN", str(root_dir / "bin" / "astra"))
    if not Path(astra_bin).is_file() and not shutil.which("astra"):
        pytest.skip(f"ASTRA executable not available at {astra_bin} or on PATH")

    from mobo_linac.astra.workdir import read_evaluation_manifest
    from mobo_linac.config import load_config
    from mobo_linac.execution import EvaluationRequest, ProcessPoolEvaluator
    params1 = [0.22, 1.0, -1.0, 0.0, 0.0, 0.0]
    params2 = [0.25, 1.2, -1.2, 5.0, 2.0, 2.0]
    with tempfile.TemporaryDirectory() as tmp_results:
        with ProcessPoolEvaluator(load_config("configs/mobo_200MeV.yaml"), base_results_dir=tmp_results,
                                  template_dir=root_dir, max_workers=2, timeout=astra_timeout) as evaluator:
            res1, res2 = evaluator.evaluate([EvaluationRequest(1, params1), EvaluationRequest(2, params2)],
                                            run_id="integration_test_run")
        assert res1["status"] == res2["status"] == "SUCCESS", (res1["error"], res2["error"])
        assert res1["eval_dir"] != res2["eval_dir"]
        # Results reference their attempt manifest; the manifest records the applied parameters.
        assert read_evaluation_manifest(res1["manifest_path"])["parameters"] == params1
        assert read_evaluation_manifest(res2["manifest_path"])["parameters"] == params2


def test_destination_reuse_and_legacy_cleanup_preserve_evidence(temp_project):
    from mobo_linac.astra.workdir import read_evaluation_manifest

    manager = AstraWorkDirManager(temp_project['results_dir'], temp_project['template_dir'])
    directory = manager.prepare_eval_dir('legacy', 1)
    (directory / 'astra.in').write_text('original effective input')
    manifest = {'eval_id': 'eval_000001', 'status': 'success'}
    manager.save_manifest(directory, manifest)
    with pytest.raises(FileExistsError):
        manager.prepare_eval_dir('legacy', 1)
    with pytest.raises(FileExistsError):
        manager.save_manifest(directory, {'status': 'failed'})
    assert read_evaluation_manifest(directory) == manifest
    manager.cleanup_eval_dir(directory)
    archive = manager.get_provenance_dir('legacy', 1, 'legacy')
    assert read_evaluation_manifest(archive) == manifest
    assert (archive / 'legacy_files' / 'astra.in').read_text() == 'original effective input'


def test_concurrent_attempts_of_same_logical_evaluation(temp_project):
    manager = AstraWorkDirManager(temp_project['results_dir'], temp_project['template_dir'])
    def prepare(_):
        attempt, archive = manager.reserve_attempt('run', 1)
        directory = manager.prepare_eval_dir('run', 1, attempt_id=attempt)
        manager.save_manifest(archive, {'attempt_id': attempt})
        return directory, archive
    with ThreadPoolExecutor(max_workers=4) as executor:
        records = list(executor.map(prepare, range(8)))
    assert len({directory for directory, _ in records}) == 8
    first, archive = records[0]
    manager.cleanup_eval_dir(first)
    assert (archive / 'manifest.json').exists()
    with pytest.raises(FileExistsError):
        manager.reserve_attempt('run', 1, first.name)
    with pytest.raises(ValueError):
        manager.cleanup_eval_dir(first.parent)


@pytest.mark.parametrize('identity', ['../outside', '/outside', '..', 'a/b', 'a\\b'])
def test_attempt_identity_rejects_path_components(temp_project, identity):
    manager = AstraWorkDirManager(temp_project['results_dir'], temp_project['template_dir'])
    with pytest.raises(ValueError):
        manager.reserve_attempt('run', 1, identity)


def test_failed_preparation_still_records_attempt(temp_project):
    (temp_project['template_dir'] / 'TWS_Sband.dat').unlink()
    result = run_astra_eval([0.2, 1, -1, 0, 0, 0], 'missing_input', 1,
                            base_results_dir=temp_project['results_dir'],
                            template_dir=temp_project['template_dir'], config=TEST_CONFIG)
    assert result['status'] == 'OUTPUT_MISSING'
    manifest = json.loads(Path(result['manifest_path']).read_text())
    assert 'Required static file' in manifest['error']
    assert manifest['attempt_id'] == result['attempt_id']


def test_input_snapshot_dereferences_mutable_symlink(temp_project):
    from mobo_linac.astra.workdir import file_sha256

    manager = AstraWorkDirManager(temp_project['results_dir'], temp_project['template_dir'])
    attempt, archive = manager.reserve_attempt('symlink', 1)
    directory = manager.prepare_eval_dir('symlink', 1, static_files=['gun.dat'], attempt_id=attempt, use_symlinks=True)
    hashes = manager.snapshot_inputs(directory, archive)
    source = temp_project['template_dir'] / 'gun.dat'
    source.write_text('changed after evaluation')
    snapshot = archive / 'inputs' / 'gun.dat'
    assert not snapshot.is_symlink()
    assert snapshot.read_text() == 'GUN DATA MOCK'
    assert file_sha256(snapshot) == hashes['gun.dat']


def test_provenance_failure_retains_workdir_and_final_failure_record(temp_project, monkeypatch):
    manager = AstraWorkDirManager(temp_project['results_dir'], temp_project['template_dir'])
    (temp_project['template_dir'] / 'TWS_Sband.dat').unlink()
    def fail_snapshot(*args, **kwargs):
        raise OSError('snapshot storage unavailable')
    monkeypatch.setattr(manager, 'snapshot_inputs', fail_snapshot)
    result = run_astra_eval([0.2, 1, -1, 0, 0, 0], 'audit_failure', 1,
                            workdir_manager=manager, clean_on_success=True, config=TEST_CONFIG)
    assert result['status'] == 'PROVENANCE_ERROR'
    assert Path(result['eval_dir']).exists()
    assert json.loads(Path(result['manifest_path']).read_text())['provenance_error'] == 'snapshot storage unavailable'


def test_missing_executable_fails_before_any_attempt_is_reserved(tmp_path, monkeypatch):
    from dataclasses import replace
    from mobo_linac.config import load_config
    config = load_config("configs/mobo_200MeV.yaml")
    config.simulation = replace(config.simulation, executable=str(tmp_path / "absent_astra"))
    monkeypatch.delenv("ASTRA_BIN", raising=False)
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    with pytest.raises(FileNotFoundError, match="ASTRA executable"):
        run_astra_eval([0.2, 1, -1, 0, 0, 0], "no_binary", 1, base_results_dir=tmp_path / "results", config=config)
    assert not (tmp_path / "results").exists()


def test_second_lattice_runs_through_configuration_only(tmp_path, monkeypatch):
    """A different template directory and static-file set needs no code change."""
    import os
    from dataclasses import replace
    from mobo_linac.astra.workdir import read_evaluation_manifest
    from mobo_linac.config import load_config
    lattice = tmp_path / "lattice_b"
    lattice.mkdir()
    (lattice / "deck.in").write_text((Path(__file__).resolve().parents[1] / "astra.in").read_text())
    for name in ("cavity_b.dat", "beam_b.ini"):
        (lattice / name).write_text(f"{name} contents")
    executable = lattice / "astra_b"
    executable.write_text("#!/bin/sh\n")
    executable.chmod(0o755)

    class Recording:
        particles = []
        def __init__(self, input_file, workdir, command=None, **kwargs):
            self.directory, self.command, self.output = Path(workdir), command, {}
        def __setitem__(self, key, value):
            pass
        def run(self):
            self.output = {"stats": {key: [value] for key, value in {
                "norm_emit_x": 1e-6, "norm_emit_y": 1e-6, "sigma_energy": 0.5e6, "sigma_x": 0.5e-3,
                "sigma_y": 0.5e-3, "sigma_xp": 0.4e-3, "sigma_yp": 0.4e-3, "sigma_z": 0.5e-3,
                "mean_kinetic_energy": 200e6, "transmission_fraction": 1.0, "z": 16.2}.items()}}
    monkeypatch.setattr("mobo_linac.astra.runner.Astra", Recording)
    before = dict(os.environ)
    config = load_config("configs/mobo_200MeV.yaml")
    config.simulation = replace(config.simulation, template_dir=str(lattice), input_template="deck.in",
                                static_files=["cavity_b.dat", "beam_b.ini"], executable=str(executable))
    result = run_astra_eval([0.2, 1, -1, 0, 0, 0], "lattice_b", 1, base_results_dir=tmp_path / "results", config=config)
    assert result["status"] == "SUCCESS", result["error"]
    manifest = read_evaluation_manifest(result["manifest_path"])
    assert set(manifest["input_hashes"]) == {"astra.in", "cavity_b.dat", "beam_b.ini"}
    assert manifest["executable"]["path"] == str(executable.resolve())
    assert "manifest" not in result  # the record references the manifest instead of duplicating it
    assert dict(os.environ) == before


def test_no_user_specific_or_source_tree_paths_in_astra_package():
    import re
    root = Path(__file__).resolve().parents[1] / "src" / "mobo_linac" / "astra"
    text = "".join(path.read_text() for path in root.glob("*.py"))
    assert "/home/" not in text and "~/Work" not in text and "Work/simulation_codes" not in text
    assert not re.search(r"parents\[\d\]", text)
    assert "os.environ[" not in text


def test_backend_timeout_is_classified_as_timeout_despite_lume_astra_handler():
    """lume-astra's execute2 raises TypeError (bytes + str) on TimeoutExpired; it must remain a TIMEOUT."""
    import sys
    from astra import tools
    from mobo_linac.astra.runner import _run_simulation
    from mobo_linac.status import SimulationStatus, classify_exception

    class SlowBackend:
        def run_astra(self, timeout=None):
            result = tools.execute2([sys.executable, "-c", "import time; print('x', flush=True); time.sleep(10)"],
                                    timeout=timeout)
            raise AssertionError(f"execute2 returned without raising: {result}")  # pragma: no cover

    with pytest.raises(TimeoutError) as raised:
        _run_simulation(SlowBackend(), timeout=1)
    assert classify_exception(raised.value) is SimulationStatus.TIMEOUT

    class FastFailure:
        def run_astra(self, timeout=None):
            raise ValueError("Couldn't find finished simulation")

    with pytest.raises(ValueError):  # an early failure keeps its own type
        _run_simulation(FastFailure(), timeout=60)
