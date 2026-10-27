# Task 04 Summary: Align GP Kernels, Noise Assumptions, and Acquisition Methods

## Explicit GP Kernel Construction & ARD
- Enhanced `build_gp_models` in `src/mobo_linac/models/gp.py`:
  - Explicit covariance kernel construction supporting both `matern52` (Matérn-5/2 with $\nu = 2.5$) and `rbf` (RBF kernel).
  - Explicit Automatic Relevance Determination (ARD) with `ard_num_dims = input_dim` (6D design space).

## Simulator Repeatability & Noise Treatment
- Configurable observation noise modes:
  - `noise_mode = "fixed"`: Near-zero fixed observation noise variance ($\sigma^2_{\text{obs}} = 10^{-6}$) for deterministic ASTRA simulation tracking.
  - `noise_mode = "inferred"`: Inferred observation noise likelihood for stochastic simulation variations.

## Acquisition Functions & Algorithm Matching
- Updated `build_acquisition_function` in `src/mobo_linac/acquisition/mobo.py`:
  - `qLogEHVI`: For deterministic ASTRA simulations without observation noise.
  - `qLogNEHVI`: For baseline evaluations with noise.
  - `qEHVI` and `qNEHVI`: Backward compatibility for standard MC acquisition calls.

## Predictive Diagnostics Implementation
- Implemented `compute_predictive_diagnostics` in `src/mobo_linac/models/diagnostics.py`:
  - Standardized residuals ($z = (y - \mu) / \sigma$)
  - Objective-specific RMSE, MAE, and $R^2$ correlation metrics
  - Leave-one-out (LOO) cross-validation error estimates

## Tests & Verification
- Created `tests/test_gp_and_acquisition.py`:
  - `test_gp_kernel_and_ard_dimensions`: Verified Matérn-5/2 ($\nu=2.5$) and RBF kernels with `ard_num_dims=6`.
  - `test_gp_noise_model_and_likelihood`: Verified fixed near-zero noise variance and inferred Gaussian likelihoods.
  - `test_gp_posterior_output_shape`: Verified posterior mean and variance output shapes $(N, M)$.
  - `test_acquisition_function_construction`: Verified construction of `qLogEHVI`, `qLogNEHVI`, `qEHVI`, and `qNEHVI`.
  - `test_predictive_diagnostics_calculation`: Verified computation of RMSE, $R^2$, and standardized residuals.
- Pytest suite executed successfully: 57/57 unit tests passed.

## Acceptance Criteria Status
- [x] Code and manuscript use the same explicit kernel description (Matérn-5/2 ARD / RBF ARD).
- [x] Noise treatment is explicitly parameterized (`fixed` near-zero vs `inferred`).
- [x] Acquisition choice supported for deterministic (`qLogEHVI`) and noisy (`qLogNEHVI`) regimes.
- [x] Predictive diagnostics generated automatically.
