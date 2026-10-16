#!/usr/bin/env bash
# Step 5 - Operating-point survey and manuscript phases (full launcher defaults). GPU optimization.
#   Phase 1: the five configured scalarized weight cases; Phase 2: unconstrained qLogNEHVI;
#   Phase 3: constrained qLogNEHVI. Each: 16 initial samples + 20 batches of 8 = 176 evaluations
#   (1,232 in total), base seed 42. Then nominal reruns of the six Phase 3 representatives
#   (verification) and 50 lattice-jitter perturbations each (robustness).
#   Descriptive survey with unequal budgets (Phase 1 has five runs); the algorithm claim is Step 4.
# Outputs: results/paper_production/05_operating_points/   (inputs of Step 7)
# Interrupted? Run ./05_operating_points.sh --resume
DEVICE="${DEVICE:-cuda:0}"
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

SEED=42
INITIAL_SAMPLES="${SURVEY_INITIAL_SAMPLES:-16}"
ITERATIONS="${SURVEY_ITERATIONS:-20}"
BATCH_SIZE="${SURVEY_BATCH_SIZE:-8}"
PERTURBATIONS="${SURVEY_PERTURBATIONS:-50}"

RESUME=0
case "${1:-}" in
  --resume) RESUME=1 ;;
  "") ;;
  -h|--help) usage; exit 0 ;;
  *) fail "Unknown option: $1 (use --resume)" ;;
esac

require_step 04_primary
start_step 05_operating_points
refuse_if_done
require_clean_tree
require_optimization_device
CAMPAIGN="$STEP_DIR/campaign"
if [[ -e "$CAMPAIGN" && "$RESUME" == 0 ]]; then
  fail "$CAMPAIGN exists from an earlier attempt. Continue it with ./05_operating_points.sh --resume"
fi

N_CASES="$("$PYTHON_BIN" -c 'import sys; from mobo_linac.config import load_config; print(len(load_config(sys.argv[1]).scalarized_cases))' "$CONFIG")"
section "Forecast"
"$PYTHON_BIN" "$PRODUCTION_DIR/production_tools.py" forecast \
  --pilot-summary "$OUT_ROOT/02_pilot/pilot_summary.json" --runs $((N_CASES + 2)) \
  --initial "$INITIAL_SAMPLES" --iterations "$ITERATIONS" --batch "$BATCH_SIZE" --workers "$WORKERS" \
  --extra-evaluations $((6 + 6 * PERTURBATIONS)) --disk-output "$STEP_DIR/.disk_gb"
((RESUME)) || require_free_disk "$(cat "$STEP_DIR/.disk_gb")"

write_record step=05_operating_points seed=$SEED p1_case=all initial_samples=$INITIAL_SAMPLES \
  iterations=$ITERATIONS batch_size=$BATCH_SIZE workers=$WORKERS perturbations=$PERTURBATIONS \
  device=$DEVICE resume=$RESUME

section "Full launcher: Phase 1-3, verification and robustness"
LAUNCH=(bash scripts/run_full_production.sh --quiet --p1-case all --iterations "$ITERATIONS"
        --workers "$WORKERS" --perturbations "$PERTURBATIONS" --output-dir "$CAMPAIGN"
        "${EVALUATOR_FLAGS[@]}")
if ((RESUME)); then
  run "${LAUNCH[@]}" --resume
else
  run "${LAUNCH[@]}" --seed "$SEED" --device "$DEVICE" --initial-samples "$INITIAL_SAMPLES" \
    --batch-size "$BATCH_SIZE"
fi

section "Summary"
summarize "$CAMPAIGN" --gate audited --output "$STEP_DIR/operating_points_summary.json"

finish_step 06_candidate_audit.sh
