#!/usr/bin/env bash
# Step 1 - Preflight (plan Stage 0). No physical optimization; about 45 min with the tests.
#   1. Environment, git state, CPU and disk report; package versions saved.
#   2. validate-config on the publication configuration; ASTRA executable and input hashes.
#   3. Unit test suite (pytest -m "not integration"), skipped with --skip-tests.
#   4. One real ASTRA evaluation (integration test), skipped with --skip-astra.
#   5. Preview of the pilot launcher commands (dry run).
#   6. Mock rehearsal of the launcher, its resume path and the benchmark dispatcher.
# Outputs: results/paper_production/01_preflight/   Logs: results/paper_production/logs/
# Re-running is allowed; every run writes new timestamped outputs.
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

RUN_TESTS=1
RUN_ASTRA=1
while (($#)); do
  case "$1" in
    --skip-tests) RUN_TESTS=0 ;;
    --skip-astra) RUN_ASTRA=0 ;;
    -h|--help) usage; exit 0 ;;
    *) fail "Unknown option: $1 (use --skip-tests, --skip-astra)" ;;
  esac
  shift
done

start_step 01_preflight
STAMP="$(date +%Y%m%d_%H%M%S)"
REHEARSAL="$STEP_DIR/mock_rehearsal_$STAMP"

section "1. Environment"
printf 'Host: %s   CPUs: %s\n' "$(hostname)" "$(nproc)"
"$PYTHON_BIN" -m pip freeze > "$STEP_DIR/pip_freeze_$STAMP.txt" 2>/dev/null || true
printf 'Package list: %s\n' "$STEP_DIR/pip_freeze_$STAMP.txt"
require_free_disk 20
if git_dirty; then
  printf 'WARNING: tracked files have uncommitted changes. Physical steps (02+) require a clean tree:\n'
  git status --short --untracked-files=no
else
  printf 'Git tree: clean at %s\n' "$(git rev-parse HEAD)"
fi

section "2. Configuration, executable and inputs"
cli validate-config --config "$CONFIG"
write_record step=01_preflight
if [[ "$MOCK" != 1 ]]; then
  "$PYTHON_BIN" - "$CONFIG" <<'PY'
import sys
from mobo_linac.astra.runner import resolve_executable
from mobo_linac.config import load_config
print("ASTRA executable:", resolve_executable(load_config(sys.argv[1])))
PY
fi

section "3. Unit tests"
if ((RUN_TESTS)); then
  run "$PYTHON_BIN" -m pytest -m "not integration" -q -p no:cacheprovider
else
  printf 'Skipped (--skip-tests).\n'
fi

section "4. One real ASTRA evaluation"
if ((RUN_ASTRA)) && [[ "$MOCK" != 1 ]]; then
  run "$PYTHON_BIN" -m pytest -q -p no:cacheprovider -m integration \
    tests/test_astra_workdirs.py::test_real_astra_isolated_run
else
  printf 'Skipped.\n'
fi

section "5. Pilot command preview"
run bash scripts/run_full_production.sh --dry-run --p1-case balanced --device "$DEVICE" \
  --initial-samples 8 --iterations 2 --batch-size 4 --workers "$WORKERS" --perturbations 10 \
  --output-dir "$OUT_ROOT/02_pilot/campaign"

section "6. Mock rehearsal (pipeline mechanics only, not physics)"
run bash scripts/run_full_production.sh --mock-evaluator --quiet --device cpu --p1-case balanced \
  --initial-samples 4 --iterations 1 --batch-size 2 --workers 2 --perturbations 2 \
  --output-dir "$REHEARSAL/launcher"
run bash scripts/run_full_production.sh --mock-evaluator --resume --quiet --p1-case balanced \
  --iterations 2 --workers 2 --perturbations 2 --output-dir "$REHEARSAL/launcher"
cli run-benchmark --mock-evaluator --quiet --config "$CONFIG" --algorithms "${ALGORITHMS[@]}" \
  --seeds 42 --budget 6 --n-sobol-init 4 --batch-size 2 --device cpu --output-dir "$REHEARSAL/benchmark"
cli analyze-benchmark --quiet --output-dir "$REHEARSAL/benchmark"
summarize "$REHEARSAL" --output "$REHEARSAL/rehearsal_summary.json"

finish_step 02_pilot.sh
