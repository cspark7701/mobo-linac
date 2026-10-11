# Task Completion Summary: Task 178

## Summary
Fixed the GitHub Actions failure `tests/test_pareto_verification.py::test_original_and_rerun_audits_link_exact_attempts - FileNotFoundError: ASTRA executable 'astra' not found`. The cause also broke 16 other unit tests on CI.

Remote workflow runs were not queried (AGENTS.md). The failure was reproduced in a clean clone with no ASTRA anywhere: `bin/` is git-ignored, `$ASTRA_BIN` was unset, and `bin/` was removed from `PATH`.

## Diagnosis
- Executable resolution accepts the configured `simulation.executable`, then `$ASTRA_BIN`, then `PATH`, and only if the candidate is an executable file.
- **Tests that replace the simulator still resolve an executable first:**
  - the `recording_astra_project` fixture set `$ASTRA_BIN` to a stub file without the executable bit, so it was skipped;
  - the `temp_project` fixtures of `test_astra_workdirs.py` and `test_parallel_evaluation.py` provided no executable at all;
  - `test_mock_campaign_and_analysis_do_not_initialize_astra` finally calls the resolver itself.
- **Why it passed locally:** on the maintainer's host these tests found the real `bin/astra`, both through the configured path and on `PATH`. The earlier clean-clone reproductions (TASK_171, TASK_173) inherited that `PATH`, so they did not expose this failure.
- **Affected on CI:** 17 tests.

## Key Changes
- `tests/conftest.py`:
  - `write_stub_executable()` writes an executable placeholder file.
  - New `astra_stub_executable` fixture puts a stub on `$ASTRA_BIN`.
  - `recording_astra_project` now uses an executable stub.
- `tests/test_astra_workdirs.py`, `tests/test_parallel_evaluation.py`: `temp_project` requests `astra_stub_executable`.
- `tests/test_package_layout.py`: the subprocess of `test_mock_campaign_and_analysis_do_not_initialize_astra` receives an executable stub through `$ASTRA_BIN`.
- The resolver and the physics are unchanged.

## Validation Results
- Clean clone, no ASTRA available, CI command (`pytest -m "not integration" --cov=mobo_linac --cov-fail-under=85`): 762 passed, 37 skipped, 0 failed; coverage 92.91 %. Before the fix: 17 failed.
- Working tree with the real `bin/astra` present: the five affected files give 81 passed.
- `ruff check tests` passes.

## Notes
`tools/check_github_actions.sh` runs in the working tree, where the configs point to the existing `bin/astra`, so it cannot detect a dependence on a local ASTRA. Only a fresh checkout without ASTRA reproduces CI.

## Status
Completed.
