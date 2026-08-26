# AGENTS.md

# Multi-Objective Bayesian Optimization for a 200 MeV Electron Injector Linac

## Project Overview

This repository develops a Machine Learning framework for optimizing a
200 MeV S-band electron injector linac using Bayesian Optimization (BO)
and Multi-Objective Bayesian Optimization (MOBO).

The accelerator beam dynamics are simulated using **ASTRA**.
Optimization variables modify the ASTRA input file (`astra.in`), execute
the simulation, extract beam quality metrics, and iteratively improve
accelerator settings.

The long-term objective is to replace scalarized weighted optimization
with true Multi-Objective Bayesian Optimization that directly learns the
Pareto front.

Current research was presented at ICABU 2025 and demonstrated
scalarized Bayesian Optimization using multiple weight combinations,
with the next phase extending to qEHVI/qNEHVI-based MOBO.

---

# Project Metadata & Authorship

- **Author**: Chong Shik Park
- **Affiliation**: Department of Accelerator Science and Center for Accelerator Research, Korea University, Sejong, 30019 Republic of Korea

---

# Agent Execution Guidelines & Operational Rules

- **Git & GitHub Actions Policy**:
  - Do NOT perform `git push` and do NOT check remote GitHub Actions status or query remote workflow executions.
  - Modifying GitHub Actions workflows in the local repository only is permitted.
- **Task Summary & Execution Plan Persistence**:
  - All executed tasks must be summarized and saved into `docs/exec-plans/completed/` following continuous numerical ordering (e.g., `TASK_01_...` through `TASK_20_...`, `TASK_21_...`, `TASK_22_...`, `TASK_23_...`, etc.).
  - Every completed task must follow the structured markdown summary format established in `docs/exec-plans/completed/`.
- **Web Interface & Document Design Standard**:
  - Created HTML documents should follow a github.io project webpage style (dark mode glassmorphism UI, Outfit/Inter typography, MathJax formulas, Chart.js visualizations), adhering to existing project templates where available.


# Repository Contents

Typical repository structure

```
mobo-linac/
│
├── astra.in                 # Main ASTRA input template
├── gun.dat                  # RF gun field map
├── PAL_SOL_A.dat            # Solenoid field map
├── TWS_Sband.dat            # Traveling-wave cavity field map
├── pal_photo2.ini           # Initial particle distribution
│
├── bin/                     # Integrated local ASTRA executables (astra, generator, etc.)
│
├── src/mobo_linac/          # Modular core package (astra, execution, models, metrics, io)
├── configs/                 # Centralized YAML configuration files
├── scripts/                 # Optimization & verification execution scripts
├── notebooks/               # Interactive evaluation & analysis notebooks
├── tests/                   # Pytest unit test suite
├── docs/                    # Simulation guide, paper LaTeX, & task summaries
├── release/                 # Publication artifacts & manifest (v1.0.0)
├── results/                 # Optimization run output logs & checkpoints
│
└── AGENTS.md
```

---

# Optimization Problem

## Design Variables (6)

The optimization controls six accelerator parameters:

1. Solenoid peak field
2. Quadrupole 1 gradient
3. Quadrupole 2 gradient
4. RF gun phase
5. ACC1/ACC2 common phase
6. ACC3/ACC4 common phase

These variables are written into `astra.in`
before each ASTRA simulation.

---

## Objectives (Minimize)

The optimization simultaneously minimizes

1. Horizontal normalized emittance

    εₙₓ

2. Vertical normalized emittance

    εₙᵧ

3. RMS energy spread

    σ_E

The current implementation internally negates these values because
BoTorch assumes maximization.

---

## Constraints

Beam quality constraints are **not objectives**.

Constraint diagnostics include

- σx
- σy
- σx'
- σy'
- bunch length σz
- average beam energy
- transmission

Current implementation records

- feasibility
- constraint violations

Future versions will model constraints using GP constraint models.

---

# Simulation Workflow

```
parameter vector
      │
      ▼
Modify astra.in
      │
      ▼
Run ASTRA
      │
      ▼
Extract beam statistics
      │
      ▼
Evaluate objectives
      │
      ▼
Update Gaussian Processes
      │
      ▼
Optimize acquisition function
      │
      ▼
Generate next candidate(s)
```

---

# Bayesian Optimization

Current implementation

- Gaussian Process surrogate (`ModelListGP` with Matérn 5/2 ARD kernel)
- Gaussian Process surrogate (`ModelListGP` with Matérn 5/2 ARD kernel)
- Multi-scale relative fixed noise variance scaling ($\sigma_{\text{obs}}^2 = \max(\eta \cdot \text{Var}(Y_m), \sigma_{\text{floor}}^2)$ with $\eta=10^{-6}$)
- Exact multi-channel analytical Normal CDF feasibility modeling ($P_{\text{feas}}$) across 7 diagnostic channels
- ProcessPoolExecutor process-safe parallel ASTRA evaluations
- Multi-tier resilient acquisition proposal engine with adaptive restart retry & quasi-random Sobol fallback
- `qLogNEHVI` / `qLogEHVI` acquisition formulations with configurable L-BFGS multi-restart budgets
- Longitudinal exit-plane loss detection & premature tracking rejection (`PREMATURE_BEAM_LOSS`)
- Fixed-reference hypervolume tracking ($\mathbf{r} = [1.5\text{ mm}, 1.5\text{ mm}, 1.5\text{ MeV}]$)
- Candidate history, SHA-256 evaluation checksums, and Pareto visualization
- Full-chain photocathode & laser jitter robustness modeling (7 physical noise channels)
- Atomic POSIX crash-proof checkpoint serialization (`_atomic_torch_save`)
- Centralized publication-grade LaTeX reporting module (`mobo_linac.metrics.latex`)
- Automated environment fallback resolution for integrated ASTRA executables (`./bin/astra`)

