# Reproducibility Guide

This guide provides instructions for reproducing all computational benchmarks, Pareto front verification results, figures, and LaTeX tables in the publication from a fresh clone.

---

## 1. Prerequisites & Environment Setup

### System Requirements
- Operating System: Linux (Ubuntu 20.04+ / RHEL 8+)
- Python: 3.11+
- ASTRA Executable: ASTRA v3.2 on system `PATH` (or specified via `ASTRA_BINARY` environment variable).

### Environment Installation
```bash
# Clone repository
git clone https://github.com/cspark7701/mobo_linac.git
cd mobo_linac

# Create conda environment from lock file
conda env create -f environment-lock.yml
conda activate linac-opt-pub

# Install package in editable mode
pip install -e .
```

---

## 2. Quick Paper Artifact Reproduction (No ASTRA Reruns)

To regenerate all figures and tables from archived processed datasets without re-running long particle tracking simulations:

```bash
./scripts/reproduce_paper.sh
```

### Generated Artifacts
- **Figures**: `docs/paper/figures/hypervolume_comparison.png`, `docs/paper/figures/verification_rerun_comparison.png`
- **Tables**: `results/verification/verification_table.tex`, `docs/paper/verification_table.tex`
- **Manuscript PDF**: `docs/paper/main.pdf`

---

## 3. Running Full Benchmarks & Verification (With ASTRA)

### Run Fast Verification Test Suite
```bash
pytest -m "not integration"
```

### Run Benchmark Campaign
```bash
mobo-linac run-benchmark --config configs/publication_200MeV.yaml --output-dir results/publication_benchmark --seeds 42 43 44 --budget 40
mobo-linac analyze-benchmark --output-dir results/publication_benchmark
```

### Run Independent Pareto Candidate Rerun Verification
```bash
mobo-linac run-verification --config configs/publication_200MeV.yaml --output-dir results/verification
```

### Run Perturbation Robustness Analysis
```bash
mobo-linac run-robustness --config configs/publication_200MeV.yaml --output-dir results/robustness
```

---

## 4. Primary Contact
For questions regarding beam dynamics settings, field maps, or algorithm configuration, please contact:
- **Author**: Chong Shik Park (`kuphy@korea.ac.kr`)
- **Institution**: Department of Accelerator Science, Korea University
