# Current Repository Architecture Baseline

## Executive Summary

This document provides a comprehensive baseline audit of the `mobo_linac` codebase prior to structural refactoring in Tasks 02–10.

---

## 1. Executable Entry Points

- **`scripts/run_unconstrained_mobo.py`** (formerly `scripts/run_mobo.py`): Main CLI script for Phase 2 Multi-Objective Bayesian Optimization (MOBO) using BoTorch (`qLogNEHVI` / `qEHVI`) and `ThreadPoolExecutor`.
- **`scripts/run_constrained_mobo.py`**: CLI script for Phase 3 Constraint-Aware MOBO modeling constraints with GP surrogates.
- **`notebooks/phase2_mobo.ipynb`**: Interactive notebook for Phase 2 MOBO optimization and visualization.
- **`notebooks/phase3_constrained_mobo.ipynb`**: Interactive notebook for Phase 3 Constrained MOBO.
- **`mobo.ipynb` & `scalarized_bo.ipynb`**: Exploratory legacy notebooks for initial MOBO and scalarized BO experiments.

---

## 2. ASTRA Simulation Runner

- **File**: `run_astra.py`
- **Function**: `run_astra_simulation(parameters, verbose=False, timeout=30)`
  - Instantiates `Astra('astra.in')`.
  - Overwrites 8 ASTRA parameters from the 6 input design parameters:
    - `solenoid:maxb(1)` $\leftarrow x_0$
    - `quadrupole:q_grad(1)` $\leftarrow x_1$
    - `quadrupole:q_grad(2)` $\leftarrow x_2$
    - `cavity:phi(1)` $\leftarrow x_3$
    - `cavity:phi(2)`, `cavity:phi(3)` $\leftarrow x_4$ (common phase)
    - `cavity:phi(4)`, `cavity:phi(5)` $\leftarrow x_5$ (common phase)
  - Calls `astra_sim.run()`.
  - **Concurrency Issue**: `Astra` runs in the current working directory. When executed concurrently via threads, multiple ASTRA runs overwrite each other's input/output files (`astra.in`, `run.log`, `fort.*`).

---

## 3. Objective & Constraint Definitions

### Objectives
Physical objectives extracted by `get_objectives(stats)` in `run_astra.py:46-51`:
1. Horizontal normalized emittance $\varepsilon_{n,x}$ [m-rad]
2. Vertical normalized emittance $\varepsilon_{n,y}$ [m-rad]
3. RMS energy spread $\sigma_E$ [eV]

*BoTorch maximization requirement*: All objectives are negated ($-\varepsilon_{n,x}, -\varepsilon_{n,y}, -\sigma_E$) before model fitting.

### Active Constraints and Code Locations
Explicit feasibility conditions in `mobo_utils.py:16-24` and `mobo_utils.py:50-58`:

| Constraint Description | Condition | File Reference |
|------------------------|-----------|----------------|
| Transverse RMS size x | `sigma_x <= 1.0e-3` m | `mobo_utils.py:17`, `mobo_utils.py:51` |
| Transverse RMS size y | `sigma_y <= 1.0e-3` m | `mobo_utils.py:18`, `mobo_utils.py:52` |
| Transverse divergence xp | `sigma_xp <= 1.0e-3` rad | `mobo_utils.py:19`, `mobo_utils.py:53` |
| Transverse divergence yp | `sigma_yp <= 1.0e-3` rad | `mobo_utils.py:20`, `mobo_utils.py:54` |
| Longitudinal bunch length z | `sigma_z <= 1.0e-3` m | `mobo_utils.py:21`, `mobo_utils.py:55` |
| Mean kinetic energy lower | `mean_kinetic_energy >= 195e6` eV | `mobo_utils.py:22`, `mobo_utils.py:56` |
| Mean kinetic energy upper | `mean_kinetic_energy <= 205e6` eV | `mobo_utils.py:23`, `mobo_utils.py:57` |

