#!/usr/bin/env bash
# Run all three optimization phases and audited analysis with shared conventions.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "$PROJECT_ROOT"

PYTHON_BIN="${PYTHON_BIN:-python3}"
CONFIG="configs/publication_200MeV.yaml"
OUTPUT_BASE_DIR="results/full_production"
N_ITERATIONS=20
BATCH_SIZE=8
NUM_INITIAL_SAMPLES=16
NUM_WORKERS=4
NUM_PERTURBATIONS=50
SEED=42
DEVICE=auto
P1_CASE=all
QUIET=0
RESUME=0
DRY_RUN=0
# Model-space reference: -(1.5 um rad, 1.5 um rad, 1.5 MeV).
REFERENCE=(-0.0000015 -0.0000015 -1500000)

usage() {
  cat <<'EOF'
Usage: scripts/run_full_production.sh [OPTIONS]
  --config PATH          Shared configuration (default: publication_200MeV.yaml)
  -o, --output-dir DIR    Fresh campaign root (default: results/full_production)
  -i, --iterations N      Total BO iterations per run (default: 20)
  -b, --batch-size Q      Candidates per BO batch (default: 8)
  --initial-samples N    Initial Sobol samples (default: 16)
  -w, --workers N         ASTRA and audit workers (default: 4)
  --seed N               Base seed (default: 42)
  -d, --device DEVICE     auto, cpu, cuda, or cuda:N (default: auto)
  --p1-case CASE          all or one Option 2 case (default: all)
  --reference RX RY RE    Reporting reference in model-space units/objective order
  --perturbations N      Robustness samples per representative (default: 50)
  -r, --resume            Continue existing runs using saved scientific settings
  -q, --quiet             Keep step messages; write detailed output to log files
  --dry-run              Print validated commands without creating outputs or running ASTRA
  -h, --help              Show help
Set PYTHON_BIN to the Python interpreter in the installed linac environment.
Existing ASTRA_BIN/GENERATOR_BIN overrides are respected. Logs are retained in
<root>/logs in both verbose and quiet modes. Resume preserves saved batch sizes,
workers, configuration, seed, device topology and pending proposals; --iterations
sets the total target. Other new-run options do not override checkpoint settings.
EOF
}
fail() { printf 'Error: %s\n' "$*" >&2; exit 1; }
need_value() { [[ $# -ge 2 && -n "$2" ]] || fail "Missing value for $1"; }
while (($#)); do
  case "$1" in
    -q|--quiet) QUIET=1; shift ;;
    -r|--resume) RESUME=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    --reference) [[ $# -ge 4 ]] || fail 'Need three reference values'; REFERENCE=("$2" "$3" "$4"); shift 4 ;;
    --config|-o|--output-dir|-i|--iterations|-b|--batch-size|--initial-samples|-w|--workers|--seed|-d|--device|--p1-case|--perturbations)
      need_value "$@"
      case "$1" in
        --config) CONFIG="$2" ;;
        -o|--output-dir) OUTPUT_BASE_DIR="$2" ;;
        -i|--iterations) N_ITERATIONS="$2" ;;
        -b|--batch-size) BATCH_SIZE="$2" ;;
        --initial-samples) NUM_INITIAL_SAMPLES="$2" ;;
        -w|--workers) NUM_WORKERS="$2" ;;
        --seed) SEED="$2" ;;
        -d|--device) DEVICE="$2" ;;
        --p1-case) P1_CASE="$2" ;;
        --perturbations) NUM_PERTURBATIONS="$2" ;;
      esac
      shift 2 ;;
    *) fail "Unknown option: $1" ;;
  esac
done
[[ -n "$OUTPUT_BASE_DIR" ]] || fail 'Output directory must not be empty'
for value in "$BATCH_SIZE" "$NUM_INITIAL_SAMPLES" "$NUM_WORKERS" "$NUM_PERTURBATIONS"; do
  [[ "$value" =~ ^[1-9][0-9]*$ ]] || fail 'Batch size, initial samples, workers and perturbations must be positive integers'
done
[[ "$N_ITERATIONS" =~ ^(0|[1-9][0-9]*)$ && "$SEED" =~ ^(0|[1-9][0-9]*)$ ]] || fail 'Iterations and seed must be nonnegative integers'
CASES=(balanced high_brightness low_energy_spread x_dominant y_dominant)
if [[ "$P1_CASE" != all ]]; then
  case "$P1_CASE" in balanced|high_brightness|low_energy_spread|x_dominant|y_dominant) CASES=("$P1_CASE") ;; *) fail "Unknown Phase 1 case: $P1_CASE" ;; esac
fi

P1_DIR="$OUTPUT_BASE_DIR/phase1_scalarized"
P2_DIR="$OUTPUT_BASE_DIR/phase2_unconstrained"
P3_DIR="$OUTPUT_BASE_DIR/phase3_constrained"
ANALYSIS_DIR="$OUTPUT_BASE_DIR/analysis"
LOG_DIR="$OUTPUT_BASE_DIR/logs"
if ((RESUME)); then
  CONFIG="$P3_DIR/config.yaml"
