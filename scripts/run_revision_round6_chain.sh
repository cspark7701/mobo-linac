#!/usr/bin/env bash
# Adopted round6 studies; one shared two-worker allocation, immutable new outputs.
set -Eeuo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export PYTHONUNBUFFERED=1
PYTHON_BIN=/home/cspark/Work/simulation_codes-working/miniforge3/envs/linac-opt/bin/python
mkdir -p results/revision_round6/logs
# Prevent two copies of this chain. Each runner additionally owns worker.lock.
exec 9>results/revision_round6/chain.lock
flock -n 9 || { echo 'Another round6 chain already owns the lock.' >&2; exit 1; }
trap 'printf "Round6 chain failed at line %s; outputs retained.\n" "$LINENO" >&2' ERR
"$PYTHON_BIN" scripts/run_revision_round6_resolution.py --resume --wait-for-workers \
  > results/revision_round6/logs/resolution_refinement.log 2>&1
"$PYTHON_BIN" scripts/analyze_revision_round6.py resolution \
  --output-dir results/revision_round6/analysis_resolution \
  > results/revision_round6/logs/resolution_analysis.log 2>&1
"$PYTHON_BIN" scripts/run_revision_round6_scaling.py --resume --wait-for-workers \
  > results/revision_round6/logs/scaling.log 2>&1
"$PYTHON_BIN" scripts/analyze_revision_round6.py scaling \
  --output-dir results/revision_round6/analysis_scaling \
  > results/revision_round6/logs/scaling_analysis.log 2>&1
printf 'Physical studies and offline analyses complete; manuscript integration, reviewer responses and final validation remain.\n'
