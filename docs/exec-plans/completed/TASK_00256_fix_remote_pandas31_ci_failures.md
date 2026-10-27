# Task Completion Summary: Task 251

## Summary
Inspected actual remote GitHub Actions job logs, reproduced the failing pandas version locally, and fixed CSV-loading deprecations while preserving exact floating-point round trips. The full local CI-equivalent suite now passes with pandas 3.1.0.

## Remote Diagnosis
Reviewed [CI run 40301199186](https://github.com/cspark7701/mobo-linac/actions/runs/40301199186), for main commit `eca310a3a5cfc66eba6021255cb78e1cc66a5f32`:

- Lint failed with the five unused-import/assignment findings already fixed locally in Task 249.
- Python 3.11 job `121499233070` and Python 3.12 job `121499233038` installed pandas **3.1.0**. Both had **14 failures and five notebook-fixture errors**, all reporting `Pandas4Warning` for the deprecated `read_csv(float_precision="round_trip")` argument. The package warning policy correctly treated the caller-attributed warning as an error.
- Python 3.10 job `121499233054` installed pandas **2.3.3** and passed: **821 passed, 42 skipped, 2 deselected**. The wheel smoke job also passed.
- These remote pandas failures differ from Task 249's separately reproduced local Jupyter-kernel environment failure. The prior notebook-interpreter fix remains valid, but it alone did not resolve the actual remote CSV-loading errors.
- The installed gh 2.45 client returned empty output for `gh run view --log-failed`; direct read-only `gh api repos/cspark7701/mobo-linac/actions/jobs/<job-id>/logs` requests provided the complete job logs. Raw log copies remain under `/tmp/mobo_remote_ci_*`.

## Key Changes
- `src/mobo_linac/io/results.py`: load CSV fields as text, retain pandas missing-value recognition, then parse schema-defined numeric columns with Python float conversion. This avoids the deprecated argument and retains exact binary64 values rather than relying on pandas' default numeric parser. Numeric columns include configured design/objective names and aliases, model values, diagnostics, particle telemetry and runtime.
- Replaced legacy-header `DataFrame.rename(inplace=True)` with assignment of the returned frame. New warning-as-error precision tests exposed this additional pandas 3.1 deprecation.
- `tests/test_checkpoint_resume.py`: use explicit float converters for the Pareto fields whose exact equality the mixed-objective campaign test checks, replacing its remaining deprecated precision argument.
- `tests/test_result_serialization.py`: added modern/legacy CSV regressions asserting exact float bits, including signed zero, subnormal values, long decimals, physical/model outcomes, diagnostics and runtime, with all reader warnings promoted to errors. Existing missing-data, status, schema and metadata tests remain active.

## Acceptance Criteria
- [x] Actual remote job failures are identified from their logs rather than inferred from local tests.
- [x] The pandas 3.1 CSV-loading failure is reproduced before applying the fix.
- [x] The reader no longer relies on deprecated precision or in-place rename arguments.
- [x] Exact numeric round-tripping and legacy headers are covered.
- [x] Full local tests and the unchanged coverage threshold pass with the remotely failing pandas version.

## Validation Results
Created temporary venvs with system site packages so the existing heavy scientific dependencies could be reused. Installed pandas versions only into those temporary environments; the regular linac-opt environment retains pandas 3.0.5.

- Before the fix, pandas 3.1.0 reproduced `test_save_and_load_evaluation_results` failing with exactly the remote `Pandas4Warning`.
- Focused serialization/run-reader suite: **43 passed** with pandas **3.1.0** (5.25 seconds), **3.0.5** (8.33 seconds), and **2.3.3** (5.31 seconds). The initial temporary pandas 2.3.3 environment lacked its pytz dependency; installing that dependency into the temporary environment resolved collection, without changing project constraints.
- The first new legacy-header precision check exposed the in-place rename deprecation (42 passed, 1 failed); the non-in-place fix made all 43 pass. A preliminary full run was interrupted after 97 passes to restart consistently with that correction.
- Final complete command: `PYTHONPATH=src OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 /tmp/mobo-pandas31-ci/bin/python -m pytest -m 'not integration' --tb=short --cov=mobo_linac --cov-report=term --cov-fail-under=85 -q` — **824 passed, 41 skipped, 2 deselected**, 524.60 seconds. Coverage **93.01%**, above the unchanged 85% requirement. Log: `/tmp/mobo_pandas31_ci_full_final.log`.
- `python -m ruff check src scripts tests tools`, `python scripts/verify_docs_sync.py`, and `git diff --check`: passed.
- Verified unique, consecutive task numbering through 251. Generated coverage data is retained under `/tmp`, not included in Git.

## Scope and Limitations
- The local full run uses Python 3.11 and pandas 3.1.0, matching the identified failing pandas release. It reuses other locally installed dependencies and is not an exact recreation of every remote dependency or the Python 3.12 runner.
- No warning filter was weakened, dependency upper bound introduced, test skipped to hide a failure, or coverage threshold changed. No workflow file needed modification.
- No ASTRA simulations, physics settings, immutable campaign artifacts or manuscript measurements were changed.
- Remote status and logs were read under the updated AGENTS.md policy. No remote workflow rerun or git push was performed. The historical failed run tested the older remote commit; confirmation of the repaired branch requires publication and a new workflow run under the repository's no-push restriction.

## Status
Fixed and validated locally against the remote failure's pandas version. Changes and this record are committed locally; a new remote CI result is pending publication.
