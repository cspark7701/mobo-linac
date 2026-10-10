#!/usr/bin/env bash
# Step 2 - Physical pilot (plan Stage 1). About 2-3 h at ~300 s per ASTRA run.
#   Balanced scalarized, unconstrained and constrained MOBO, seed 42:
#   8 initial samples + 2 batches of 4 = 16 evaluations per run (48 in total),
#   then nominal reruns (verification) and 10 lattice-jitter perturbations per representative.
#   Measures ASTRA runtime and disk use per evaluation; later steps forecast from them.
# Exit gate (automatic): every run complete, valid ASTRA evaluations, at least one feasible
#   candidate, audit rows produced. Then review failures and verification statuses yourself.
# Outputs: results/paper_production/02_pilot/
# Interrupted? Run ./02_pilot.sh --resume
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

SEED=42
P1_CASE=balanced
INITIAL_SAMPLES="${PILOT_INITIAL_SAMPLES:-8}"
ITERATIONS="${PILOT_ITERATIONS:-2}"
BATCH_SIZE="${PILOT_BATCH_SIZE:-4}"
PERTURBATIONS="${PILOT_PERTURBATIONS:-10}"

RESUME=0
case "${1:-}" in
  --resume) RESUME=1 ;;
  "") ;;
  -h|--help) usage; exit 0 ;;
  *) fail "Unknown option: $1 (use --resume)" ;;
esac

require_step 01_preflight
start_step 02_pilot
refuse_if_done
require_clean_tree
CAMPAIGN="$STEP_DIR/campaign"
if [[ -e "$CAMPAIGN" && "$RESUME" == 0 ]]; then
  fail "$CAMPAIGN exists from an earlier attempt. Continue it with ./02_pilot.sh --resume"
fi

write_record step=02_pilot seed=$SEED p1_case=$P1_CASE initial_samples=$INITIAL_SAMPLES \
  iterations=$ITERATIONS batch_size=$BATCH_SIZE workers=$WORKERS perturbations=$PERTURBATIONS \
  device=$DEVICE resume=$RESUME

section "Pilot campaign"
LAUNCH=(bash scripts/run_full_production.sh --quiet --p1-case "$P1_CASE" --iterations "$ITERATIONS"
        --workers "$WORKERS" --perturbations "$PERTURBATIONS" --output-dir "$CAMPAIGN"
        "${EVALUATOR_FLAGS[@]}")
if ((RESUME)); then
  run "${LAUNCH[@]}" --resume
else
  run "${LAUNCH[@]}" --seed "$SEED" --device "$DEVICE" --initial-samples "$INITIAL_SAMPLES" \
    --batch-size "$BATCH_SIZE"
fi

section "Pilot summary and exit gate"
summarize "$CAMPAIGN" --gate audited --output "$STEP_DIR/pilot_summary.json"

finish_step 03_screening.sh
cat <<'EOF'
Before continuing, check in results/paper_production/02_pilot/:
  - pilot_summary.json: failure categories, runtime median/p95, MB per evaluation
  - campaign/analysis/verification/verification_summary.csv: VERIFIED statuses
  - campaign/analysis/robustness/: applied lattice-jitter channels
EOF
