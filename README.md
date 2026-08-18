# Multi-Objective Bayesian Optimization for a 200 MeV Electron Injector Linac

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0+-ee4c2c.svg)](https://pytorch.org/)
[![BoTorch](https://img.shields.io/badge/BoTorch-0.10+-red.svg)](https://botorch.org/)
[![ASTRA](https://img.shields.io/badge/Simulation-ASTRA-green.svg)](https://www.desy.de/~mprue/Astra/)

## Overview

This repository develops a Machine Learning framework for optimizing a **200 MeV S-band electron injector linac** using **Bayesian Optimization (BO)** and **Multi-Objective Bayesian Optimization (MOBO)** powered by [BoTorch](https://botorch.org/) and [lume-astra](https://github.com/linac-group/lume-astra).

The accelerator beam dynamics are simulated using **ASTRA** (*A Space Charge Tracking Algorithm*). Optimization variables modify the ASTRA input file (`astra.in`), execute parallel simulations, extract beam quality metrics, update Gaussian Process (GP) surrogate models, and optimize acquisition functions to learn the Pareto front.

Research on initial scalarized Bayesian Optimization was presented at **ICABU 2025**, and the framework has been extended to true parallel multi-objective optimization via `qLogNEHVI` / `qEHVI` and explicit constraint modeling.

---

## Quick Links & Documentation

- 📖 **[Unified Simulation Procedure & Publication Workflow Guide](docs/simulation_guide.md)**: Master guide for ASTRA simulation procedure, MOBO architecture, benchmark protocol, robustness analysis, Pareto verification, and paper reproduction.
- 📄 **[Journal Paper Draft (LaTeX)](docs/paper/main.tex)**: Journal manuscript draft, figures, and compiled PDF in `docs/paper/`.
- 📋 **[Completed Milestone Execution Plans](docs/exec-plans/completed/TASK_20_final_audit.md)**: Refactoring and publication task logs (Tasks 01--20).

---

## Repository Structure

```
mobo_linac/
├── README.md                          # Project documentation
├── AGENTS.md                          # Developer & agent design specifications
├── pyproject.toml                     # Package dependencies & CLI entry points
├── bin/                               # Integrated local ASTRA binaries (astra, generator)
│
├── src/mobo_linac/                    # Core Python package
│   ├── acquisition/                   # Resilient qLogNEHVI / qLogEHVI acquisition functions
│   ├── astra/                         # Isolated workdir manager & dynamic runner
│   ├── campaigns/                     # Unified MoboCampaignRunner execution engine
│   ├── execution/                     # ProcessPoolExecutor parallel batch evaluator
│   ├── config.py                      # Centralized YAML configuration parser
│   ├── evaluation.py                  # EvaluationResult & FailureCategory schema
│   ├── objectives.py                  # Physical <-> Model space conversions
│   ├── constraints.py                 # Dynamic beam quality constraint evaluator
│   ├── metrics/                       # Fixed reference hypervolume, Pareto & LaTeX reporting
│   ├── models/                        # Multi-scale Gaussian Processes & SurrogatePipeline
│   ├── robustness/                    # Full-chain photocathode/laser perturbation analysis
│   ├── io/                            # Results dataframes & atomic CheckpointState serialization
│   └── plotting/                      # Pareto, hypervolume, & diagnostic figures
│
├── configs/
│   ├── mobo_200MeV.yaml               # Centralized configuration file
│   └── publication_200MeV.yaml        # Canonical publication configuration
│
├── docs/
│   ├── simulation_guide.md            # Step-by-step execution guide
│   ├── paper/                         # LaTeX journal manuscript (main.tex, main.pdf)
│   ├── exec-plans/                    # Active and completed task plans
│   ├── 04_refactor_tasks/             # Modular refactoring specifications (Tasks 01--11)
│   └── index.html                     # Project technical web portal
│
├── scripts/                           # Campaign, comparison, & LaTeX export scripts
├── notebooks/                         # Interactive analysis notebooks
├── tests/                             # Pytest test suite (58+ unit tests)
└── results/                           # Optimization run output directories
```


---

## Optimization Problem Formulation

### Design Variables (6)

The optimization controls six accelerator design parameters, which are written into `astra.in` before each ASTRA simulation:

| Index | Parameter Description | ASTRA Input Variable | Units / Details |
|:-----:|-----------------------|---------------------|-----------------|
| 1 | Solenoid Peak Field | `solenoid:maxb(1)` | Peak magnetic field [T] |
| 2 | Quadrupole 1 Gradient | `quadrupole:q_grad(1)` | Gradient [T/m] |
| 3 | Quadrupole 2 Gradient | `quadrupole:q_grad(2)` | Gradient [T/m] |
| 4 | RF Gun Phase | `cavity:phi(1)` | Phase [deg] |
| 5 | ACC1/ACC2 Common Phase | `cavity:phi(2)` & `cavity:phi(3)` | Common phase [deg] |
| 6 | ACC3/ACC4 Common Phase | `cavity:phi(4)` & `cavity:phi(5)` | Common phase [deg] |

---

### Objectives (3 Minimize)

The optimization simultaneously minimizes three primary beam quality metrics:

1. **Horizontal Normalized Emittance** ($\varepsilon_{n,x}$)
2. **Vertical Normalized Emittance** ($\varepsilon_{n,y}$)
3. **RMS Energy Spread** ($\sigma_E$)

*Note: Objective values are negated internally because BoTorch assumes maximization.*

---

### Constraints & Beam Diagnostics

Beam quality metrics and physical boundaries determine simulation feasibility:

* **Transverse RMS Beam Sizes**: $\sigma_x \le 1.0\text{ mm}$, $\sigma_y \le 1.0\text{ mm}$
* **Transverse RMS Divergence**: $\sigma_{x'} \le 1.0\text{ mrad}$, $\sigma_{y'} \le 1.0\text{ mrad}$
* **Longitudinal RMS Bunch Length**: $\sigma_z \le 1.0\text{ mm}$
* **Mean Kinetic Energy**: $195\text{ MeV} \le E_{\text{kin}} \le 205\text{ MeV}$

In **Phase 2**, feasibility diagnostic violations apply penalties. In **Phase 3**, constraints are explicitly modeled using separate Gaussian Process surrogate models for Probability of Feasibility computation.

---

## Simulation & Optimization Workflow

```
         Parameter Vector (6D)
                  │
                  ▼
         Modify ASTRA Input File (astra.in)
                  │
                  ▼
         Run Parallel ASTRA Simulations
                  │
                  ▼
         Extract Beam Quality Statistics
                  │
                  ▼
         Evaluate Objectives & Constraints
                  │
                  ▼
         Update GP Surrogates (BoTorch)
                  │
                  ▼
         Optimize Acquisition Function (qLogNEHVI)
                  │
                  ▼
         Generate Next Candidate Batch
```

---

## Output Directory Structure

Each optimization run automatically generates a timestamped directory under `results/`:

```
results/YYYYMMDD_HHMMSS/
├── config.json            # Configuration parameters and runtime settings
├── train_X.csv            # Evaluated design parameter vectors
├── train_Y.csv            # Evaluated objective values
├── pareto.csv             # Extracted Pareto non-dominated set
├── hypervolume.csv        # Hypervolume progression over iterations
├── candidate_history.csv  # Detailed history of candidate proposals
├── constraints.csv        # Diagnostic values and constraint statuses
├── gp_checkpoint/         # Saved PyTorch / GPyTorch GP model checkpoints
└── figures/               # Generated figures (Pareto front, hypervolume, etc.)
```

---

## Prerequisites & Installation

The repository is self-contained with **pre-bundled ASTRA binaries** in `./bin/` and automated **`lume-astra` Python interface integration**.

### 1. Quick Setup (Single Command)

Clone the repository and install the package with all Python dependencies (including `lume-astra` directly from source):

```bash
git clone https://github.com/cspark7701/mobo_linac.git
cd mobo_linac
pip install -e .
```

### 2. ASTRA Binary Executables

The compiled ASTRA simulation binaries are integrated into the local `./bin/` directory:
- `bin/astra`: Main ASTRA tracking simulation executable.
- `bin/generator`: Particle distribution generator executable.

By default, `mobo_linac.astra.runner` automatically detects and uses the local `./bin/astra` and `./bin/generator` binaries without requiring manual environment variables.

If you wish to override these binaries with custom external builds, you can set the environment variables:

```bash
export ASTRA_BIN="/path/to/custom/bin/astra"
export GENERATOR_BIN="/path/to/custom/bin/generator"
```

---

## Usage Examples & CLI Commands

The framework provides a unified console entry point `mobo-linac` (or `python -m mobo_linac.cli`):

### 1. Run Phase 2 Unconstrained MOBO
```bash
mobo-linac run-unconstrained --config configs/publication_200MeV.yaml --n-iterations 300 -q 8 --num-workers 12
```

### 2. Run Phase 3 Constrained MOBO (Feasibility-Aware)
```bash
mobo-linac run-constrained --config configs/publication_200MeV.yaml --n-iterations 300 -q 8 --num-workers 12
```

### 3. Run Paired Multi-Seed Benchmark Campaign
```bash
mobo-linac run-benchmark --config configs/publication_200MeV.yaml --seeds 42 43 44 --budget 40 --num-workers 12
```

### 4. Run Robustness & Engineering Sensitivity Analysis
```bash
mobo-linac run-robustness --config configs/publication_200MeV.yaml --num-perturbations 50 --num-workers 12
```

### 5. Run Independent Pareto Candidate Verification Reruns
```bash
mobo-linac run-verification --config configs/publication_200MeV.yaml --output-dir results/verification
```

### 6. Resume Interrupted Campaign from Checkpoint
```bash
mobo-linac resume --run-dir results/<run_id>
```

> **Tip**: Pass `--dry-run` to preview planned execution details without starting ASTRA simulations, or `--mock-evaluator` for fast CI testing without an ASTRA binary.


---

## Development Roadmap

- [x] **Phase 1: Scalarized BO**
  - Scalarized BO with multiple weight combinations
  - Comparison with MOGA
  - Parallel ASTRA execution & GP surrogate
- [x] **Phase 2: True Multi-Objective BO**
  - Independent GP models per objective (`ModelListGP`)
  - Pareto front optimization using `qLogNEHVI` / `qEHVI`
  - Hypervolume tracking & candidate history logging
- [x] **Phase 3: Constraint-Aware MOBO & High-Fidelity Refactoring (v1.0.0)**
  - Exact analytical Normal CDF multi-constraint feasibility modeling ($P_{\text{feas}}$)
  - Relative fixed noise variance scaling for multi-scale GP surrogates ($\mu\text{m}\cdot\text{rad}$ vs $\text{MeV}$)
  - Dynamic parameter mapping to arbitrary ASTRA namelists & cavity decoupling
  - Longitudinal exit-plane loss detection & premature beam loss trapping (`PREMATURE_BEAM_LOSS`)
  - Full-chain photocathode & laser jitter robustness modeling (7 physical noise channels)
  - Multi-tier resilient acquisition proposal engine with adaptive retry & Sobol fallback
  - Atomic POSIX crash-proof checkpoint serialization (`_atomic_torch_save`)
  - Centralized publication-grade LaTeX reporting module (`mobo_linac.metrics.latex`)
- [ ] **Phase 4: Distributed High-Performance Optimization**
  - Distributed ASTRA evaluations via Ray / Dask / MPI on multi-node clusters
- [ ] **Phase 5: Advanced Surrogate Architectures**
  - MultiTaskGP, SAASBO, TuRBO trust-region BO, Deep Kernel Learning

---

## Reproducibility

For comprehensive instructions on reproducing all computational benchmarks, verification results, and figures, please see the [REPRODUCIBILITY.md](REPRODUCIBILITY.md) guide.

---

## Citation & Conference Presentation

Preliminary scalarized Bayesian Optimization results were presented at **ICABU 2025**:
* *Multi-Objective Bayesian Optimization for a 200 MeV Electron Injector Linac*, ICABU 2025.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
