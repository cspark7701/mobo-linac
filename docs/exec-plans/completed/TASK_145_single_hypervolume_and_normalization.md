# Task Completion Summary: Task 145

## Summary
Implemented TASK_19 from `docs/05_refactor_tasks/`. One module now computes Pareto fronts, hypervolume and normalization. The metric history is incremental, the reference policies are configured and recorded, and the hidden normalized reference default is gone.

## Key Changes
- **`mobo_linac.metrics.front`** (new) provides `pareto_mask`, `dominating_front`, `hypervolume`, `front_size` and `normalize`. The following use it:
  - `compute_hypervolume`;
  - `HypervolumeTracker` (including Pareto size);
  - `compute_normalized_hypervolume`;
  - the incremental metric history;
  - `RunArtifactWriter` Pareto exports.
- **One normalization**: `normalize_objectives_model` is now the same function as `normalize_objectives_physical`.
- **Incremental metric history**: `compute_campaign_metrics_history` keeps the valid and feasible fronts and recomputes the hypervolume only when a new point enters a front. Its values match full recomputation to 1e-12 relative, and a 2,000-record history runs within the test budget.
- **`hypervolume.csv`** no longer repeats reference points as stringified lists; they live only in `reporting_metadata.json`. Readers still validate the archived per-row reference columns.
- **Tracker required**: `RunArtifactWriter.write` requires the fixed-reference tracker, removing the alternative one-column `hypervolume.csv`. `save_evaluation_results` takes an explicit `reporting_ref_point` and tracks one cumulative iteration.
- **Reference policy**: new `ExecutionConfig` fields, all schema-validated, set the policy:
  - `reporting_reference_offset` (0.10);
  - `acquisition_reference_offset` (0.05);
  - `acquisition_reference_basis` (`all_valid` or `feasible`).
  Each proposal records its acquisition reference point, offset and basis.

## Acceptance Criteria
- [x] One HV and one Pareto implementation remain; all callers import them.
- [x] HV values are unchanged: incremental results match full recomputation, and existing reporting and paper-output tests pass.
- [x] Metric history grows linearly in a large-history regression test.
- [x] The acquisition reference policy is configured and recorded with each proposal.

## Validation Results
Relevant modules pass: reporting metrics, hypervolume, result serialization, run data, paper outputs, comparison, benchmark, benchmark campaign, checkpoint/resume, scalarized suite, config, docs sync, candidate evaluator, parallel evaluation and configuration boundaries. No ASTRA campaign, push or remote query was performed.

## Scope and Limitations
Two documented hypervolume views remain:
- per iteration in model units (`hypervolume.csv`);
- per evaluation, normalized (`metrics_history.csv`).

Both use one implementation. Merging them into a single file would change published artifact formats, so it was not done. The tuning utility's own reference offset is handled in TASK_23.

## Status
Completed.
