#!/usr/bin/env bash
# ==============================================================================
# Full Production Simulation & Analysis Pipeline Script
# ==============================================================================
# This script executes the complete production-grade simulation and analysis
# pipeline for the 200 MeV S-band electron injector linac MOBO optimization.
#
# Key Features:
#   1. Parallel ASTRA Multi-Worker Execution.
#   2. Screen Verbose On/Off Toggle (quiet mode for token-efficient AI prompts).
#   3. Full production MOBO simulation execution (Phase 2 & Phase 3).
#   4. Complete post-simulation analysis, hypervolume tracking, & Pareto rerun audit.
#
# Usage:
#   ./scripts/run_full_production.sh                  # Run with full screen output
#   ./scripts/run_full_production.sh --quiet          # Run silently (no screen flooding)
#   ./scripts/run_full_production.sh --iterations 15  # Custom iteration budget
#   ./scripts/run_full_production.sh --workers 8      # Custom worker count
# ==============================================================================

set -euo pipefail

# ------------------------------------------------------------------------------
# Default Parameter Settings
# ------------------------------------------------------------------------------
VERBOSE=1
N_ITERATIONS=20
BATCH_SIZE=8
NUM_INITIAL_SAMPLES=16
NUM_WORKERS=4
SEED=42
DEVICE="auto"
OUTPUT_BASE_DIR="results/full_production"
RESUME_FLAG=""
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
    -b|-q|--batch-size)
      # Set candidate proposal batch size q
      BATCH_SIZE="$2"
      shift 2
      ;;
    -w|--workers)
      # Set custom number of parallel CPU worker processes
      NUM_WORKERS="$2"
      shift 2
      ;;
    -d|--device)
      # Set target PyTorch compute device (auto, cuda, cpu)
      DEVICE="$2"
      shift 2
      ;;
    -o|--output-dir)
      # Set custom base output directory
      OUTPUT_BASE_DIR="$2"
      shift 2
      ;;
    -r|--resume)
      RESUME_FLAG="--resume"
      shift
      ;;
    -h|--help)
      echo "Usage: ./scripts/run_full_production.sh [OPTIONS]"
      echo "Options:"
      echo "  -r, --resume         Resume existing runs from latest checkpoints"
      echo "  -q, --quiet          Suppress screen output (token-efficient mode)"
      echo "  -i, --iterations N   Number of BO iterations (default: 20)"
      echo "  -b, --batch-size Q   Batch size q (default: 8)"
      echo "  -w, --workers W      Number of parallel CPU worker cores (default: 4)"
      echo "  -d, --device DEV     Target PyTorch device (auto, cuda, cpu; default: auto GPU selection)"
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
# ANSI Color Palette & Logging Helpers
# ------------------------------------------------------------------------------
CLR_RESET="\033[0m"
CLR_BOLD="\033[1m"
CLR_DIM="\033[2m"
CLR_CYAN="\033[1;36m"
CLR_BLUE="\033[1;34m"
CLR_GREEN="\033[1;32m"
CLR_YELLOW="\033[1;33m"
CLR_MAGENTA="\033[1;35m"
CLR_RED="\033[1;31m"

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

