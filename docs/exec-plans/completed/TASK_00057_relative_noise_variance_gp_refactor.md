# TASK_56: Relative Observation Noise Scaling for Multi-Scale Surrogate GPs

**Date**: 2026-08-14  
**Author**: Chong Shik Park  
**Status**: COMPLETED  
**Refactoring Task Ref**: `docs/04_refactor_tasks/TASK_01_relative_noise_variance_gp.md`

---

## 1. Overview & Problem

In deterministic simulation optimization with ASTRA, observation noise for Gaussian Processes is fixed near-zero. However, the three optimization objectives have vastly different physical dimensions and variances:
- Normalized emittance $\varepsilon_{n,x}, \varepsilon_{n,y} \sim 10^{-6}\text{ m}\cdot\text{rad}$ (sample variance $\sim 10^{-14}\text{ m}^2$)
- RMS energy spread $\sigma_E \sim 10^6\text{ eV}$ (sample variance $\sim 10^{10}\text{ eV}^2$)

Previously, `fixed_noise_val` was hardcoded to a uniform scalar $1.0\times 10^{-6}$. For emittance, $10^{-6}$ was $> 10^5\times$ larger than the signal variance, causing the GP to treat emittance measurements as pure noise and severely degrading interpolation accuracy.

---

## 2. Implementation Summary

1. **Relative Noise Scaling in `build_gp_models()`** ([`src/mobo_linac/models/gp.py`](file:///home/cspark/Work/projects/mobo_linac/src/mobo_linac/models/gp.py)):
   - Implemented dynamic relative noise computation:
     $$\sigma_{\text{noise}, j}^2 = \max\left(\eta \cdot \operatorname{Var}(Y_{:, j}), \, \epsilon_{\text{min}}\right)$$
     with default relative ratio $\eta = 1.0\times 10^{-6}$ and safe floor $\epsilon_{\text{min}} = 1.0\times 10^{-24}$.
   - Preserved explicit overrides (`train_Yvar`, `objective_noise_variances`, and explicit `fixed_noise_val`).

2. **Configuration Extension** ([`src/mobo_linac/config.py`](file:///home/cspark/Work/projects/mobo_linac/src/mobo_linac/config.py)):
   - Added `relative_noise_ratio: float = 1.0e-6` and `min_noise_variance: float = 1.0e-24` to `GpModelConfig`.
   - Updated dataclass validation to ensure non-negative parameters.

3. **Surrogate Pipeline Integration** ([`src/mobo_linac/models/pipeline.py`](file:///home/cspark/Work/projects/mobo_linac/src/mobo_linac/models/pipeline.py)):
   - Propagated `relative_noise_ratio` and `min_noise_variance` across objective and constraint surrogate models.

4. **Campaign Runner Integration** ([`src/mobo_linac/campaigns/runner.py`](file:///home/cspark/Work/projects/mobo_linac/src/mobo_linac/campaigns/runner.py)):
   - Connected `MoboCampaignRunner` to pass `self.config.model.relative_noise_ratio` and `min_noise_variance` into `SurrogatePipeline`.

5. **Unit Test Suite** ([`tests/test_gp_models.py`](file:///home/cspark/Work/projects/mobo_linac/tests/test_gp_models.py)):
   - Added `test_relative_noise_variance_scaling()` verifying:
     - Standardized likelihood noise is normalized across all objectives to $\approx 10^{-6}$.
     - Physical noise variance scales with physical dimensions ($< 10^{-18}\text{ m}^2$ for emittance, $> 1\text{ eV}^2$ for energy spread).
     - GP interpolation accuracy satisfies $R^2 \ge 0.99$.
     - Standardized posterior variance at training points is near-zero ($\le 10^{-4}$).

---

## 3. Validation Results

```bash
pytest tests/test_gp_models.py tests/test_surrogate_pipeline.py tests/test_gp_and_acquisition.py tests/test_config.py -v
```
- **19 passed** across all model, pipeline, acquisition, and configuration tests in 65s.
