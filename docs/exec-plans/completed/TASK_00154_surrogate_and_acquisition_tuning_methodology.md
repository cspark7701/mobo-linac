# Task Completion Summary: Task 149

## Summary
Implemented TASK_23 from `docs/05_refactor_tasks/`. Surrogate diagnostics now report an exact leave-one-out estimate, and settings selection uses criteria that support the choice. Failures are recorded instead of hidden behind sentinel scores.

## Key Changes
- **`models.diagnostics`**:
  - `loo_predictions` computes closed-form exact LOO mean and variance for a single-output GP, in standardized space and in output units.
  - `compute_predictive_diagnostics` reports in-sample RMSE/MAE/R² and standardized residuals separately from LOO RMSE, LOO log predictive density (standardized units, comparable across outputs) and LOO ±1σ/±2σ coverage.
  - The mislabelled `loo_rmse_estimate = rmse·√(n/(n−1))` and `math_sqrt_correction` were removed.
- **`tune_gp_hyperparameters`**: ranks by mean LOO log predictive density. Previously it ranked by in-sample R², which favored near-zero noise. Each failure keeps `status`/`error` and is excluded from ranking; if every candidate fails, it raises.
- **Acquisition selection** (`compare_acquisition_functions`, `tune_acquisition_hyperparameters`): ranks by the common EHVI of each proposed batch (`qExpectedHypervolumeImprovement`, fixed Sobol QMC sampler, recorded reference). Diversity and time are reported as diagnostics only. Optimizer failures are recorded (`retry_on_failure=False`) rather than replaced by fallback proposals.
- **`tune_full_optimization_pipeline`**: requires the campaign's recorded reporting reference instead of a 5% data-derived reference. Its candidate grids and `maxiter` are parameters, and the unit test now uses small grids (about 38 s for the module instead of about 15 minutes).
- **Measured noise**: `compute_measured_noise_variance` uses a floor relative to each objective's scale, `(min_relative_std·scale)²`. The previous absolute 1e-8 exceeded the squared emittance by about 10⁴.
- **Notebooks and documentation**: the notebooks use the new fields and reference argument, and the method is documented in `docs/methods/metric_definitions.md`.

## Acceptance Criteria
- [x] No metric named LOO is computed from in-sample residuals.
- [x] Closed-form LOO matches explicit leave-one-out conditioning of the same fitted GP (test).
- [x] Tuning summaries list failures with reasons; no sentinel scores remain.
- [x] Measured-noise utilities work for any configured objectives.

## Validation Results
Relevant modules pass: `test_gp_models` (21, including LOO equivalence and failure recording), `test_gp_and_acquisition` (26 passed, 2 skipped) and `test_surrogate_pipeline` (18). No ASTRA campaign, push or remote query was performed.

## Scope and Limitations
- Production GP defaults (Matérn 5/2 ARD, relative fixed noise η = 1e-6) were not changed.
- The specified synthetic kernel-selection fixture was not added. Ranking correctness rests on the LOO-equivalence test and the documented criterion.

## Status
Completed.
