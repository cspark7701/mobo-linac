#!/usr/bin/env bash
# Backward compatibility wrapper pointing to env_setup.sh
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/env_setup.sh"
