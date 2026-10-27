# Task Completion Summary: Task 168

## Summary
Fixed the two failing real-ASTRA integration tests, and the runner defect behind one of them. Removed the stale non-editable `mobo_linac` copy from the `linac-opt` environment.

## Root Causes
- **`test_parallel_evaluation.py::test_real_parallel_astra_evaluations`** ("Candidate 0 failed: None"):
  - One real ASTRA run takes about 280 s with two parallel workers on the reference host (measured: 281.4 s), and longer under load. The tests set a 300 s limit.
  - When the limit is hit, lume-astra's `tools.execute2` evaluates `ex.stdout + '\n'` on `subprocess.TimeoutExpired`, whose captured output is bytes. That raises `TypeError: can't concat str to bytes` before `why_error = "timeout"` is recorded.
  - As a result, every timeout was recorded as a generic `RUN_FAILED`, which is not retried and does not name the cause.
  - The test also asserted the pre-refactor lowercase status `"success"` and failed on the wrong key (`error` instead of `status`).
  - It also wrote into the repository's `results/` directory.
- **`test_astra_workdirs.py::test_real_astra_isolated_run`** (`KeyError: 'manifest'`): since TASK_157, results reference `manifest_path` instead of embedding the manifest. The test still read the removed inline key.

## Key Changes
- **`astra/runner.py`**: new `_run_simulation(astra_sim, timeout)` wraps the backend call. A failure raised after the time limit has elapsed becomes a `TimeoutError` chained to the backend error. Classification uses measured elapsed time and exception type, never message text. Timeouts are therefore reported as `TIMEOUT` (`ASTRA_TIMEOUT`) and follow the configured retry policy. Early failures keep their own type. No beam-physics or parsing behavior changed.
- **Tests**:
  - New `pytest --astra-timeout` option and `astra_timeout` fixture (default 1800 s) for integration tests that launch real ASTRA.
  - Both integration tests check the `SUCCESS` status and read parameters from the attempt manifest via `read_evaluation_manifest`.
  - The parallel test writes to `tmp_path`.
  - New unit test `test_backend_timeout_is_classified_as_timeout_despite_lume_astra_handler` drives the real lume-astra `execute2` with a sleeping subprocess and a 1 s limit. It asserts a `TIMEOUT` classification, and that a fast failure keeps its type.
- **Environment**: deleted `linac-opt/lib/python3.11/site-packages/mobo_linac/` (108 files from 2026-09-07; untracked by the installed editable distribution's RECORD). `import mobo_linac` and `mobo-linac` now resolve to `src/` from any directory.

## Validation Results
- `tests/test_astra_workdirs.py` and `tests/test_parallel_evaluation.py` unit tests: 34 passed.
- Real ASTRA: `test_real_astra_isolated_run` passed in 322 s and `test_real_parallel_astra_evaluations` passed in 337 s, run concurrently.

## Open Item
`execution.timeout_sec` is 30 s in `configs/mobo_200MeV.yaml` and `configs/publication_200MeV.yaml`, far below the measured run time of a single ASTRA simulation. Physical campaigns with those configurations will time out every evaluation (now correctly reported as `TIMEOUT`). The configuration was not changed here, because the campaign plan freezes its bytes. The limit should be set deliberately, for example from the Stage 1 pilot's p95 duration.

## Status
Completed.
