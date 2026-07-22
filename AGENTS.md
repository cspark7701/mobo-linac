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
with the next phase extending to qEHVI/qNEHVI-based MOBO. :contentReference[oaicite:1]{index=1}

---

# Repository Contents

Typical repository structure

```
project/
│
├── astra.in                 # Main ASTRA input
├── gun.dat                  # RF gun field map
├── PAL_SOL_A.dat            # Solenoid field map
├── TWS_Sband.dat            # Traveling-wave cavity field map
├── pal_photo2.ini           # Initial particle distribution
│
├── notebooks/
│      optimization.ipynb
│      ...
│
├── scripts/
│      run_astra.py
│      bo.py
│      moo.py
│      utilities.py
│
├── results/
│      logs/
│      checkpoints/
│      pareto/
│      figures/
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

- Gaussian Process surrogate
- Parallel ASTRA evaluation
- qLogNEHVI acquisition
- Hypervolume tracking
- Pareto visualization
- Constraint diagnostics
- GP normalization
- ThreadPool parallel execution

---

# Development Roadmap

## Phase 1 (Completed)

- Scalarized BO
- Multiple weight combinations
- GP surrogate
- qEI
- Comparison with MOGA
- Parallel ASTRA execution

---

## Phase 2 (Current)

Replace scalarization with true MOBO

Objectives

- εx
- εy
- σE

Models

Independent GP for each objective

Acquisition

- qLogNEHVI
- qEHVI (optional)

Outputs

- Pareto front
- Hypervolume
- Candidate history

---

## Phase 3

Constraint-aware Bayesian Optimization

Investigate

- GP constraints
- Feasibility-weighted acquisition
- Constrained qNEHVI
- Probability of Feasibility

---

## Phase 4

High-performance optimization

- Distributed ASTRA evaluations
- MPI
- Ray
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
