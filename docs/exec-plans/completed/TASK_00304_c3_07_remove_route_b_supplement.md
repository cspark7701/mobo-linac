# Task Completion Summary: Task 00304

## Summary
Follow-up to C3-07 after the C3-01 route (a) decision: the supplement no longer contains anything about the withdrawn route (b).

## Key Changes
- **Evidence.** Removed `docs/paper/revisions/evidence/r3_validation_design.json` and `r3_validation_sample.csv`; they remain in commit `e32f63a`.
- **Supplement map and inventory.** Removed the two S1.13 rows of `evidence_map.csv` and the `scripts/evaluate_revision_validation.py` row of `input_inventory.csv`. The README now describes re-tracking records by the resolution check alone.
- **Shared helpers.** `ARMS`, `SEEDS`, `N_INIT`, `feasible` and `load_ledgers` moved to the new `scripts/revision_ledgers.py`. The C3-02 and C3-04 generators import from it instead of the route (b) driver, which re-exports the names for its own use and its tests.
- **Task list.** C3-07 records the cleanup.

## Validation Results
- `ruff check src scripts tests tools` passed; the supplement manifest check passed.
- `scripts/check_supplement_regeneration.py` passed; the regenerated bounds, Sobol and attribution evidence match the committed files.
- `tests/test_revision_validation.py`, `test_revision_resolution_bounds.py`, `test_revision_sobol_uncertainty.py` and `test_supplement_map.py` passed (12).

## Status
Completed and committed locally. No push performed.
