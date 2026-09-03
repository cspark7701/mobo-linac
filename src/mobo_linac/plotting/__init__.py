"""
Plotting and Visualization Module for mobo_linac.

Provides modular plotting submodules:
  - pareto: 2D/3D Pareto fronts & multi-phase comparisons
  - convergence: Hypervolume progression, objective evolution, benchmarks
  - diagnostics: Feasibility rate, constraint diagnostics, violin plots, GP slices
  - parameters: Design variable heatmaps & parallel coordinates
  - common: Labels, scales, figure save utilities, and memory cleanup contexts
"""

from mobo_linac.plotting.common import (
    DESIGN_VAR_LABELS,
    DESIGN_VAR_SHORT_LABELS,
    EMIT_SCALE,
    ENERGY_SCALE,
    OBJ_LABELS,
    close_all_figures,
    figure_scope,
    save_fig,
)
from mobo_linac.plotting.convergence import (
    plot_benchmark_comparison,
    plot_benchmark_feasibility_comparison,
    plot_best_so_far,
    plot_hypervolume_comparison,
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
    plot_pareto_front_comparison,
    plot_pareto_verification_comparison,
)

__all__ = [
    # Pareto
    "plot_pareto_front",
    "plot_pareto_front_3d",
    "plot_pareto_front_comparison",
    "plot_pareto_verification_comparison",
    # Convergence
    "plot_hypervolume_progress",
    "plot_hypervolume_comparison",
    "plot_objective_evolution",
    "plot_best_so_far",
    "plot_scalarized_objective_trace",
    "plot_benchmark_comparison",
    "plot_benchmark_feasibility_comparison",
    # Diagnostics
    "plot_feasibility_rate",
    "plot_constraint_diagnostics",
    "plot_constraint_violins",
    "plot_gp_surrogate_slice",
    # Parameters
    "plot_design_variable_heatmap",
    "plot_parallel_coordinates",
    # Common
    "save_fig",
    "figure_scope",
    "close_all_figures",
    "EMIT_SCALE",
    "ENERGY_SCALE",
    "DESIGN_VAR_LABELS",
    "OBJ_LABELS",
]
