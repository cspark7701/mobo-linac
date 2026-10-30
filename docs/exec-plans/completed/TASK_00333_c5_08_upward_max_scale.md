# Task Completion Summary: Task 00333

## Summary
C5-08 of the round5 revision (Reviewer 2 comment 6, optional; done). The primary feasible fractions were reclassified under a common upward scale that covers the largest observed increase of a size or divergence at any refinement or source level.

## Key Changes
- **Analysis.** New `scripts/analyze_revision_upward_max.py` reuses the C3-02 reclassification.
  - It finds the largest increase in `r2_convergence_values.csv`: σ_y of the crowding-distance setting with the second random source, +16.2 %.
  - It rounds the scale up to ×1.17 and applies it, with the nine bunch-length and mean-energy shifts, to the archived primary and Sobol-arm evaluations.
- **Results** (constraint-aware minus unconstrained, and minus weighted-sum):
  - differences of 0.276 and 0.300 at nominal bunch length and energy, and 0.242–0.292 and 0.267–0.317 over the shifts;
  - smallest lower interval limits of 0.200 and 0.240;
  - all ten groups positive for every pair, including those with the Sobol arm.

  This reproduces the reviewer's check.
- **Evidence (new; `r4_*` unchanged).** `docs/paper/revisions/evidence/r5_upward_max_runs.csv`, `_paired.csv` and `_metadata.json`, mapped to S1.13 and listed in `input_inventory.csv` (level 2a).
- **Manuscript, Sec. V B.**
  - A half-sentence reports the ×1.17 scale.
  - The sentence from C5-06 now speaks of "three further post-hoc sensitivity checks".
  - The caveat reads "None of these checks is re-tracking …".
- **Test.** New `tests/test_revision_upward_max.py`.
- Task C5-08 is marked done in the consolidated round5 task list.

## Validation Results
- `ruff`, the supplement manifest check and the documentation-sync check passed.
- Focused tests passed (68): the new test, the scenario, bounds, supplement-map, documentation-link, hygiene and paper-output tests.
- The full test suite was not run, at the author's direction (the machine is shared). The new script is outside the `mobo_linac` coverage target.
- The preprint builds without errors, undefined references or overfull boxes (57 pages).

## Status
Completed and committed locally. No push performed. No simulation was run.
