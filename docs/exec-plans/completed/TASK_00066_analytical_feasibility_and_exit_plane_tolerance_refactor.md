# Task Execution Summary: TASK_65 — Analytical Probability of Feasibility & Dynamic Exit-Plane Detection (Refactor A)

## 1. Overview & Objectives
- **Goal**: Implement Refactor A to enhance physical surrogate accuracy and robustness:
  1. Fix the analytical Probability of Feasibility ($P_{\text{feas}}$) calculation in [`SurrogatePipeline`](file:///home/cspark/Work/projects/mobo_linac/src/mobo_linac/models/pipeline.py) by computing exact Normal CDF probabilities for physical constraint channels against operational thresholds rather than assuming unshifted $c \le 0$.
  2. Dynamically link the longitudinal exit-plane detection threshold to configurable execution parameters (`z_stop_m` and `z_loss_tolerance_m`) in [`ExecutionConfig`](file:///home/cspark/Work/projects/mobo_linac/src/mobo_linac/config.py) and [`EvaluationResult`](file:///home/cspark/Work/projects/mobo_linac/src/mobo_linac/evaluation.py).

---

## 2. Work Implemented

### 2.1 Analytical Normal CDF Feasibility Formulation in `SurrogatePipeline`
- **Location**: `src/mobo_linac/models/pipeline.py`
- Updated `SurrogatePipeline.__init__` to accept `constraints_config: Optional[Union[ConstraintsConfig, MoboConfig]]`.
- Refactored `predict_probability_of_feasibility(X: Tensor) -> Tensor`:
  - For 7-channel physical linac diagnostics (`[sigma_x, sigma_y, sigma_xp, sigma_yp, sigma_z, energy, transmission]`):
    - **Upper Bounds**: $P(Y \le \text{max}) = \Phi\left(\frac{\text{max} - \mu}{\sigma}\right)$
    - **Two-Sided Energy Bounds**: $P(E_{\text{min}} \le E \le E_{\text{max}}) = \Phi\left(\frac{E_{\text{max}} - \mu_E}{\sigma_E}\right) - \Phi\left(\frac{E_{\text{min}} - \mu_E}{\sigma_E}\right)$
    - **Lower Bound Transmission**: $P(T \ge T_{\text{min}}) = \Phi\left(\frac{\mu_T - T_{\text{min}}}{\sigma_T}\right)$
    - Overall Feasibility: $P_{\text{feas}}(X) = \prod_{i=1}^7 P_i(X)$ clamped to $[0, 1]$.
  - Includes a fallback for standard zero-thresholded constraints ($c_i(x) \le 0$).

### 2.2 Configurable Exit Plane Tracking & Loss Tolerance
- **Location**: `src/mobo_linac/config.py`, `src/mobo_linac/evaluation.py`, `src/mobo_linac/campaigns/runner.py`
- Extended `ExecutionConfig` with `z_stop_m: float = 16.2` and `z_loss_tolerance_m: float = 0.1`.
- In `create_evaluation_result()`, premature tracking loss threshold is evaluated dynamically as $z_{\text{final}} < (z_{\text{stop}} - z_{\text{tol}})$.
- Updated `MoboCampaignRunner` to pass `constraints_config=self.config.constraints` when creating `SurrogatePipeline`.

### 2.3 Verification & Unit Testing
- **Location**: `tests/test_surrogate_pipeline.py`
- Added `test_surrogate_pipeline_analytical_physical_feasibility` validating that feasible interior candidate predictions yield high analytical feasibility ($P_{\text{feas}} > 0.8$) instead of degenerating to $0.0$.

---

## 3. Verification Results

```bash
pytest tests/test_surrogate_pipeline.py -v
```
**Output:**
```
tests/test_surrogate_pipeline.py::test_surrogate_pipeline_fit_and_prediction PASSED [ 33%]
tests/test_surrogate_pipeline.py::test_surrogate_pipeline_constraint_surrogates PASSED [ 66%]
tests/test_surrogate_pipeline.py::test_surrogate_pipeline_analytical_physical_feasibility PASSED [100%]

============================== 3 passed in 2.40s ===============================
```

Full core regression test suite:
```bash
pytest tests/test_config.py tests/test_surrogate_pipeline.py tests/test_gp_and_acquisition.py tests/test_pareto.py tests/test_robustness_analysis.py tests/test_result_serialization.py tests/test_parameter_mapping.py tests/test_evaluation_result.py tests/test_transmission_and_diagnostics.py -v
============================= 47 passed in 15.20s ==============================
```

---

## 4. Key Files Modified
- `src/mobo_linac/models/pipeline.py`: Added analytical multi-channel feasibility computation in `SurrogatePipeline`.
- `src/mobo_linac/config.py`: Added `z_stop_m` and `z_loss_tolerance_m` to `ExecutionConfig`.
- `src/mobo_linac/evaluation.py`: Dynamic exit plane tolerance checking in `create_evaluation_result`.
- `src/mobo_linac/campaigns/runner.py`: Passed `constraints_config` to `SurrogatePipeline`.
- `tests/test_surrogate_pipeline.py`: Added analytical physical feasibility test.
