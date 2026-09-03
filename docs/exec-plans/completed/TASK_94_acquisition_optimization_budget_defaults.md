# Task Execution Summary: TASK_94 — Acquisition Multi-Restart Optimization Defaults & Fallback Routing

## 1. Overview & Objectives
- **Problem**: During Phase 1 execution, BoTorch triggered `scipy.optimize.minimize` status 2 (`ABNORMAL`) warnings in `gen_candidates_scipy` / `_optimize_acqf_batch` when `raw_samples` was too small, causing initial conditions to land in vanishing gradient regions.
- **Goal**: Apply Solution 1 across configuration files and runtime defaults:
  - Increase `acqf_raw_samples` from `128`/`512` to `1024` for dense high-acquisition basin initialization.
  - Set `acqf_num_restarts` to `10` to avoid low-quality tail restarts.
  - Set `acqf_maxiter` to `200` and `acqf_batch_limit` to `5`.
  - Route Phase 1 scalarized BO acquisition optimization through `generate_next_candidates` to enable adaptive multi-tier restart retries, GPU-to-CPU fallback, and quasi-random Sobol safety nets.

---

## 2. Work Implemented

### 2.1 Centralized YAML Configuration Updates
- Updated `execution` blocks across:
  - [`configs/publication_200MeV.yaml`](file:///home/cspark/Work/projects/mobo-linac/configs/publication_200MeV.yaml)
  - [`configs/mobo_200MeV.yaml`](file:///home/cspark/Work/projects/mobo-linac/configs/mobo_200MeV.yaml)
  - [`configs/publication.yaml`](file:///home/cspark/Work/projects/mobo-linac/configs/publication.yaml)
- Explicit parameters configured:
  ```yaml
  execution:
    acqf_raw_samples: 1024
    acqf_num_restarts: 10
    acqf_maxiter: 200
    acqf_batch_limit: 5
  ```

### 2.2 Core Package & Dataclass Defaults
- [`src/mobo_linac/config.py`](file:///home/cspark/Work/projects/mobo-linac/src/mobo_linac/config.py):
  - Updated `ExecutionConfig.acqf_num_restarts` default value to `10`.
- [`src/mobo_linac/campaigns/runner.py`](file:///home/cspark/Work/projects/mobo-linac/src/mobo_linac/campaigns/runner.py):
  - Refactored `run_scalarized_bo_campaign` acquisition candidate generation step to use `generate_next_candidates` with `num_restarts=exec_cfg.acqf_num_restarts` (10) and `raw_samples=exec_cfg.acqf_raw_samples` (1024), providing resilient fallback handling.
  - Updated fallback parameter defaults in `run_phase1_scalarized_bo` helper.

### 2.3 Unit Test Alignments
- [`tests/test_gp_and_acquisition.py`](file:///home/cspark/Work/projects/mobo-linac/tests/test_gp_and_acquisition.py):
  - Updated `test_execution_config_hyperparameter_propagation` assertion to verify default `acqf_num_restarts == 10`.

---

## 3. Key Files Created / Updated
- `configs/publication_200MeV.yaml`
- `configs/mobo_200MeV.yaml`
- `configs/publication.yaml`
- `src/mobo_linac/config.py`
- `src/mobo_linac/campaigns/runner.py`
- `tests/test_gp_and_acquisition.py`
- `docs/exec-plans/completed/TASK_94_acquisition_optimization_budget_defaults.md`
