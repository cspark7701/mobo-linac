# Task Completion Summary: Task 00296

## Summary
Consolidated round3 task C3-04: replace the pooled exact-binomial Sobol interval with run-level uncertainty, and correct the Sobol-arm statements (Reviewer 1 M2, Reviewer 2 R3(b) and minor 1).

## Key Changes
- **Analysis (`scripts/analyze_revision_sobol_uncertainty.py`, test `tests/test_revision_sobol_uncertainty.py`).**
  - The sampling unit is the matched group: one scramble and one campaign each, so ten units.
  - For the shared initial design, the Sobol arm and each BO arm, it reports the per-run fractions, their mean, s.d. and range, and a percentile bootstrap over the ten runs (10,000 resamples). The bootstrap is labelled approximate.
  - Evidence: `evidence/r3_sobol_uncertainty_{runs,summary}.csv` and `_metadata.json`, mapped to S1.6. They supersede the pooled intervals of `r2_space_filling_initial.csv`, which is left unchanged.
- **Results.**
  - Sobol arm: 41/1,440 (2.8 %); run-level fractions 1.4–4.9 %, s.d. 1.3 points, bootstrap 2.1–3.6 %.
  - Shared initial designs: 5/160 (3.1 %), run-level 0–6.3 %.
  - The counts reproduce the round2 values.
- **Manuscript.**
  - Sec. V C: the "exact 95 % interval 2.1–3.8 %" is replaced by the run-level statement.
  - "At least two thirds …" becomes "they account for at most about one third of the constraint-aware gain over the Sobol arm (shares of 0.34 and 0.26)". "Uniform sampling" becomes "space-filling sampling".
  - The energy-band sentence is now direction-specific: −0.069 for unconstrained MOBO, +0.035 for scalarized BO.
  - The Conclusions sentence is rephrased to match.
  - The design-specific binomial intervals of the independent jitter trials are unchanged.
- **Task list:** C3-04 is ticked.

## Validation Results
- The new test and `tests/test_paper_outputs.py` passed (54); `ruff` passed.
- The supplement manifest check passed.
- `latexmk` builds `main.pdf` (54 pages) without errors, undefined references or overfull boxes.

## Status
Completed and committed locally. No push performed. The round2 response still quotes the old interval; C3-12 corrects it in the round3 response.
