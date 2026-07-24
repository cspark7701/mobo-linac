# Task 06 — Fixed Reporting Reference Point and Hypervolume Audit

## Summary

Task 06 established a dual reference point system separating dynamic acquisition reference points from fixed reporting reference points to enable consistent, comparable hypervolume tracking.

## Accomplishments

1. **Dual Reference Point Architecture**: Created `HypervolumeTracker` in `src/mobo_linac/metrics/hypervolume.py`:
   - `acquisition_ref_point`: Dynamically computed per batch with small offset for BoTorch acquisition function optimization.
   - `reporting_ref_point`: Fixed across the entire optimization campaign, stored in configuration, ensuring monotonic hypervolume progress without artificial reference shifts.
2. **Reference Point Compatibility Validation**: Added `validate_reference_point_compatibility` to reject hypervolume comparisons between runs initialized with different reference points.
3. **Hypervolume Progress Tracking**: Tracked both feasible-only hypervolume and all-point hypervolume across optimization iterations.

## Status

**Completed**. Tested in `tests/test_hypervolume.py`.
