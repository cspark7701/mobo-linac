# Task Completion Summary: Task 00335

## Summary
Put the manuscript in the PRAB submission format, at the author's choice of both options: the two-column layout and a flat APS upload package. The manuscript already used REVTeX 4.2 with `aps,prab` and `apsrev4-2`; this task changes the layout and the supplement citation, and adds a builder for the upload folder. No result, value or argument changed.

## Key Changes
- **Layout (`docs/paper/main.tex`).** `preprint` is replaced by `reprint`, giving the two-column PRAB layout (30 pages). Line numbers and `\finalfalse` are kept. Replacing `reprint` with `preprint` still gives the one-column copy (57 pages).
- **Supplemental Material.**
  - `references.bib` has an APS-style `SupplementalMaterial` entry: "See Supplemental Material at [URL will be inserted by publisher] for Supplement S1, …".
  - It is cited at the first mention of the supplement (Sec. II), in Appendix A and in the Data availability statement. The review-only wording ("supplied with this manuscript for review", "the commit hash recorded in the review package") is replaced by "provided as Supplemental Material" and "the commit hash recorded with the archive".
  - The supplement README describes S1 as the Supplemental Material and names its archive and manifest.
- **Upload builder (`scripts/build_prab_submission.py`, test `tests/test_build_prab_submission.py`).** It writes `build/prab_submission/` (gitignored):
  - `manuscript.tex`: `main.tex` with the six generated tables (`\inputwide`, `\IfFileExists`) and `main.bbl` inlined;
  - the eleven cited figures, without subdirectories;
  - `supplement_S1.zip`: a `git archive` of HEAD without `docs/paper/reviews/`;
  - `submission_manifest.json`: commit, clean-tree flag and SHA-256 of every file.
  `--compile` builds the flat copy in `build/prab_submission_check/`, so the upload folder holds only upload files.
- **`docs/paper/README.md`.** The format paragraph now names the two-column submission layout and the builder.

## Validation Results
- **Full test suite: not run**, following the round5 direction (the machine is shared with another production job).
- **Focused tests passed:** the four new builder tests, and the documentation-link, paper-output, manuscript-hygiene and supplement-map tests.
- `ruff check src scripts tests tools`, `scripts/verify_docs_sync.py` and `scripts/build_supplement_manifest.py` passed.
- **`latexmk`:**
  - two-column `main.pdf`: 30 pages;
  - one-column check copy: 57 pages, deleted after the check;
  - both without undefined references or overfull boxes.
- **Flat copy:** `manuscript.tex` compiles to 30 pages, and its `pdftotext` output is identical to that of `main.pdf`. The zip holds 861 files and no file under `docs/paper/reviews/`.

## Status
Completed and committed locally. No push performed and nothing uploaded. The funding and acknowledgments marker remains for the author; `\finaltrue` is not set.
