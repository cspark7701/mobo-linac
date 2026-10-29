# Task Completion Summary: Task 00302

## Summary
Consolidated round3 task C3-10: the editorial pass on precision, length, style and source hygiene (Reviewer 1 minors 3–4, Reviewer 2 minors 3, 4 and 6–9).

## Key Changes
- **Precision and labels.**
  - Tables IV (primary results) and V (robustness) carry a nominal-resolution note. It is added to the generated `.tex` files and to their generators (`scripts/generate_primary_paper_table.py`, `scripts/analyze_revision_robustness.py`).
  - Table X (`c08_settings.tex`) says that the digits identify archived evaluations and are not resolved physical values; both Pareto-figure captions carry the same scope.
  - Sec. V H adds the same statement with a reference to Table `tab:resolution`.
  - Running-text emittances and spreads are rounded to three significant figures in Secs. V H, V J and VI A and in Appendix C. Published values of earlier studies are kept as published.
- **Determinism (Sec. III A).** Added that determinism holds for the fixed source file, whose sampling error spreads the emittances by 1–12 %, is common to all methods and is not represented by the GP noise.
- **Length and placement.**
  - Sec. V F is reduced to a summary; the probe moves to the new Appendix `app:smoothing`.
  - The stage- and region-resolved coverage and the refit details of Sec. V G move to Appendix D, with a summary kept in the main text.
  - Sec. II A is reduced to its findings, and the level definitions move to a new "Resolution check" paragraph in Appendix A.
- **Abstract.** The long feasibility sentence is split into three; the abstract remains free of numbers.
- **APS style.** "Ref." for in-text references (Secs. I and II B), and "Sec. 4.3" for Kim et al. (Secs. II A and VI A).
- **Source hygiene.**
  - The `% C05 …` comment is removed from Sec. III C.
  - The new `tests/test_manuscript_hygiene.py` fails on revision-tag comments in `main.tex` and the files it inputs. The evidence snippets that are not included keep their headers.
- **Layout.** Table `tab:resolution` is now a full-width float, which removes an overfull line in the two-column layout.
- **Not done:** reordering the paper to lead with the comparison and the measured numerical limitation (Reviewer 1 minor 4). It is deferred to the route (b) scope text and left unchecked.

## Validation Results
- One-column `main.pdf`: 56 pages. Two-column `reprint` check copy: 31 pages, deleted after the check. Both build without errors, undefined references or overfull boxes.
- `tests/test_paper_outputs.py`, `tests/test_manuscript_hygiene.py` and `tests/test_supplement_map.py` passed (59). The robustness and primary-table tests passed (32).
- `ruff`, the documentation-sync check and the manifest check passed.

## Status
Completed and committed locally. No push performed.
