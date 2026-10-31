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
# A complete, stable-source validation run precedes the remaining physical stages.
"$PYTHON_BIN" -c 'import sys,json;sys.path.insert(0,"scripts");from evaluate_revision_round6_scaling import code_identity;print(json.dumps(code_identity(),sort_keys=True))' > results/revision_round6/validation_start_code.json
"$PYTHON_BIN" -m pytest -m "not integration" --tb=short --cov=mobo_linac \
  --cov-report=term-missing --cov-fail-under=100 > results/revision_round6/logs/final_validation.log 2>&1
"$PYTHON_BIN" -m ruff check src scripts tests
"$PYTHON_BIN" scripts/verify_docs_sync.py
"$PYTHON_BIN" scripts/build_supplement_manifest.py
"$PYTHON_BIN" - <<'PYCODE'
import json, sys
from pathlib import Path
sys.path.insert(0, 'scripts')
from evaluate_revision_round6_scaling import code_identity
from prepare_revision_round6 import sha
base=Path('results/revision_round6')
assert json.loads((base/'validation_start_code.json').read_text())==code_identity(), 'Code changed during validation'
(base/'validation_complete.json').write_text(json.dumps({
    'status':'passed','coverage_required':100,'code_sha256':code_identity(),
    'test_log_sha256':sha(base/'logs/final_validation.log')},indent=2)+'\n')
PYCODE
"$PYTHON_BIN" scripts/record_revision_round6_stage.py validation
"$PYTHON_BIN" scripts/evaluate_revision_round6_resolution.py --resume --wait-for-workers \
  > results/revision_round6/logs/resolution_refinement.log 2>&1
"$PYTHON_BIN" scripts/analyze_revision_round6.py resolution --resume \
  --output-dir results/revision_round6/analysis_resolution \
  > results/revision_round6/logs/resolution_analysis.log 2>&1
"$PYTHON_BIN" scripts/record_revision_round6_stage.py numerical
"$PYTHON_BIN" scripts/evaluate_revision_round6_scaling.py --resume --wait-for-workers \
  > results/revision_round6/logs/scaling.log 2>&1
"$PYTHON_BIN" scripts/analyze_revision_round6.py scaling --resume \
  --output-dir results/revision_round6/analysis_scaling \
  > results/revision_round6/logs/scaling_analysis.log 2>&1
"$PYTHON_BIN" scripts/record_revision_round6_stage.py scaling
printf 'Physical studies and offline analyses complete; manuscript integration, reviewer responses and final validation remain.\n'
