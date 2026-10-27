# Task Completion Summary: Task 147

## Summary
Implemented TASK_21 from `docs/05_refactor_tasks/`. Scalarized suite cases are now configuration data with stable seed offsets. Aggregation uses the weights and seeds each case recorded, and the suite's hypervolume trajectory has a documented definition.

## Key Changes
- **Configuration**: `ScalarizedCaseConfig` (label, weights, seed_offset, description, optional LaTeX symbol) under `MoboConfig.scalarized_cases`, schema-validated with unique identifiers and seed offsets. The five published cases, with offsets 0/100/200/300/400, are defined in `configs/mobo_200MeV.yaml`, `publication_200MeV.yaml` and `publication.yaml`. Weight counts are checked against the objective count when a case is used, so changing objectives does not invalidate unrelated configurations.
- **Seeds**: a case's seed is `seed + seed_offset` (`case_offset` policy), independent of which cases are selected. Previously a case got `seed + 100 * position` within the selected subset. The `legacy_subset_index` policy reproduces archived runs; for the full suite in configured order the two policies give the same seeds.
- **Aggregation**:
  - Weights and seeds are read from each case's checkpoint; cases without them are rejected. The fabricated `[1/3, 1/3, 1/3]` weights for unknown cases were removed.
  - The summary records `weights` (JSON), `seed` and `w_<objective>` columns.
  - `hypervolume.csv` holds one cumulative union row per case boundary, replacing the arbitrary stride-8 sampling.
  - `cases_summary.json` is written atomically.
- **Removed constants**: `OPTION_2_CASES`, `get_option2_case(s)` and the dead "run all if empty" fallback. The CLI and scripts validate case ids against configuration, and argparse no longer duplicates case names.
- **LaTeX case table**: reads the recorded `weights` list, still accepting the archived `w_emit_x/w_emit_y/w_energy_spread` columns.

## Acceptance Criteria
- [x] One case alone and within the suite uses the same seed and gives identical results with the mock evaluator (tested).
- [x] No weight vectors or case names are hard-coded in package code.
- [x] Aggregated summaries report the weights stored in each case run.

## Validation Results
Relevant modules pass: scalarized suite (9, including the subset-vs-suite reproducibility test), scalarized BO, config, CLI, latex reporting, docs sync, production launcher, checkpoint/resume and configuration boundaries. No ASTRA campaign, push or remote query was performed.

## Scope and Limitations
Per-case extremum columns in the case summary remain those of the 200 MeV objectives until the generic tables of TASK_33.

## Status
Completed.
