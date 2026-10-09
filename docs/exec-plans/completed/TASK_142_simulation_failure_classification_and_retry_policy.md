# Task Completion Summary: Task 142

## Summary
Implemented TASK_16 from `docs/05_refactor_tasks/`. Simulation status is now typed from parser to manifest. Validity and failure categories are decided by one classifier, and retries depend on the outcome category. While doing this, a defect was found and fixed: the configured ASTRA timeout was never passed to lume-astra.

## Key Changes
- **`mobo_linac.status`** (new) holds:
  - `SimulationStatus`, which gains `RUN_FAILED`, `PROVENANCE_ERROR` and `WORKER_CRASH`;
  - `FailureCategory`, which gains `CORRUPTED_OUTPUT`, `PROVENANCE_FAILURE` and `WORKER_CRASH`;
  - the single `FAILURE_CATEGORY_BY_STATUS` table and `DEFAULT_RETRY_STATUSES`;
  - `decode_status`, which also accepts archived lowercase strings;
  - `classify_exception`. It uses exception types (`TimeoutExpired`/`TimeoutError`, floating-point errors, `FileNotFoundError`, decode errors) and the recorded run information (`why_error == "timeout"`, a run started without finishing). It never matches message substrings, so text such as "information" or "infeasible" no longer selects a category.
- **Parser**: classifies exceptions passed as objects. Exit-plane settings come only from configuration. `diagnostics` holds only the seven canonical channels; `z_final_m` and particle counts go to a separate `telemetry` field. The `z_final`, `z_stop_m` and objective-copy aliases are no longer emitted.
- **Runner**:
  - Status travels as `SimulationStatus` values, and provenance failures are `PROVENANCE_ERROR`.
  - Telemetry is written to the manifest.
  - **Timeout fix**: lume-astra's `run()` calls `run_astra(timeout=None)`, so `execution.timeout_sec` was never enforced. The runner now calls `run_astra(timeout=...)` when the runtime provides it.
- **Evaluation**:
  - `create_evaluation_result` maps non-success statuses through the table. For successful simulations it checks measurements with `valid_channel_measurement` and feasibility with `ConstraintEvaluator`, and the reason lists the violated channels.
  - Transmission below `min_transmission` is now ordinary `INFEASIBLE_BEAM`. `INVALID_TRANSMISSION` is reserved for values outside [0, 1].
  - Complete beam loss (`CHARGE_ZERO`) is `EMPTY_OUTPUT`.
  - The NaN check covers configured objectives and canonical channels only, not auxiliary fields.
  - `EvaluationResult` gains a `telemetry` field; archived diagnostic aliases are decoded on read.
- **Retry policy**: `ExecutionConfig.retry_statuses` defaults to `TIMEOUT`, `WORKER_CRASH`, `PROVENANCE_ERROR` and `UNHANDLED_EXCEPTION`, is schema-validated, and checkpoint comparison fills it in for older checkpoints. Workers retry only listed statuses, and attempt history records `retried`. Deterministic outcomes such as premature beam loss run once.
- **Statuses elsewhere**: the mock evaluator, verification mock adapter, audit, CSV reader (the invented `NONE` category is now `SUCCESS`/`UNHANDLED_EXCEPTION`) and the simulation guide use the typed statuses; the guide documents the status-to-category and retry table.

## Acceptance Criteria
- [x] No status string literals or message-substring classification remain in the parser, runner or evaluation.
- [x] A premature-loss candidate is evaluated once with `retries > 0`; a timeout is retried up to the budget.
- [x] Archived lowercase manifest statuses and legacy telemetry aliases decode correctly.
- [x] Each status category and the retry policy have focused regression tests.

## Validation Results
- New and updated tests cover:
  - type-based classification, including misleading messages;
  - runtime timeout and unfinished-run records;
  - telemetry separation;
  - retry policy (premature loss once, timeout three times);
  - category changes for below-threshold and zero transmission.
- Full unit suite run file by file (integration tests excluded); results are recorded in the commit validation.
- No production ASTRA campaign, push or remote workflow query was performed.

## Scope and Limitations
- Physics thresholds and the exit-plane values are unchanged. Reported category counts change only where the old category was wrong: below-threshold transmission was labelled `INVALID_TRANSMISSION`, a timeout reported only in message text was undetected, and zero-charge runs were counted as valid.
- Moving `z_stop_m`/`z_loss_tolerance_m` from `execution` to a lattice section is deferred to TASK_27.

## Status
Completed.
