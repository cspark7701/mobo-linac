# Task Completion Summary: Task 00285

## Summary
Consolidated round2 task C2-10, author decisions of 2026-10-29: Physical Review Accelerators and Beams (PRAB) is the target journal, and the table of contents is removed. The manuscript is converted to the PRAB format.

## Key Changes
- **Document class (`docs/paper/main.tex`).**
  - `revtex4-2` with `aps,prab,reprint,superscriptaddress,amsmath,amssymb,floatfix` replaces `article`. The geometry, natbib and unsrtnat settings are removed, and references use `apsrev4-2`.
  - Front matter follows REVTeX: the title and the author, email and two affiliations are set after `\begin{document}`, and the abstract precedes `\maketitle`.
  - The keywords line, the table of contents and its `\addcontentsline` entries are removed. The PDF metadata keeps the keywords.
  - The acknowledgments use the `acknowledgments` environment, still with the author's pending marker. The Data availability section is kept.
- **Style.**
  - APS cross-reference style: "Sec.", "Secs.", "Fig.", "Figs.", "Table" and "Appendix" before `\ref`.
  - The title quantity is plain "200~MeV", so it renders bold.
  - The noise-variance equation is split over two aligned lines to fit one column.
- **Floats.**
  - Wide figures and tables are two-column floats.
  - The two stacked three-panel Pareto figures and the two bar-chart figures are single-column.
  - Generated tables are included through a new `\inputwide` wrapper, so the table generators are unchanged.
- **Supporting files.**
  - `docs/paper/README.md`: the format paragraph is updated.
  - `.gitignore`: ignores REVTeX's generated `*Notes.bib`.
  - `tests/test_paper_outputs.py`: accepts `\inputwide` as well as `\input` for the generated tables.
- **Task list:** the C2-10 table-of-contents and journal items and the status row are updated. Funding and acknowledgments and `\finaltrue` remain open.

## Validation Results
- `latexmk` built `main.pdf` (30 pages, two-column reprint) without errors, undefined references or overfull boxes. The page layout was inspected visually.
- `tests/test_paper_outputs.py` (53 tests) and `tests/test_supplement_map.py` passed. `ruff check tests`, `scripts/verify_docs_sync.py` and `scripts/build_supplement_manifest.py` passed.
- BibTeX reports only missing-year warnings for two web references (KLSProjectOverview, LumeAstra).

## Status
Completed and committed locally. No push performed. C2-10 stays open for funding and `\finaltrue`, and closes only when the reviewers accept.
