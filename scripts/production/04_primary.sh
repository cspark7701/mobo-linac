#!/usr/bin/env bash
# Step 4 - Primary experiment (plan Stage 3). About 4-5 days at ~300 s per ASTRA run.
#   constrained_qlognehvi, unconstrained_qlognehvi and scalarized_bo; seeds 42-51 (all kept);
#   budget 160 evaluations per algorithm-seed pair (16 Sobol + 18 batches of 8) = 4,800 evaluations.
#   This is the paper's algorithm comparison; it starts from fresh runs, separate from screening.
# Exit gate (automatic): every run complete with valid and feasible evaluations.
# Outputs: results/paper_production/04_primary/
# Interrupted? Run ./04_primary.sh again: completed runs are kept and skipped. An incomplete
#   run is reported and preserved; investigate it rather than deleting it.
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

SEEDS=(42 43 44 45 46 47 48 49 50 51)
BUDGET="${PRIMARY_BUDGET:-160}"
N_SOBOL_INIT="${PRIMARY_N_SOBOL_INIT:-16}"
BATCH_SIZE="${PRIMARY_BATCH_SIZE:-8}"
[[ "${1:-}" == -h || "${1:-}" == --help ]] && { usage; exit 0; }

require_step 03_screening
start_step 04_primary
refuse_if_done
require_clean_tree
BENCHMARK="$STEP_DIR/benchmark"

section "Forecast"
"$PYTHON_BIN" "$PRODUCTION_DIR/production_tools.py" forecast \
  --pilot-summary "$OUT_ROOT/02_pilot/pilot_summary.json" --runs $(( ${#SEEDS[@]} * ${#ALGORITHMS[@]} )) \
  --initial "$N_SOBOL_INIT" --iterations $(( (BUDGET - N_SOBOL_INIT) / BATCH_SIZE )) --batch "$BATCH_SIZE" \
  --workers "$WORKERS" --concurrent-campaigns "$MAX_CONCURRENT_CAMPAIGNS" --disk-output "$STEP_DIR/.disk_gb"
require_free_disk "$(cat "$STEP_DIR/.disk_gb")"

write_record step=04_primary algorithms="${ALGORITHMS[*]}" seeds="${SEEDS[*]}" budget=$BUDGET \
  n_sobol_init=$N_SOBOL_INIT batch_size=$BATCH_SIZE workers=$WORKERS device=$DEVICE \
  max_concurrent_campaigns=$MAX_CONCURRENT_CAMPAIGNS campaign_threads=$CAMPAIGN_THREADS

BENCH_ARGS=(--config "$CONFIG" --algorithms "${ALGORITHMS[@]}" --seeds "${SEEDS[@]}" --budget "$BUDGET"
            --n-sobol-init "$N_SOBOL_INIT" --batch-size "$BATCH_SIZE" --num-workers "$WORKERS"
            --max-concurrent-campaigns "$MAX_CONCURRENT_CAMPAIGNS" --total-workers "$WORKERS"
            --campaign-threads "$CAMPAIGN_THREADS"
            --device "$DEVICE" --output-dir "$BENCHMARK" "${EVALUATOR_FLAGS[@]}")
section "Plan"
cli run-benchmark "${BENCH_ARGS[@]}" --dry-run
section "Primary benchmark"
cli run-benchmark "${BENCH_ARGS[@]}"
section "Analysis"
cli analyze-benchmark --output-dir "$BENCHMARK"
summarize "$BENCHMARK" --gate feasible --output "$STEP_DIR/primary_summary.json"

finish_step 05_operating_points.sh
cat <<'EOF'
Results in results/paper_production/04_primary/benchmark/:
  aggregate_metrics.csv, tables/benchmark_summary_table.csv, figures/, per_seed/<algorithm>_seed_<seed>/
Report every seed, including poor runs.
EOF
