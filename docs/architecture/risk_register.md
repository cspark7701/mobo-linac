# Risk Register & Mitigation Strategy

## Overview

This risk register documents critical architectural, numerical, and software reliability risks identified during the Task 01 repository audit, along with planned task mitigations in the refactoring roadmap.

---

## Identified Risks

### Risk 01: Shared Working Directory Race Condition in Parallel ASTRA Executions
- **Severity**: High
- **Impact**: When running parallel evaluations via threads, concurrent `astra` processes overwrite input/output files (`astra.in`, `run.log`, Fortran temporary files) in the root working directory. This causes corrupted simulation output, silent data mixing, or process crashes.
- **Planned Mitigation**: Task 02 (Isolated ASTRA work directories) & Task 03 (Process-safe parallel evaluation).

### Risk 02: Moving / Dynamic Hypervolume Reference Point
- **Severity**: High
- **Impact**: `compute_ref_point` recalculates `ref_point` dynamically at each iteration based on current `train_Y` min/max. As bounds change, hypervolume values across iterations fluctuate non-monotonically, invalidating comparative hypervolume analysis between different runs or algorithms.
- **Planned Mitigation**: Task 06 (Fixed hypervolume reporting reference point based on physical design limits).

### Risk 03: Objective GP Surrogate Distortions from Sentinel Values
- **Severity**: High
- **Impact**: Failed or infeasible simulations receive arbitrary large sentinel penalty values (`-1e-3, -1e-3, -1e8`). Fitting Gaussian Processes directly on sentinel values distorts the response surface, causing false gradients and improper acquisition function landscape topology.
- **Planned Mitigation**: Task 04 (Centralized config) & Task 05 (Evaluation result schema separating validity, feasibility, and physical objectives).

### Risk 04: Scattered Unit Definitions & Duplicated Physical Constants
- **Severity**: Medium
- **Impact**: Units for emittance ($\text{m}$ vs $\mu\text{m}$), energy ($\text{eV}$ vs $\text{MeV}$), and beam sizes are hardcoded with inconsistent multipliers across `run_astra.py`, `mobo_utils.py`, `plot_utils.py`, and `utils.py`.
- **Planned Mitigation**: Task 04 (Centralized configuration, Pydantic schemas, and explicit units).

### Risk 05: Unclear Simulation Validity vs. Beam Quality Feasibility
- **Severity**: Medium
- **Impact**: ASTRA executable timeouts, crashes, or unparseable outputs are mixed together with physical beam constraint violations ($\sigma_x > 1.0\text{ mm}$).
- **Planned Mitigation**: Task 05 (Structured `EvaluationResult` data schema).

### Risk 06: Lack of Automated Testing Suite & CI Integration
- **Severity**: Medium
- **Impact**: Regression risks when refactoring code; inability to verify optimization logic without executing full ASTRA simulations.
- **Planned Mitigation**: Task 07 (Package layout `pyproject.toml`) & Task 08 (Tests and CI with mock ASTRA runner).