---

# Execution & Environment Architecture

- **ASTRA Binaries**: Pre-bundled local executables stored under `./bin/` (`astra`, `generator`, `PAstra`). `mobo_linac.astra.runner` dynamically detects `$PROJECT_ROOT/bin/astra` with fallback support for custom `$ASTRA_BIN` environment variables.
- **Python Dependencies**: Package specified in `pyproject.toml` using PEP 508 direct Git dependencies for `lume-astra` (`git+https://github.com/ChristopherMayes/lume-astra.git`).

---

# Development Roadmap

## Phase 1 (Completed)

- Scalarized BO with multiple weight combinations ($w_1 \varepsilon_{n,x} + w_2 \varepsilon_{n,y} + w_3 \sigma_E$)
- Single-objective GP surrogate (`SingleTaskGP` with Matérn 5/2 ARD kernel) & `qLogNEI`
- Standalone production script `scripts/run_scalarized_bo.py`
- Interactive evaluation & analysis notebook `notebooks/phase1_scalarized_bo.ipynb`
- Comparison with MOGA benchmark
- Parallel ASTRA evaluation worker pools

---

## Phase 2 (Completed)

Replaced scalarization with true Multi-Objective Bayesian Optimization (MOBO)

Objectives:
- Horizontal emittance $\varepsilon_x$
- Vertical emittance $\varepsilon_y$
- RMS energy spread $\sigma_E$

Models:
- Independent Gaussian Process (`ModelListGP`) per objective with Matérn 5/2 ARD kernel

Acquisition:
- `qLogNEHVI` & `qLogEHVI` acquisition functions

Outputs:
- Pareto front (`pareto.csv`)
- Hypervolume history (`hypervolume.csv`)
- Candidate proposal history (`candidate_history.csv`)

---

## Phase 3 (Completed)

Constraint-aware Bayesian Optimization, High-Fidelity Physics & Architecture Refactoring (Release `v1.0.0`)

Implemented:
- Explicit GP models for beam quality constraints ($\sigma_x, \sigma_y, \sigma_z, \sigma_{x'}, \sigma_{y'}, E_{\text{kin}}, \text{transmission}$)
- Exact multi-channel analytical Normal CDF Probability of Feasibility modeling ($P_{\text{feas}}$)
- Multi-scale Gaussian Process relative noise variance scaling for $\mu\text{m}\cdot\text{rad}$ vs $\text{MeV}$
- Config-driven dynamic parameter mapping to arbitrary ASTRA namelists & cavity decoupling
- Longitudinal exit-plane verification & premature beam loss / core collimation trapping
- Robustness evaluation under engineering tolerances ($\pm 0.1^\circ$ RF phase, $\pm 0.1\%$ magnet fields) and full-chain photocathode/laser jitter
- Multi-tier resilient acquisition optimization with adaptive retry and Sobol fallback
- Atomic POSIX crash-proof checkpoint writes (`_atomic_torch_save`)
- Centralized publication-ready LaTeX table reporting module (`mobo_linac.metrics.latex`)
- Automated Pareto candidate verification protocol with SHA-256 checksum audit
- Archived publication artifacts (`release/publication_artifact_manifest.json`, tag `v1.0.0`)

---

## Phase 4 (Next)

High-performance optimization

- Distributed ASTRA evaluations
- MPI
- Ray
- Dask
- Multi-node clusters
- Dask
- Multi-node clusters

---

## Phase 5

Surrogate enhancement

Investigate

- MultiTaskGP
- SAASBO
- TuRBO
- Trust-region BO
- Deep Kernel Learning

---

# Coding Guidelines

Always

- Keep ASTRA input generation separate from optimization logic.
- Never hard-code objective definitions.
- Maintain reproducibility through random seeds.
- Save every iteration.
- Export Pareto fronts automatically.
- Save GP checkpoints.
- Keep simulation outputs immutable.

---

# Output Directory

Each optimization run should create

```
results/

    YYYYMMDD_HHMMSS/

        config.json

        train_X.csv

        train_Y.csv

        pareto.csv

        hypervolume.csv

        candidate_history.csv

        constraints.csv

        gp_checkpoint/

        figures/
```

---

# Future Features

The repository is expected to evolve toward

- true Multi-Objective Bayesian Optimization
- constraint-aware optimization
- asynchronous batch BO
- adaptive acquisition switching
- trust-region BO
- multi-fidelity BO
- robust optimization
- uncertainty quantification
- experiment-in-the-loop optimization

---

# Development Philosophy

This project is intended to become a reusable accelerator optimization
framework rather than a collection of scripts.

Priority order

1. Correct accelerator physics
2. Reliable optimization
3. Clean software architecture
4. Reproducibility
5. Computational efficiency

AI-generated code should preserve scientific correctness,
maintain modularity,
and avoid changing beam physics unless explicitly requested.

All optimization routines should remain independent of ASTRA-specific
details whenever possible, enabling future support for additional beam
dynamics codes such as GPT, IMPACT-T, elegant, OPAL, or TRACK.
