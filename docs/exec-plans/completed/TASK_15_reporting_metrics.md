# Task 05 Summary: Standardize Hypervolume and Publication Metrics

## Standardized Reporting Module & Fixed Engineering Scales
- Created `src/mobo_linac/metrics/reporting.py`:
  - `DEFAULT_ENGINEERING_SCALES`: Fixed scale factors ($S_{\varepsilon_{n,x}} = 10^{-6}\text{ m}\cdot\text{rad}$, $S_{\varepsilon_{n,y}} = 10^{-6}\text{ m}\cdot\text{rad}$, $S_{\sigma_E} = 10^{6}\text{ eV}$).
  - `DEFAULT_REPORTING_REF_POINT_MODEL_NORM`: Fixed reporting reference point in normalized model space ($[-10.0, -10.0, -10.0]$).
  - Objective normalization functions: `normalize_objectives_physical` and `normalize_objectives_model`.

## Full Campaign Metrics History Computation
- Implemented `compute_campaign_metrics_history` tracking all required publication metrics across cumulative ASTRA evaluations:
  - `cumulative_astra_evaluations`: Primary progress x-axis
  - `fixed_ref_all_valid_hv`: Dimensionless hypervolume of all valid evaluations
  - `fixed_ref_feasible_hv`: Dimensionless hypervolume of physically feasible evaluations
  - `feasible_fraction`: Cumulative ratio of feasible candidates
  - `first_feasible_eval_index`: 1-based index of first feasible candidate
  - `pareto_set_size`: Number of non-dominated feasible candidates
  - `invalid_run_count`: Cumulative simulation failure/timeout count
  - `total_wallclock_s`: Cumulative wall-clock runtime
  - `total_simulation_runtime_s`: Sum of individual ASTRA execution times

## Cross-Run Compatibility Verification
- Implemented `validate_campaign_compatibility`:
  - Enforces identical objective normalization scale factors.
  - Enforces identical fixed reporting reference points.
  - Rejects incompatible campaign metric comparisons by default.

## Documentation Deliverables
- Created [docs/methods/metric_definitions.md](file:///home/cspark/Work/projects/mobo_linac/docs/methods/metric_definitions.md): Technical documentation detailing fixed engineering scales, normalized model space, reference points, metric column definitions, and cross-run compatibility rules.

## Tests & Verification
- Created `tests/test_reporting_metrics.py`:
  - `test_known_answer_hypervolume_single_point_3d`: Verified analytical hypervolume ($2^3 = 8.0$).
  - `test_known_answer_hypervolume_two_points_2d`: Verified 2D non-dominated box hypervolume ($2.0 + 2.0 - 1.0 = 3.0$).
  - `test_objective_normalization_scales`: Verified fixed engineering scale division.
  - `test_campaign_metrics_history_computation`: Verified cumulative evaluation metrics, first feasible index, and runtimes.
  - `test_campaign_compatibility_verification`: Verified cross-run compatibility checks and exception raising.
- Pytest suite executed successfully: 62/62 unit tests passed.

## Acceptance Criteria Status
- [x] Reporting reference point is fixed and immutable within and across runs.
- [x] Hypervolume histories are non-negative, dimensionless, and reproducible.
- [x] Cross-run tools reject incompatible metrics by default.
- [x] Machine-readable metrics history generated per evaluation.
- [x] Cumulative ASTRA evaluations serve as primary x-axis.
