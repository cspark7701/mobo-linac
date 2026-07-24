# Step-by-Step Simulation & Execution Guide

This document provides complete instructions for executing accelerator beam dynamics simulations and Multi-Objective Bayesian Optimization (MOBO) campaigns for the **200 MeV Electron Injector Linac**.

---

## 1. Prerequisites & Environment Setup

### 1.1 Python Environment
Ensure you are using Python $\ge 3.10$ with PyTorch, BoTorch, GPyTorch, and ASTRA Python wrappers installed:
```bash
# Activate your conda or virtual environment
conda activate linac-opt   # or source venv/bin/activate
```

### 1.2 Package Installation
Install `mobo_linac` in editable development mode from the repository root:
```bash
cd /home/cspark/Work/projects/mobo_linac
pip install -e .
```

Verify that the CLI entry point is installed and working:
```bash
mobo-linac --help
```

### 1.3 ASTRA Binary Verification
Ensure the `ASTRA` executable is present in your `PATH` or accessible by the environment:
```bash
which ASTRA
```

---

## 2. Simulation Methods

You can run simulations using three distinct interfaces:
- **Method A: Package CLI (`mobo-linac`)** — *Recommended for production and reproducible runs*.
- **Method B: Modular Python Scripts** — *Recommended for controlled campaigns & comparative research*.
- **Method C: Jupyter Notebooks** — *Recommended for interactive exploratory analysis*.

---

### Method A: Package CLI (`mobo-linac`)

The command-line interface provides standardized execution, checkpointing, and post-analysis.

#### 2.1 Run a New Optimization Campaign
To launch a full MOBO campaign with default or custom configuration:
```bash
mobo-linac run --config configs/mobo_200mev.yaml
```
- **Execution Flow**:
  1. Loads `configs/mobo_200mev.yaml` (design variables, bounds, objectives, constraints).
  2. Generates initial Sobol quasi-random sample points ($N=16$).
  3. Evaluates ASTRA simulations in process-isolated working directories (`results/<run_id>/work/eval_<id>/`).
  4. Fits independent Gaussian Process (GP) surrogates.
  5. Optimizes the $q\text{LogNEHVI}$ acquisition function to select batch candidates ($q=4$).
  6. Iterates for the specified number of optimization batches (saving checkpoints per iteration).

#### 2.2 Resume an Interrupted Campaign
If a campaign is interrupted or you wish to run additional iterations:
```bash
mobo-linac resume --run-dir results/<run_id>
```

#### 2.3 Analyze Results and Generate Plots
To post-process an existing run directory and export diagnostic figures:
```bash
mobo-linac analyze --run-dir results/<run_id>
```

---

### Method B: Modular Python Scripts

For batch campaign execution, validation, and Phase 2 vs Phase 3 comparisons, use the dedicated scripts in `scripts/`.

#### 2.1 Reproducible Validation Campaign (Phase 3 Constrained MOBO)
Executes a single controlled campaign with feasibility filtering:
```bash
python scripts/run_validation_campaign.py
```
- **Key Features**:
  - Uses fixed reporting reference point derived from the initial sample space.
  - Generates full dataset exports in `results/validation_<timestamp>/`.

#### 2.2 Controlled Comparison & Independent Pareto Candidate Verification
Executes Phase 2 (Unconstrained MOBO) and Phase 3 (Constrained MOBO) under exact protocol parity, followed by independent rerun verification of key Pareto candidates:
```bash
python scripts/run_comparison_and_verification.py
```
- **Key Features**:
  - Parity enforcement: identical initial seed ($42$), Sobol initial design ($N=16$), batch size ($q=4$), parameter bounds, and fixed reporting reference point.
  - Selects 5 representative Pareto candidates (`min_emit_x`, `min_emit_y`, `min_sigma_energy`, `knee_point`, `balanced_feasible`).
  - Reruns candidates in fresh isolated workdirs to check for zero cross-talk ($< 10^{-3}\%$ relative error threshold).
  - Automatically exports comparison figures and updates [docs/results/mobo_validation_report.md](file:///home/cspark/Work/projects/mobo_linac/docs/results/mobo_validation_report.md).

#### 2.3 Individual MOBO Scripts
- `python scripts/run_mobo.py`: Runs baseline unconstrained MOBO.
- `python scripts/run_constrained_mobo.py`: Runs feasibility-constrained MOBO.

---

### Method C: Jupyter Notebooks

For interactive visualization, step-by-step debugging, or custom plot generation:

#### Execution Order:

1. **[get_data.ipynb](file:///home/cspark/Work/projects/mobo_linac/get_data.ipynb)**:
   - Initial Sobol sampling ($N=16$).
   - Runs initial ASTRA evaluations to populate baseline training dataset (`train_X.csv`, `train_Y.csv`).

2. **[mobo.ipynb](file:///home/cspark/Work/projects/mobo_linac/mobo.ipynb)** or **[scalarized_bo.ipynb](file:///home/cspark/Work/projects/mobo_linac/scalarized_bo.ipynb)**:
   - Interactive iteration of Bayesian Optimization algorithm ($q\text{LogNEHVI}$ or scalarized acquisition).
   - Real-time display of GP surrogate fit and hypervolume growth.

3. **[get_data-postprocessing.ipynb](file:///home/cspark/Work/projects/mobo_linac/get_data-postprocessing.ipynb)**:
   - Post-processing and diagnostic analysis of completed runs.
   - Generates 2D/3D Pareto front scatter plots, constraint violation breakdown, and manuscript figure exports.

---

## 3. Output Directory Structure

Each optimization campaign creates a timestamped run directory under `results/`:

```text
results/<run_id>/
├── config.yaml                     # Saved run configuration
├── evaluations.csv                 # Master evaluation history with metadata
├── objectives_physical.csv         # Physical objective values (emit_x, emit_y, sigma_e)
├── objectives_model.csv            # Model space negated objective values (-emit_x, -emit_y, -sigma_e)
├── constraints.csv                 # Diagnostic beam metrics (sigma_x, sigma_y, E_kin, transmission)
├── candidate_history.csv           # Physical parameter vectors evaluated
├── hypervolume.csv                 # Iteration-by-iteration hypervolume history
├── pareto_all.csv                  # Non-dominated set among all valid points
├── pareto_feasible.csv             # Non-dominated set among physically feasible points
├── failures.csv                    # Log of invalid or failed simulations
├── checkpoints/                    # GP model and optimizer state checkpoints
├── figures/                        # Generated diagnostic plots
└── work/                           # Isolated ASTRA working directories
    ├── eval_000001/
    │   ├── astra.in
    │   ├── gun.dat
    │   ├── PAL_SOL_A.dat
    │   ├── TWS_Sband.dat
    │   ├── pal_photo2.ini
    │   ├── manifest.json
    │   └── astra.Log.001
    └── ...
```

---

## 4. Verification & Testing

To run the automated unit test suite without executing ASTRA:
```bash
pytest
```
To include real ASTRA integration tests:
```bash
pytest -m integration
```
