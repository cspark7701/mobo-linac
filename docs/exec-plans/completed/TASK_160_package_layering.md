# Task Completion Summary: Task 160

## Summary
Implemented TASK_34 from `docs/05_refactor_tasks/`. The package now has documented, test-enforced layers and no import cycles. Function-level package imports remain only where they are documented exceptions, and the campaign engine imports without Matplotlib.

## Key Changes
- **Layers** (README, enforced by `test_package_layers_are_respected`): core → `io` → `models`/`acquisition`/`metrics` → `astra`/`execution`/`plotting` → `campaigns`/`robustness`/`verification` → `cli`.
- **Core modules**, created or relocated to break the cycles:
  - `utils/durable.py` (from `io/durable.py`), used by configuration exports.
  - `requests.py` (from `execution/requests.py`), so the ASTRA runner no longer imports the execution package.
  - `conventions.py`: `reporting_metadata` and `validate_campaign_compatibility`, moved out of `metrics.reporting`, which re-exports them; I/O and metrics both use them.
  - `perturbations.py`: the perturbation specification and channels, moved out of `robustness.evaluator`, which re-exports them, so the configuration validates its `perturbations` section without importing robustness.
- **Run-artifact writer**: `RunArtifactWriter` and `save_evaluation_results` moved to `metrics.exports`, since they combine I/O and metrics. `io.artifacts` keeps only the completion marker (`write_completion_marker`, `validate_run_completion`).
- **Imports**:
  - 40 function-level package imports were hoisted to module level.
  - The remaining lazy imports are the CLI subcommands (workflow on demand) and plotting, imported only in the figure export paths; `campaign_figures()` now imports plotting lazily.
  - Unused imports were removed across the package and scripts.
- **Implicit run discovery**: `discover_candidate_source` now announces (warning and log) which run it auto-selects when no input is given.

## Acceptance Criteria
- [x] No function-level `from mobo_linac...` imports remain except the documented exceptions (tested).
- [x] `import mobo_linac.campaigns` (and robustness and verification) does not import Matplotlib (subprocess test).
- [x] The layer-contract test passes.

## Validation Results
The full test suite passes (all 39 test files) after the relocations and the import cleanup. Tests that patched names now bound at module level (benchmark runner, campaign plotting) patch the binding module. No ASTRA campaign, push or remote query was performed.

## Scope and Limitations
- `metrics.reporting` and `robustness.evaluator` re-export the relocated names.
- `mobo_linac.io` no longer exports the run-artifact writer; it is in `mobo_linac.metrics`.

## Status
Completed.
