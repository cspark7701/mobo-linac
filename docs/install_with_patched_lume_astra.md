# Step-by-Step Guide: Installing `mobo-linac` with Patched `lume-astra`

This guide provides complete, reproducible instructions for setting up a fresh environment and installing **`mobo-linac`** alongside a locally cloned and patched **`lume-astra`** package.

---

## 📁 Workspace Directory Structure

It is recommended to organize the repositories side-by-side in a parent workspace directory (e.g., `~/Work/` or `~/projects/`):

```text
workspace/
├── lume-astra/                # Cloned and patched LUME-ASTRA repository
└── mobo-linac/                # Main MOBO Linac optimization repository
    ├── bin/                   # Local ASTRA binaries
    ├── patches/               # Included patch files
    └── src/mobo_linac/        # Core package
```

---

## 📋 Prerequisites

- **OS**: Linux 64-bit (Ubuntu 20.04+, RHEL 8+, or WSL2 on Windows)
- **Conda**: Miniconda / Anaconda / Mamba
- **Git**: Installed and configured
- **Compilers / Runtime**: Standard Linux C/Fortran libraries (`gfortran`, `libgomp`)

---

## 🚀 Step-by-Step Installation

### Step 1: Clone Both Repositories

In your chosen workspace directory:

```bash
# 1. Clone LUME-ASTRA
git clone https://github.com/ChristopherMayes/lume-astra.git

# 2. Clone MOBO-LINAC
git clone https://github.com/cspark7701/mobo-linac.git
```

---

### Step 2: Create and Activate Conda Environment

```bash
# Create dedicated Python 3.11 environment
conda create -n linac-opt python=3.11 -y

# Activate the environment
conda activate linac-opt
```

---

### Step 3: Upgrade Build Tools

```bash
python -m pip install --upgrade pip setuptools wheel
```

---

### Step 4: Install Particle Distgen

> ⚠️ **Important**: Do **not** run `pip install distgen` (PyPI hosts an unrelated Linux distribution tool under that name). Always install directly from GitHub:

```bash
pip install git+https://github.com/ColwynGulliford/distgen.git
```

---

### Step 5: Apply Patch & Install `lume-astra` from Source

Navigate to the `lume-astra` repository, apply the patch from `mobo-linac/patches/lume_astra.patch`, and install in editable mode:

```bash
cd lume-astra

# Option A: Apply the included patch from mobo-linac
git apply ../mobo-linac/patches/lume_astra.patch

# Option B: Alternatively, apply inline patch directly if needed:
# sed -i '/numpy/d' requirements.txt

# Install lume-astra in editable mode
pip install -e .

# Return to mobo-linac directory
cd ../mobo-linac
```

---

### Step 6: Install `mobo-linac` in Editable Mode

From inside the `mobo-linac` directory:

```bash
# Install mobo-linac with core and dev dependencies
pip install -e ".[dev]"
```

---

### Step 7: Configure ASTRA Binaries and Load Environment

Ensure executable permissions on bundled ASTRA simulation binaries and source environment variables:

```bash
# Ensure execution permissions on local ASTRA binaries
chmod +x bin/*

# Source portable environment loader (sets ASTRA_BIN and PATH)
source env_setup.sh
```

---

## 🧪 Verification & Health Check

### 1. Verify `lume-astra` Source Binding

Confirm that Python imports `lume-astra` from your local patched directory:

```bash
python -c "import astra; print('lume-astra location:', astra.__file__)"
```
*Expected Output:*
```text
lume-astra location: /path/to/workspace/lume-astra/astra/__init__.py
```

### 2. Verify `mobo-linac` CLI Entry Point

```bash
mobo-linac --help
```

### 3. Run Unit Test Suite

Run the full unit test suite (excluding long-running ASTRA particle tracking simulations):

```bash
pytest -v -m "not integration" --tb=short
```
*Expected Result: All 160+ unit tests pass with 100% success.*

---

## 💡 Summary Cheatsheet (Copy & Paste)

```bash
# Clone
git clone https://github.com/ChristopherMayes/lume-astra.git
git clone https://github.com/cspark7701/mobo-linac.git

# Environment
conda create -n linac-opt python=3.11 -y
conda activate linac-opt
pip install --upgrade pip setuptools wheel
pip install git+https://github.com/ColwynGulliford/distgen.git

# Patch & Install lume-astra
cd lume-astra
git apply ../mobo-linac/patches/lume_astra.patch
pip install -e .
cd ../mobo-linac

# Install mobo-linac & setup
pip install -e ".[dev]"
chmod +x bin/*
source env_setup.sh

# Verify
mobo-linac --help
pytest -v -m "not integration" --tb=short
```
