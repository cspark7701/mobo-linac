#!/usr/bin/env bash
# Round2 revision simulations authorized by the author on 2026-10-27
# (docs/paper/revisions/consolidated_round2_revision_tasks.md).
#   1. references : MOGA-derived nominal re-evaluation (1 run), its lattice jitter (50 runs) and
#                   jitter of the two TDR-passing primary observations (100 runs).        ~1 h
#   2. tdr        : constraint-aware qLogNEHVI under the KLS TDR optimization constraints,
#                   seeds 42-44, 160 evaluations each (16 shared Sobol + 18 batches of 8). ~10 h
#   3. sobol      : budget-matched Sobol arm, seeds 42-51, 160 points of each seed's scrambled
#                   Sobol sequence (its first 16 are the shared initial design), no acquisition. ~10 h
# Usage: scripts/run_revision_round2_simulations.sh [references|tdr|sobol|all]
# Outputs are immutable: a stage refuses to start if its output directory already has content.
set -Eeuo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
OUT="${ROUND2_ROOT:-results/revision_round2}"
WORKERS="${WORKERS:-8}"
DEVICE="${DEVICE:-cuda:0}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
STAGE="${1:-all}"
mkdir -p "$OUT/logs"

record() {  # record STAGE STATUS: append a provenance line for the stage
  "$PYTHON_BIN" - "$OUT/run_record.jsonl" "$1" "$2" <<'EOF'
import hashlib, json, subprocess, sys, time
from pathlib import Path
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
entry = {"stage": sys.argv[2], "status": sys.argv[3], "time": time.strftime("%Y-%m-%dT%H:%M:%S"),
         "commit": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip(),
         "dirty": bool(subprocess.run(["git", "status", "--porcelain", "--", "src", "scripts", "configs"],
                                      capture_output=True, text=True).stdout.strip()),
         "configs": {p: sha(p) for p in ("configs/publication_200MeV.yaml", "configs/revision_tdr_200MeV.yaml")},
         "astra_sha256": sha("bin/astra")}
with open(sys.argv[1], "a") as handle:
    handle.write(json.dumps(entry, sort_keys=True) + "\n")
EOF
}

fresh() { [[ ! -e "$1" ]] || [[ -z "$(ls -A "$1")" ]] || { echo "ERROR: $1 already has content" >&2; exit 1; }; }

run_references() {
  fresh "$OUT/references"
  record references started
  "$PYTHON_BIN" scripts/evaluate_revision_reference_settings.py --output-dir "$OUT/references" --workers "$WORKERS"
  record references completed
}

run_tdr() {
  fresh "$OUT/tdr_benchmark"
  record tdr started
  "$PYTHON_BIN" -m mobo_linac.cli run-benchmark --config configs/revision_tdr_200MeV.yaml \
    --algorithms constrained_qlognehvi --seeds 42 43 44 --budget 160 --n-sobol-init 16 --batch-size 8 \
    --num-workers "$WORKERS" --max-concurrent-campaigns 1 --total-workers "$WORKERS" --campaign-threads 1 \
    --device "$DEVICE" --output-dir "$OUT/tdr_benchmark"
  record tdr completed
}

run_sobol() {
  record sobol started
  for seed in 42 43 44 45 46 47 48 49 50 51; do
    local dir="$OUT/sobol/sobol_seed_$seed"
    if [[ -f "$dir/run_complete.json" ]]; then echo "Skipping completed $dir"; continue; fi
    fresh "$dir"
    # The reporting reference is the primary benchmark's frozen model-space reference.
    "$PYTHON_BIN" -m mobo_linac.cli run-unconstrained --config configs/publication_200MeV.yaml \
      --num-initial-samples 160 --n-iterations 0 --seed "$seed" --num-workers "$WORKERS" --device cpu \
      --output-dir "$dir" --reporting-ref-point -0.0000015 -0.0000015 -1500000.0 --quiet
  done
  record sobol completed
}

case "$STAGE" in
  references) run_references 2>&1 | tee "$OUT/logs/references.log" ;;
  tdr) run_tdr 2>&1 | tee "$OUT/logs/tdr.log" ;;
  sobol) run_sobol 2>&1 | tee "$OUT/logs/sobol.log" ;;
  all)
    run_references 2>&1 | tee "$OUT/logs/references.log"
    run_tdr 2>&1 | tee "$OUT/logs/tdr.log"
    run_sobol 2>&1 | tee "$OUT/logs/sobol.log" ;;
  *) echo "Unknown stage: $STAGE" >&2; exit 2 ;;
esac
