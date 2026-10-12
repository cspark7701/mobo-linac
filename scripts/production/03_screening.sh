#!/usr/bin/env bash
# Step 3 - Paired screening (plan Stage 2). About 8 h at ~300 s per ASTRA run.
#   constrained_qlognehvi, unconstrained_qlognehvi and scalarized_bo; seeds 42, 43, 44;
#   budget 40 evaluations per algorithm-seed pair (8 Sobol + 8 batches of 4) = 360 evaluations.
#   Failed evaluations count against the fixed budget. Screening is never pooled into Step 4.
# Exit gate (automatic): every run complete with valid and feasible evaluations. Then check
#   that failure causes and GP fit/fallback outcomes are understood.
# Outputs: results/paper_production/03_screening/
# Interrupted? Run ./03_screening.sh again: completed runs are kept and skipped.
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

SEEDS=(42 43 44)
BUDGET="${SCREENING_BUDGET:-40}"
N_SOBOL_INIT="${SCREENING_N_SOBOL_INIT:-8}"
BATCH_SIZE="${SCREENING_BATCH_SIZE:-4}"
[[ "${1:-}" == -h || "${1:-}" == --help ]] && { usage; exit 0; }

require_step 02_pilot
start_step 03_screening
refuse_if_done
require_clean_tree
BENCHMARK="$STEP_DIR/benchmark"

section "Forecast"
"$PYTHON_BIN" "$PRODUCTION_DIR/production_tools.py" forecast \
  --pilot-summary "$OUT_ROOT/02_pilot/pilot_summary.json" --runs $(( ${#SEEDS[@]} * ${#ALGORITHMS[@]} )) \
  --initial "$N_SOBOL_INIT" --iterations $(( (BUDGET - N_SOBOL_INIT) / BATCH_SIZE )) --batch "$BATCH_SIZE" \
  --workers "$WORKERS" --concurrent-campaigns "$MAX_CONCURRENT_CAMPAIGNS" --disk-output "$STEP_DIR/.disk_gb"
require_free_disk "$(cat "$STEP_DIR/.disk_gb")"

write_record step=03_screening algorithms="${ALGORITHMS[*]}" seeds="${SEEDS[*]}" budget=$BUDGET \
  n_sobol_init=$N_SOBOL_INIT batch_size=$BATCH_SIZE workers=$WORKERS device=$DEVICE \
  max_concurrent_campaigns=$MAX_CONCURRENT_CAMPAIGNS campaign_threads=$CAMPAIGN_THREADS

BENCH_ARGS=(--config "$CONFIG" --algorithms "${ALGORITHMS[@]}" --seeds "${SEEDS[@]}" --budget "$BUDGET"
            --n-sobol-init "$N_SOBOL_INIT" --batch-size "$BATCH_SIZE" --num-workers "$WORKERS"
            --max-concurrent-campaigns "$MAX_CONCURRENT_CAMPAIGNS" --total-workers "$WORKERS"
            --campaign-threads "$CAMPAIGN_THREADS"
            --device "$DEVICE" --output-dir "$BENCHMARK" "${EVALUATOR_FLAGS[@]}")
section "Plan"
cli run-benchmark "${BENCH_ARGS[@]}" --dry-run
section "Screening benchmark"
cli run-benchmark "${BENCH_ARGS[@]}"
section "Analysis"
cli analyze-benchmark --output-dir "$BENCHMARK"
summarize "$BENCHMARK" --gate feasible --output "$STEP_DIR/screening_summary.json"

finish_step 04_primary.sh
cat <<'EOF'
Before continuing, check in results/paper_production/03_screening/:
  - screening_summary.json: failure categories per run
  - benchmark/aggregate_metrics.csv and benchmark/tables/benchmark_summary_table.csv
  - benchmark/per_seed/*/proposal_history.json: Sobol fallbacks and GP fit outcomes
EOF
