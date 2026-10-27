# Task Completion Summary: Task 165

## Summary
Implemented TASK_39 from `docs/05_refactor_tasks/`. Compatibility layers whose migrations are complete and unused public helpers were removed. Internal and test callers now use the canonical APIs. The one remaining user-facing shim (the deprecated CLI input aliases) names its removal version, and a test prevents new re-export shims.

## Key Changes
- **Removed re-export shims** (callers migrated):
  - `plotting/visualizations.py` → `mobo_linac.plotting`.
  - `reporting_metadata` and `validate_campaign_compatibility` via `metrics.reporting` → `mobo_linac.conventions`.
  - Perturbation types via `robustness.evaluator` → `mobo_linac.perturbations` (still exported by the `mobo_linac.robustness` package).
  - Durable helpers via `astra.workdir` → `utils.durable`.
  - `mobo_linac.cli.MockEvaluator` → `mobo_linac.execution.MockEvaluator`.
- **Removed wrappers and duplicate aliases**:
  - `normalize_objectives_model` (an alias of `normalize_objectives_physical`).
  - `compute_file_sha256` (wrapped `file_sha256`).
  - `export_phase1_cases_latex_table` (wrapped `generate_phase1_cases_latex_table`; the suite, paper pipeline and `run_full_production.sh` now call the generator).
- **Removed unused code**: `HypervolumeTracker.save_csv`/`load_history` (superseded by `RunArtifactWriter`) and `close_all_figures`.
- **Already resolved by earlier tasks**, verified absent: `CliMockEvaluator`/`MockBatchEvaluator`, `AstraRunner`, `ProposalResult` tuple emulation, `CheckpointState` dict emulation, the CLI fallback dispatch, the suite empty-target fallback, the `z_target_m` branch, `run_campaign_variant`, `generate_results_summary_latex_table`, `find_pareto_csv`, `DEFAULT_*_SCALES` and the private plotting aliases.
- **Deprecations**: `--history-path` and `--pareto-csv` warn that they will be removed in 1.1.0. CHANGELOG has an `[Unreleased]` section listing the removals and their replacements.
- **Guard**: `test_package_modules_carry_no_reexport_shims` forbids `noqa: F401` re-exports outside package `__init__` files. Ruff (TASK_37) reports zero unused imports in `src/`, `scripts/` and `tests/`.
- **Kept on purpose**:
  - `transform_to_model_space`/`transform_to_physical_space`: a named inverse pair whose shared implementation is a sign involution.
  - `export_verification_latex_table`: supplies a default path and is used by `reproduce_paper.sh`.
  - Archived-artifact compatibility readers (legacy objective aliases, version-1 perturbation files, `legacy_subset_index` seeds), which are needed to read published results.

## Acceptance Criteria
- [x] No internal module imports `plotting.visualizations`, `CliMockEvaluator` or other shims (the modules no longer exist; guarded by test).
- [x] Each remaining shim emits a `DeprecationWarning` with its removal version (CLI input aliases, 1.1.0).
- [x] Lint reports zero unused imports in `src/` and `scripts/`.

## Validation Results
The affected test files pass: benchmark, reporting metrics, hypervolume, Pareto verification, scalarized suite and BO, visualizations, robustness, comparison report, package layout, paper outputs, candidate evaluator, LaTeX reporting, config, logger, notebooks, docs sync and production launcher. Package `DeprecationWarning`s are errors under the pytest configuration. Ruff is clean.

## Status
Completed.
