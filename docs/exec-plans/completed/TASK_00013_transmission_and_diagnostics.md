# Task 02 Summary: Implement Transmission and Diagnostic Integrity

## Particle Count & Transmission Extraction
- Implemented `n_particles_initial` and `n_particles_final` extraction in `src/mobo_linac/astra/runner.py`.
- Formulated exact transmission fraction calculation:
  ```python
  transmission_fraction = float(n_particles_final) / float(n_particles_initial)
  ```
- Exported explicit unit-bearing diagnostic names across all evaluation records and DataFrames:
  - `sigma_x_m`, `sigma_y_m`
  - `sigma_xp_rad`, `sigma_yp_rad`
  - `sigma_z_m`
  - `mean_kinetic_energy_eV`
  - `sigma_energy_eV`
  - `n_particles_initial`, `n_particles_final`
  - `transmission_fraction`

## Diagnostic Integrity & Range Validation
- Enforced strict failure semantics in `create_evaluation_result`:
  - Missing transmission or missing required diagnostics set `simulation_valid = False` and `failure_category = MISSING_OUTPUT` (never defaulting missing transmission to 100%).
  - Non-finite (NaN/Inf) or negative RMS beam diagnostic quantities set `simulation_valid = False` and `failure_category = NAN_INF_DIAGNOSTICS`.
  - Unphysical transmission (`transmission < 0.0` or `transmission > 1.0`) set `simulation_valid = False` and `failure_category = INVALID_TRANSMISSION`.
  - Valid simulations with `transmission < min_transmission` set `simulation_valid = True`, `physically_feasible = False`, and `failure_category = INVALID_TRANSMISSION`.

## Tests & Verification
- Created `tests/test_transmission_and_diagnostics.py`:
  - `test_transmission_full`: Verified 100% transmission.
  - `test_transmission_partial`: Verified partial transmission pass/fail threshold behavior.
  - `test_transmission_missing`: Verified missing transmission rejection.
  - `test_diagnostic_units`: Verified explicit unit-bearing diagnostic fields in dict and DataFrame.
  - `test_nonfinite_diagnostics`: Verified rejection of NaN, Inf, negative RMS, and out-of-bounds transmission.
- Pytest suite executed successfully: 47/47 unit tests passed.

## Acceptance Criteria Status
- [x] Transmission is computed from real simulation output.
- [x] Missing transmission cannot pass feasibility.
- [x] Constraint evaluation consumes explicit unit-bearing diagnostic fields.
- [x] Old ambiguous diagnostic keys are mapped alongside explicit unit-bearing fields.
- [x] Tests cover full, partial, zero, missing transmission, and range boundary conditions.
