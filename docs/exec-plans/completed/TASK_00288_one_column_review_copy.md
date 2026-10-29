# Task Completion Summary: Task 00288

## Summary
Set the manuscript in one column for reviewing, at the author's request (2026-10-29). The REVTeX option changes from `reprint` to `preprint`. The two-column PRAB layout can be restored by switching the option back.

## Key Changes
- **Manuscript (`docs/paper/main.tex`).**
  - The class options are `aps,prab,preprint,superscriptaddress,amsmath,amssymb,floatfix`.
  - `\datafigure` caps figure heights at `0.7\textheight` with `keepaspectratio`. Without the cap, the portrait constraint-space figures would be too tall at the full one-column width.
  - The supplement README path uses `\path` so that it can break across lines. This removes a 45 pt overfull line.
  - The `\inputwide` comment now describes a page-wide float.
- **Format descriptions.**
  - `docs/paper/README.md` describes the one-column review copy and how to restore the two-column layout.
  - The round2 overview and task-list C2-10 give 52 pages for the one-column copy and 30 pages with `reprint`.
  - Both responses state 52 pages in the one-column review format (30 pages in the two-column layout).
- **Packaging.**
  - `round2_manuscript.diff` is regenerated.
  - `round2_changed_files.json` hashes are updated for the five changed files.

## Validation Results
- `latexmk` builds `main.pdf`: 52 pages, one column. There are no errors, undefined references or overfull boxes.
- One "float is stuck" warning remains. It comes from a `\FloatBarrier`, and the float is placed at the barrier.
- A temporary copy with `reprint` built to 30 pages without errors, undefined references or overfull boxes. The copy was deleted.
- `ruff check scripts tests` and `scripts/verify_docs_sync.py` passed.
- `tests/test_paper_outputs.py`: 53 passed.
- `scripts/build_supplement_manifest.py` check passed.

## Status
Completed and committed locally. No push performed. C2-10 remains open (funding and acknowledgments, `\finaltrue`). C2-15 needs the author's go-ahead.