log_step "${CLR_CYAN}======================================================================${CLR_RESET}"
log_step "${CLR_CYAN}${CLR_BOLD} Starting Full Production Linac MOBO Simulation & Analysis Pipeline${CLR_RESET}"
log_step "${CLR_CYAN}======================================================================${CLR_RESET}"
log_step "  ${CLR_BOLD}Project Root:${CLR_RESET}         ${PROJECT_ROOT}"
log_step "  ${CLR_BOLD}Parallel CPU Workers:${CLR_RESET} ${NUM_WORKERS}"
log_step "  ${CLR_BOLD}BO Iterations:${CLR_RESET}        ${N_ITERATIONS}"
log_step "  ${CLR_BOLD}Batch Size (q):${CLR_RESET}       ${BATCH_SIZE}"
log_step "  ${CLR_BOLD}Verbose Screen:${CLR_RESET}       $([ ${VERBOSE} -eq 1 ] && echo -e "${CLR_GREEN}ON (Full)${CLR_RESET}" || echo -e "${CLR_YELLOW}OFF (Quiet Mode - Step Progress Only)${CLR_RESET}")"
log_step "  ${CLR_BOLD}Output Base Dir:${CLR_RESET}      ${OUTPUT_BASE_DIR}"
log_step "${CLR_CYAN}======================================================================${CLR_RESET}"

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
      echo -e "\n${CLR_RED}${CLR_BOLD}[ERROR] Step execution failed!${CLR_RESET}" >&2
      exit 1
    fi
  else
    if ! eval "${cmd}" > "${log_file}" 2>&1; then
      echo -e "\n${CLR_RED}${CLR_BOLD}[ERROR] Step execution failed!${CLR_RESET}" >&2
      echo -e "${CLR_RED}Error Log Snippet (${log_file}):${CLR_RESET}" >&2
      tail -n 25 "${log_file}" >&2
      exit 1
    fi
  fi
}

