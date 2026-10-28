# Task Completion Summary: Task 00277

## Summary
Investigate the still-failing GitHub Actions CI run for the pushed commit `d179506` (run 40622201199), as authorized by the user, and fix it locally.

## Key Changes
- **Remote finding (verified from the job logs).**
  - Lint and the wheel smoke test now pass, so the Task 00276 fix worked.
  - All three test jobs (3.10, 3.11, 3.12) failed on one test, `tests/test_cli.py::test_script_wrappers_define_no_parsers_and_delegate_to_the_cli`. It requires every `scripts/run_*.py` file to be a thin CLI wrapper without argparse.
  - The violator was `scripts/run_revision_reference_settings.py` (Task 00265), a standalone revision driver with its own parser.
  - Package coverage was 100 %.
- **Why it was missed.** Task 00276 ran only the new test files. The repository-wide wrapper rule lives in an older test file.
- **Fix.**
  - Renamed the driver to `scripts/evaluate_revision_reference_settings.py`, outside the wrapper namespace. Its content is unchanged.
  - Updated `scripts/run_revision_round2_simulations.sh` and `tests/test_revision_reference_settings.py`.
  - The shell driver was executing the Sobol stage at the time. It was edited by replace-and-rename (new inode), so the running process kept reading its original copy, and it continued unaffected.
  - Historical task summaries keep the old name as a historical identifier. The completed reference runs are unaffected.

## Validation Results
- Ran in a clean worktree without `results/`, as on CI:
  - `ruff check src scripts tests tools` and `scripts/verify_docs_sync.py` passed;
  - the full CI test command gave 1050 passed, 32 skipped and 1 failed, and the wrapper test passed.
- The one failure, `test_backend_timeout_is_classified_as_timeout_despite_lume_astra_handler`, uses a 1 s subprocess timeout. It failed only under the machine load of the time (load average about 27 on 24 cores). It passed in 3 of 3 isolated reruns and on CI. It also caused the 2 uncovered lines (99.97 %). Remote coverage was 100 %.

## Status
Completed and committed locally. No push performed; CI will re-run when the author pushes.
