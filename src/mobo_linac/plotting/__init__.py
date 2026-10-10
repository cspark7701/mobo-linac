"""
Plotting and Visualization Module for mobo_linac.

Every figure takes labels, display units, scales and constraint limits from the
configuration (``PlotSchema``):
  - pareto: pairwise projections, 3D view, front overlays, verification bars
  - convergence: hypervolume progress/histories, objective evolution, benchmarks
  - diagnostics: feasibility rate, constraint channels with active limits, GP slices
  - parameters: design-variable correlation and parallel coordinates
  - publication: manuscript figures from recorded run directories
"""

from mobo_linac.plotting.common import (
    PlotSchema,
    figure_scope,
    save_fig,
)
from mobo_linac.plotting.convergence import (
    plot_benchmark_comparison,
    plot_benchmark_feasibility_comparison,
    plot_best_so_far,
    plot_hypervolume_histories,
    plot_hypervolume_progress,
    plot_objective_evolution,
    plot_scalarized_objective_trace,
)
from mobo_linac.plotting.diagnostics import (
    plot_constraint_diagnostics,
    plot_constraint_violins,
    plot_feasibility_rate,
    plot_gp_surrogate_slice,
)
from mobo_linac.plotting.parameters import (
    plot_design_variable_heatmap,
    plot_parallel_coordinates,
)
from mobo_linac.plotting.pareto import (
    plot_pareto_front,
    plot_pareto_front_3d,
    plot_pareto_front_overlay,
    plot_pareto_verification_comparison,
)

__all__ = [
    "plot_pareto_front",
    "plot_pareto_front_3d",
    "plot_pareto_front_overlay",
    "plot_pareto_verification_comparison",
    "plot_benchmark_comparison",
    "plot_benchmark_feasibility_comparison",
    "plot_best_so_far",
    "plot_hypervolume_histories",
    "plot_hypervolume_progress",
    "plot_objective_evolution",
    "plot_scalarized_objective_trace",
    "plot_constraint_diagnostics",
    "plot_constraint_violins",
    "plot_feasibility_rate",
    "plot_gp_surrogate_slice",
    "plot_design_variable_heatmap",
    "plot_parallel_coordinates",
    "PlotSchema",
    "figure_scope",
    "save_fig",
]