# ------------------------------------------------------------------------------
# Step 1: Environment & Binary Verification
# ------------------------------------------------------------------------------
log_step "\n\n${CLR_CYAN}${CLR_BOLD}▶ [Step 1/7]${CLR_RESET} ${CLR_BOLD}Verifying environment & executable permissions...${CLR_RESET}"
chmod +x bin/* 2>/dev/null || true
export ASTRA_BIN="${PROJECT_ROOT}/bin/astra"
export GENERATOR_BIN="${PROJECT_ROOT}/bin/generator"
export PATH="${PROJECT_ROOT}/bin:${PATH}"
log_step "  ${CLR_GREEN}✓${CLR_RESET} Environment & binary permissions verified"

# ------------------------------------------------------------------------------
# Step 2: Execute Phase 1 Scalarized BO Production Simulation
# ------------------------------------------------------------------------------
RUN_P1_CMD="mobo-linac run-scalarized \
    --config configs/mobo_200MeV.yaml \
    --n-iterations ${N_ITERATIONS} \
    --batch-size ${BATCH_SIZE} \
    --num-initial-samples ${NUM_INITIAL_SAMPLES} \
    --num-workers ${NUM_WORKERS} \
    --device ${DEVICE} \
    --seed ${SEED} \
    ${RESUME_FLAG} \
    --output-dir ${P1_DIR}"

execute_step "\n\n${CLR_CYAN}${CLR_BOLD}▶ [Step 2/7]${CLR_RESET} ${CLR_BOLD}Running Phase 1 Scalarized BO Simulation...${CLR_RESET}" "${RUN_P1_CMD}" "${P1_DIR}/simulation.log"
log_step "  ${CLR_GREEN}✓${CLR_RESET} Phase 1 Simulation complete -> Saved in ${P1_DIR}"

# ------------------------------------------------------------------------------
# Step 3: Execute Phase 2 Unconstrained MOBO Production Simulation
# ------------------------------------------------------------------------------
RUN_P2_CMD="mobo-linac run-unconstrained \
    --config configs/mobo_200MeV.yaml \
    --n-iterations ${N_ITERATIONS} \
    --batch-size ${BATCH_SIZE} \
    --num-initial-samples ${NUM_INITIAL_SAMPLES} \
    --num-workers ${NUM_WORKERS} \
    --device ${DEVICE} \
    --seed ${SEED} \
    ${RESUME_FLAG} \
    --output-dir ${P2_DIR}"

execute_step "\n\n${CLR_CYAN}${CLR_BOLD}▶ [Step 3/7]${CLR_RESET} ${CLR_BOLD}Running Phase 2 Unconstrained MOBO Simulation...${CLR_RESET}" "${RUN_P2_CMD}" "${P2_DIR}/simulation.log"
log_step "  ${CLR_GREEN}✓${CLR_RESET} Phase 2 Simulation complete -> Saved in ${P2_DIR}"

# ------------------------------------------------------------------------------
# Step 4: Execute Phase 3 Constrained MOBO Production Simulation
# ------------------------------------------------------------------------------
RUN_P3_CMD="mobo-linac run-constrained \
    --config configs/mobo_200MeV.yaml \
    --n-iterations ${N_ITERATIONS} \
    --batch-size ${BATCH_SIZE} \
    --num-initial-samples ${NUM_INITIAL_SAMPLES} \
    --num-workers ${NUM_WORKERS} \
    --device ${DEVICE} \
    --seed ${SEED} \
    ${RESUME_FLAG} \
    --output-dir ${P3_DIR}"

execute_step "\n\n${CLR_CYAN}${CLR_BOLD}▶ [Step 4/7]${CLR_RESET} ${CLR_BOLD}Running Phase 3 Constraint-Aware MOBO Simulation...${CLR_RESET}" "${RUN_P3_CMD}" "${P3_DIR}/simulation.log"
log_step "  ${CLR_GREEN}✓${CLR_RESET} Phase 3 Simulation complete -> Saved in ${P3_DIR}"

# ------------------------------------------------------------------------------
# Step 5: Execute 3-Phase Comparative Analysis & Pareto Verification
# ------------------------------------------------------------------------------
ANALYSIS_CMD="python3 scripts/run_comparison_and_verification.py \
    --phase1-dir ${P1_DIR} \
    --phase2-dir ${P2_DIR} \
    --phase3-dir ${P3_DIR} \
    --output-dir ${ANALYSIS_DIR}"

execute_step "\n\n${CLR_CYAN}${CLR_BOLD}▶ [Step 5/7]${CLR_RESET} ${CLR_BOLD}Executing 3-Phase Comparative Analysis & Independent Rerun Audit...${CLR_RESET}" "${ANALYSIS_CMD}" "${ANALYSIS_DIR}/analysis.log"
log_step "  ${CLR_GREEN}✓${CLR_RESET} 3-Phase Comparative analysis complete -> Saved in ${ANALYSIS_DIR}"

# ------------------------------------------------------------------------------
# Step 6: Engineering Tolerance Robustness Analysis
# ------------------------------------------------------------------------------
mkdir -p ${ANALYSIS_DIR}/robustness
ROBUST_CMD="python3 scripts/run_robustness_analysis.py \
    --pareto-csv ${P3_DIR}/pareto.csv \
    --output-dir ${ANALYSIS_DIR}/robustness \
    --num-workers ${NUM_WORKERS}"

execute_step "\n\n${CLR_CYAN}${CLR_BOLD}▶ [Step 6/7]${CLR_RESET} ${CLR_BOLD}Running Engineering Tolerance Robustness Analysis...${CLR_RESET}" "${ROBUST_CMD}" "${ANALYSIS_DIR}/robustness.log"
log_step "  ${CLR_GREEN}✓${CLR_RESET} Robustness analysis complete -> Saved in ${ANALYSIS_DIR}/robustness"

# ------------------------------------------------------------------------------
# Step 7: Final Summary & Verification Report Generation
# ------------------------------------------------------------------------------
log_step "\n\n${CLR_GREEN}${CLR_BOLD}▶ [Step 7/7] Pipeline Execution Finished Successfully!${CLR_RESET}"
log_step "${CLR_GREEN}======================================================================${CLR_RESET}"
log_step "${CLR_GREEN}${CLR_BOLD} Summary of Output Directories:${CLR_RESET}"
log_step "   Phase 1 BO:    ${P1_DIR}"
log_step "   Phase 2 MOBO:  ${P2_DIR}"
log_step "   Phase 3 MOBO:  ${P3_DIR}"
log_step "   Analysis:      ${ANALYSIS_DIR}"
log_step "   Robustness:    ${ANALYSIS_DIR}/robustness"
log_step "   Report:        ${ANALYSIS_DIR}/comparison_report.md"
log_step "${CLR_GREEN}======================================================================${CLR_RESET}"


