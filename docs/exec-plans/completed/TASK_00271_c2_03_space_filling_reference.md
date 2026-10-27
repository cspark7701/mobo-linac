# Task Completion Summary: Task 00271

## Summary
Complete the required part of consolidated round2 task C2-03: report an initialization-only space-filling reference from the shared Sobol initial designs, and explain the baseline feasibility gain with the C2-02 channel classification. The optional budget-matched Sobol arm (10 × 160 evaluations) is still running. Its comparison will be added in a follow-up commit.

## Key Changes
- Add `scripts/analyze_revision_space_filling.py`:
  - part `initial`: the 160 shared initial points;
  - part `sobol`: the Sobol arm, with a check that each seed's first 16 points equal the shared design, and paired comparisons.
  - Evidence: `r2_space_filling_initial.csv` and `r2_space_filling_metadata.json`.
- Result: 5 of 160 shared Sobol points are feasible, 3.1 % (exact 95 % interval 1.0–7.1 %). The pooled post-initialization feasible fractions are 44.7 %, 17.1 % and 13.5 %.
- Channel shares, Sobol against the constraint-blind baselines:
  - transverse violations 95.6 % against 76 %;
  - bunch-length violations 55.0 % against 32–33 %;
  - energy-band violations 40.0 % against 32.2 % and 42.6 %.
  - So emittance and spread minimization favours smaller transverse sizes, divergences and bunch lengths, while nothing in the baselines' targets steers the mean energy.
- Manuscript: a Results paragraph labels the reference as initialization-only, not a matched arm, and keeps the statement that no advantage over a full space-filling search is established.

## Validation Results
- `ruff check` passed. `tests/test_revision_space_filling.py`: 2 passed (rate definitions; archived count 5/160).
- `latexmk` built the PDF without undefined references or overfull boxes.

## Status
Required part completed and committed locally. The optional Sobol-arm comparison is pending. No push performed.
