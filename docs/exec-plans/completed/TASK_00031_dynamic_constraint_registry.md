# Task 30 Summary: Dynamic Constraint Registry (`mobo_linac.constraints`)

## Summary

Task 30 refactored the constraint evaluation architecture to eliminate hardcoded tensor column magic numbers and hardcoded threshold values in `src/mobo_linac/cli.py` by implementing a dynamic constraint function factory `get_botorch_constraint_functions()` in `src/mobo_linac/constraints.py`.

## Accomplishments

1. **Dynamic Factory Function (`get_botorch_constraint_functions`)**:
   - Added `get_botorch_constraint_functions(config)` to `src/mobo_linac/constraints.py`.
   - Dynamically builds BoTorch tensor constraint functions ($c_i(Y) \le 0$) directly from `MoboConfig` / `ConstraintsConfig` thresholds (`max_sigma_x_m`, `max_sigma_y_m`, `max_sigma_xp_rad`, `max_sigma_yp_rad`, `max_sigma_z_m`, `min_mean_kinetic_energy_eV`, `max_mean_kinetic_energy_eV`).
2. **Eliminated Magic Numbers in `cli.py`**:
   - Replaced hardcoded inline constraint lambda functions (`c_sigma_x`, `c_sigma_y`, `c_E_min`, `c_E_max`, etc.) and magic threshold numbers (`1.0e-3`, `195e6`, `205e6`) in `src/mobo_linac/cli.py` with `get_botorch_constraint_functions()`.
3. **Unit Tests & Verification**:
   - Added `test_get_botorch_constraint_functions()` unit test to `tests/test_constraints.py`.
   - All tests in `tests/test_constraints.py` passed in 0.09s.
   - Entire pytest test suite (**76/76 unit tests**) passed cleanly.

## Status

**Completed**. Dynamic constraint registry implemented, magic numbers removed, unit tests passed, and execution summary saved.
