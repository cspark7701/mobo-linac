# Task Completion Summary: Task 247

## Summary
C06: Evaluate six residual/temperature conventions on frozen early, middle and late surrogates with common candidates and posterior samples. Quantify raw-unit ranking changes and dimensionless unit invariance without changing or relabelling the production method.

## Key Changes
- `scripts/analyze_revision_scaling.py`
- `tests/test_revision_scaling.py`
- `docs/paper/main.tex`
- `docs/paper/revisions/consolidated_round1_revision_tasks.md`
- `docs/paper/reviews/reviewer1_round1_response.md`
- `docs/paper/reviews/reviewer2_round1_response.md`
- `docs/paper/revisions/evidence/c06_acquisition_values.csv`
- `docs/paper/revisions/evidence/c06_metadata.json`
- `docs/paper/revisions/evidence/c06_rank_sensitivity.csv`
- `docs/paper/revisions/evidence/c06_report.md`
- `docs/paper/revisions/evidence/c06_smoothing_scales.csv`

## Validation Results
Computed 576 finite acquisition values across 18 comparisons. Dimensionless equivalent-unit values agree within 1.5e-13. Eight focused unit-invariance/manuscript tests passed; the PDF built successfully. No optimization or physical simulation was run.

## Status
Completed the author-approved offline sensitivity; corrected-arm performance remains unmeasured and explicitly not adopted. No push was performed.
