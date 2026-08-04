#!/usr/bin/env bash
# ==============================================================================
# Full Production Simulation & Analysis Pipeline Script
# ==============================================================================
# This script executes the complete production-grade simulation and analysis
# pipeline for the 200 MeV S-band electron injector linac MOBO optimization.
#
# Key Features:
#   1. Automatic 90% CPU Core Parallelization.
#   2. Screen Verbose On/Off Toggle (quiet mode for token-efficient AI prompts).
#   3. Full production MOBO simulation execution (Phase 2 & Phase 3).
#   4. Complete post-simulation analysis, hypervolume tracking, & Pareto rerun audit.
#
# Usage:
#   ./scripts/run_full_production.sh                  # Run with full screen output
#   ./scripts/run_full_production.sh --quiet          # Run silently (no screen flooding)
#   ./scripts/run_full_production.sh --iterations 15  # Custom iteration budget
# ==============================================================================

set -euo pipefail

# ------------------------------------------------------------------------------
# Default Parameter Settings
# ------------------------------------------------------------------------------
VERBOSE=1
N_ITERATIONS=10
BATCH_SIZE=4
NUM_WORKERS=""
SEED=42
OUTPUT_BASE_DIR="results/full_production"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# ------------------------------------------------------------------------------
# Command Line Argument Parser
# ------------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    -q|--quiet)
      # Turn off verbose screen output to prevent token consumption in AI prompts
      VERBOSE=0
      shift
      ;;
    -i|--iterations)
      # Set custom number of MOBO optimization iterations
      N_ITERATIONS="$2"
      shift 2
      ;;
    -b|--batch-size)
      # Set candidate proposal batch size q
      BATCH_SIZE="$2"
      shift 2
      ;;
    -w|--workers)
      # Set custom number of parallel CPU worker processes
      NUM_WORKERS="$2"
      shift 2
      ;;
    -o|--output-dir)
      # Set custom base output directory
      OUTPUT_BASE_DIR="$2"
      shift 2
      ;;
    -h|--help)
      echo "Usage: ./scripts/run_full_production.sh [OPTIONS]"
      echo "Options:"
      echo "  -q, --quiet          Suppress screen output (token-efficient mode)"
      echo "  -i, --iterations N   Number of BO iterations (default: 10)"
      echo "  -b, --batch-size Q   Batch size q (default: 4)"
      echo "  -w, --workers W      Number of parallel CPU worker cores (default: 90% system capacity)"
      echo "  -o, --output-dir DIR Output directory (default: results/full_production)"
      echo "  -h, --help           Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Navigate to project root
cd "${PROJECT_ROOT}"

# ------------------------------------------------------------------------------
# Step 1: Calculate Available CPU Cores for Parallel Simulation
# ------------------------------------------------------------------------------
if [ -z "${NUM_WORKERS}" ]; then
  # Detect total system CPU cores and compute 90% allocation (minimum 1 worker)
  NUM_WORKERS=$(python3 -c "import os; print(max(1, int(os.cpu_count() * 0.9)))")
fi


# Helper function to print high-level step progress (always printed)
log_step() {
  echo -e "$1"
}

# Helper function to print detailed logs (printed when VERBOSE=1)
log_info() {
  if [ "${VERBOSE}" -eq 1 ]; then
    echo -e "$1"
  fi
}

log_step "======================================================================"
log_step " Starting Full Production Linac MOBO Simulation & Analysis Pipeline"
log_step "======================================================================"
log_step "  Project Root:        ${PROJECT_ROOT}"
log_step "  Allocated CPU Cores: ${NUM_WORKERS} (90% capacity)"
log_step "  BO Iterations:       ${N_ITERATIONS}"
log_step "  Batch Size (q):      ${BATCH_SIZE}"
log_step "  Verbose Screen:      $([ ${VERBOSE} -eq 1 ] && echo 'ON (Full)' || echo 'OFF (Quiet Mode - Step Progress Only)')"
log_step "  Output Base Dir:     ${OUTPUT_BASE_DIR}"
log_step "======================================================================"

# Create output structure
P1_DIR="${OUTPUT_BASE_DIR}/phase1_scalarized"
P2_DIR="${OUTPUT_BASE_DIR}/phase2_unconstrained"
P3_DIR="${OUTPUT_BASE_DIR}/phase3_constrained"
ANALYSIS_DIR="${OUTPUT_BASE_DIR}/analysis"
mkdir -p "${P1_DIR}" "${P2_DIR}" "${P3_DIR}" "${ANALYSIS_DIR}"

# Helper function to execute a step with error handling
execute_step() {
  local step_title="$1"
  local cmd="$2"
  local log_file="$3"

  log_step "${step_title}"
  if [ "${VERBOSE}" -eq 1 ]; then
    if ! eval "${cmd}"; then
      echo -e "\n\033[1;31m[ERROR] ${step_title} FAILED!\033[0m" >&2
      exit 1
    fi
  else
    if ! eval "${cmd}" > "${log_file}" 2>&1; then
      echo -e "\n\033[1;31m[ERROR] ${step_title} FAILED!\033[0m" >&2
      echo -e "\033[1;31mError Log Snippet (${log_file}):\033[0m" >&2
      tail -n 25 "${log_file}" >&2
      exit 1
    fi
  fi
}

