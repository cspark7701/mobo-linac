# TASK_58: Longitudinal Exit-Plane Verification & Premature Loss Trapping

**Date**: 2026-08-14  
**Author**: Chong Shik Park  
**Status**: COMPLETED  
**Refactoring Task Ref**: `docs/04_refactor_tasks/TASK_03_exit_plane_loss_detection.md`

---

## 1. Overview & Problem

In ASTRA simulations, when total beam loss occurs prematurely along the linac (for example, hitting the aperture or beam pipe at $z = 3.5\text{ m}$), ASTRA terminates particle tracking and outputs statistical profiles up to that coordinate.

If statistics are extracted naively using `raw_stats["norm_emit_x"][-1]`, the evaluator receives emittance calculated at $z = 3.5\text{ m}$ (where kinetic energy is only $\sim 30\text{ MeV}$). In severe collimation scenarios where only a tiny fraction of core particles survive prior to loss, the emittance can appear artificially small. Without explicit longitudinal exit-plane verification, these partial tracking artifacts could contaminate GP training data as valid simulations.

---

## 2. Implementation Summary

1. **FailureCategory Semantic Expansion** ([`src/mobo_linac/evaluation.py`](file:///home/cspark/Work/projects/mobo_linac/src/mobo_linac/evaluation.py)):
   - Added `PREMATURE_BEAM_LOSS = "PREMATURE_BEAM_LOSS"` to `FailureCategory`.

2. **Longitudinal Coordinate Diagnostics Extraction** ([`src/mobo_linac/astra/runner.py`](file:///home/cspark/Work/projects/mobo_linac/src/mobo_linac/astra/runner.py)):
   - Extracted final particle tracking coordinate `z_final = float(raw_stats["z"][-1])` if `"z"` is present in `raw_stats`.
   - Recorded `diagnostics["z_final_m"]`, `diagnostics["z_final"]`, and `diagnostics["z_stop_m"]`.

3. **Exit-Plane Validation & Loss Trapping** ([`src/mobo_linac/evaluation.py`](file:///home/cspark/Work/projects/mobo_linac/src/mobo_linac/evaluation.py)):
   - In `create_evaluation_result()`, verified the final longitudinal coordinate against the linac exit plane target (default 16.2 m from `astra.in`, or `config.execution.z_stop_m`).
   - If tracking terminates early ($z_{\text{final}} < z_{\text{target}} - 0.1\text{ m}$), the simulation is rejected with:
     - `simulation_valid = False`
     - `physically_feasible = False`
     - `failure_category = FailureCategory.PREMATURE_BEAM_LOSS.value`
     - `failure_reason = "Premature tracking termination at z = ... m (expected exit plane >= ... m)"`

4. **GP Training Filter Exclusion**:
   - Because `get_train_tensors(exclude_invalid=True)` filters out `res.simulation_valid == False`, premature beam loss results are strictly excluded from Gaussian Process surrogate training tensors.

5. **Unit Test Suite** ([`tests/test_evaluation_result.py`](file:///home/cspark/Work/projects/mobo_linac/tests/test_evaluation_result.py), [`tests/test_transmission_and_diagnostics.py`](file:///home/cspark/Work/projects/mobo_linac/tests/test_transmission_and_diagnostics.py)):
   - Added test cases verifying:
     - Premature aborts at $z = 5.0\text{ m}$ and $z = 12.0\text{ m}$ are caught and classified as `PREMATURE_BEAM_LOSS`.
     - Complete linac tracking to $z = 16.2\text{ m}$ is marked `simulation_valid = True`.
     - `get_train_tensors` excludes `PREMATURE_BEAM_LOSS` records from GP training.

---

## 3. Validation Results

```bash
pytest tests/test_evaluation_result.py tests/test_transmission_and_diagnostics.py -v
```
- **14 passed** in 1.27s.
