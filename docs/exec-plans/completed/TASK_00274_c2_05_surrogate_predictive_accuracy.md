# Task Completion Summary: Task 00274

## Summary
Complete consolidated round2 task C2-05, including its authorized optional offline refit: interpret the undercoverage of the next-batch predictive intervals, resolve the existing C11 records by stage and feasible region, and test the fixed-noise setting by refitting every archived training set with inferred noise.

## Key Changes
- **Script** `scripts/analyze_revision_calibration.py`:
  - part A summarizes the existing C11 records by stage (batches 1–6, 7–12, 13–18) and production-feasible region, with run-level quartiles;
  - part B refits all 540 pre-proposal training sets offline (no ASTRA) with the production surrogate builder, once with fixed and once with inferred homoscedastic noise, and repeats the chronological next-batch check.
- **Region and stage (part A).** For constraint-aware MOBO, the horizontal-emittance coverage is 89.9 % for feasible and 69.5 % for infeasible observations (RMSE 2.60 and 10.33 µm·rad). The transverse diagnostics rise from 75.6–80.0 % early to 88.3–91.0 % late, and energy from 67.5 % to 97.5 %. Bunch length falls from 89.2 % to 84.4 %. The emittance coverage is not monotonic in stage.
- **Refit (part B).**
  - The fixed-noise refits reproduce the saved-snapshot coverage to within 0.5 percentage points.
  - Inferred noise raises the constraint-aware objective coverage to 83.4, 86.6 and 92.7 %, and the diagnostics to 86.9–93.9 %.
  - The RMSE changes by at most 14 %, except energy, which falls from 0.89 to 0.14 MeV.
  - The fitted noise is 1e-4 to 1e-3 of the training variance and sits at the constraint lower bound for energy and bunch length, so it reflects regularization, not detected noise.
  - In 88 of 4680 refits, both optimizers failed and the initial hyperparameters were restored, as in production.
- **Manuscript.**
  - Section 5.6 discusses the three causes: fixed near-zero noise, kernel misspecification and adaptive test points.
  - It states the consequence for the feasibility weights, reports the region and stage results and the refit, and makes no claim of calibrated local prediction.
  - The Limitations section notes that the undercoverage is concentrated in the infeasible region and only partly removed.
- Evidence: `r2_calibration_stages.csv`, `r2_calibration_refit_predictions.csv.gz`, `r2_calibration_refit_summary.csv` and `r2_calibration_metadata.json`.

## Validation Results
- The refit ran on `cuda:0` and every input ledger checksum was verified against its completion marker.
- `tests/test_revision_calibration.py` passed (4 tests).
- `latexmk` built a 35-page PDF without undefined references.

## Status
Completed and committed locally. No push performed.
