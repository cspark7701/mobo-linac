# Task Execution Summary: TASK_63 — Configurable Acquisition Multi-Restart Optimization Budget (Refactor Task 08)

## 1. Overview & Objectives
- **Task Reference**: `docs/04_refactor_tasks/TASK_08_configurable_acquisition_optimization.md`
- **Goal**: Refactor acquisition function optimization in `src/mobo_linac/acquisition/mobo.py`, `src/mobo_linac/config.py`, and `src/mobo_linac/campaigns/runner.py` to allow user-configurable multi-restart parameters (`num_restarts`, `raw_samples`, `maxiter`, `batch_limit`), enabling fast unit testing and scalable production campaign tuning.

---

## 2. Work Implemented

### 2.1 Configurable `ExecutionConfig` Acquisition Fields
- **Location**: `src/mobo_linac/config.py`
- Added acquisition optimization fields to `ExecutionConfig`:
  - `acqf_num_restarts: int = 20`
  - `acqf_raw_samples: int = 1024`
  - `acqf_maxiter: int = 200`
  - `acqf_batch_limit: int = 5`

### 2.2 Refactored `generate_next_candidates` with Device & Budget Controls
- **Location**: `src/mobo_linac/acquisition/mobo.py`
- Extended `generate_next_candidates()` signature:
  ```python
  def generate_next_candidates(
      acq_func: Any,
      bounds: torch.Tensor,
      batch_size: int = 8,
      num_restarts: int = 20,
      raw_samples: int = 1024,
      maxiter: int = 200,
      batch_limit: int = 5,
      options: Optional[Dict[str, Any]] = None,
      device: Optional[Union[torch.device, str]] = None,
  ) -> Tuple[torch.Tensor, torch.Tensor]:
  ```
- Target device placement ensures tensors are created on the target compute device (`cpu` or `cuda`).
- Options dictionary allows fine-grained L-BFGS tuning.

### 2.3 Connected Acquisition Optimization to `MoboCampaignRunner`
- **Location**: `src/mobo_linac/campaigns/runner.py`
- Updated both single-objective scalarized (`qLogNEI`) and multi-objective (`qLogNEHVI`/`qLogEHVI`) candidate generation routines to pass configured `self.config.execution` settings.

### 2.4 Test Suite & Unit Verification
- **Location**: `tests/test_gp_and_acquisition.py`
- Added `test_configurable_acquisition_optimization_budget` verifying:
  - `ExecutionConfig` default budget parameters.
  - Rapid candidate generation with a compact restart budget (`num_restarts=2, raw_samples=32, maxiter=10, batch_limit=2`).
  - Output candidate bounds satisfaction and shape integrity `(batch_size, 6)`.

---

## 3. Verification & Test Results

```bash
pytest tests/test_gp_and_acquisition.py -v
```
**Output:**
```
tests/test_gp_and_acquisition.py::test_gp_kernel_and_ard_dimensions PASSED [ 14%]
tests/test_gp_and_acquisition.py::test_gp_noise_model_and_likelihood PASSED [ 28%]
tests/test_gp_and_acquisition.py::test_gp_posterior_output_shape PASSED  [ 42%]
tests/test_gp_and_acquisition.py::test_acquisition_function_construction PASSED [ 57%]
tests/test_gp_and_acquisition.py::test_predictive_diagnostics_calculation PASSED [ 71%]
tests/test_gp_and_acquisition.py::test_constrained_acquisition_construction PASSED [ 85%]
tests/test_gp_and_acquisition.py::test_configurable_acquisition_optimization_budget PASSED [100%]

============================== 7 passed in 5.17s ===============================
```

Full core test suite (30 passed in 7.86s):
```bash
pytest tests/test_config.py tests/test_gp_and_acquisition.py tests/test_pareto.py tests/test_robustness_analysis.py tests/test_result_serialization.py tests/test_parameter_mapping.py -v
============================== 30 passed in 7.86s ==============================
```

---

## 4. Key Files Modified
- `src/mobo_linac/config.py`: Added acquisition optimization parameters to `ExecutionConfig`.
- `src/mobo_linac/acquisition/mobo.py`: Configurable optimization budgets and device placement in `generate_next_candidates`.
- `src/mobo_linac/campaigns/runner.py`: Connected execution config to candidate proposal calls.
- `tests/test_gp_and_acquisition.py`: Added budget configuration unit test.
