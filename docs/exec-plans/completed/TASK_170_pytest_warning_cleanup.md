# Task Completion Summary: Task 170

## Summary
Removed every entry from the pytest warnings summary. Warnings caused by the test code were fixed in the tests. Known third-party notices are ignored by exact message in the pytest configuration. Warnings raised by `mobo_linac` itself remain errors (TASK_163). Model numerics and beam physics are unchanged.

## Key Changes
- **Fixed in tests**:
  - `test_gp_models.py::test_exact_loo_matches_explicit_leave_one_out_conditioning` computed its reference values from tensors that still carried an autograd graph (`UserWarning` on scalar conversion). The reference values are now computed with autograd off and compared as plain numbers.
  - `test_result_serialization.py::test_journal_appends_are_constant_time_without_rereading` replaced the durable append with a lambda that left files open (`ResourceWarning`). The replacement now writes through a context manager.
- **Scoped to the tests that need it**: the four tests in `test_gp_and_acquisition.py` that construct the legacy `qEHVI`/`qNEHVI` acquisitions on purpose ignore BoTorch's `NumericsWarning` for those classes (test marks).
- **Ignored by message in `pyproject.toml`** (third-party sources only):
  - Deprecations inside dependencies: `torch.jit.script` (torch), the `pmd_beamphysics` package name and `unit()` (lume-astra), and `set_under` (openPMD-beamphysics).
  - GPyTorch `NumericalWarning`s:
    - "Very small noise values detected": the deterministic fixed noise (relative 1e-6 of Var(Y)) is about 1e-6 after outcome standardization, and GPyTorch rounds it up to its double-precision floor of 1e-6. The effect is negligible.
    - "Negative variance values detected": round-off clipping for near-noiseless simulation data.
  - These filters apply to the test run only; package runtime behavior is unchanged.

## Skipped Tests
- Seven tests skip because CUDA is unavailable. The environment has torch 2.12.0 without a CUDA build, and the host has no NVIDIA driver.
  - `test_gp_and_acquisition.py::test_cuda_fallback_preserves_real_gp_placement` (2 parametrizations).
  - `test_reporting_metrics.py::test_normalization_and_hypervolume_use_input_placement` (CUDA float32/float64).
  - `test_objectives.py::test_transforms_preserve_tensor_placement_and_dtype` (CUDA float32/float64).
  - `test_checkpoint_resume.py::test_cuda_rng_continuation`.
- The two real-ASTRA tests are marked `integration`. They are deselected by `-m "not integration"` and pass when run (TASK_168).

## Validation Results
Full unit suite: 777 passed, 7 skipped (CUDA), 2 deselected (integration), with no warnings summary in any test file.

## Status
Completed.
