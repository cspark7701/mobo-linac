# Task Completion Summary: Task 187

## Summary
Fixed `tests/test_gp_models.py::test_mean_only_outcome_keeps_input_scaling_warnings_visible` by explicitly validating normalized training inputs when building the project's custom-kernel GPs.

## Key Changes
- Reproduced the failure in the installed BoTorch 0.17.2 environment: no input-scaling warning was emitted for inputs outside the configured unit-cube bounds.
- Inspected the installed SingleTaskGP constructor and validation helpers. With a custom covariance module, the constructor uses `check_nans_only=True`, bypassing input scaling and outcome standardization checks. The existing selective outcome-warning filter was not swallowing the input warning; BoTorch never generated it.
- `models/gp.py` now checks the configured Normalize transform's output with BoTorch's `check_min_max_scaling` before constructing the GP. The same input transform is retained by the model, and BoTorch's `validate_input_scaling` setting controls the explicit check.
- Regression tests cover constant outcomes with fixed and inferred noise, non-unit physical bounds with constant and ordinary outcomes, retained original training inputs, unmodified extrapolating normalized values, and explicitly disabled validation.

## Acceptance Criteria
- [x] The reported warning-preservation regression passes.
- [x] Input scaling warnings remain visible for custom-kernel GPs.
- [x] Input/outcome transforms, configured kernels and noise settings retain their existing behavior.
- [x] Validation can still be disabled through the existing BoTorch setting.

## Validation Results
Used `/home/cspark/Work/simulation_codes-working/miniforge3/envs/linac-opt/bin/python` with `PYTHONPATH=src OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1`.

- Before the fix, the reported isolated test failed with `DID NOT WARN`.
- `python -m pytest tests/test_gp_models.py tests/test_gp_and_acquisition.py tests/test_surrogate_pipeline.py -q --tb=short`: **74 passed, 6 skipped**, 16.98 seconds. CUDA-dependent cases were skipped in this environment.
- `python -m ruff check src/mobo_linac/models/gp.py tests/test_gp_models.py`: passed.
- `git diff --check`: passed.

## Scope and Limitations
- This adds explicit diagnostic validation for normalized inputs; it does not clip or reject out-of-bounds observations by default.
- Uses BoTorch's existing warning category, tolerance and validation setting. Mean-only outcome scaling and its selective expected-warning suppression are preserved.
- No beam physics, simulation settings or archived outputs changed. No ASTRA simulations, commits, pushes or remote workflow queries were performed. The entire pytest suite was not rerun.

## Status
Completed.
