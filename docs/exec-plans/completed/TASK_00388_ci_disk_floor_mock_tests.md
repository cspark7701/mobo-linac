# Task Completion Summary: Task 00388

## Summary
Fixed the remote GitHub Actions failure of CI run 43503352797 on commit `78f53f8`, with the user's approval to read the remote logs. All three `test` jobs (Python 3.10, 3.11 and 3.12) failed. Each had the same two tests failing, with `RuntimeError: Insufficient disk space; preserve evidence and pause.`:
- `tests/test_convergence_matrix.py::test_mock_prepare_run_resume_and_analysis`
- `tests/test_convergence_step_test.py::test_mock_prepare_run_resume_and_analysis`

`lint` and `wheel-smoke` passed. Coverage reached 100 % in the failing jobs, and the remaining 1,137 tests passed.

## Cause
`scripts/evaluate_convergence_matrix.py` and `scripts/evaluate_convergence_step_test.py` write `minimum_free_disk_GiB: 100` into every frozen spec, mock specs included. `execute()` refuses to start a phase below that free space. GitHub-hosted runners have about 14 GB free, so the mock runs stopped at the guard. The same happens on any machine with less than 100 GiB free, including this one (22 GB free). This was a test-environment dependence, not a code regression.

## Key Changes
- **`tests/test_convergence_matrix.py`.** After `prepare()`, a new helper `no_disk_floor()` sets `minimum_free_disk_GiB` to 0 in the mock spec file.
- **`tests/test_convergence_step_test.py`.**
  - `_mock_step2()` sets the floor to 0 in the convergence-matrix mock spec, where it already edits that spec.
  - The step-test mock spec is set to 0 after `prepare()`.
- These follow the convention of the round-6 tests (`test_revision_round6.py`, `test_revision_round6_recovery.py`).
- The production disk guard and the 100 GiB floor of real campaigns are unchanged. No script, configuration or result changed.

## Validation Results
- With a pytest plugin reporting 10 GiB free, matching a CI runner, the two test modules pass (17 passed). With the fix stashed they fail exactly as in CI (2 failed, 15 passed).
- On this machine's real disk (22 GB free) the two modules pass with the fix (17 passed).
- The tests now run to completion. They emit numpy "Mean of empty slice" `RuntimeWarning`s, which originate in numpy, not `mobo_linac`, so CI's warnings-as-errors filters do not apply.
- `ruff check` passed on both files.
- `ruff check src scripts tests tools` and `scripts/verify_docs_sync.py` passed.
- A full local run of the CI test command (`pytest -m "not integration" --cov=mobo_linac --cov-fail-under=100`), started before the fix, reproduced the remote result exactly: the same two tests failed with the disk-space error, 1,138 passed, and coverage was 100 %. The fixed modules then passed; the full suite was not rerun after the fix.

## Status
Completed and committed locally. Not pushed; the remote CI result after the push is not yet verified.
