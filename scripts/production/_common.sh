# Shared settings and helpers for the step-by-step paper production scripts.
# Sourced by NN_*.sh; not executable on its own.
set -Eeuo pipefail

PRODUCTION_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${PRODUCTION_DIR}/../.." && pwd)"
cd "$PROJECT_ROOT"

# ---------------------------------------------------------------------------
# Protocol shared by every step (docs/strategic_simulation_campaign_plan.md).
# Variables written as ${NAME:-default} may be overridden from the environment
# for rehearsals only; each step records the values it actually used.
# ---------------------------------------------------------------------------
PYTHON_BIN="${PYTHON_BIN:-python3}"
export PYTHON_BIN
OUT_ROOT="${PRODUCTION_ROOT:-results/paper_production}"
CONFIG="configs/publication_200MeV.yaml"
DEVICE="${DEVICE:-cpu}"              # CPU is the reproducibility baseline
WORKERS="${WORKERS:-4}"              # parallel ASTRA processes
ALGORITHMS=(constrained_qlognehvi unconstrained_qlognehvi scalarized_bo)
# Mock evaluator: rehearsal of the scripts themselves, never physical evidence.
MOCK="${MOCK_EVALUATOR:-0}"
DEFAULT_OUT_ROOT="results/paper_production"

LOG_DIR="$OUT_ROOT/logs"
STATUS_DIR="$OUT_ROOT/status"
EVALUATOR_FLAGS=()
if [[ "$MOCK" == 1 ]]; then
  EVALUATOR_FLAGS=(--mock-evaluator)
fi

# usage: print the script's header comment (everything before the source line).
usage() { sed -n '2,/^source /p' "$0" | sed -n 's/^# \{0,1\}//p'; }
fail() { printf '\nERROR: %s\n' "$*" >&2; exit 1; }
section() { printf '\n==== %s ====\n' "$*"; }
run() { printf '+'; printf ' %q' "$@"; printf '\n'; "$@"; }
cli() { run "$PYTHON_BIN" -m mobo_linac.cli "$@"; }

# start_step NAME: open the step log (printed and saved) and the step output directory.
start_step() {
  STEP="$1"
  STEP_DIR="$OUT_ROOT/$STEP"
  if [[ "$MOCK" == 1 && "$OUT_ROOT" == "$DEFAULT_OUT_ROOT" ]]; then
    fail "MOCK_EVALUATOR=1 needs PRODUCTION_ROOT set to a rehearsal directory, not $DEFAULT_OUT_ROOT"
  fi
  mkdir -p "$LOG_DIR" "$STATUS_DIR" "$STEP_DIR"
  STEP_LOG="$LOG_DIR/${STEP}_$(date +%Y%m%d_%H%M%S).log"
  exec > >(tee -a "$STEP_LOG") 2>&1
  trap 'printf "\nFAILED: %s (line %s). Log: %s\n" "$STEP" "$LINENO" "$STEP_LOG"; date > "$STATUS_DIR/$STEP.failed"' ERR
  section "$STEP  $(date '+%Y-%m-%d %H:%M:%S')"
  printf 'Project:   %s\nOutputs:   %s\nLog:       %s\n' "$PROJECT_ROOT" "$STEP_DIR" "$STEP_LOG"
  printf 'Python:    %s\nCommit:    %s%s\n' "$(command -v "$PYTHON_BIN")" \
    "$(git rev-parse --short HEAD)" "$(git_dirty && echo ' (uncommitted changes)' || true)"
  if [[ "$MOCK" == 1 ]]; then printf 'Evaluator: MOCK (rehearsal only, not physics)\n'; fi
  check_python
}

# finish_step: mark the step complete and point to the next one.
finish_step() {
  local next="${1:-}"
  date '+%Y-%m-%d %H:%M:%S' > "$STATUS_DIR/$STEP.done"
  rm -f "$STATUS_DIR/$STEP.failed"
  section "$STEP complete"
  if [[ -n "$next" ]]; then printf 'Review the outputs above, then run: scripts/production/%s\n' "$next"; fi
}

step_done() { [[ -f "$STATUS_DIR/$1.done" ]]; }
require_step() {
  local step
  for step in "$@"; do
    step_done "$step" || fail "Step $step has not completed. Run scripts/production/$step.sh first."
  done
}
refuse_if_done() {
  if step_done "$STEP"; then
    fail "$STEP already completed ($(cat "$STATUS_DIR/$STEP.done")). Outputs are immutable; use a new PRODUCTION_ROOT to repeat it."
  fi
}

git_dirty() { [[ -n "$(git status --porcelain --untracked-files=no)" ]]; }
# Physical stages start only from a committed tree so the recorded commit describes the code.
require_clean_tree() {
  if [[ "$MOCK" != 1 ]] && git_dirty; then
    if [[ "${ALLOW_DIRTY:-0}" == 1 ]]; then
      printf 'WARNING: uncommitted changes (ALLOW_DIRTY=1); the record marks this run dirty.\n'
    else
      git status --short --untracked-files=no
      fail "Commit or stash tracked changes before a physical stage (or set ALLOW_DIRTY=1)."
    fi
  fi
}

check_python() {
  local location
  location="$("$PYTHON_BIN" -c 'import mobo_linac, pathlib; print(pathlib.Path(mobo_linac.__file__).resolve())' 2>/dev/null)" \
    || fail "$PYTHON_BIN cannot import mobo_linac. Activate the linac environment or set PYTHON_BIN."
  [[ "$location" == "$PROJECT_ROOT/src/"* ]] \
    || fail "mobo_linac resolves to $location, not this checkout ($PROJECT_ROOT/src). Reinstall with pip install -e ."
}

# require_free_disk GB: refuse to start when the output file system has less free space.
require_free_disk() {
  local need_gb="$1" free_gb
  free_gb=$(df -Pk "$OUT_ROOT" | awk 'NR==2 {printf "%d", $4 / 1048576}')
  printf 'Free disk: %s GB (need about %s GB)\n' "$free_gb" "$need_gb"
  if (( free_gb < need_gb )); then
    [[ "${ALLOW_LOW_DISK:-0}" == 1 ]] || fail "Not enough free disk space (set ALLOW_LOW_DISK=1 to override)."
    printf 'WARNING: low disk space accepted (ALLOW_LOW_DISK=1).\n'
  fi
}

# write_record KEY=VALUE...: freeze commit, configuration, executable, inputs and parameters.
write_record() {
  "$PYTHON_BIN" "$PRODUCTION_DIR/production_tools.py" record --config "$CONFIG" --mock "$MOCK" \
    --output "$STEP_DIR/step_record_$(date +%Y%m%d_%H%M%S).json" -- "$@"
}

summarize() { "$PYTHON_BIN" "$PRODUCTION_DIR/production_tools.py" summarize "$@"; }