# ------------------------------------------------------------------------------
# Step 2: Environment & Binary Verification
# ------------------------------------------------------------------------------
log_step "[Step 1/7] Verifying environment & executable permissions..."
chmod +x bin/* 2>/dev/null || true
export ASTRA_BIN="${PROJECT_ROOT}/bin/astra"
export GENERATOR_BIN="${PROJECT_ROOT}/bin/generator"
export PATH="${PROJECT_ROOT}/bin:${PATH}"

# ------------------------------------------------------------------------------
# Step 3: Execute Phase 1 Scalarized BO Production Simulation
# ------------------------------------------------------------------------------
RUN_P1_CMD="python3 scripts/run_scalarized_bo.py \
    --config configs/mobo_200MeV.yaml \
    --n-iterations ${N_ITERATIONS} \
    --batch-size ${BATCH_SIZE} \
    --num-workers ${NUM_WORKERS} \
    --seed ${SEED} \
    --output-dir ${P1_DIR}"

execute_step "[Step 2/7] Running Phase 1 Scalarized BO Simulation..." "${RUN_P1_CMD}" "${P1_DIR}/simulation.log"
log_step "  ✓ Phase 1 Simulation complete -> Saved in ${P1_DIR}"

# ------------------------------------------------------------------------------
# Step 4: Execute Phase 2 Unconstrained MOBO Production Simulation
# ------------------------------------------------------------------------------
RUN_P2_CMD="python3 scripts/run_validation_campaign.py \
    --n-iterations ${N_ITERATIONS} \
    --batch-size ${BATCH_SIZE} \
    --num-workers ${NUM_WORKERS} \
    --seed ${SEED} \
    --output-dir ${P2_DIR}"

execute_step "[Step 3/7] Running Phase 2 Unconstrained MOBO Simulation..." "${RUN_P2_CMD}" "${P2_DIR}/simulation.log"
log_step "  ✓ Phase 2 Simulation complete -> Saved in ${P2_DIR}"

# ------------------------------------------------------------------------------
# Step 5: Execute Phase 3 Constrained MOBO Production Simulation
# ------------------------------------------------------------------------------
RUN_P3_CMD="python3 scripts/run_validation_campaign.py \
    --n-iterations ${N_ITERATIONS} \
    --batch-size ${BATCH_SIZE} \
    --num-workers ${NUM_WORKERS} \
    --seed ${SEED} \
    --output-dir ${P3_DIR}"

execute_step "[Step 4/7] Running Phase 3 Constraint-Aware MOBO Simulation..." "${RUN_P3_CMD}" "${P3_DIR}/simulation.log"
log_step "  ✓ Phase 3 Simulation complete -> Saved in ${P3_DIR}"

# ------------------------------------------------------------------------------
# Step 6: Execute Comparative Analysis & Pareto Verification
# ------------------------------------------------------------------------------
ANALYSIS_CMD="python3 scripts/run_comparison_and_verification.py \
    --phase2-dir ${P2_DIR} \
    --phase3-dir ${P3_DIR} \
    --output-dir ${ANALYSIS_DIR}"

execute_step "[Step 5/7] Executing Comparative Analysis & Independent Rerun Audit..." "${ANALYSIS_CMD}" "${ANALYSIS_DIR}/analysis.log"
log_step "  ✓ Comparative analysis complete -> Saved in ${ANALYSIS_DIR}"

# ------------------------------------------------------------------------------
# Step 7: Engineering Tolerance Robustness Analysis
# ------------------------------------------------------------------------------
mkdir -p ${ANALYSIS_DIR}/robustness
ROBUST_CMD="python3 scripts/run_robustness_analysis.py \
    --pareto-csv ${P3_DIR}/pareto.csv \
    --output-dir ${ANALYSIS_DIR}/robustness \
    --num-workers ${NUM_WORKERS}"

execute_step "[Step 6/7] Running Engineering Tolerance Robustness Analysis..." "${ROBUST_CMD}" "${ANALYSIS_DIR}/robustness.log"
log_step "  ✓ Robustness analysis complete -> Saved in ${ANALYSIS_DIR}/robustness"


# ------------------------------------------------------------------------------
# Step 8: Final Summary & Verification Report Generation
# ------------------------------------------------------------------------------
log_step "[Step 7/7] Pipeline Execution Finished Successfully!"
log_step "======================================================================"
log_step " Summary of Output Directories:"
log_step "   Phase 1 BO:    ${P1_DIR}"
log_step "   Phase 2 MOBO:  ${P2_DIR}"
log_step "   Phase 3 MOBO:  ${P3_DIR}"
log_step "   Analysis:      ${ANALYSIS_DIR}"
log_step "   Robustness:    ${ANALYSIS_DIR}/robustness"
log_step "   Report:        ${ANALYSIS_DIR}/comparison_report.md"
log_step "======================================================================"


