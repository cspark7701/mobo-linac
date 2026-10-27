# Task Completion Summary: Task 140

## Summary
Read `AGENTS.md` and `README.md`, then reviewed the whole repository after the first `05_refactor_tasks` collection (Tasks 01–14) had been implemented at commit `41fe16a`. The review covered every module in `src/mobo_linac/`, the scripts, configurations, tests, CI workflow, packaging files, notebooks and documentation. The refactor opportunities found are recorded as TASK_15–TASK_40 in `docs/05_refactor_tasks/`.

## Key Changes
- Created `docs/05_refactor_tasks/TASK_15_...md` through `TASK_40_...md`, continuing the collection's numbering. Each task has evidence with file/line references, problem and impact, proposed refactor, acceptance criteria, validation plan, scope/compatibility and relationship to previous work.
- Updated `docs/05_refactor_tasks/README.md` and `TASK_ORDER.md` with a second-review section: priorities, dependency order, the most consequential findings and implementation rules.
- P1 tasks (15–24) cover:
  - mandatory configuration instead of silent 200 MeV defaults;
  - typed simulation status and category-aware retries;
  - one Pareto/knee selection service;
  - a configuration-driven robustness model;
  - a single hypervolume implementation and reference policy;
  - benchmark aggregation fixes (objective extrema are always empty);
  - scalarized-suite seed reproducibility;
  - campaign defaults and the `run-validation` output-directory defect;
  - GP/acquisition tuning methodology (in-sample R², mislabelled "LOO");
  - plots drawn from the configured constraints instead of fixed limit values.
- P2 tasks (25–40) cover durable I/O, incremental artifacts and journal, configuration consolidation, the checkpoint schema, runner decomposition, the evaluator protocol, ASTRA execution and portable binaries, surrogate settings, reporting tables, package layering, logging, CLI/scripts/notebooks, tests/CI, packaging, removal of shims and dead code, and repository/documentation hygiene.

## Acceptance Criteria
- [x] Read repository instructions and README before reviewing implementation files.
- [x] Saved numbered refactor proposals under `docs/05_refactor_tasks/` without renumbering the existing tasks.
- [x] Kept the new proposals separate from the completed TASK_01–14 records.
- [x] Saved this completion summary with the next available number, TASK_140.
- [x] Left runtime code, beam physics, configs, simulation outputs and publication artifacts unchanged.

## Validation Results
- Checked that the new tasks are numbered continuously (15–40), that each contains the required sections, that dependencies only point to earlier tasks, and that every relative link in the new tasks, README and TASK_ORDER resolves.
- Ran spot checks supporting specific findings: compiling `config.py` with `-W error` gives `SyntaxError: invalid escape sequence '\s'`; `best_norm_emit_*` columns are read in `campaigns/analysis.py` but never written; several public functions have no callers; there are 397 test functions.
- Ran no production ASTRA evaluations, full pytest run, remote workflow checks, commits or pushes. This was a source review and documentation task only.

## Status
Completed (review and proposals only; the 26 proposed refactors remain unimplemented).
