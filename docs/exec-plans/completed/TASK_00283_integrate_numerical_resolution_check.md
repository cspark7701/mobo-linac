# Task Completion Summary: Task 00283

## Summary
Complete consolidated round2 task C2-12: analyze the numerical-resolution check of the ten reported settings (150 ASTRA runs, 15 levels each, completed at 23:07 on 2026-10-28) and integrate it into the manuscript, the supplement and the task list.

## Key Changes
- **Analysis fix (`scripts/analyze_revision_convergence.py`, `tests/test_revision_convergence.py`).**
  - The primary and TDR-constrained campaigns reuse run names and evaluation ids, so `archived()` found the primary ledger for the closest TDR-campaign observation.
  - It now chooses the ledger by role, as the driver does. A new test covers the case.
  - The driver had read the correct parameters, so the simulations are unaffected.
- **Evidence:** `docs/paper/revisions/evidence/r2_convergence_{values,summary,classification}.csv` and `r2_convergence_metadata.json`.
- **Result.**
  - **Determinism:** production-level reruns reproduce all archived values to floating-point precision.
  - **Emittances are not converged at the production resolution.**
    - At the fine level (40k particles, 64-cell grids, quarter step), ε_n,x is 12–34 % and ε_n,y 17–43 % lower.
    - The integration step dominates: the quarter step alone lowers them by up to 28 % and 38 %.
    - The change from the medium to the fine level is still up to 9 %.
    - Their order across the settings: Spearman 0.79 (x) and 0.94 (y).
    - Random 10k sources spread them by 1–12 %.
  - **Other quantities are stable:**
    - σ_E changes by at most 4 % and keeps its order;
    - σ_z by at most 1 %;
    - mean energy by at most 0.05 MeV;
    - transmission not at all.
    - Sizes and divergences fall by up to 22 %.
  - **Classifications:**
    - All ten settings are production-feasible at every level.
    - TDR candidate B passes at all 15 levels. Candidate A fails in σ_x at grid 64 and with 2 of 5 random sources.
    - The MOGA-derived nominal and the closest TDR-campaign observation pass the TDR inequalities at the medium and fine levels.
- **Manuscript (`docs/paper/main.tex`).**
  - Section 2.1 reports the check, and notes the reconstructed generator input in the source paragraph.
  - A new paragraph in `sec:tdr_reach` says that TDR membership near the limits is not resolved, and the table caption points to it.
  - Limitations: the method comparison has not been tested at a converged resolution.
  - Abstract: one qualitative sentence; the TDR clause is qualified.
  - Conclusions and future work are updated, and the caveat after the contribution list cites the check. No fifth contribution is added.
- **Supplement:** the four evidence files are mapped to S1.13, and the README row is updated.
- **Task list:** the C2-12 result is recorded, and the C2-04, C2-12 and run-note rows are updated. The task list records a conflict the author needs to resolve with the earlier recorded author confirmation that a convergence study was done (Tasks 00226 and 00227).
- The responses (Reviewer 1 M2, Reviewer 2 N4(b)) were updated, but remain uncommitted C2-11 drafts.

## Validation Results
- `ruff check src scripts tests tools` and `scripts/verify_docs_sync.py` passed.
- `tests/test_revision_convergence.py` (5 tests) and `tests/test_supplement_map.py` passed.
- `scripts/build_supplement_manifest.py` check passed.
- `latexmk` built `main.pdf` (38 pages) without undefined references.

## Status
Completed and committed locally. No push performed.
