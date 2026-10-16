#!/usr/bin/env bash
# Step 7 - Manuscript figures, tables and campaign inventory. Minutes; no simulation is rerun.
#   Figures and LaTeX tables from the Step 5 phases and their verification CSV, the manuscript
#   consistency check, and an inventory of every stage (runs, completion checksums, records).
#   Also stages the primary comparison figures and summary, and the audit tables of Step 6.
#   Outputs are staged for review; docs/paper/ is not modified.
# Outputs: results/paper_production/07_paper_outputs/
# This reporting-only stage does not fit models or run acquisition optimization.
DEVICE="${DEVICE:-cuda:0}"
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
[[ "${1:-}" == -h || "${1:-}" == --help ]] && { usage; exit 0; }

require_step 04_primary 05_operating_points 06_candidate_audit
start_step 07_paper_outputs
refuse_if_done
CAMPAIGN="$OUT_ROOT/05_operating_points/campaign"
for target in figures tables; do
  [[ ! -e "$STEP_DIR/$target" ]] || fail "$STEP_DIR/$target exists from an earlier attempt; move it aside to regenerate."
done
PAPER_ARGS=(--phase1-dir "$CAMPAIGN/phase1_scalarized" --phase2-dir "$CAMPAIGN/phase2_unconstrained"
            --phase3-dir "$CAMPAIGN/phase3_constrained"
            --verification-csv "$CAMPAIGN/analysis/verification/verification_summary.csv"
            --output-dir "$STEP_DIR/figures" --tables-dir "$STEP_DIR/tables")
write_record step=07_paper_outputs device=$DEVICE optimization=none

section "Figures and tables"
mkdir -p "$STEP_DIR/figures" "$STEP_DIR/tables"
cli paper-figures "${PAPER_ARGS[@]}"
section "Manuscript consistency check"
cli paper-figures "${PAPER_ARGS[@]}" --check-only
section "Primary comparison and audit inputs of the manuscript"
for figure in benchmark_hv_comparison.pdf benchmark_feasibility_comparison.pdf; do
  run cp "$OUT_ROOT/04_primary/benchmark/figures/$figure" "$STEP_DIR/figures/"
done
run cp "$OUT_ROOT/04_primary/benchmark/tables/benchmark_summary_table.csv" "$STEP_DIR/tables/"
run cp "$OUT_ROOT/06_candidate_audit/robustness/robustness_table.tex" "$STEP_DIR/tables/"
# The audit and survey verification tables share a generator; give the audit table its own label.
sed -e 's/\\label{tab:pareto_verification}/\\label{tab:audit_verification}/' \
    -e 's/\\caption{Independent Verification Results of Representative Pareto Candidates}/\\caption{Independent reruns of the representatives of the primary audit run (constraint-aware qLogNEHVI, seed 42).}/' \
    "$OUT_ROOT/06_candidate_audit/verification/verification_table.tex" > "$STEP_DIR/tables/audit_verification_table.tex"
grep -q 'tab:audit_verification' "$STEP_DIR/tables/audit_verification_table.tex" || fail "Could not relabel the audit verification table"
section "Campaign inventory"
"$PYTHON_BIN" "$PRODUCTION_DIR/production_tools.py" inventory "$OUT_ROOT" \
  --output "$STEP_DIR/campaign_inventory.json"

finish_step
cat <<EOF
Staged for review in $STEP_DIR (figures/, tables/, campaign_inventory.json).
To promote them into the manuscript (docs/paper/main.tex) after review:
  scripts/reproduce_paper.sh --phase1-dir $CAMPAIGN/phase1_scalarized \\
    --phase2-dir $CAMPAIGN/phase2_unconstrained --phase3-dir $CAMPAIGN/phase3_constrained \\
    --verification-csv $CAMPAIGN/analysis/verification/verification_summary.csv
  cp $STEP_DIR/figures/benchmark_*.pdf docs/paper/figures/
  cp $STEP_DIR/tables/{audit_verification_table,robustness_table}.tex docs/paper/
The primary comparison numbers come from $STEP_DIR/tables/benchmark_summary_table.csv.
EOF
