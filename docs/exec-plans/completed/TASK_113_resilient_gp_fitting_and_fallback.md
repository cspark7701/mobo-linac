# Task Execution Summary: TASK_113 — Resilient Multi-Tiered GP Hyperparameter Fitting & Numerical Recovery

## 1. Overview & Objectives
- **Goal**: Resolve `ModelFittingError: All attempts to fit the model have failed` occurring during production MOBO optimization iterations (e.g. Iteration 07/20 in Phase 2 unconstrained MOBO).
- **Context**: During production campaigns, as training points accumulate in multi-objective space, observation noise matrices or covariance kernels can become locally ill-conditioned for certain channels (such as `sigma_energy`), causing second-order quasi-Newton (`L-BFGS-B` via SciPy) line searches to trigger `NotPSDError` across all restart attempts and aborting the entire simulation campaign.

---

## 2. Root Cause Analysis
1. **Quasi-Newton Sensitivity**: `fit_gpytorch_mll` fits hyperparameters via `scipy_minimize` with `L-BFGS-B`. When fitting complex multi-parameter ARD covariance surfaces with small fixed noise variances ($10^{-6}$), exploratory parameter steps during Hessian approximation can land in regions where the Cholesky decomposition of the covariance matrix fails (`linear_operator.utils.errors.NotPSDError: Matrix not positive definite after repeatedly adding jitter up to 1.0e-03`).
2. **Cascading Failure**: In BoTorch's fallback mechanism, if all 5 L-BFGS attempts fail with `NotPSDError`, it raises an unhandled `ModelFittingError`, halting the entire campaign pipeline.

---

## 3. Work Implemented

### 3.1 Multi-Tiered Resilient Fitting Engine ([`src/mobo_linac/models/gp.py`](file:///home/cspark/Work/projects/mobo-linac/src/mobo_linac/models/gp.py))
- Enhanced `fit_gp_models` and added `_fit_single_mll_resilient` implementing an adaptive three-tier optimization strategy:
  1. **Tier 1 (Fast Quasi-Newton)**: Standard `fit_gpytorch_mll` (L-BFGS-B) with moderate Cholesky jitter (`1e-4`) for fast convergence.
  2. **Tier 2 (First-Order Adam Fallback)**: If Tier 1 raises `ModelFittingError` or non-PSD exceptions, automatically intercept and execute first-order gradient descent via `fit_gpytorch_mll_torch(mll, step_limit=200)` with adaptive jitter (`1e-3`). First-order updates are immune to Hessian inversion failures.
  3. **Tier 3 (Graceful Prior Retention)**: If both Tier 1 and Tier 2 fail, log a warning and retain the prior/initialized hyperparameter state with `mll.eval()`, preventing fatal crashes and allowing the optimization campaign to progress smoothly.

---

## 4. Verification Results

### 4.1 Checkpoint Iteration 06/07 Reproduction Test
Tested `SurrogatePipeline.fit(train_X, train_Y)` on the exact 64-point training dataset from `checkpoint_iter_06.pt` that previously failed:
```text
Standard L-BFGS GP hyperparameter fitting failed (ModelFittingError: All attempts to fit the model have failed.). Attempting first-order Adam fallback optimization...
Pipeline successfully fitted on iteration 6 data!
Predict mean shape: torch.Size([5, 3]) var shape: torch.Size([5, 3])
```
Successfully recovered and generated candidate proposals (`Shape: torch.Size([4, 6])`).

### 4.2 Unit Test Verification
```bash
pytest tests/test_gp_models.py -v
```
**Output:**
```
tests/test_gp_models.py::test_gp_deterministic_fixed_noise_mode PASSED   [ 12%]
tests/test_gp_models.py::test_gp_measured_fixed_noise_mode PASSED        [ 25%]
tests/test_gp_models.py::test_gp_inferred_noise_mode PASSED              [ 37%]
tests/test_gp_models.py::test_surrogate_pipeline_integration PASSED      [ 50%]
tests/test_gp_models.py::test_repeatability_utility PASSED               [ 62%]
tests/test_gp_models.py::test_relative_noise_variance_scaling PASSED     [ 75%]
tests/test_gp_models.py::test_tune_gp_hyperparameters PASSED             [ 87%]
tests/test_gp_models.py::test_build_scalarized_gp_model PASSED           [100%]
============================== 8 passed in 17.75s ==============================
```

---

## 5. Key Files Created / Modified
- Modified: [`src/mobo_linac/models/gp.py`](file:///home/cspark/Work/projects/mobo-linac/src/mobo_linac/models/gp.py)
- Created: [`docs/exec-plans/completed/TASK_113_resilient_gp_fitting_and_fallback.md`](file:///home/cspark/Work/projects/mobo-linac/docs/exec-plans/completed/TASK_113_resilient_gp_fitting_and_fallback.md)
