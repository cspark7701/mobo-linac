# Reproducibility Guide

This guide provides instructions for reproducing all computational benchmarks, Pareto front verification results, figures, and LaTeX tables in the publication from a fresh clone.

---

## 1. Prerequisites & Environment Setup

### System Requirements
- Operating System: Linux (Ubuntu 20.04+ / RHEL 8+)
- Python: 3.11+
- ASTRA Executable: ASTRA v3.2 on system `PATH` (or specified via `ASTRA_BIN` environment variable).

### Environment Installation
```bash
# Clone repository
git clone https://github.com/cspark7701/mobo-linac.git
cd mobo-linac

# Create the exact publication environment (one command; installs the package too)
./install.sh --create-env linac-opt-pub --publication
#   equivalently: conda env create -f environment-lock.yml
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

---

## 5. Exact Publication Dependency Versions

For exact reproduction of the environment used in the publication, `requirements-publication.txt`
is the single pin list (environment-lock.yml only wraps it with Python 3.11.10). It matches the
recorded environment in `docs/environment/package_versions.txt` (checked by the test suite):

- Python: 3.11.10
- PyTorch: 2.5.0
- GPyTorch: 1.12
- BoTorch: 0.11.3
- NumPy: 1.26.4
- SciPy: 1.17.1
- pandas: 3.0.3
- matplotlib: 3.10.9
- lume-astra: 0.6.1 at commit 0af6c84; distgen at commit d856bc1
- ASTRA: v3.2
