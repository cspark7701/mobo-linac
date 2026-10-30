# Task Completion Summary: Task 00322

## Summary
Closed consolidated round4 task C4-11: the responses and the validation. Committed the two point-by-point responses, and packaged the manuscript diff, the analysis-code diff, the changed-file inventory and the round4 overview against the reviewed baseline `887673c`. All round4 tasks, C4-01 to C4-11, are now closed.

## Key Changes
- **Responses (`docs/paper/reviews/reviewer{1,2}_round4_response.md`).**
  - **Reviewer 1:** C1–C3, the scope confirmation, and corrections to the round3 response:
    - the Limitations population statement (also raised by Reviewer 2);
    - the contents of Table I;
    - Table XI, not Table X;
    - the scope of the rounding statement.
  - **Reviewer 2:** comments 1–9. For comment 9 it explains why Reviewer 1's "scenarios" wording was used instead of "bounding shifts". It also corrects the round3 response: the shares appear only in Sec. V C, the amplitude sentence was superseded, and the table is XI, not X.
  - **Unchanged:** the round3 response files.
- **Packaging (`docs/paper/revisions/`).**
  - `round4_manuscript.diff`: `main.tex`, the only changed manuscript source.
  - `round4_analysis_code.diff`: the new scenario script and its test.
  - `round4_changed_files.json`: 30 baseline-relative files (26 added, 4 modified) with SHA-256 hashes. It excludes the packaging files and this summary.
  - `round4_revision_overview.md`: the responses, the inventory, the main change per task, what was not done, the scope dispositions, the format and the checks.
- **Task list.** C4-11 is ticked with a Done note, and the status section states that every task is closed.
- **Record correction.** The C4-05 records (TASK_00315 and the task list) named Sec. V A for the Pareto cardinalities; they are in Sec. V B.

## Validation Results
- **Full suite as in CI** (`pytest -m "not integration" --cov=mobo_linac --cov-fail-under=100`, serial) on the C4-02 commit `047978f` with the responses and overview drafts present: 1,105 passed, 2 deselected, 100.00 % coverage. The only failure was the docs-links test, whose overview links pointed at package files not yet generated.
- **After packaging:**
  - `tests/test_docs_links.py`, `test_paper_outputs.py`, `test_manuscript_hygiene.py` and `test_supplement_map.py` passed (61 tests);
  - `ruff check src scripts tests tools`, `scripts/verify_docs_sync.py` and `scripts/build_supplement_manifest.py` passed;
  - `scripts/check_supplement_regeneration.py` passed, and `r3_regeneration_check.json` is unchanged.
- **`latexmk`:**
  - one-column `main.pdf`: 57 pages, with the abstract on page 1 and the Introduction from page 2;
  - two-column `reprint` check copy: 31 pages, deleted after the check;
  - both without undefined references or overfull boxes.
- **Abstract:** 262 words and no digits.

## Status
Completed and committed locally. No push performed. No simulation was run in round4. Closing the tasks does not establish reviewer agreement or journal acceptance.
