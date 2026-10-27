# Task Completion Summary: Task 163

## Summary
Implemented TASK_37 from `docs/05_refactor_tasks/`. The test suite now has one pytest configuration with package warnings as errors, module-named test files without `sys.path` edits, and a single scripted evaluator double. CI adds lint, a Python version matrix matching the declared range, a coverage floor and a wheel smoke test.

## Key Changes
- **One pytest configuration**: `pytest.ini` is removed; the configuration is in `pyproject.toml` only.
  - `filterwarnings` turns `SyntaxWarning` and every `DeprecationWarning`, `RuntimeWarning` and `UserWarning` raised by `mobo_linac` into errors. Third-party warnings are reported but do not fail.
  - Package warnings that tests expect are asserted with `pytest.warns`: a truncated journal tail during repair. The dry-run CLI test no longer triggers implicit run discovery.
- **Lint**: `ruff` is configured in `pyproject.toml` (pyflakes, syntax errors, invalid escape sequences; `__init__` re-exports exempt). All findings were fixed, mostly unused imports in tests, plus one real `F821` (an annotation now under `TYPE_CHECKING`).
- **Test organization**:
  - `test_task10_comparison.py` was renamed to `test_comparison_report.py`.
  - Task-number references were removed from test docstrings.
  - The `sys.path` manipulation in `test_docs_sync.py` and `test_comparison_report.py` was removed; the pytest `pythonpath` configuration covers it.
- **One evaluator double**: `tests/evaluators.py::ScriptedEvaluator` (records submissions; interrupts by batch index or first identity; out-of-order completion; callback-error swallowing; batch hook; runtime override) replaces `InterruptingStreamEvaluator`, two `InterruptedEvaluator`s, `SwallowingEvaluator`, `ParallelTimingEvaluator`, `RecordingEvaluator` and `InterruptingEvaluator`. The data and callable adapters live in the same module.
- **CI** (`.github/workflows/ci.yml`):
  - `lint` runs ruff.
  - `test` runs Python 3.10/3.11/3.12 with `pip install -e .[dev]` only (no separate Git installs). It checks the version against the distribution metadata instead of a literal, checks docs sync, and runs pytest with warnings-as-errors and a coverage floor of 85% (measured locally at 93%).
  - `wheel-smoke` builds the wheel, installs it into a fresh virtual environment and runs the CLI outside the source tree, including a check that the campaign engine imports without Matplotlib.
- **Python range**: `requires-python` is now `>=3.10`, matching the tested matrix and the dependencies. The `dev` extra gains ruff, build and notebook execution tools. The README badge and INSTALL were updated.

## Acceptance Criteria
- [x] One pytest configuration; the full suite passes with package warnings as errors.
- [x] No test file name contains a task number, and no test edits `sys.path`. The one remaining `sys.path` expression is inside a subprocess script that tests running outside the source tree.
- [x] Each evaluator double is defined once. The worker-level `run_astra_eval` stubs in the parallel tests are per-test simulator behaviors, not evaluator doubles.
- [x] CI runs lint, tests across the declared Python range and a wheel smoke test. The workflow was validated locally (YAML parse, smoke commands); no remote run was queried.

## Validation Results
The full suite passes under the new warning policy (all test files). Ruff reports no findings. Coverage is 93%. No push or remote workflow query was performed.

## Scope and Limitations
Configuration data is not yet packaged into the wheel, so the smoke test passes the configuration path explicitly; TASK_38 addresses packaging.

## Status
Completed.
