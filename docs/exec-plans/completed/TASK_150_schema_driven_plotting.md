# Task Completion Summary: Task 150

## Summary
Implemented TASK_24 from `docs/05_refactor_tasks/`. Every figure now takes its labels, display units, scales and constraint limits from the configuration. Each figure has a single code path, and campaign exports no longer leave figures open.

## Key Changes
- **Display metadata**:
  - `DiagnosticChannel` gains `label`, `display_unit` and `display_scale` (mm, mrad, MeV, %).
  - `DesignVariableConfig.label`, `ObjectiveConfig.label` and `ObjectiveConfig.display_unit` are optional.
  - The 200 MeV configurations carry the previous LaTeX labels.
  - `PlotSchema` (in `plotting.common`) derives axis specifications for design variables and objectives (reporting scale, direction) and constraint channels with lower/upper limits from the *active* profile. Figures without a configuration raise.
- **One path per figure**:
  - The hard-coded three-objective/six-variable branches and the module-level label lists were removed.
  - Constraint diagnostics and violin plots draw every channel, including transmission (previously never plotted), with the configured limits. The fixed 1.0 mm/mrad and 195/205 MeV lines are gone.
  - `plot_best_so_far` follows each objective's direction.
- **Pareto**: projections cover every objective pair and highlight the actual non-dominated feasible front, drawn by the shared `pareto_mask`; the 3D figure labels only that front. `plot_pareto_front_comparison` was replaced by `plot_pareto_front_overlay(results_by_label, config)`.
- **Hypervolume comparison**: `plot_hypervolume_comparison` (which crashed on tracker histories) was replaced by `plot_hypervolume_histories`, which accepts trackers, frames or record lists. Manuscript figures in `plotting.publication` keep their names and use `PlotSchema` labels.
- **Verification bars**: every configured objective is shown, and missing measurements are NaN gaps; previously they were drawn as 0.0.
- **Figure lifecycle**: `finalize_campaign` exports inside `figure_scope`, so mock suites end with zero open figures.
- **Python version**: `Path | None` annotations in `plotting/publication.py` became `Optional[Path]`, compatible with the declared Python ≥3.9.
- **Compatibility shim**: `plotting.visualizations` is reduced to a re-export of `mobo_linac.plotting`; internal callers import the package directly.

## Acceptance Criteria
- [x] No numeric constraint limit or objective/variable label literal remains in plotting code.
- [x] A stringent profile draws the stringent limits, and transmission appears in diagnostics (tested).
- [x] Public plotting functions are exercised with a non-canonical configuration (five variables, four objectives).
- [x] Figure count is zero after a full mock campaign export (tested).

## Validation Results
Relevant modules pass: visualizations (11), paper outputs (51), benchmark, benchmark campaign, CLI (43), comparison, package layout, config, scalarized suite, checkpoint/resume and configuration boundaries. No ASTRA campaign, push or remote query was performed.

## Scope and Limitations
- Figure filenames and manuscript styles are unchanged.
- The notebooks still call the earlier plotting signatures; they are rewritten as thin clients in TASK_36.
- The manuscript verification bar chart keeps its archived legacy-record branch until TASK_33.

## Status
Completed.
