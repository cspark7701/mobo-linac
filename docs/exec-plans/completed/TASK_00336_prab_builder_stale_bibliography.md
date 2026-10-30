# Task Completion Summary: Task 00336

## Summary
Fixed `python scripts/build_prab_submission.py --compile`, which failed with `RuntimeError: undefined references in build/prab_submission_check/manuscript.log`. The undefined citation was `SupplementalMaterial`. The builder inlines `docs/paper/main.bbl` from the last paper build, and that file (13:45) predated Task 00335's commit (14:10), which added the citation and its `references.bib` entry. The stale bibliography therefore lacked the entry. No manuscript text, result or value changed.

## Key Changes
- **Stale-bibliography check (`scripts/build_prab_submission.py`).**
  - `flatten()` compares the citation keys of `main.tex` with the `\bibitem` keys of `main.bbl`, using the new helpers `cited_keys()` and `bibitem_keys()`.
  - `cited_keys()` ignores comments. `bibitem_keys()` handles the REVTeX optional labels, which hold nested braces and brackets.
  - When a cited key is missing, the builder stops before writing anything. The error names the keys and the `latexmk` command instead of reporting undefined references only after the compile check.
- **Test (`tests/test_build_prab_submission.py`).** The new test covers:
  - a missing key, which raises the error;
  - a commented citation, which is ignored;
  - `\bibitem` with and without an optional label.
- **`docs/paper/README.md`.** Notes the check and that the paper must be rebuilt after changing citations.
- **Paper rebuilt.** `latexmk -cd -pdf docs/paper/main.tex` regenerated `main.bbl` (gitignored) with the `SupplementalMaterial` entry.

## Validation Results
- **Focused tests:** the five builder tests passed. The full suite was not run (focused-test policy).
- **Lint:** `ruff check` passed on the changed files.
- **Real paper:** before the rebuild, the check reported exactly `['SupplementalMaterial']` missing from the 49 parsed `\bibitem` keys.
- **Paper build:** `latexmk` built the paper with no undefined references.
- **Builder:** `python scripts/build_prab_submission.py --compile` now completes. It compiles `build/prab_submission_check/manuscript.pdf` and writes 12 files to `build/prab_submission/`.

## Status
Completed and committed locally. No push performed and nothing uploaded.
