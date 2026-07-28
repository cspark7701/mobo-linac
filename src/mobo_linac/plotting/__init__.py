"""
Plotting and Visualization Module for mobo_linac.
"""

from mobo_linac.plotting.visualizations import (
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

__all__ = [
    "plot_hypervolume_progress",
    "plot_pareto_front",
    "plot_pareto_front_3d",
    "plot_objective_evolution",
    "plot_best_so_far",
    "plot_feasibility_rate",
    "plot_constraint_diagnostics",
    "plot_constraint_violins",
    "plot_design_variable_heatmap",
    "plot_parallel_coordinates",
    "plot_scalarized_objective_trace",
    "plot_gp_surrogate_slice",
    "plot_hypervolume_comparison",
    "plot_pareto_front_comparison",
    "plot_pareto_verification_comparison",
]
