# TASK_57: Config-Driven Dynamic Parameter Mapping & Beamline Element Decoupling

**Date**: 2026-08-14  
**Author**: Chong Shik Park  
**Status**: COMPLETED  
**Refactoring Task Ref**: `docs/04_refactor_tasks/TASK_02_dynamic_parameter_mapping.md`

---

## 1. Overview & Problem

In earlier versions of `mobo_linac`, `run_astra_eval` in [`src/mobo_linac/astra/runner.py`](file:///home/cspark/Work/projects/mobo_linac/src/mobo_linac/astra/runner.py) hardcoded the injection of exactly 6 parameter vector indices into 8 specific ASTRA namelist variables:
```python
astra_sim["solenoid:maxb(1)"] = float(parameters[0])
astra_sim["quadrupole:q_grad(1)"] = float(parameters[1])
astra_sim["quadrupole:q_grad(2)"] = float(parameters[2])
astra_sim["cavity:phi(1)"] = float(parameters[3])
astra_sim["cavity:phi(2)"] = float(parameters[4])
astra_sim["cavity:phi(3)"] = float(parameters[4])
astra_sim["cavity:phi(4)"] = float(parameters[5])
astra_sim["cavity:phi(5)"] = float(parameters[5])
```
This hardcoding bypassed `MoboConfig.design_variables`, preventing users from optimizing linac variants with decoupled cavities (e.g. independent ACC1 and ACC2 phases), additional quadrupole magnets, or alternate RF amplitude variables.

---

## 2. Implementation Summary

1. **Dynamic Parameter Mapper (`apply_parameters_to_astra`)** ([`src/mobo_linac/astra/runner.py`](file:///home/cspark/Work/projects/mobo_linac/src/mobo_linac/astra/runner.py)):
   - Implemented `apply_parameters_to_astra(astra_sim, parameters, config=None) -> List[str]`.
   - When `config` is provided (either as a `MoboConfig` or dictionary with `design_variables`), parameters are dynamically assigned to `dv.astra_key` or `dv.coupled_targets` if `dv.is_coupled == True`.
   - If `config` is `None`, cleanly falls back to the nominal 6-parameter mapping for full backward compatibility.
   - Raises descriptive `ValueError` if the length of `parameters` does not match the configured design variables count.

2. **Runner & Class Updates** ([`src/mobo_linac/astra/runner.py`](file:///home/cspark/Work/projects/mobo_linac/src/mobo_linac/astra/runner.py)):
   - Updated `run_astra_eval()` to accept optional `config` and record dynamically applied parameter names in the JSON `manifest.json`.
   - Updated `AstraRunner` class constructor and `run()` method to store and forward `config`.

3. **Parallel Execution Layer** ([`src/mobo_linac/execution/parallel.py`](file:///home/cspark/Work/projects/mobo_linac/src/mobo_linac/execution/parallel.py)):
   - Updated `evaluate_candidates_parallel()`, `_worker_eval_task()`, and `BatchEvaluator` to serialize and propagate configuration dictionaries across worker processes.

4. **Campaign Integration** ([`src/mobo_linac/campaigns/runner.py`](file:///home/cspark/Work/projects/mobo_linac/src/mobo_linac/campaigns/runner.py)):
   - Passed `self.config` from `MoboCampaignRunner` to `BatchEvaluator`.

5. **Unit Tests** ([`tests/test_parameter_mapping.py`](file:///home/cspark/Work/projects/mobo_linac/tests/test_parameter_mapping.py)):
   - Added unit test suite covering:
     - Nominal 6-parameter fallback mapping.
     - Dynamic mapping via loaded `MoboConfig` YAML.
     - Custom 7-parameter configuration with decoupled cavity phases.
     - Dimension mismatch exception validation.
     - `AstraRunner` configuration retention.

---

## 3. Validation Results

```bash
pytest -m "not integration" tests/test_parameter_mapping.py tests/test_astra_workdirs.py tests/test_parallel_evaluation.py -v
```
- **16 passed, 2 deselected** in 5.99s.
