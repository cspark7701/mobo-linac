# Task Completion Summary: Task 00321

## Summary
C4-02 of the round4 revision (Reviewer 2 comment 5, optional). Two further post-hoc diagnostic-shift scenarios for the primary feasible fractions were computed from the archived ledgers and reported in Sec. V B as scenarios, not bounds.

## Key Changes
- **Analysis.** New `scripts/analyze_revision_shift_scenarios.py` reuses the C3-02 reclassification (`run_table`, `paired`). It adds two scenarios:
  - **Upward scenario.** Sizes and divergences are scaled by 1.012, the largest step-only increase in `r2_convergence_values.csv`, combined with the nine bunch-length and energy shifts.
  - **Differential case.** In each matched group, the lowest constraint-aware post-initialization fraction over the 27 common-shift scenarios is compared with each other method's highest.
- **Evidence (new; `r3_*` unchanged).** `docs/paper/revisions/evidence/r4_shift_scenarios_upward_runs.csv`, `_upward_paired.csv`, `_differential.csv` and `_metadata.json`.
- **Results** (constraint-aware minus unconstrained, and minus weighted-sum):
  - **×1.012:** post-initialization differences of 0.279 and 0.311 at nominal bunch length and energy, and 0.246–0.295 and 0.280–0.329 with the shifts. Every interval excludes zero, and every group is positive.
  - **Differential case:** means 0.166 and 0.211, smallest group differences 0.062 and 0.132, and all ten groups positive.
  - Both reproduce Reviewer 2's calculation.
- **Manuscript.** One passage in Sec. V B reports the two scenarios. The existing caveat now covers them: "None of these scenarios is re-tracking of the primary campaigns, a refinement model for every evaluation or a worst-case error bound".
- **Supplement.** Four rows in `evidence_map.csv` (S1.13). One row in `input_inventory.csv` (level 2a: ledgers and derived evidence). The S1.13 description in the README.
- **Test.** New `tests/test_revision_shift_scenarios.py`.
- Task C4-02 is marked done in the consolidated round4 task list.

## Validation Results
- `ruff`, the documentation-sync check and the supplement manifest check passed.
- The new test and the resolution-bounds, documentation-link and manuscript-hygiene tests passed (9 tests).
- The analysis runs in about one second on one worker.
- The preprint builds without errors, undefined references or overfull boxes (57 pages).

## Status
Completed and committed locally. No push performed. No simulation was run.
