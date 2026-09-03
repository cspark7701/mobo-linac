"""
Unit tests for modularized plotting suite in mobo_linac.plotting.
"""

from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
import torch

from mobo_linac.evaluation import EvaluationResult
from mobo_linac.plotting import (
    plot_benchmark_comparison,
    plot_benchmark_feasibility_comparison,
    plot_best_so_far,
    plot_constraint_diagnostics,
    plot_constraint_violins,
    plot_design_variable_heatmap,
    plot_feasibility_rate,
    plot_gp_surrogate_slice,
    plot_hypervolume_comparison,
    plot_hypervolume_progress,
    plot_objective_evolution,
    plot_parallel_coordinates,
    plot_pareto_front,
    plot_pareto_front_3d,
    plot_pareto_front_comparison,
    plot_pareto_verification_comparison,
    plot_scalarized_objective_trace,
)
from mobo_linac.plotting.visualizations import (
    plot_pareto_front as compat_plot_pareto_front,
    plot_hypervolume_progress as compat_plot_hv_progress,
)


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
    """Tests 2D and 3D Pareto front plotting."""
    fig_2d = plot_pareto_front(sample_evaluation_results, output_path=tmp_path / "pareto_2d.png")
    assert isinstance(fig_2d, plt.Figure)
    assert (tmp_path / "pareto_2d.png").exists()
    plt.close(fig_2d)

    fig_3d = plot_pareto_front_3d(sample_evaluation_results, output_path=tmp_path / "pareto_3d.png")
    assert isinstance(fig_3d, plt.Figure)
    assert (tmp_path / "pareto_3d.png").exists()
    plt.close(fig_3d)


def test_convergence_plotting(sample_evaluation_results, tmp_path):
    """Tests convergence and hypervolume plotting routines."""
    history = [
        {"iteration": i, "feasible_hypervolume": 10.0 + i * 0.5, "all_point_hypervolume": 12.0 + i * 0.4}
        for i in range(10)
    ]
    fig_hv = plot_hypervolume_progress(history, output_path=tmp_path / "hv.png")
    assert isinstance(fig_hv, plt.Figure)
    assert (tmp_path / "hv.png").exists()
    plt.close(fig_hv)

    fig_evol = plot_objective_evolution(sample_evaluation_results, output_path=tmp_path / "evol.png")
    assert isinstance(fig_evol, plt.Figure)
    plt.close(fig_evol)

    fig_best = plot_best_so_far(sample_evaluation_results, output_path=tmp_path / "best.png")
    assert isinstance(fig_best, plt.Figure)
    plt.close(fig_best)

    fig_trace = plot_scalarized_objective_trace(sample_evaluation_results, output_path=tmp_path / "trace.png")
    assert isinstance(fig_trace, plt.Figure)
    plt.close(fig_trace)


def test_diagnostics_plotting(sample_evaluation_results, tmp_path):
    """Tests feasibility and constraint diagnostics plotting."""
    fig_feas = plot_feasibility_rate(sample_evaluation_results, output_path=tmp_path / "feas.png")
    assert isinstance(fig_feas, plt.Figure)
    assert (tmp_path / "feas.png").exists()
    plt.close(fig_feas)

    fig_diag = plot_constraint_diagnostics(sample_evaluation_results, output_path=tmp_path / "diag.png")
    assert isinstance(fig_diag, plt.Figure)
    plt.close(fig_diag)

    fig_viol = plot_constraint_violins(sample_evaluation_results, output_path=tmp_path / "viol.png")
    assert isinstance(fig_viol, plt.Figure)
    plt.close(fig_viol)


def test_parameters_plotting(sample_evaluation_results, tmp_path):
    """Tests design variable heatmaps and parallel coordinate plotting."""
    fig_hm = plot_design_variable_heatmap(sample_evaluation_results, output_path=tmp_path / "heatmap.png")
    assert isinstance(fig_hm, plt.Figure)
    assert (tmp_path / "heatmap.png").exists()
    plt.close(fig_hm)

    fig_pc = plot_parallel_coordinates(sample_evaluation_results, output_path=tmp_path / "parallel.png")
    assert isinstance(fig_pc, plt.Figure)
    assert (tmp_path / "parallel.png").exists()
    plt.close(fig_pc)


def test_comparative_and_verification_plotting(sample_evaluation_results, tmp_path):
    """Tests multi-phase comparison and verification bar plots."""
    results_dict = {
        "Phase 2 (Unconstrained)": sample_evaluation_results[:10],
        "Phase 3 (Constrained)": sample_evaluation_results[10:],
    }
    fig_comp = plot_pareto_front_comparison(results_dict=results_dict, output_path=tmp_path / "comp.png")
    assert isinstance(fig_comp, plt.Figure)
    plt.close(fig_comp)

    records = [
        {"role": "Min emit_x", "stored_emit_x_m_rad": 3.4e-6, "rerun_emit_x_m_rad": 3.41e-6},
        {"role": "Min emit_y", "stored_emit_x_m_rad": 3.5e-6, "rerun_emit_x_m_rad": 3.52e-6},
    ]
    fig_verif = plot_pareto_verification_comparison(records, output_path=tmp_path / "verif.png")
    assert isinstance(fig_verif, plt.Figure)
    assert (tmp_path / "verif.png").exists()
    plt.close(fig_verif)


def test_visualizations_backward_compatibility(sample_evaluation_results, tmp_path):
    """Tests that legacy imports from mobo_linac.plotting.visualizations continue working."""
    fig1 = compat_plot_pareto_front(sample_evaluation_results)
    assert isinstance(fig1, plt.Figure)
    plt.close(fig1)

    fig2 = compat_plot_hv_progress([{"iteration": 1, "feasible_hypervolume": 10.0}])
    assert isinstance(fig2, plt.Figure)
    plt.close(fig2)
