#!/usr/bin/env bash
# ==============================================================================
# sync_site.sh — Synchronize docs/site/ bundle to standalone mobo-linac.github.io repo
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SOURCE_SITE_DIR="${REPO_ROOT}/docs/site"

DEFAULT_TARGET="/home/cspark/Work/simulation_codes-working/mobo-linac.github.io"
TARGET_DIR="${1:-${DEFAULT_TARGET}}"

echo "========================================================================"
echo " MOBO-LINAC Documentation Website Synchronizer"
echo "========================================================================"
echo " Source Directory : ${SOURCE_SITE_DIR}"
echo " Target Directory : ${TARGET_DIR}"
echo "------------------------------------------------------------------------"

if [ ! -d "${SOURCE_SITE_DIR}" ]; then
  echo "Error: Source directory '${SOURCE_SITE_DIR}' does not exist." >&2
  exit 1
fi

if [ ! -d "${TARGET_DIR}" ]; then
  echo "Target directory '${TARGET_DIR}' does not exist yet."
  read -rp "Create directory '${TARGET_DIR}'? (y/N): " CONFIRM
  if [[ "${CONFIRM}" =~ ^[Yy]$ ]]; then
    mkdir -p "${TARGET_DIR}"
    echo "Created '${TARGET_DIR}'."
  else
    echo "Sync canceled."
    exit 0
  fi
fi

# Sync files
rsync -avh --delete \
  --exclude ".git" \
  --exclude ".github" \
  "${SOURCE_SITE_DIR}/" "${TARGET_DIR}/"

echo "------------------------------------------------------------------------"
echo " Synchronization complete."
echo " Files synchronized to: ${TARGET_DIR}"
echo "========================================================================"
