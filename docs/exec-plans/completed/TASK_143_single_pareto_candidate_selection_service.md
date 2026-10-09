# Task Completion Summary: Task 143

## Summary
Implemented TASK_17 from `docs/05_refactor_tasks/`. Robustness analysis, rerun verification, publication summaries and campaign finalization now use one feasible-Pareto selection service with a single, documented knee definition.

## Key Changes
- **`mobo_linac.metrics.selection`** (new) provides:
  - `select_representatives(results, config)`, which returns a frozen `RepresentativeSet` (roles, policy, objective columns, feasible-Pareto identities, normalized costs);
  - `pareto_subset`, `valid_measured` and a vectorized `compute_crowding_distances`.
- **Single knee definition (`ideal_distance`)**: the knee is the feasible-Pareto point nearest the ideal corner after direction-aware min–max normalization. It replaces three previous definitions (origin in scaled space, origin or ideal in the verifier, min–max squared distance in publication).
- **Roles**: one extreme per configured objective (`min_emit_x`, `min_emit_y`, `min_sigma_energy` for 200 MeV; `min_/max_<name>` otherwise), plus `knee_point`, `balanced` and `crowding_distance_max`. `balanced_feasible` is now `balanced`; `robust_recommended` was removed because it only duplicated the knee.
- **No infeasible fallback**: selection raises when no measured feasible point exists. `extract_pareto_sets` returns empty feasible sets in that case, no longer requires six design variables, never negates objectives itself, and never mutates its inputs.
- **Shared consumers**: robustness, verification and `campaign_summary` all use the service. The selection is written to `representatives.json` in campaign, verification and robustness output directories.
- **Identity joins**: Pareto CSV exports carry `run_id`/`evaluation_id`, and `load_candidates` joins them to history by identity. Archived exports without identities fall back to exact values. Duplicate detection keys on `(run_id, evaluation_id)`.
- **Documentation**: the verification protocol, robustness rationale, simulation guide and metric definitions were updated.

## Acceptance Criteria
- [x] Exactly one knee implementation; robustness, verification and reports name the same evaluation for each role.
- [x] Selection without feasible points raises a clear error.
- [x] Input results are unchanged after selection.
- [x] Mixed-direction and four-objective fixtures select the correct extremes.

## Validation Results
- New tests cover cross-workflow knee consistency, the absence of an infeasible fallback, input immutability, mixed-direction extremes and the `representatives.json` record.
- Affected modules pass: pareto, robustness, verification, comparison, paper outputs, run data, scalarized suite and checkpoint/resume (65 passed, 1 skipped).
- No ASTRA campaign, push or remote workflow query was performed.

## Scope and Limitations
- Verification now reruns six roles instead of seven. Knee assignments in regenerated reports may differ where the old definitions disagreed.

## Status
Completed.
