# Task Completion Summary: Task 00293

## Summary
The author chose route (b) for consolidated round3 task C3-01 (2026-10-29): a physically resolved comparison, which Reviewer 1 makes conditional on numerical validation. C3-11 (refined re-tracking) is authorized with 20 workers. This task predeclares the validation design, adds the driver and its tests, and launches stage A. The manuscript is unchanged until the stage B results exist.

## Key Changes
- **Driver (`scripts/evaluate_revision_validation.py`).** It has three stages:
  - `ladder` (stage A): the ten C2-12 settings beyond the fine level (40k particles, 64-cell grids, H/4), one factor at a time: H/8, H/16, 80k particles, and 80k particles with 96-cell grids. That is 40 runs, longest first.
  - `select`: the predeclared method-balanced sample.
  - `sample` (stage B): re-tracking of the sample at a chosen level.
- **`scripts/evaluate_revision_convergence.py`.** `make_sources` and `build_template` accept a source set; the default behaviour is unchanged.
- **Predeclared design (`docs/paper/revisions/evidence/r3_validation_design.json`, `r3_validation_sample.csv`).**
  - The sample has 704 points in all four arms:
    - all per-run feasible Pareto points (136/64/41/23);
    - every post-initialization observation whose classification changes under the C2-12 bounds (142/106/94/18);
    - two random post-initialization observations per run (80; seed 20261029).
  - The level-selection rule uses a 3 % tolerance (0.05 MeV for energy), applied per factor. A 3-day cost gate on stage B requires reporting to the author before launch.
  - The stage B endpoints are listed in the design file. Both files are mapped to S1.13.
- **Tests (`tests/test_revision_validation.py`).** They cover:
  - the level definitions;
  - the plan order;
  - the bounding-shift classification;
  - nondominance;
  - stratum exclusivity and the reproducibility of the selection.
- **Task list.** C3-01 records route (b) and the design. C3-11 is authorized and its status updated.

## Validation Results
- The new and related tests passed (10), and `ruff check scripts tests` passed.
- A mock rehearsal of the ladder completed all 40 tasks.
- The documentation-sync check passed. The supplement manifest was rebuilt (215 ledgers), and its check passed.
- Stage A was launched at about 15:55 on 2026-10-29, with 20 workers, writing to `results/revision_round3/ladder/`. At 17:11, 20 ASTRA processes were running and no run had finished.

## Estimated time (20 workers)
- **Stage A: about 4–5 h.** The longest runs, with 96-cell grids, take an estimated 3–4 h.
- **Stage B: 704 runs.** The time depends on the selected level:
  - about 24 h if the C2-12 fine level suffices;
  - about 32 h at H/8;
  - about 43 h at H/16.

  A 96-cell grid would exceed the cost gate. These estimates scale the C2-12 runtimes, which were measured under contention.

## Status
Committed locally. No push performed. Remaining work:
- after stage A finishes: level selection, then stage B;
- an analysis script for stage B;
- the manuscript revision for route (b) and the task-list closure.
