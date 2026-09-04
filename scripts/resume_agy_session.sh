#!/usr/bin/env bash
# ==============================================================================
# resume_agy_session.sh — Resume / Continue Antigravity (agy) Session for mobo-linac
# Multi-Objective Bayesian Optimization for 200 MeV Electron Injector Linac
#
# Usage:
#   ./scripts/resume_agy_session.sh [OPTIONS] [EXTRA_AGY_ARGS...]
#
# Options:
#   -c, --current     Resume the specific session active during script creation:
#                     (0f80aacb-6645-433f-8dba-7023ef5fcd12)
#   -l, --latest      Find and resume the most recent conversation matching this repo.
#   -i, --id ID       Resume a specific conversation ID.
#   --list            List available conversations matching this repository.
#   -h, --help        Show this help message.
# ==============================================================================

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

BRAIN_DIR="${HOME}/.gemini/antigravity-cli/brain"
DEFAULT_CONV_ID="0f80aacb-6645-433f-8dba-7023ef5fcd12"
TARGET_ID=""
MODE="auto"
EXTRA_ARGS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        -c|--current)
            TARGET_ID="${DEFAULT_CONV_ID}"
            MODE="specific"
            shift
            ;;
        -l|--latest)
            MODE="latest"
            shift
            ;;
        -i|--id)
            TARGET_ID="$2"
            MODE="specific"
            shift 2
            ;;
        --list)
            MODE="list"
            shift
            ;;
        -h|--help)
            cat << 'HLP'
Usage: ./scripts/resume_agy_session.sh [OPTIONS] [EXTRA_AGY_ARGS...]

Resumes an Antigravity (agy) CLI session for the mobo-linac repository.
Ensures you return directly to this workspace and conversation state after
quitting (/quit, /exit, or Ctrl+D Ctrl+D).

Options:
  -c, --current    Resume the pinned conversation ID associated with this milestone:
                   (0f80aacb-6645-433f-8dba-7023ef5fcd12)
  -l, --latest     Automatically find and resume the most recently active session
                   for this repository.
  -i, --id <ID>    Resume a specific conversation by ID.
  --list           List all conversation sessions associated with this repo.
  -h, --help       Show this help message.

Default behavior (no flags):
  Resumes the latest session associated with this repository; falls back to
  pinned session ID or standard `agy --continue`.
HLP
            exit 0
            ;;
        *)
            EXTRA_ARGS+=("$1")
            shift
            ;;
    esac
done

if ! command -v agy &>/dev/null; then
    echo "[ERROR] 'agy' command not found in PATH." >&2
    echo "Please ensure the Antigravity CLI is installed and in your environment." >&2
    exit 1
fi

find_repo_sessions() {
    python3 -c "
import os
from pathlib import Path

repo_path = '${REPO_ROOT}'
brain_dir = Path('${BRAIN_DIR}')
matched = []

if brain_dir.is_dir():
    for transcript in brain_dir.glob('*/.system_generated/logs/transcript.jsonl'):
        conv_id = transcript.parts[-4]
        mtime = transcript.stat().st_mtime
        try:
            with open(transcript, 'r', errors='ignore') as f:
                content = f.read(65536)
                if repo_path in content or 'mobo-linac' in content:
                    matched.append((mtime, conv_id))
        except Exception:
            pass

matched.sort(key=lambda x: x[0], reverse=True)
for mtime, cid in matched:
    print(f'{cid}')
"
}

if [ "${MODE}" = "list" ]; then
    echo "=== Antigravity Sessions for ${REPO_ROOT} ==="
    mapfile -t SESSIONS < <(find_repo_sessions)
    if [ ${#SESSIONS[@]} -eq 0 ]; then
        echo "No sessions found."
    else
        for sid in "${SESSIONS[@]}"; do
            pin=""
            if [ "${sid}" = "${DEFAULT_CONV_ID}" ]; then
                pin=" [current / pinned]"
            fi
            echo "  - ${sid}${pin}"
        done
    fi
    exit 0
fi

if [ "${MODE}" = "auto" ] || [ "${MODE}" = "latest" ]; then
    mapfile -t SESSIONS < <(find_repo_sessions)
    if [ ${#SESSIONS[@]} -gt 0 ]; then
        TARGET_ID="${SESSIONS[0]}"
    else
        TARGET_ID="${DEFAULT_CONV_ID}"
    fi
fi

if [ -n "${TARGET_ID}" ]; then
    echo "======================================================================"
    echo " Resuming Antigravity Session for mobo-linac                         "
    echo "======================================================================"
    echo " Conversation ID : ${TARGET_ID}"
    echo " Working Directory: ${REPO_ROOT}"
    echo " Command         : agy --conversation ${TARGET_ID} ${EXTRA_ARGS[*]:-}"
    echo "======================================================================"
    exec agy --conversation "${TARGET_ID}" "${EXTRA_ARGS[@]:-}"
else
    echo "======================================================================"
    echo " Continuing Most Recent Antigravity Session                          "
    echo "======================================================================"
    exec agy --continue "${EXTRA_ARGS[@]:-}"
fi
