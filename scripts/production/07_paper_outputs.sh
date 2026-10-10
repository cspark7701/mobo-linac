#!/usr/bin/env bash
# Step 7 - Manuscript figures, tables and campaign inventory. Minutes; no simulation is rerun.
#   Figures and LaTeX tables from the Step 5 phases and their verification CSV, the manuscript
#   consistency check, and an inventory of every stage (runs, completion checksums, records).
#   The primary comparison tables are in 04_primary/benchmark/{tables,figures}.
#   Outputs are staged for review; docs/paper/ is not modified.
# Outputs: results/paper_production/07_paper_outputs/
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
write_record step=07_paper_outputs

section "Figures and tables"
mkdir -p "$STEP_DIR/figures" "$STEP_DIR/tables"
cli paper-figures "${PAPER_ARGS[@]}"
section "Manuscript consistency check"
cli paper-figures "${PAPER_ARGS[@]}" --check-only
section "Campaign inventory"
"$PYTHON_BIN" "$PRODUCTION_DIR/production_tools.py" inventory "$OUT_ROOT" \
  --output "$STEP_DIR/campaign_inventory.json"

finish_step
cat <<EOF
Staged for review in $STEP_DIR (figures/, tables/, campaign_inventory.json).
To promote them into the manuscript after review:
  scripts/reproduce_paper.sh --phase1-dir $CAMPAIGN/phase1_scalarized \\
    --phase2-dir $CAMPAIGN/phase2_unconstrained --phase3-dir $CAMPAIGN/phase3_constrained \\
    --verification-csv $CAMPAIGN/analysis/verification/verification_summary.csv
EOF