*Note*: Beam transmission is documented as a constraint in `AGENTS.md` but is **not** explicitly checked in `mobo_utils.py`.

---

## 4. Checkpoint & Resume Logic

- **File**: `file_io.py`
- **Functions**: `save_checkpoint`, `load_checkpoint`
- **State saved**: PyTorch dictionary containing `iteration`, `train_X`, `train_Y`, `train_feas_mask`, `hypervolumes`, `train_constraints_list`.
- **Limitation**: Resuming relies on loading the latest `.pt` checkpoint file. If a run crashes mid-batch, partial evaluations within that batch are lost.

---

## 5. Parallel Execution Code

- **File**: `scripts/run_unconstrained_mobo.py:138` (formerly `run_mobo.py`), `scripts/run_constrained_mobo.py:138`
- **Implementation**: `ThreadPoolExecutor(max_workers=args.num_workers)`
- **Flaw**: Python threads share global memory and working directory context. Because `Astra` writes temporary files directly to the current working directory (`./`), thread-based parallel execution creates severe file collisions and data corruption.

---

## 6. BoTorch APIs Used

- `botorch.models.SingleTaskGP`, `botorch.models.ModelListGP`
- `botorch.models.transforms.input.Normalize`, `botorch.models.transforms.outcome.Standardize`
- `botorch.fit.fit_gpytorch_mll`, `gpytorch.mlls.ExactMarginalLogLikelihood`
- `botorch.optim.optimize_acqf`
- `botorch.acquisition.multi_objective.monte_carlo.qExpectedHypervolumeImprovement`
- `botorch.acquisition.multi_objective.logei.qLogNoisyExpectedHypervolumeImprovement`
- `botorch.utils.multi_objective.box_decompositions.non_dominated.FastNondominatedPartitioning`
- `botorch.utils.multi_objective.hypervolume.Hypervolume`
- `botorch.utils.multi_objective.pareto.is_non_dominated`

---

## 7. Required Findings Matrix

| Audit Question | Finding | Technical Detail / Reference |
|---|---|---|
| Parallel ASTRA evaluations share a working directory? | **YES** | `run_astra_simulation` creates `Astra('astra.in')` in current process working directory without isolating subdirectories. |
| `train_Y` stores physical or negated objectives? | **NEGATED** | `train_Y` stores $[-\varepsilon_{n,x}, -\varepsilon_{n,y}, -\sigma_E]$ because BoTorch enforces maximization. |
| Hypervolume reference point changes during a run? | **YES** | `compute_ref_point` in `mobo_utils.py:81` dynamically computes `ref_point` based on `train_Y.min()` and `train_Y.max()` at each iteration. |
| Infeasible samples excluded from objective GP training? | **PARTIALLY** | In `run_unconstrained_mobo.py:180-186` (legacy `run_mobo.py`), infeasible points are filtered out *only* if at least 1 feasible point exists. If 0 feasible points exist, it trains on all samples including sentinels. |
| Invalid simulations assigned sentinel values? | **YES** | `mobo_utils.py:27` assigns dummy `emit_x=1e-3, emit_y=1e-3, sigma_energy=1e8` on simulation error/timeout (negated to `[-1e-3, -1e-3, -1e8]`). |
| Constraints differ between scripts and documentation? | **YES** | `AGENTS.md` lists beam transmission as a constraint; `mobo_utils.py` omits transmission checks. Unit scaling factors ($\mu\text{m}$ vs $\text{m}$) vary across scripts. |

---

## 8. Testability Limitations

1. **No Automated Test Suite**: The repository lacks `tests/` directory or `pytest` integration.
2. **Hard Dependency on External Binary**: `run_astra_simulation` requires live execution of external ASTRA binary files (`astra`, `generator`).
3. **No Mock / Synthetic Simulator**: No dry-run or mock mode exists for unit testing optimization logic without running computationally heavy simulations.
