# Task 04 — Centralized Configuration, Units, Objectives, and Constraints

## Summary

Task 04 removed duplicated constants and hardcoded limits across the codebase by establishing a single authoritative YAML configuration file and Python dataclass schema.

## Accomplishments

1. **Central YAML Config**: Created `configs/mobo_200mev.yaml` defining:
   - 6 design variables with explicit bounds, units, nominal values, and coupled phase targets (`cavity:phi(2)` coupled to `cavity:phi(3)`, `cavity:phi(4)` coupled to `cavity:phi(5)`).
   - 3 physical objectives ($\varepsilon_{n,x}$, $\varepsilon_{n,y}$, $\sigma_E$) with physical minimization directions and model space negation conventions.
   - Constraint thresholds ($\sigma_{x,y} \le 1.0$ mm, $\sigma_{xp,yp} \le 1.0$ mrad, $\sigma_z \le 1.0$ mm, $E_{\text{kin}} \in [195, 205]$ MeV, transmission $\ge 90\%$).
2. **Typed Config Parser**: Created `MoboConfig` dataclass in `src/mobo_linac/config.py`.
3. **Canonical Model Space Transformation**: Implemented `transform_to_model_space` and `transform_to_physical_space` in `src/mobo_linac/objectives.py`.
4. **Constraint Evaluator**: Created `ConstraintEvaluator` in `src/mobo_linac/constraints.py`.

## Status

**Completed**. Tested via `tests/test_config.py`, `tests/test_objectives.py`, and `tests/test_constraints.py`.
