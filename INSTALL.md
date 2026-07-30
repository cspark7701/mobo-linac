# Installation & Environment Setup Guide for `mobo_linac`

This document provides complete instructions for setting up the **Multi-Objective Bayesian Optimization for Electron Injector Linac (`mobo_linac`)** framework on a new machine or for a new user.

---

## 📋 Prerequisites

Before installing, ensure your system meets the following requirements:

- **Operating System**: Linux 64-bit (Ubuntu 20.04+, RHEL/CentOS 8+, or WSL2 on Windows)
- **Python**: Python 3.10 or 3.11 (Python 3.11 recommended)
- **Environment Manager**: [Conda / Miniconda](https://docs.conda.io/en/latest/miniconda.html) or `mamba` (recommended)
- **Git**: Installed and configured
- **System Libraries**: Standard Linux C/Fortran runtime libraries (`gfortran`, `libgomp`) for running ASTRA binaries

---

## ⚡ Option 1: Quick Automated Setup (Recommended)

Clone the repository and run the automated installation script:

```bash
# 1. Clone the repository
git clone https://github.com/cspark7701/mobo_linac.git
cd mobo_linac

# 2. Run the automated installer (creates 'linac-opt' conda env and runs unit tests)
./install.sh --create-env

# 3. Activate environment & load environment variables
conda activate linac-opt
source env_setup.sh
```

---

## 🛠️ Option 2: Step-by-Step Manual Setup

If you prefer to set up your environment manually, follow these step-by-step instructions:

### Step 1: Clone the Repository

```bash
git clone https://github.com/cspark7701/mobo_linac.git
cd mobo_linac
```

### Step 2: Create and Activate a Conda Environment

```bash
conda create -n linac-opt python=3.11 -y
conda activate linac-opt
```

### Step 3: Upgrade Base Build Tools

```bash
python -m pip install --upgrade pip setuptools wheel
```

### Step 4: Install Accelerator Physics Dependencies

> ⚠️ **Important Note on `distgen`**: Do **NOT** run `pip install distgen` directly without specifying the git repository. PyPI hosts an unrelated Linux config tool with the same name. Always install Particle Distgen directly from the official GitHub repository:

```bash
# Install Particle Distribution Generator
pip install git+https://github.com/ColwynGulliford/distgen.git

# Install LUME-ASTRA Python interface
pip install git+https://github.com/ChristopherMayes/lume-astra.git
```

### Step 5: Install `mobo_linac` Package

Install the `mobo_linac` core package in editable mode:

```bash
pip install -e .
```

### Step 6: Make Local Binaries Executable & Source Environment

```bash
# Ensure execution permissions on local ASTRA binaries
chmod +x bin/*

# Source portable environment loader
source env_setup.sh
```

---

## 🧪 Step 7: Verify Installation with Pytest

Run the unit test suite (excluding long-running real ASTRA integration simulations) to verify the installation:

```bash
pytest -v -m "not integration"
```

Expected output:
```text
====================== 76 passed, 2 deselected in 14s =======================
```

---

## ⚙️ Environment Variables & Custom Binaries

The framework includes pre-bundled Linux 64-bit ASTRA binaries under `./bin/`:
- `./bin/astra`: ASTRA particle tracking executable
- `./bin/generator`: Initial particle distribution generator executable

When `source env_setup.sh` is executed, the following environment variables are set automatically:

```bash
export ASTRA_BIN="$(pwd)/bin/astra"
export GENERATOR_BIN="$(pwd)/bin/generator"
export PATH="$(pwd)/bin:${PATH}"
```

### Using Custom External ASTRA Binaries
If you have custom compiled ASTRA executables built for your specific cluster architecture:

```bash
export ASTRA_BIN="/path/to/your/custom/astra"
export GENERATOR_BIN="/path/to/your/custom/generator"
```

---

## ❓ Troubleshooting & FAQ

### 1. `ImportError: cannot import name 'Generator' from 'distgen'`
- **Cause**: PyPI's `distgen` package (a RedHat config generator) was installed instead of SLAC's Particle Distgen.
- **Fix**: Run `pip install --force-reinstall git+https://github.com/ColwynGulliford/distgen.git`.

### 2. `Permission denied` when running ASTRA
- **Cause**: `./bin/astra` executable flags are missing.
- **Fix**: Run `chmod +x bin/astra bin/generator`.

### 3. Warning about Pytest Config in `pyproject.toml`
- Pytest uses `pytest.ini` by default when both `pytest.ini` and `pyproject.toml` are present. This is normal and expected behavior.

---

## 🚀 Running Your First Optimization

After installation and verification, you can run a quick MOBO test run:

```bash
# Test run Phase 2 MOBO with 4 workers
python scripts/run_mobo.py --n-iterations 10 --batch-size 4 --num-workers 4
```

For full simulation procedures and publication guidelines, see [`docs/simulation_guide.md`](docs/simulation_guide.md).
