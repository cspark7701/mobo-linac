# Task 47 Summary: Correct Fixed-Noise GP Treatment (Codex Task 07)

## Summary

Task 47 corrected observation noise treatment for GP surrogate modeling across deterministic ASTRA simulations, measured repeatability studies, and stochastic/inferred simulation settings.

## Key Implementation & Enhancements

1. **`GpModelConfig` Integration ([`src/mobo_linac/config.py`](file:///home/cspark/Work/projects/mobo_linac/src/mobo_linac/config.py#L110-L130))**:
   - Added `GpModelConfig` dataclass supporting `covar_type` (`matern52`, `rbf`), `noise_mode` (`deterministic_fixed`, `fixed`, `measured_fixed`, `inferred`), `fixed_noise_variance`, and `objective_noise_variances`.
   - Updated `MoboConfig` and `load_config()` to load model configuration sections from YAML configuration files.

2. **Fixed-Noise Non-Trainable GP Construction ([`src/mobo_linac/models/gp.py`](file:///home/cspark/Work/projects/mobo_linac/src/mobo_linac/models/gp.py#L22-L90))**:
   - Updated `build_gp_models()`:
     - For `deterministic_fixed` / `measured_fixed`: Supplies `train_Yvar` (observation noise variance tensor) to `SingleTaskGP`, instantiating non-trainable `FixedNoiseGaussianLikelihood` during `fit_gpytorch_mll`.
     - For `inferred`: Builds standard trainable `GaussianLikelihood`.
     - Supports per-objective noise variances via `objective_noise_variances` or explicit `train_Yvar` tensors.

3. **Repeatability & Measured Noise Utility ([`src/mobo_linac/models/repeatability.py`](file:///home/cspark/Work/projects/mobo_linac/src/mobo_linac/models/repeatability.py))**:
   - Created `compute_measured_noise_variance()` to compute per-objective variances from repeated evaluation data.
   - Created `create_measured_yvar_tensor()` to generate `(N, M)` PyTorch observation variance tensors.

4. **SurrogatePipeline Integration ([`src/mobo_linac/models/pipeline.py`](file:///home/cspark/Work/projects/mobo_linac/src/mobo_linac/models/pipeline.py))**:
   - Updated `SurrogatePipeline` constructor and `fit()` method to pass `noise_mode`, `fixed_noise_variance`, `objective_noise_variances`, and `train_Yvar` down to `build_gp_models()`.
   - Updated primary campaign runner [`src/mobo_linac/campaigns/runner.py`](file:///home/cspark/Work/projects/mobo_linac/src/mobo_linac/campaigns/runner.py#L290-L300) to pass `config.model` settings.

5. **Unit Verification Suite ([`tests/test_gp_models.py`](file:///home/cspark/Work/projects/mobo_linac/tests/test_gp_models.py))**:
   - Created comprehensive unit tests for `deterministic_fixed`, `measured_fixed`, `inferred` noise modes, posterior predictions, and repeatability utilities.
   - Executed full test suite: **95/95 unit tests passed** in 55.45s.

## Status

**Completed**. Fixed-noise GP treatment implemented with non-trainable `train_Yvar` observation variance. Summary saved to `docs/exec-plans/completed/TASK_47_fixed_noise_gp_treatment.md`.
