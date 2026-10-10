#!/usr/bin/env bash
# Step 6 - Independent candidate audit of the primary experiment (plan Stage 4). About 7 h.
#   The run is predeclared (constrained_qlognehvi, seed 42) so the audit is not chosen after
#   seeing results. Six representatives (one per objective minimum, knee, balanced, max crowding):
#   independent nominal ASTRA reruns (verification), then 50 lattice-jitter perturbations each
#   (robustness, 300 evaluations). Charge and laser channels are unsupported for the fixed
#   pal_photo2.ini source; report the scores as lattice-jitter robustness.
# Outputs: results/paper_production/06_candidate_audit/
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

AUDIT_ALGORITHM=constrained_qlognehvi
AUDIT_SEED=42
PERTURBATIONS="${AUDIT_PERTURBATIONS:-50}"
ROBUSTNESS_SEED=42
[[ "${1:-}" == -h || "${1:-}" == --help ]] && { usage; exit 0; }

require_step 04_primary
start_step 06_candidate_audit
refuse_if_done
require_clean_tree
RUN_DIR="$OUT_ROOT/04_primary/benchmark/per_seed/${AUDIT_ALGORITHM}_seed_${AUDIT_SEED}"
[[ -f "$RUN_DIR/run_complete.json" ]] || fail "Audited run is not complete: $RUN_DIR"
[[ -s "$RUN_DIR/pareto_feasible.csv" ]] || fail "No feasible Pareto set in $RUN_DIR"
for target in verification robustness; do
  [[ ! -e "$STEP_DIR/$target" ]] || fail "$STEP_DIR/$target exists from an earlier attempt; move it aside to repeat the audit."
done

write_record step=06_candidate_audit run_dir="$RUN_DIR" perturbations=$PERTURBATIONS \
  robustness_seed=$ROBUSTNESS_SEED workers=$WORKERS

section "Verification: independent nominal reruns"
cli run-verification --config "$RUN_DIR/config.yaml" --input "$RUN_DIR" \
  --num-workers "$WORKERS" --output-dir "$STEP_DIR/verification" "${EVALUATOR_FLAGS[@]}"
section "Robustness: applied lattice jitter"
cli run-robustness --config "$RUN_DIR/config.yaml" --input "$RUN_DIR/pareto_feasible.csv" \
  --num-workers "$WORKERS" --num-perturbations "$PERTURBATIONS" --seed "$ROBUSTNESS_SEED" \
  --output-dir "$STEP_DIR/robustness" "${EVALUATOR_FLAGS[@]}"

section "Summary"
summarize "$STEP_DIR" --output "$STEP_DIR/audit_summary.json" || true

finish_step 07_paper_outputs.sh
printf 'Review each VERIFIED / failed status and its hashes in %s/verification.\n' "$STEP_DIR"
