#!/usr/bin/env bash
# ==============================================================================
# check_ci_prepush.sh - Pre-push GitHub Actions CI & Integrity Validator
# ==============================================================================
# Simulates and verifies all steps executed in .github/workflows/ci.yml locally
# prior to pushing to remote git repositories:
#   1. Binary permissions check (bin/*)
#   2. Package import and version smoke test
#   3. CLI entry point and argument parsing smoke test
#   4. Documentation & configuration sync audit (scripts/verify_docs_sync.py)
#   5. Pytest unit test suite without integration tests (pytest -v -m "not integration")
#   6. Optional: Full integration test suite (--with-integration)
# ==============================================================================

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

WITH_INTEGRATION=false
FAIL_FAST=false
VERBOSE=false

print_usage() {
    cat <<USG
Usage: ./scripts/check_ci_prepush.sh [OPTIONS]

Simulate local GitHub Actions CI steps before pushing commits to remote.

Options:
  -i, --with-integration  Include long-running integration tests (disabled by default in CI).
  -x, --fail-fast         Exit immediately on first test failure.
  -v, --verbose           Show verbose test details.
  -h, --help              Display this help message.
USG
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -i|--with-integration)
            WITH_INTEGRATION=true
            shift
            ;;
        -x|--fail-fast)
            FAIL_FAST=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        *)
            echo "Error: Unknown option: $1"
            print_usage
            exit 1
            ;;
    esac
done

COLOR_GREEN="\033[0;32m"
COLOR_RED="\033[0;31m"
COLOR_YELLOW="\033[0;33m"
COLOR_BLUE="\033[0;34m"
COLOR_RESET="\033[0m"

pass() {
    echo -e "${COLOR_GREEN}✓ [PASS]${COLOR_RESET} $1"
}

fail() {
    echo -e "${COLOR_RED}✗ [FAIL]${COLOR_RESET} $1"
    if [[ "${FAIL_FAST}" == "true" ]]; then
        exit 1
    fi
}

info() {
    echo -e "${COLOR_BLUE}==>${COLOR_RESET} $1"
}

TOTAL_STEPS=5
if [[ "${WITH_INTEGRATION}" == "true" ]]; then
    TOTAL_STEPS=6
fi

CURRENT_STEP=0
STEP_FAILS=0

step_header() {
    CURRENT_STEP=$((CURRENT_STEP + 1))
    echo ""
    info "[Step ${CURRENT_STEP}/${TOTAL_STEPS}] $1"
}

echo "======================================================================"
echo " GitHub Actions Pre-Push CI Check: mobo-linac"
echo " Workflow reference: .github/workflows/ci.yml"
echo " Integration tests:  ${WITH_INTEGRATION}"
echo "======================================================================"

# Step 1: Binary permissions
step_header "Verifying binary permissions (bin/*)..."
if [[ -d "bin" ]]; then
    chmod +x bin/* 2>/dev/null || true
    pass "Binary execution permissions verified."
else
    pass "No bin/ directory found; skipping."
fi

# Step 2: Package import & version smoke test
step_header "Smoke test: Package import & version check..."
if python3 -c "import mobo_linac; print('mobo_linac version:', mobo_linac.__version__); assert mobo_linac.__version__ == '1.0.0'" ; then
    pass "mobo_linac imports successfully and version matches 1.0.0."
else
    fail "Package import or version assertion failed!"
    STEP_FAILS=$((STEP_FAILS + 1))
fi

# Step 3: CLI smoke test
step_header "Smoke test: CLI entrypoint & help dispatch..."
if python3 -m mobo_linac.cli --help > /dev/null ; then
    pass "CLI entrypoint 'python3 -m mobo_linac.cli --help' executed successfully."
else
    fail "CLI invocation failed!"
    STEP_FAILS=$((STEP_FAILS + 1))
fi

# Step 4: Documentation & configuration sync audit
step_header "Audit: Configuration & documentation synchronization..."
if python3 scripts/verify_docs_sync.py ; then
    pass "Documentation & configuration parameters are synchronized."
else
    fail "Documentation / configuration synchronization check failed!"
    STEP_FAILS=$((STEP_FAILS + 1))
fi

# Step 5: Run CI Unit Test Suite (excluding integration tests requiring external tracking runs)
step_header "Pytest: CI Unit Test Suite (pytest -m 'not integration')..."
PYTEST_ARGS=(-v -m "not integration" --tb=short)
if [[ "${FAIL_FAST}" == "true" ]]; then
    PYTEST_ARGS+=(-x)
fi
if [[ "${VERBOSE}" == "false" ]]; then
    PYTEST_ARGS+=(--quiet)
fi

if pytest "${PYTEST_ARGS[@]}" ; then
    pass "Pytest unit test suite passed."
else
    fail "Pytest unit test suite encountered failures!"
    STEP_FAILS=$((STEP_FAILS + 1))
fi

# Optional Step 6: Full Integration Test Suite
if [[ "${WITH_INTEGRATION}" == "true" ]]; then
    step_header "Pytest: Integration Test Suite (pytest -m 'integration')..."
    if pytest -v -m "integration" --tb=short ; then
        pass "Integration test suite passed."
    else
        fail "Integration tests encountered failures!"
        STEP_FAILS=$((STEP_FAILS + 1))
    fi
fi

echo ""
echo "======================================================================"
if [[ ${STEP_FAILS} -eq 0 ]]; then
    echo -e "${COLOR_GREEN}✓ All GitHub Actions pre-push CI validation checks PASSED.${COLOR_RESET}"
    echo "  Your branch is in a clean, CI-compliant state for git push."
    echo "======================================================================"
    exit 0
else
    echo -e "${COLOR_RED}✗ ${STEP_FAILS} check(s) FAILED.${COLOR_RESET}"
    echo "  Please fix the issues above before pushing to remote."
    echo "======================================================================"
    exit 1
fi
