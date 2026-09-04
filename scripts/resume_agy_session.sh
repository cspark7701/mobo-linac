#!/usr/bin/env bash
# ==============================================================================
# resume_agy_session.sh - Resume Antigravity (agy) Session for mobo-linac
# ==============================================================================
# Finds the most recent Antigravity conversation associated with this repository
# and resumes it using `agy --conversation <conversation_id>` (or `agy --continue`).
# Supports passing additional flags/options directly to agy.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

BRAIN_DIR="${HOME}/.gemini/antigravity-cli/brain"

# Function to find the most recent conversation ID belonging to this repository
find_latest_repo_conversation() {
    python3 - <<PY
import os
import sys

brain_dir = os.path.expanduser("${BRAIN_DIR}")
repo_path = "${PROJECT_ROOT}"

if not os.path.isdir(brain_dir):
    sys.exit(1)

candidates = []
for cid in os.listdir(brain_dir):
    transcript = os.path.join(brain_dir, cid, ".system_generated", "logs", "transcript.jsonl")
    if os.path.isfile(transcript):
        try:
            mtime = os.path.getmtime(transcript)
            with open(transcript, "r", encoding="utf-8", errors="ignore") as f:
                # Read initial segment of transcript to detect repository association
                header = f.read(65536)
                if repo_path in header:
                    candidates.append((mtime, cid))
        except Exception:
            continue

candidates.sort(reverse=True)
if candidates:
    print(candidates[0][1])
    sys.exit(0)
sys.exit(1)
PY
}

echo "======================================================================"
echo " Antigravity (agy) Session Resumer for mobo-linac"
echo " Project root: ${PROJECT_ROOT}"
echo "======================================================================"

CONVO_ID=""
if CONVO_ID=$(find_latest_repo_conversation 2>/dev/null); then
    echo "Found latest repo conversation ID: ${CONVO_ID}"
    echo "Launching: agy --conversation ${CONVO_ID} $@"
    echo "======================================================================"
    exec agy --conversation "${CONVO_ID}" "$@"
else
    echo "Notice: No prior repository-specific conversation ID found in ${BRAIN_DIR}."
    echo "Falling back to: agy --continue $@"
    echo "======================================================================"
    exec agy --continue "$@"
fi
