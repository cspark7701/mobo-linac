#!/usr/bin/env bash
# ==============================================================================
# Portable Environment Loader Script for mobo_linac
# ==============================================================================
# Usage:
#   source env_setup.sh
# ==============================================================================

# Dynamically resolve project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

export PROJECT_ROOT="${SCRIPT_DIR}"
export ASTRA_BIN="${SCRIPT_DIR}/bin/astra"
export GENERATOR_BIN="${SCRIPT_DIR}/bin/generator"
export PATH="${SCRIPT_DIR}/bin:${PATH}"
export PYTHONPATH="${SCRIPT_DIR}/src:${PYTHONPATH:-}"

echo "[mobo_linac] Environment configured:"
echo "  PROJECT_ROOT:  ${PROJECT_ROOT}"
echo "  ASTRA_BIN:     ${ASTRA_BIN}"
echo "  GENERATOR_BIN: ${GENERATOR_BIN}"
