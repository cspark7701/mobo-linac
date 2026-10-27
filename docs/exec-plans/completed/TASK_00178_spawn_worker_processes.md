# Task Completion Summary: Task 173

## Summary
ASTRA worker pools now start their workers with the `spawn` method instead of the Linux default `fork`. The parent process holds PyTorch and BLAS threads. Forking it can deadlock a child, and Python 3.12 warns about this (`DeprecationWarning: This process ... is multi-threaded, use of fork() may lead to deadlocks in the child`). Physics, evaluation results and the worker protocol are unchanged.

## Key Changes
- `src/mobo_linac/execution/parallel.py`:
  - New module constant `DEFAULT_START_METHOD = "spawn"`.
  - `ProcessPoolEvaluator(mp_context=None)` reads the constant when the evaluator is constructed and always passes an explicit context to `ProcessPoolExecutor`.
  - An unknown start method is rejected.
  - Workers already received everything they need in the serialized `WorkerTask` and did not rely on inherited state. The worker modules do not log and do not change the environment.
- Tests:
  - Some tests substitute a local stub simulator, which the workers must inherit; only those opt into `fork`. These are the `evaluate_candidates` helper and `test_batch_evaluator_class` in `tests/test_parallel_evaluation.py` (`PATCHED_WORKER_CONTEXT`), and the `recording_astra_project` fixture in `tests/conftest.py` (patches `DEFAULT_START_METHOD`).
  - New `test_workers_spawn_by_default_and_run_in_a_fresh_interpreter` asserts that production pools spawn and run work in a separate process.
  - New `test_unknown_start_method_is_rejected`.
- `pyproject.toml`:
  - Ignores Python's fork warning by exact message, for the stub-simulator tests only. The comment points to the test that guards the production default.
  - The `torch.jit.script` deprecation filter now also matches `FutureWarning`, the category newer torch releases use.
- `README.md`: the evaluator description mentions spawned workers.

## Validation Results
- Python 3.12 with current packages, full unit suite: 762 passed, 37 skipped, 1 warning. Before the change it reported 22 warnings.
  - The remaining warning is botorch 0.18 reporting that `ninja` is not installed for its fused qLogEHVI extension, so it uses its pure-Python implementation. It comes from the environment.
- Python 3.11 affected files (`test_parallel_evaluation`, `test_pareto_verification`, `test_candidate_evaluator`, `test_config`, `test_docs_links`): 144 passed.
- Real ASTRA through spawned workers: `test_real_parallel_astra_evaluations` passed (197 s), with multiprocessing deprecation warnings treated as errors.
- Ruff and `scripts/verify_docs_sync.py` pass.

## Status
Completed.
