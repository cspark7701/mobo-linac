#!/usr/bin/env bash
# ==============================================================================
# Shell environment loader for mobo_linac (source it; install with ./install.sh)
# ==============================================================================
# Usage:
#   source setup.sh                  Activate the conda environment 'linac-opt'
#   MOBO_LINAC_ENV=NAME source setup.sh
#
# Puts the bundled ASTRA tools (./bin) on PATH, exports ASTRA_BIN and GENERATOR_BIN,
# and activates the conda environment when conda is available and the environment exists.
# The package itself is imported from the editable install (./install.sh); this script
# does not modify the Python module search path. Sourcing it again does not duplicate PATH.
# ==============================================================================

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  echo "setup.sh must be sourced so its settings stay in your shell: source setup.sh" >&2
  exit 1
fi

_mobo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

export PROJECT_ROOT="${_mobo_root}"
export ASTRA_BIN="${_mobo_root}/bin/astra"
export GENERATOR_BIN="${_mobo_root}/bin/generator"
case ":${PATH}:" in
  *":${_mobo_root}/bin:"*) ;;
  *) export PATH="${_mobo_root}/bin:${PATH}" ;;
esac

_mobo_env="${MOBO_LINAC_ENV:-linac-opt}"
if command -v conda >/dev/null 2>&1; then
  if ! type conda 2>/dev/null | grep -q "function"; then
    eval "$(conda shell.bash hook 2>/dev/null)"  # enable 'conda activate' in this shell
  fi
  if conda env list 2>/dev/null | awk '{print $1}' | grep -qx "${_mobo_env}"; then
    conda activate "${_mobo_env}" || echo "[mobo_linac] WARNING: could not activate conda environment '${_mobo_env}'." >&2
  else
    echo "[mobo_linac] WARNING: conda environment '${_mobo_env}' not found; create it with ./install.sh --create-env ${_mobo_env}." >&2
  fi
else
  echo "[mobo_linac] conda not found; using the current Python environment." >&2
fi

echo "[mobo_linac] Environment configured:"
echo "  PROJECT_ROOT:  ${PROJECT_ROOT}"
echo "  ASTRA_BIN:     ${ASTRA_BIN}"
echo "  GENERATOR_BIN: ${GENERATOR_BIN}"
echo "  Python:        $(command -v python || echo 'not found')"
for _mobo_tool in "${ASTRA_BIN}" "${GENERATOR_BIN}"; do
  [[ -x "${_mobo_tool}" ]] || echo "[mobo_linac] WARNING: ${_mobo_tool} is missing or not executable." >&2
done
if [[ ":${PYTHONPATH:-}:" == *":${_mobo_root}/src:"* ]]; then
  echo "[mobo_linac] WARNING: PYTHONPATH contains ${_mobo_root}/src; remove it (left by an older setup.sh)" \
       "so the installed package is the one imported." >&2
fi
unset _mobo_root _mobo_env _mobo_tool
