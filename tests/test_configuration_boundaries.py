"""Scientific APIs take the configuration explicitly and support non-canonical layouts."""

import subprocess
import sys

from dataclasses import asdict

import pytest

from mobo_linac.config import config_from_dict, load_config


def noncanonical_config():
    """Five design variables and four objectives, including a maximized one."""
    data = asdict(load_config("configs/mobo_200MeV.yaml"))
    data["design_variables"] = data["design_variables"][:5]
    data["objectives"].append({
        "name": "peak_current", "explicit_name": "peak_current_A", "unit": "A",
        "physical_direction": "maximize", "model_sign": 1, "reporting_scale": 10.0,
    })
    data["execution"].update(acqf_raw_samples=16, acqf_num_restarts=2, acqf_maxiter=5)
    return config_from_dict(data, default_name="noncanonical")


@pytest.mark.parametrize("mode", ["unconstrained_mobo", "constrained_mobo", "scalarized_bo"])
def test_noncanonical_configuration_runs_campaign_exports_and_reports(tmp_path, mode):
    from mobo_linac.campaigns.runner import MoboCampaignRunner
    from mobo_linac.execution.mock import MockEvaluator
    from mobo_linac.io.run_data import read_run_data
    from mobo_linac.metrics.publication import campaign_summary

    config = noncanonical_config()
    runner = MoboCampaignRunner(
        config=config, output_dir=tmp_path / mode, num_initial_samples=4, num_batches=1,
        batch_size=2, seed=7, optimization_mode=mode, device="cpu", export_plots=True,
        evaluator=MockEvaluator(tmp_path / "mock", config=config),
    )
    results, tracker, run_dir = runner.run()
    assert len(results) == 6
    assert all(len(r.x_physical) == 5 for r in results)
    assert all(len(r.objectives_physical) == 4 for r in results if r.simulation_valid)
    assert tracker.reporting_ref_point.shape == (4,)
    run = read_run_data(run_dir)
    summary = campaign_summary(run)
    assert set(summary["objective_extrema"]) == {
        "norm_emit_x_m_rad", "norm_emit_y_m_rad", "sigma_energy_eV", "peak_current_A"}
    header = (run_dir / "candidate_history.csv").read_text().splitlines()[0]
    assert "peak_current_A" in header and "acc3_acc4_phase_deg" not in header


def test_library_imports_never_load_a_default_configuration():
    code = (
        "import mobo_linac.config as c\n"
        "c.load_config = lambda *a, **k: (_ for _ in ()).throw(AssertionError('implicit load'))\n"
        "import mobo_linac.campaigns, mobo_linac.metrics, mobo_linac.io, mobo_linac.robustness\n"
        "import mobo_linac.verification, mobo_linac.execution, mobo_linac.plotting\n"
    )
    subprocess.run([sys.executable, "-c", code], check=True)


def test_benchmark_reference_follows_objective_count():
    from mobo_linac.config import BenchmarkConfig
    config = noncanonical_config()
    assert BenchmarkConfig().resolved_reporting_ref_point(len(config.objectives)) == [1.5] * 4
    with pytest.raises(ValueError, match="match configured objectives"):
        BenchmarkConfig(reporting_ref_point=[1.5, 1.5, 1.5]).resolved_reporting_ref_point(4)
