# Task Completion Summary: Task 00287

## Summary
Make the two constraint-space figures single-column in the PRAB manuscript at the author's request (2026-10-29). As full-width floats, both portrait figures were taller than the page.

## Key Changes
- **Figures (`docs/paper/main.tex`).**
  - `fig:primary_constraints` and `fig:survey_constraints` change from `figure*` to `figure`, at `\linewidth`. The two stacked Pareto figures and the two bar charts already use this treatment.
  - The figures no longer exceed the page height; before the change, they were 48.6 pt and 27.6 pt too tall.
  - They now appear in the left column of pages 13 and 24. The page count stays at 30.
- **Packaging (`docs/paper/revisions/`).**
  - `round2_manuscript.diff` is regenerated against `9077875`. Before regenerating it, a check confirmed that the committed diff reproduces exactly.
  - In `round2_changed_files.json`, only the `main.tex` hash is updated.

## Validation Results
- `latexmk` builds `main.pdf` (30 pages). There are no errors, undefined references, overfull boxes or "float too large" warnings.
- The build still gives two "float is stuck" warnings. They come from the `\FloatBarrier` calls, which place those floats at the barrier.
- `tests/test_paper_outputs.py`: 53 passed.
- `scripts/build_supplement_manifest.py` check passed.

## Status
Completed and committed locally. No push performed. C2-10 remains open (funding and acknowledgments, `\finaltrue`). C2-15 needs the author's go-ahead.
