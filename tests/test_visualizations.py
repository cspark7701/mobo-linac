"""
Unit tests for modularized plotting suite in mobo_linac.plotting.
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
import torch

from mobo_linac.config import load_config
from mobo_linac.evaluation import EvaluationResult
from mobo_linac.plotting import (
    plot_best_so_far,
    plot_constraint_diagnostics,
    plot_constraint_violins,
    plot_design_variable_heatmap,
    plot_feasibility_rate,
    plot_hypervolume_histories,
    plot_hypervolume_progress,
    plot_objective_evolution,
    plot_parallel_coordinates,
    plot_pareto_front,
    plot_pareto_front_3d,
    plot_pareto_front_overlay,
    plot_pareto_verification_comparison,
    plot_scalarized_objective_trace,
)

CONFIG = load_config("configs/mobo_200MeV.yaml")


@pytest.fixture
def sample_evaluation_results():
    """Generates sample EvaluationResult objects for plotting tests."""
    results = []
    np.random.seed(42)
    for i in range(20):
        emit_x = 3.5e-6 + 0.1e-6 * np.sin(i)
        emit_y = 3.6e-6 + 0.1e-6 * np.cos(i)
        sigma_e = 0.9e6 + 0.05e6 * np.sin(i)
        res = EvaluationResult(
            evaluation_id=f"eval_{i}",
            run_id="test_run",
            x_physical=[0.2 + 0.01 * i, 1.0 - 0.05 * i, -1.0 + 0.05 * i, -10.0 + i, -5.0 + 0.5 * i, 0.0 + 0.2 * i],
            objectives_physical=[emit_x, emit_y, sigma_e],
            objectives_model=[-emit_x, -emit_y, -sigma_e],
            diagnostics={
                "sigma_x_m": 0.5e-3,
                "sigma_y_m": 0.5e-3,
                "sigma_xp_rad": 0.4e-3,
                "sigma_yp_rad": 0.4e-3,
                "sigma_z_m": 0.6e-3,
                "mean_kinetic_energy_eV": 200.0e6 + 1.0e6 * np.cos(i),
                "transmission_fraction": 1.0,
                "z_final_m": 16.2,
            },
            simulation_valid=True,
            physically_feasible=(i % 3 != 0),
            failure_category="SUCCESS" if (i % 3 != 0) else "INFEASIBLE_BEAM",
        )
        results.append(res)
    return results


def test_pareto_plotting(sample_evaluation_results, tmp_path):
    """Projections draw the actual non-dominated feasible front."""
    fig_2d = plot_pareto_front(sample_evaluation_results, output_path=tmp_path / "pareto_2d.png", config=CONFIG)
    assert (tmp_path / "pareto_2d.png").exists()
    labels = {text.get_text() for ax in fig_2d.axes for text in ax.get_legend().get_texts()}
    assert "Feasible Pareto front" in labels
    shown = {label for ax in fig_2d.axes for label in (ax.get_xlabel(), ax.get_ylabel())}
    assert shown >= {r"$\varepsilon_{n,x}$ [μm·rad]", r"$\sigma_E$ [MeV]"}
    plt.close(fig_2d)
    fig_3d = plot_pareto_front_3d(sample_evaluation_results, output_path=tmp_path / "pareto_3d.png", config=CONFIG)
    assert (tmp_path / "pareto_3d.png").exists()
    plt.close(fig_3d)


def test_convergence_plotting(sample_evaluation_results, tmp_path):
    history = [{"iteration": i, "feasible_hypervolume": 10.0 + i * 0.5, "all_point_hypervolume": 12.0 + i * 0.4}
               for i in range(10)]
    fig_hv = plot_hypervolume_progress(history, output_path=tmp_path / "hv.png")
    assert (tmp_path / "hv.png").exists()
    plt.close(fig_hv)
    for function, kwargs in ((plot_objective_evolution, {}), (plot_best_so_far, {}),
                             (plot_scalarized_objective_trace, {"weights": [1, 1, 1]})):
        fig = function(sample_evaluation_results, output_path=tmp_path / f"{function.__name__}.png", config=CONFIG, **kwargs)
        assert (tmp_path / f"{function.__name__}.png").exists()
        plt.close(fig)


def test_hypervolume_histories_accept_trackers_and_frames(tmp_path):
    from mobo_linac.metrics.hypervolume import HypervolumeTracker
    tracker = HypervolumeTracker([-1e-5, -1e-5, -1e7], CONFIG)
    tracker.track_iteration(0, torch.tensor([[-1e-6, -1e-6, -1e6]], dtype=torch.double), torch.tensor([True]))
    frame = pd.DataFrame({"iteration": [0, 1], "feasible_hypervolume": [1.0, 2.0], "all_point_hypervolume": [1.5, 2.5]})
    fig = plot_hypervolume_histories({"tracker": tracker, "frame": frame}, output_path=tmp_path / "hv_cmp.png")
    assert (tmp_path / "hv_cmp.png").exists()
    plt.close(fig)


def test_diagnostics_plotting(sample_evaluation_results, tmp_path):
    for function, name in ((plot_feasibility_rate, "feas"), (plot_constraint_diagnostics, "diag"),
                           (plot_constraint_violins, "viol")):
        fig = function(sample_evaluation_results, CONFIG, output_path=tmp_path / f"{name}.png")
        assert (tmp_path / f"{name}.png").exists()
        plt.close(fig)


def test_constraint_figures_draw_the_active_profile_limits(sample_evaluation_results):
    from copy import deepcopy
    stringent = deepcopy(CONFIG)
    stringent.constraints.max_sigma_x_m = 0.3e-3
    stringent.constraints.min_transmission = 0.9999
    fig = plot_constraint_diagnostics(sample_evaluation_results, stringent)
    by_label = {ax.get_ylabel(): ax for ax in fig.axes if ax.get_visible()}
    assert "Transmission [%]" in by_label  # transmission is now a plotted channel
    def limits(ax):
        return sorted(round(line.get_ydata()[0], 6) for line in ax.get_lines() if line.get_color() == "crimson")
    assert limits(by_label[r"$\sigma_x$ [mm]"]) == [0.3]
    assert limits(by_label["Transmission [%]"]) == [99.99]
    assert limits(by_label[r"$E_{kin}$ [MeV]"]) == [195.0, 205.0]
    plt.close(fig)


def test_parameters_plotting(sample_evaluation_results, tmp_path):
    fig_hm = plot_design_variable_heatmap(sample_evaluation_results, CONFIG, output_path=tmp_path / "heatmap.png")
    assert (tmp_path / "heatmap.png").exists()
    plt.close(fig_hm)
    fig_pc = plot_parallel_coordinates(sample_evaluation_results, CONFIG, output_path=tmp_path / "parallel.png")
    assert (tmp_path / "parallel.png").exists()
    plt.close(fig_pc)


def test_comparative_and_verification_plotting(sample_evaluation_results, tmp_path):
    fig_comp = plot_pareto_front_overlay({"Phase 2": sample_evaluation_results[:10],
                                          "Phase 3": sample_evaluation_results[10:]}, CONFIG,
                                         output_path=tmp_path / "comp.png")
    assert (tmp_path / "comp.png").exists()
    plt.close(fig_comp)
    records = [
        {"role": "min_emit_x", "stored_objectives": {"norm_emit_x_m_rad": 3.4e-6}, "rerun_objectives": {"norm_emit_x_m_rad": 3.41e-6}},
        {"role": "min_emit_y", "stored_objectives": {"norm_emit_x_m_rad": 3.5e-6}, "rerun_objectives": {}},
    ]
    fig_verif = plot_pareto_verification_comparison(records, CONFIG, output_path=tmp_path / "verif.png")
    assert (tmp_path / "verif.png").exists()
    heights = [patch.get_height() for patch in fig_verif.axes[0].patches]
    assert np.isnan(heights).any() and 0.0 not in heights  # missing reruns are gaps, never zero
    plt.close(fig_verif)


def test_figures_require_configuration(sample_evaluation_results):
    with pytest.raises(TypeError, match="MoboConfig"):
        plot_pareto_front(sample_evaluation_results)


def test_figure_scope_and_cleanup(sample_evaluation_results, tmp_path):
    from mobo_linac.plotting import close_all_figures, figure_scope
    close_all_figures()
    with figure_scope(auto_close=True):
        plot_pareto_front(sample_evaluation_results, config=CONFIG)
        plot_objective_evolution(sample_evaluation_results, config=CONFIG)
        assert len(plt.get_fignums()) >= 2
    assert len(plt.get_fignums()) == 0


def test_noncanonical_configuration_figures(tmp_path):
    from tests.test_configuration_boundaries import noncanonical_config
    from mobo_linac.execution.mock import MockEvaluator
    from mobo_linac.requests import requests_for
    from mobo_linac.evaluation import create_evaluation_result
    config = noncanonical_config()
    mock = MockEvaluator(tmp_path, config=config)
    results = [create_evaluation_result(raw, config)
               for raw in mock.evaluate(requests_for([[v.nominal_value + 0.01 * i for v in config.design_variables] for i in range(6)]))]
    plt.close("all")
    for function, args in ((plot_pareto_front, {}), (plot_objective_evolution, {}), (plot_best_so_far, {})):
        function(results, config=config, **args)
    for function in (plot_constraint_diagnostics, plot_design_variable_heatmap, plot_parallel_coordinates):
        function(results, config)
    assert len(plt.get_fignums()) == 6
    plt.close("all")


def test_campaign_finalization_leaves_no_open_figures(tmp_path):
    from mobo_linac.campaigns.runner import MoboCampaignRunner
    from mobo_linac.execution.mock import MockEvaluator
    plt.close("all")
    MoboCampaignRunner(config=CONFIG, output_dir=tmp_path / "run", num_initial_samples=3, num_batches=0,
                       device="cpu", export_plots=True, evaluator=MockEvaluator(tmp_path)).run()
    assert plt.get_fignums() == []
