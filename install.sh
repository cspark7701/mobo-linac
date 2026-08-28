#!/usr/bin/env bash
# ==============================================================================
# Automated Installation & Environment Setup Script for mobo_linac
# ==============================================================================
# Usage:
#   ./install.sh                # Install into current active Python environment
#   ./install.sh --create-env   # Create a new conda environment 'linac-opt' and install
#   ./install.sh --env-name myenv # Specify custom conda environment name
# ==============================================================================

set -euo pipefail

ENV_NAME="linac-opt"
CREATE_ENV=false
PYTHON_VERSION="3.11"

# Parse command line flags
while [[ $# -gt 0 ]]; do
  case "$1" in
    --create-env)
      CREATE_ENV=true
      shift
      ;;
    --env-name)
      ENV_NAME="$2"
      CREATE_ENV=true
      shift 2
      ;;
    --python-version)
      PYTHON_VERSION="$2"
      shift 2
      ;;
    -h|--help)
      echo "Usage: ./install.sh [OPTIONS]"
      echo "Options:"
      echo "  --create-env              Create a new Conda environment (default name: linac-opt)"
      echo "  --env-name <name>         Specify custom Conda environment name"
      echo "  --python-version <ver>    Specify Python version (default: 3.11)"
      echo "  -h, --help                Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

echo "======================================================================"
echo " Starting mobo_linac Environment Setup"
echo " Working Directory: ${SCRIPT_DIR}"
echo "======================================================================"

# 1. Conda environment creation (if requested)
if [ "${CREATE_ENV}" = true ]; then
  if command -v conda &> /dev/null; then
    echo "[1/5] Creating Conda environment '${ENV_NAME}' (Python ${PYTHON_VERSION})..."
    conda create -y -n "${ENV_NAME}" python="${PYTHON_VERSION}"
    echo "Activating Conda environment '${ENV_NAME}'..."
    eval "$(conda shell.bash hook)"
    conda activate "${ENV_NAME}"
  elif command -v mamba &> /dev/null; then
    echo "[1/5] Creating Mamba environment '${ENV_NAME}' (Python ${PYTHON_VERSION})..."
    mamba create -y -n "${ENV_NAME}" python="${PYTHON_VERSION}"
    echo "Activating Mamba environment '${ENV_NAME}'..."
    eval "$(mamba shell.bash hook)"
    mamba activate "${ENV_NAME}"
  else
    echo "ERROR: Conda/Mamba not found on PATH. Cannot create environment."
    exit 1
  fi
else
  echo "[1/5] Using active Python environment: $(which python)"
fi

# Verify Python version
PYTHON_CURR_VER=$(python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "Python Version: ${PYTHON_CURR_VER}"

# 2. Make local binaries executable
echo "[2/5] Setting executable permissions for local ASTRA binaries in bin/..."
if [ -d "${SCRIPT_DIR}/bin" ]; then
  chmod +x "${SCRIPT_DIR}/bin/"* || true
  echo "Binaries in bin/ updated."
else
  echo "WARNING: bin/ directory not found in ${SCRIPT_DIR}"
fi

# 3. Install Python dependencies
echo "[3/5] Upgrading build tools & installing core dependencies..."
python -m pip install --upgrade pip setuptools wheel

echo "Installing Particle Distgen (ColwynGulliford/distgen)..."
python -m pip install git+https://github.com/ColwynGulliford/distgen.git

echo "Installing lume-astra..."
if [ -d "/home/cspark/Work/simulation_codes-working/lume-astra" ]; then
  echo "Installing from local modified source: /home/cspark/Work/simulation_codes-working/lume-astra"
  python -m pip install -e /home/cspark/Work/simulation_codes-working/lume-astra
elif [ -d "${SCRIPT_DIR}/../lume-astra" ]; then
  echo "Installing from local source: ${SCRIPT_DIR}/../lume-astra"
  python -m pip install -e "${SCRIPT_DIR}/../lume-astra"
else
  python -m pip install git+https://github.com/ChristopherMayes/lume-astra.git
fi

# 4. Install mobo_linac package in editable mode
echo "[4/5] Installing mobo_linac package in editable mode..."
python -m pip install -e .[dev] || python -m pip install -e .

# 5. Run test suite verification
echo "[5/5] Running pytest unit test suite verification..."
python -m pytest -v -m "not integration"

echo "======================================================================"
echo " SUCCESS: mobo_linac installation and verification complete!"
echo "======================================================================"
echo "To load environment variables in new terminal sessions, run:"
echo "  source env_setup.sh"
echo "======================================================================"
