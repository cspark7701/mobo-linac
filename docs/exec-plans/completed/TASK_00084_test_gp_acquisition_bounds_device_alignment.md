# Task Execution Summary: TASK_83 — Bounds Device Alignment in test_gp_and_acquisition.py

## 1. Overview & Objectives
- **Goal**: Fix device mismatch in `test_configurable_acquisition_optimization_budget` and `test_resilient_acquisition_sobol_fallback` in [`tests/test_gp_and_acquisition.py`](file:///home/cspark/Work/projects/mobo-linac/tests/test_gp_and_acquisition.py) where `candidates` on CUDA was compared directly against CPU-bound `bounds[0]` / `bounds[1]`.

---

## 2. Root Cause & Work Implemented

### 2.1 Root Cause
- In `generate_next_candidates`, when GPU/CUDA acceleration is active, `candidates` is returned on `cuda:0`.
- The assertions in `test_configurable_acquisition_optimization_budget` and `test_resilient_acquisition_sobol_fallback`:
  ```python
  assert (candidates >= bounds[0] - 1e-6).all()
  assert (candidates <= bounds[1] + 1e-6).all()
  ```
  performed cross-device elementwise comparisons between a CUDA tensor and a CPU tensor (`bounds`), triggering `RuntimeError: Expected all tensors to be on the same device`.

### 2.2 Fix Applied
- Converted `bounds` to match `candidates.device` before evaluating bounds assertions:
  ```python
  bounds_dev = bounds.to(device=candidates.device, dtype=torch.double)
  assert (candidates >= bounds_dev[0] - 1e-6).all()
  assert (candidates <= bounds_dev[1] + 1e-6).all()
  ```

---

## 3. Verification Results

```bash
pytest tests/test_gp_and_acquisition.py -v
```
**Output:**
```
============================= test session starts ==============================
collected 8 items

tests/test_gp_and_acquisition.py::test_gp_kernel_and_ard_dimensions PASSED [ 12%]
tests/test_gp_and_acquisition.py::test_gp_noise_model_and_likelihood PASSED [ 25%]
tests/test_gp_and_acquisition.py::test_gp_posterior_output_shape PASSED  [ 37%]
tests/test_gp_and_acquisition.py::test_acquisition_function_construction PASSED [ 50%]
tests/test_gp_and_acquisition.py::test_predictive_diagnostics_calculation PASSED [ 62%]
tests/test_gp_and_acquisition.py::test_constrained_acquisition_construction PASSED [ 75%]
tests/test_gp_and_acquisition.py::test_configurable_acquisition_optimization_budget PASSED [ 87%]
tests/test_gp_and_acquisition.py::test_resilient_acquisition_sobol_fallback PASSED [100%]

============================== 8 passed in 8.20s ===============================
```

---

## 4. Key Files Modified
- `tests/test_gp_and_acquisition.py`
