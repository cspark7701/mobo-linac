# Task Completion Summary: Task 159

## Summary
Implemented TASK_33 from `docs/05_refactor_tasks/`. Publication tables and comparison reports are now built from one table model, with objective columns taken from the configuration, a single comparison report for any number of campaigns, and canonical verification records.

## Key Changes
- **Table model** (`metrics.latex.Table`): LaTeX (booktabs) and Markdown renderers with one escaping policy. Configured LaTeX labels and headers pass through as `RawLatex`; data cells are always escaped.
- **Objective columns** (`objective_columns`): configured LaTeX label, display unit (`latex_unit` converts μ and ·) and display scale, from the new shared `mobo_linac.display.objective_displays` (also used by `PlotSchema`). Without a configuration, recorded names and units are shown in SI.
- **Verification table**: one path through `verification_table` for LaTeX and the Markdown report, covering every recorded objective. Previously, archived 200 MeV records lost ε_y in the legacy branch; their aliases are now decoded on read. The verifier passes its configuration, and no longer writes the `stored_/rerun_emit_*` alias fields.
- **Robustness and Phase 1 case tables**: generic.
  - The scalarized suite records `objective_order`, `objective_units`, and `min_<objective>` / `min_feasible_<objective>` in SI.
  - Archived μm/MeV case columns are converted on read.
- **Campaign summary**: rows come from the configured objectives. `campaign_summary` drops the `min_emit_x_um`-style keys.
  - The knee target distance uses a new optional `ObjectiveConfig.target`, a display-only field set in both YAML files, instead of module constants.
  - `compute_target_distance(values, targets)` is generic.
- **Comparison report**: `generate_comparison_report(runs, names, verification, report_path, ...)` handles any number of campaigns and links only figures that exist next to the report. The previously advertised but never produced hypervolume comparison figure is no longer referenced. `read_comparison_runs` checks supplied observations against the recorded runs.
  - The phase-specific package functions were removed.
  - The production script keeps a thin three-phase helper used by the notebooks.
- **Removed**: the unused `generate_results_summary_latex_table`, and the `diff_emit_*_pct` compatibility fields of `compute_metric_deltas` (`objective_deltas_pct` is canonical).

## Acceptance Criteria
- [x] No hard-coded objective names, units, targets or phase counts remain in the reporting modules. A source-scan test checks this; alias decoding for archived files stays in the reader.
- [x] Verification tables include all configured objectives, including ε_y for archived alias records (tested).
- [x] Reports never reference a missing figure (tested with and without figure files).
- [x] Manuscript tables keep their labels. With the run configuration they show the configured labels and units; previously missing columns (ε_y) now appear.

## Validation Results
Relevant modules pass: LaTeX reporting (8), comparison (6), paper outputs (51), run data, scalarized suite, candidate evaluator, verification, robustness, docs sync, package layout, config, configuration boundaries and visualizations. No ASTRA campaign, push or remote query was performed.

## Scope and Limitations
- Table labels used by `docs/paper/main.tex` are unchanged.
- Number formatting follows the configured display units (4 decimals) or SI (6 significant digits) when no configuration is supplied.

## Status
Completed.
