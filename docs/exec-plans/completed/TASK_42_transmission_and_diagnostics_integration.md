# Task 42 Summary: Transmission Computation & Diagnostic Integrity (Codex Task 02)

## Summary

Task 42 verified and enhanced real transmission fraction extraction, diagnostic integrity checks, physical feasibility boundaries, and outcome tensor exports across `mobo_linac`.

## Details & Implementation

1. **ASTRA Output Particle Count Extraction (`src/mobo_linac/astra/runner.py`)**:
   - `n_particles_initial` and `n_particles_final` are extracted from ASTRA particle distribution outputs (`astra_sim.particles[0].n_particle` / `astra_sim.particles[-1].n_particle`) or statistical table headers (`landf_n_particles` / `n_stat`).
   - `transmission_fraction = float(n_particles_final) / float(n_particles_initial)` is computed explicitly when `n_init > 0`.
2. **Missing & Invalid Transmission Protection (`src/mobo_linac/evaluation.py` & `src/mobo_linac/constraints.py`)**:
   - If transmission cannot be extracted or is `None`, `create_evaluation_result()` sets `simulation_valid = False` and `failure_category = FailureCategory.MISSING_OUTPUT.value`. Missing transmission is NEVER defaulted to `1.0`.
   - If transmission is outside $[0.0, 1.0]$, `simulation_valid = False` and `failure_category = FailureCategory.INVALID_TRANSMISSION.value`.
   - If transmission $< 0.90$ (configured minimum threshold), `simulation_valid = True`, `physically_feasible = False`, and `failure_category = FailureCategory.INVALID_TRANSMISSION.value`.
3. **8th Continuous Tensor Constraint (`src/mobo_linac/constraints.py`)**:
   - Continuous tensor constraint function `c_transmission(Y) = min_transmission - Y[..., 9] <= 0` is integrated in `get_botorch_constraint_functions()`.
4. **Structured CSV & DataFrame Exports (`src/mobo_linac/io/results.py`)**:
   - Explicit unit-bearing diagnostic columns (`n_particles_initial`, `n_particles_final`, `transmission_fraction`) are exported in candidate history CSVs, DataFrames, verification manifests, and LaTeX reports.
5. **Unit Tests (`tests/test_transmission_and_diagnostics.py`)**:
   - Added unit tests for 100% full, partial (95% passing / 85% failing threshold), missing transmission, zero transmission, out-of-bounds transmission ($>1.0$), non-finite/NaN/Inf diagnostics, and invalid initial particle counts ($0$).
   - Executed full test suite: **83/83 unit tests passed** in 12.11s.

## Status

**Completed**. Transmission computation, diagnostic validation, and test suite verified. Saved summary in `docs/exec-plans/completed/TASK_42_transmission_and_diagnostics_integration.md`.
