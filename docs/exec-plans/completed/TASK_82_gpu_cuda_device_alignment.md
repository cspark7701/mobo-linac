# Task Execution Summary: TASK_82 — Multi-Device GPU/CUDA Tensor Alignment Fix

## 1. Overview & Objectives
- **Goal**: Resolve multi-device tensor mismatches (`RuntimeError: Expected all tensors to be on the same device, but got tensors is on cpu, different from other tensors on cuda:...`) occurring on machines equipped with NVIDIA GPUs / CUDA.

---

## 2. Root Cause Analysis
- When CUDA was available on the target machine, `build_gp_models()` placed the training data tensors on `cuda:0` while `covar_module`, `input_transform`, and `SingleTaskGP` modules were created with CPU default parameters unless explicitly transferred.
- When constructing acquisition functions (`build_acquisition_function`), `ref_point`, `train_X`, and `train_Y` remained on CPU while the GP surrogate model was on CUDA.
- In candidate optimization and diagnostics (`compute_predictive_diagnostics`, `generate_next_candidates`, `MoboCampaignRunner`), `bounds` and test input tensors remained on CPU while being passed into CUDA-bound models/acquisition functions, and `.tolist()` was called on GPU tensors without `.cpu()`.

---

## 3. Work Implemented

### 3.1 Surrogate Model Device Synchronization ([`src/mobo_linac/models/gp.py`](file:///home/cspark/Work/projects/mobo-linac/src/mobo_linac/models/gp.py))
- Explicitly transferred `SingleTaskGP` instances and `ModelListGP` to `target_device`:
  ```python
  gp = SingleTaskGP(...).to(device=target_device, dtype=torch.double)
  model_list = ModelListGP(*models).to(device=target_device, dtype=torch.double)
  ```

### 3.2 Acquisition Function Device Invariance ([`src/mobo_linac/acquisition/mobo.py`](file:///home/cspark/Work/projects/mobo-linac/src/mobo_linac/acquisition/mobo.py))
- Inferred `model_device` from `model.parameters()` in `build_acquisition_function`.
- Explicitly transferred `ref_point_dbl`, `train_X_dbl`, `train_Y_dbl`, and `feasible_mask` to `model_device`.
- In `generate_next_candidates`, inferred `target_device` from `acq_func` and moved `bounds` and Sobol fallbacks to `target_device`.

### 3.3 Campaign Runner Device Safety ([`src/mobo_linac/campaigns/runner.py`](file:///home/cspark/Work/projects/mobo-linac/src/mobo_linac/campaigns/runner.py))
- Synchronized `SingleTaskGP` and `Normalize` bounds in `scalarized_bo` mode to `self.device`.
- Synchronized composite `ModelListGP` in constrained mode.
- Used `.detach().cpu().tolist()` for all candidate tensor conversions.

### 3.4 Diagnostics Device Invariance ([`src/mobo_linac/models/diagnostics.py`](file:///home/cspark/Work/projects/mobo-linac/src/mobo_linac/models/diagnostics.py))
- Dynamically transferred input evaluation data `train_X` and `train_Y` to `model_device`.

### 3.5 Test Suite Device Adaptivity ([`tests/test_gp_models.py`](file:///home/cspark/Work/projects/mobo-linac/tests/test_gp_models.py), [`tests/test_gp_and_acquisition.py`](file:///home/cspark/Work/projects/mobo-linac/tests/test_gp_and_acquisition.py))
- Updated `test_X` and evaluation tensors to dynamically match `model_device`.

---

## 4. Verification Results

```bash
pytest tests/test_checkpoint_resume.py tests/test_cli.py tests/test_gp_and_acquisition.py tests/test_gp_models.py -v
```
**Output:**
```
============================= test session starts ==============================
collected 20 items

tests/test_checkpoint_resume.py::test_uninterrupted_vs_resumed_campaign PASSED [  5%]
tests/test_checkpoint_resume.py::test_missing_checkpoint_raises PASSED   [ 10%]
tests/test_checkpoint_resume.py::test_corrupted_checkpoint_raises PASSED [ 15%]
tests/test_cli.py::test_cli_help PASSED                                  [ 20%]
tests/test_cli.py::test_cli_dry_run PASSED                               [ 25%]
tests/test_cli.py::test_cli_mock_evaluator_workflows PASSED              [ 30%]
tests/test_gp_and_acquisition.py::test_gp_kernel_and_ard_dimensions PASSED [ 35%]
tests/test_gp_and_acquisition.py::test_gp_noise_model_and_likelihood PASSED [ 40%]
tests/test_gp_and_acquisition.py::test_gp_posterior_output_shape PASSED  [ 45%]
tests/test_gp_and_acquisition.py::test_acquisition_function_construction PASSED [ 50%]
tests/test_gp_and_acquisition.py::test_predictive_diagnostics_calculation PASSED [ 55%]
tests/test_gp_and_acquisition.py::test_constrained_acquisition_construction PASSED [ 60%]
tests/test_gp_and_acquisition.py::test_configurable_acquisition_optimization_budget PASSED [ 65%]
tests/test_gp_and_acquisition.py::test_resilient_acquisition_sobol_fallback PASSED [ 70%]
tests/test_gp_models.py::test_gp_deterministic_fixed_noise_mode PASSED   [ 75%]
tests/test_gp_models.py::test_gp_measured_fixed_noise_mode PASSED        [ 80%]
tests/test_gp_models.py::test_gp_inferred_noise_mode PASSED              [ 85%]
tests/test_gp_models.py::test_surrogate_pipeline_integration PASSED      [ 90%]
tests/test_gp_models.py::test_repeatability_utility PASSED               [ 95%]
tests/test_gp_models.py::test_relative_noise_variance_scaling PASSED     [100%]

======================== 20 passed in 165.20s (0:02:45) ========================
```

---

## 5. Key Files Modified
- `src/mobo_linac/models/gp.py`
- `src/mobo_linac/acquisition/mobo.py`
- `src/mobo_linac/campaigns/runner.py`
- `src/mobo_linac/models/diagnostics.py`
- `tests/test_gp_models.py`
- `tests/test_gp_and_acquisition.py`
