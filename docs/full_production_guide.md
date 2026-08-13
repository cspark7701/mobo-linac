# Full Production Simulation & Analysis Pipeline Guide

This document provides complete instructions and architecture documentation for running the consolidated production simulation and analysis script: **[`scripts/run_full_production.sh`](../scripts/run_full_production.sh)**.

---

## 📌 Overview & Design Goals

The `run_full_production.sh` script automates the complete 200 MeV electron injector linac optimization and scientific analysis pipeline in a single, robust bash script.

### Key Capabilities:
### Key Capabilities:
1. **Automated 90% CPU Parallelization**: Dynamically detects available CPU cores (`os.cpu_count()`) and allocates 90% capacity to `ProcessPoolExecutor` worker pools for maximum throughput without overloading the host OS. Custom worker counts can be specified via `-w` / `--workers`.
2. **Screen Verbose Toggle (`-q` / `--quiet`)**: Provides a quiet execution mode that suppresses screen output and redirects progress logs to dedicated files. This prevents token explosion when running under AI agent prompts (e.g. Antigravity / Codex).
3. **End-to-End Execution**: Automatically runs Phase 1 (Scalarized BO), Phase 2 (Unconstrained MOBO), and Phase 3 (Constraint-Aware MOBO) campaigns, computes hypervolume progression, reruns independent Pareto candidate verifications, and performs engineering tolerance robustness analysis.
4. **Clean Directory Separation**: Organizes all generated datasets, CSVs, checkpoints, LaTeX tables, and figures into distinct output subdirectories under `results/`.

---

## 🛠️ Usage & Options

### Basic Usage

```bash
# Execute with default settings and screen verbosity ON
./scripts/run_full_production.sh
```

### Quiet Mode (Recommended for AI Prompts)

```bash
# Execute silently (redirects stdout/stderr to simulation log files)
./scripts/run_full_production.sh --quiet
```

### Advanced Parameter Scanning

```bash
# Custom worker core count, iteration budget, batch size, and output directory
./scripts/run_full_production.sh -w 8 --iterations 20 --batch-size 8 --output-dir results/production_campaign_v1
```

---

## ⚙️ Command-Line Arguments Reference

| Flag | Long Option | Default | Description |
|:---:|:---:|:---:|:---|
| `-q` | `--quiet` | Off (`VERBOSE=1`) | Suppresses screen output and logs directly to files. |
| `-i` | `--iterations` | `10` | Total number of Bayesian Optimization iterations ($N$). |
| `-b` | `--batch-size` | `4` | Number of candidate parameter vectors proposed per iteration ($q$). |
| `-w` | `--workers` | `90% CPU` | Custom number of parallel worker processes. |
| `-d` | `--device` | `auto` | Target compute device for PyTorch GP fitting and BoTorch optimization (`auto`, `cuda`, `cpu`). |
| `-o` | `--output-dir` | `results/full_production` | Base directory for storing all simulation and analysis artifacts. |
| `-h` | `--help` | N/A | Displays CLI usage help message. |

---

## 📂 Output Folder Structure

Each pipeline run populates the specified output directory as follows:

```
results/full_production/
├── phase1_scalarized/
│   ├── simulation.log            # Execution log (quiet mode)
│   ├── config.json               # Run configuration & parameters
│   ├── evaluations.csv           # Evaluated design vectors & scalar outcomes
│   ├── pareto.csv                # Non-dominated front under scalar weights
│   └── hypervolume.csv           # Hypervolume tracking
│
├── phase2_unconstrained/
│   ├── simulation.log            # Execution log (quiet mode)
│   ├── config.json               # Run configuration & parameters
│   ├── train_X.csv               # Evaluated 6D design vectors
│   ├── train_Y.csv               # Evaluated 3D objective values
│   ├── pareto.csv                # Extracted non-dominated Pareto set
│   ├── hypervolume.csv           # Iteration-by-iteration hypervolume growth
│   └── gp_checkpoint/            # PyTorch GP surrogate model checkpoints
│
├── phase3_constrained/
│   ├── simulation.log            # Execution log (quiet mode)
│   ├── config.json               # Run configuration & parameters
│   ├── train_X.csv               # Evaluated 6D design vectors
│   ├── train_Y.csv               # Evaluated 3D objective values
│   ├── pareto.csv                # Extracted non-dominated Pareto set
│   ├── constraints.csv           # 8-diagnostic constraint evaluations
│   ├── hypervolume.csv           # Feasible hypervolume growth
│   └── gp_checkpoint/            # PyTorch GP surrogate model checkpoints
│
└── analysis/
    ├── analysis.log              # Post-processing execution log
    ├── comparison_report.md      # Generated Markdown validation report
    ├── verification_records.csv  # Independent Pareto candidate rerun audit
    ├── verification_table.tex    # Formatted LaTeX verification table
    ├── hypervolume_comparison.png# Comparative hypervolume progression plot
    ├── pareto_front_comparison.png# 2D physical objective projections
    └── robustness/               # Sensitivity analysis under perturbed RF phase & magnet fields
```


---

## 🧪 1-to-1 Notebook Mirror

This shell pipeline is mirrored 1-to-1 in the interactive Jupyter notebook:
👉 **[`notebooks/full_production_pipeline.ipynb`](../notebooks/full_production_pipeline.ipynb)**

Both the shell script and the notebook utilize identical underlying Python modules from `mobo_linac`, ensuring exact numerical agreement between CLI automation and interactive analysis.
