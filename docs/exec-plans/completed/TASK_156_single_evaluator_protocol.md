# Task Completion Summary: Task 156

## Summary
Implemented TASK_30 from `docs/05_refactor_tasks/`. Campaigns, robustness and verification now share one request-based evaluator protocol, with three adapters and no capability probing.

## Key Changes
- **Protocol**: `execution.contracts.Evaluator.evaluate(requests, run_id, on_complete)`.
  - `evaluate_requests` calls only `evaluate`; completions a backend only returns are published when it returns.
  - Completion decoding is factored into one function, and the duplicated identity check was removed.
- **`ProcessPoolEvaluator`** (replaces `BatchEvaluator` and `evaluate_candidates_parallel`):
  - Takes the `MoboConfig` and keeps a persistent `ProcessPoolExecutor` (`close()` / context manager).
  - Every worker count runs process-isolated; `in_process=True` is an explicit opt-in.
  - Worker tasks are a typed `WorkerTask` dataclass, run by `run_worker_task`.
  - One `failure_result` factory covers worker exceptions and crashed or broken pools.
  - Results are asserted aligned rather than filtered.
  - Settings are validated explicitly instead of through ad-hoc `ExecutionConfig(...).validate()` calls.
- **`MockEvaluator`** (replaces `MockBatchEvaluator` and the `CliMockEvaluator` alias):
  - Reports configured objectives and every registered diagnostic channel; non-canonical channels get in-limit values derived from their defaults.
  - Identities go through `format_eval_id`.
  - `respond()` returns one raw result; `evaluate()` streams completions.
  - Results are labelled `execution_kind: "mock"`, and nothing is written relative to the working directory.
- **`FunctionEvaluator`**: adapts `function(request, run_id)` and always reports the submitted identities, which fixes the legacy path that turned task ids into run ids.
- **Single backend per study**:
  - `CandidateEvaluatorBase.evaluate_plan_parallel(tasks, evaluator=None, ...)` uses one backend; the default is the process pool from `default_evaluator()`.
  - `RobustnessEvaluator.evaluate_candidates(..., evaluator=None, run_id=...)`, `run_robustness_workflow(..., evaluator=None)` and `ParetoVerifier.verify_candidates(candidates, evaluator=None)` follow the same pattern.
  - Mock verification statuses come from the completions' `execution_kind`.
  - `custom_evaluator`, `request_evaluator`, `batch_evaluator`, `mock_evaluator` (verification), `mock_rerun_data_map` and the inline adapters were removed.
- **Removed `AstraRunner`**: it was used only by tests; the integration test now uses `ProcessPoolEvaluator`.
- **Template directory**: candidate studies default to the configured template directory, and the CLI `--template-dir` default is the configuration.
- **Test helpers**: `execution.requests.requests_for` builds plain requests. Tests use the new protocol, and `tests/evaluators.py` provides data and callable adapters.

## Acceptance Criteria
- [x] No `hasattr`/`getattr` capability probing of evaluators remains in execution code (source-scan test).
- [x] Robustness and verification accept the same evaluator object as campaigns (`MockEvaluator`, `ProcessPoolEvaluator`).
- [x] The mock evaluator supports any configured objective/diagnostic layout (non-canonical configuration test).
- [x] A crash in a single-worker run is reported as `WORKER_CRASH` exactly like a pooled run (tested with a hard worker exit).

## Validation Results
Relevant modules pass:
- parallel evaluation (14), mock evaluator (11), candidate evaluator (11)
- Pareto verification (19), robustness (18), evaluation result
- comparison, workdirs, parameter mapping, config
- checkpoint/resume (65), CLI (43), benchmark campaign
- scalarized BO and suite, package layout
- visualizations, configuration boundaries, logger, docs sync, GP/acquisition

No ASTRA campaign, push or remote query was performed.

## Scope and Limitations
- `ProcessPoolExecutor` remains the production backend. MPI/Ray/Dask backends can implement the same `evaluate` protocol (Phase 4).
- The benchmark runner keeps its `mock_evaluator` option, which injects any evaluator.

## Status
Completed.
