#!/usr/bin/env bash
# ==============================================================================
# mobo_linac installation (the one setup script)
# ==============================================================================
# Usage:
#   ./install.sh                     Install into the active Python environment (editable, with dev extras)
#   ./install.sh --publication       Install the exact publication environment (requirements-publication.txt)
#   ./install.sh --create-env NAME   Create and use a conda/mamba environment NAME first
#   ./install.sh --no-tests          Skip the unit test verification
#
# The script never edits PYTHONPATH and only activates an environment it was asked to create.
# The ASTRA executable is found from the configuration (simulation.executable), $ASTRA_BIN or PATH.
# ==============================================================================
set -euo pipefail

ENV_NAME=""
PUBLICATION=false
RUN_TESTS=true
PYTHON_VERSION="3.11.10"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --create-env) ENV_NAME="$2"; shift 2 ;;
    --publication) PUBLICATION=true; shift ;;
    --no-tests) RUN_TESTS=false; shift ;;
    --python-version) PYTHON_VERSION="$2"; shift 2 ;;
    -h|--help) sed -n '2,13p' "$0"; exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

if [[ -n "${ENV_NAME}" ]]; then
  manager="$(command -v mamba || command -v conda || true)"
  [[ -n "${manager}" ]] || { echo "ERROR: conda/mamba not found; cannot create ${ENV_NAME}." >&2; exit 1; }
  "${manager}" create -y -n "${ENV_NAME}" python="${PYTHON_VERSION}"
  eval "$("${manager}" shell.bash hook)"
  "$(basename "${manager}")" activate "${ENV_NAME}"
fi
echo "Python: $(command -v python) ($(python --version 2>&1))"

[[ -d bin ]] && chmod +x bin/* 2>/dev/null || true
python -m pip install --upgrade pip setuptools wheel
if ${PUBLICATION}; then
  python -m pip install -r requirements-publication.txt
else
  python -m pip install -e ".[dev]"
fi

if ${RUN_TESTS}; then
  python -m pytest -m "not integration" -q
fi
echo "mobo_linac installed: $(python -c 'import mobo_linac; print(mobo_linac.__version__)')"
