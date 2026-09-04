# Task Execution Summary: TASK_110 — Pytest Device Alignment Fix & Workspace Cleanup Script

## 1. Overview & Objectives
- **Goal**:
  1. Resolve failing unit test in `tests/test_gp_models.py` (`test_build_scalarized_gp_model`) caused by device mismatch when running on CUDA-enabled systems.
  2. Implement an automated, safe workspace cleanup script (`cleanup.sh`) to purge transient simulation outputs, caches, and build artifacts without disturbing essential simulation inputs or tracked repository assets.

---

## 2. Work Implemented

### 2.1 Pytest CUDA Device Mismatch Resolution ([`tests/test_gp_models.py`](file:///home/cspark/Work/projects/mobo-linac/tests/test_gp_models.py))
- **Issue Diagnosed**:
  - `build_scalarized_gp_model` automatically targets the active device (`cuda:0` when available via `mobo_linac.utils.device.get_device()`).
  - In `test_build_scalarized_gp_model`, `test_X` was created as a CPU tensor (`torch.rand(4, 6, dtype=torch.double)`), resulting in:
    ```
    RuntimeError: Expected all tensors to be on the same device, but got tensors is on cpu, different from other tensors on cuda:0 (when checking argument in method wrapper_CUDA_cat)
    ```
- **Fix**:
  - Dynamically inspect the device of the fitted model parameters:
    ```python
    model_device = next(fitted_gp.parameters()).device
    test_X = torch.rand(4, 6, dtype=torch.double, device=model_device)
    ```
  - Re-tested `tests/test_gp_models.py`; all 8 tests pass cleanly on both CPU and CUDA environments.

### 2.2 Workspace Cleanup Script ([`scripts/cleanup.sh`](file:///home/cspark/Work/projects/mobo-linac/scripts/cleanup.sh))
- Implemented executable bash script `scripts/cleanup.sh` (`chmod +x scripts/cleanup.sh`):
  - **Granular Target Selection**:
    - `--cache` / `cache`: Cleans `.pytest_cache`, `__pycache__`, `*.pyc`, `*.pyo`, `*.pyd`, `build/`, `dist/`, `*.egg-info/`, and editor swap files.
    - `--results` / `results`: Cleans campaign simulation and optimization run folders (`results/*`) while preserving `.gitkeep`.
    - `--results-notebooks` / `results_notebooks`: Cleans interactive notebook run artifacts (`results_notebooks/*`, `results_notebook/*`).
    - `--img` / `img`: Cleans generated plots and visual figures (`img/*`).
    - `--docs` / `docs` / `latex`: Cleans transient LaTeX build files (`docs/paper/*.{aux,bbl,blg,log,out,toc}`).
    - `-a` / `--all` / `all`: Cleans all targets (default if no target flags/arguments are passed).
  - **Execution Modes**: Supports `-n` / `--dry-run` to preview deletions and `-f` / `--force` to bypass interactive confirmation prompts.
  - **Safeguards**: Never touches core physics simulation input files (`pal_photo2.ini`, `PAL_SOL_A.dat`, `TWS_Sband.dat`, `gun.dat`, `astra.in`) or binary executables in `bin/`.

---

## 3. Verification Results

### 3.1 Unit Test Verification
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
============================== 8 passed in 10.59s ==============================
```

```bash
pytest tests/test_scalarized_bo.py tests/test_surrogate_pipeline.py tests/test_gp_and_acquisition.py -v
```
**Output:**
```
======================== 17 passed in 559.43s (0:09:19) ========================
```

### 3.2 Cleanup Script Dry-Run Verification
```bash
./scripts/cleanup.sh --dry-run
```
Confirmed correct identification of transient items across test caches and bytecode without touching simulation or source files.

---

## 4. Key Files Created / Modified
- Modified: [`tests/test_gp_models.py`](file:///home/cspark/Work/projects/mobo-linac/tests/test_gp_models.py)
- Created: [`scripts/cleanup.sh`](file:///home/cspark/Work/projects/mobo-linac/scripts/cleanup.sh)
- Created: [`docs/exec-plans/completed/TASK_110_pytest_cuda_device_fix_and_cleanup_script.md`](file:///home/cspark/Work/projects/mobo-linac/docs/exec-plans/completed/TASK_110_pytest_cuda_device_fix_and_cleanup_script.md)