fi
# Validate scientific settings and reference before creating output directories.
"$PYTHON_BIN" - "$CONFIG" "$N_ITERATIONS" "$BATCH_SIZE" "$NUM_INITIAL_SAMPLES" "$NUM_WORKERS" "$SEED" "${REFERENCE[@]}" <<'PY'
import sys
import torch
from mobo_linac.config import load_config, validate_campaign_options
config = load_config(sys.argv[1])
iterations, batch, initial, workers, seed = map(int, sys.argv[2:7])
validate_campaign_options(num_initial_samples=initial, num_batches=iterations,
                          batch_size=batch, num_workers=workers, seed=seed)
ref = torch.tensor([float(v) for v in sys.argv[7:]], dtype=torch.double)
if len(config.objectives) != 3 or len(ref) != 3 or not torch.isfinite(ref).all():
    raise ValueError('This three-phase Option 2 pipeline requires three objectives and a finite reference')
PY

CLI=("$PYTHON_BIN" -m mobo_linac.cli)
COMMON=(--config "$CONFIG" --n-iterations "$N_ITERATIONS" --batch-size "$BATCH_SIZE"
        --num-initial-samples "$NUM_INITIAL_SAMPLES" --num-workers "$NUM_WORKERS"
        --device "$DEVICE" --seed "$SEED" --reporting-ref-point "${REFERENCE[@]}")
if ((QUIET)); then COMMON+=(--quiet); fi

if ((RESUME)); then
  for run in "${CASES[@]/#/$P1_DIR/}" "$P2_DIR" "$P3_DIR"; do
    [[ -f "$run/checkpoints/checkpoint.pt" || -f "$run/checkpoints/pending_batch.pt" ]] || fail "No checkpoint for $run"
  done
elif [[ -e "$OUTPUT_BASE_DIR" ]]; then
  fail 'Output root already exists; select a fresh root or use --resume'
fi
if ((!DRY_RUN)); then
  if ((!RESUME)); then
    ASTRA_BIN="${ASTRA_BIN:-$PROJECT_ROOT/bin/astra}"
    GENERATOR_BIN="${GENERATOR_BIN:-$PROJECT_ROOT/bin/generator}"
    [[ -x "$ASTRA_BIN" && -x "$GENERATOR_BIN" ]] || fail 'ASTRA_BIN and GENERATOR_BIN must be executable files'
    export ASTRA_BIN GENERATOR_BIN
  fi
  mkdir -p "$LOG_DIR"
fi

execute_step() {
  local name="$1"; shift
  printf '\n%s\n' "$name"
  if ((DRY_RUN)); then
    printf '  '; printf '%q ' "$@"; printf '\n'
  elif ((QUIET)); then
    if ! "$@" >"$LOG_DIR/$name.log" 2>&1; then
      tail -n 25 "$LOG_DIR/$name.log" >&2
      fail "Step $name failed; see $LOG_DIR/$name.log"
    fi
  else
    "$@" 2>&1 | tee "$LOG_DIR/$name.log"
  fi
}

if ((RESUME)); then
  for case_name in "${CASES[@]}"; do
    execute_step "phase1_$case_name" "${CLI[@]}" resume --run-dir "$P1_DIR/$case_name" --n-iterations "$N_ITERATIONS"
  done
  execute_step phase1_aggregate "$PYTHON_BIN" -c 'import sys; from mobo_linac.campaigns.scalarized_suite import aggregate_scalarized_cases, export_phase1_cases_latex_table; from pathlib import Path; root=Path(sys.argv[1]); aggregate_scalarized_cases(root); export_phase1_cases_latex_table(root/"cases_summary.csv",root/"phase1_cases_table.tex")' "$P1_DIR"
  execute_step phase2 "${CLI[@]}" resume --run-dir "$P2_DIR" --n-iterations "$N_ITERATIONS"
  execute_step phase3 "${CLI[@]}" resume --run-dir "$P3_DIR" --n-iterations "$N_ITERATIONS"
else
  execute_step phase1 "${CLI[@]}" run-scalarized --suite option2 --case "$P1_CASE" "${COMMON[@]}" --output-dir "$P1_DIR"
  execute_step phase2 "${CLI[@]}" run-unconstrained "${COMMON[@]}" --output-dir "$P2_DIR"
  execute_step phase3 "${CLI[@]}" run-constrained "${COMMON[@]}" --output-dir "$P3_DIR"
fi
execute_step comparison "$PYTHON_BIN" scripts/run_comparison_and_verification.py \
  --config "$CONFIG" --phase1-dir "$P1_DIR" --phase2-dir "$P2_DIR" --phase3-dir "$P3_DIR" \
  --num-workers "$NUM_WORKERS" --output-dir "$ANALYSIS_DIR"
execute_step robustness "$PYTHON_BIN" scripts/run_robustness_analysis.py \
  --config "$CONFIG" --pareto-csv "$P3_DIR/pareto_feasible.csv" \
  --num-workers "$NUM_WORKERS" --num-perturbations "$NUM_PERTURBATIONS" --seed "$SEED" \
  --output-dir "$ANALYSIS_DIR/robustness"
if ((DRY_RUN)); then
  printf '\nCommand preview complete.\n'
else
  printf '\nPipeline complete. Review verification statuses and applied robustness channels in %s.\n' "$ANALYSIS_DIR"
fi
