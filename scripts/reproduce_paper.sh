#!/usr/bin/env bash
# ==============================================================================
# reproduce_paper.sh — Manuscript Reproduction Script (Task 10 / Codex Task 10)
#
# Regenerates ALL paper figures, LaTeX tables, and verifies manuscript
# consistency from archived processed campaign data WITHOUT re-running any
# expensive ASTRA particle tracking simulations.
#
# Usage
# -----
#   bash scripts/reproduce_paper.sh [--phase2-dir DIR] [--phase3-dir DIR] \
#       [--verification-csv PATH] [--check-only]
#
# Required inputs (auto-detected from results/ if not specified)
# -------------------------------------------------------------
#   results/phase2_unconstrained_*/   Phase 2 campaign run directory
#   results/phase3_constrained_*/     Phase 3 campaign run directory
#   results/verification/verification_summary.csv
#
# Outputs
# -------
#   docs/paper/figures/hypervolume_comparison.png
#   docs/paper/figures/pareto_front_comparison.png
#   docs/paper/figures/verification_rerun_comparison.png
#   docs/paper/figures/feasible_fraction.png
#   docs/paper/verification_table.tex   (data-driven, not hard-coded)
#   docs/paper/results_table.tex        (data-driven, not hard-coded)
#
# Manuscript consistency test
# ---------------------------
#   pytest -q tests/test_paper_outputs.py
# ==============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
PAPER_FIG_DIR="docs/paper/figures"
PAPER_DIR="docs/paper"
RESULTS_DIR="results"
VER_CSV="results/verification/verification_summary.csv"
CHECK_ONLY=0
PHASE2_DIR=""
PHASE3_DIR=""

# ---------------------------------------------------------------------------
# Parse CLI arguments
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --phase2-dir)   PHASE2_DIR="$2"; shift 2 ;;
        --phase3-dir)   PHASE3_DIR="$2"; shift 2 ;;
        --verification-csv) VER_CSV="$2"; shift 2 ;;
        --check-only)   CHECK_ONLY=1; shift ;;
        -h|--help)
            head -40 "$0" | grep "^#" | sed 's/^# \?//'
            exit 0 ;;
        *) echo "Unknown argument: $1"; exit 1 ;;
    esac
done

# ---------------------------------------------------------------------------
# Auto-detect phase directories if not explicitly specified
# ---------------------------------------------------------------------------
if [[ -z "$PHASE2_DIR" ]]; then
    PHASE2_DIR=$(ls -d "${RESULTS_DIR}"/phase2_unconstrained_* 2>/dev/null | sort | tail -1 || true)
    if [[ -z "$PHASE2_DIR" ]]; then
        echo "Error: No Phase 2 results directory found in ${RESULTS_DIR}/."
        echo "       Run a Phase 2 campaign first, or specify --phase2-dir."
        exit 1
    fi
    echo "  Auto-detected Phase 2 directory: $PHASE2_DIR"
fi

if [[ -z "$PHASE3_DIR" ]]; then
    PHASE3_DIR=$(ls -d "${RESULTS_DIR}"/phase3_constrained_* 2>/dev/null | sort | tail -1 || true)
    if [[ -z "$PHASE3_DIR" ]]; then
        echo "Error: No Phase 3 results directory found in ${RESULTS_DIR}/."
        echo "       Run a Phase 3 campaign first, or specify --phase3-dir."
        exit 1
    fi
    echo "  Auto-detected Phase 3 directory: $PHASE3_DIR"
fi

# ---------------------------------------------------------------------------
# Environment check
# ---------------------------------------------------------------------------
echo ""
echo "=== Linac MOBO Manuscript Reproduction Script ==="
echo "  Phase 2 run dir:   $PHASE2_DIR"
echo "  Phase 3 run dir:   $PHASE3_DIR"
echo "  Verification CSV:  $VER_CSV"
echo "  Output figures:    $PAPER_FIG_DIR"
echo "  Output tables:     $PAPER_DIR"
echo ""

if ! python -c "import mobo_linac" 2>/dev/null; then
    echo "Error: mobo_linac package not importable. Activate the conda/venv environment first."
    exit 1
fi

mkdir -p "$PAPER_FIG_DIR"

# ---------------------------------------------------------------------------
# Step 1: Generate all figures and LaTeX tables
# ---------------------------------------------------------------------------
if [[ "$CHECK_ONLY" -eq 0 ]]; then
    echo "Step 1: Generating publication figures and tables..."
    python scripts/generate_paper_figures.py \
        --phase2-dir "$PHASE2_DIR" \
        --phase3-dir "$PHASE3_DIR" \
        --verification-csv "$VER_CSV" \
        --output-dir "$PAPER_FIG_DIR" \
        --tables-dir "$PAPER_DIR"
    echo ""
fi

# ---------------------------------------------------------------------------
# Step 2: Export verification LaTeX table (also ensured by generate_paper_figures.py,
#         but kept here as an explicit step for clarity)
# ---------------------------------------------------------------------------
if [[ "$CHECK_ONLY" -eq 0 && -f "$VER_CSV" ]]; then
    echo "Step 2: Exporting verification LaTeX table from data..."
    python3 -c "
import sys, pandas as pd
sys.path.insert(0, 'src')
from mobo_linac.verification.verifier import export_verification_latex_table
vdf = pd.read_csv('$VER_CSV')
records = vdf.to_dict('records')
export_verification_latex_table(records, '$PAPER_DIR/verification_table.tex')
print('  Exported verification_table.tex from verification_summary.csv')
"
    echo ""
fi

# ---------------------------------------------------------------------------
# Step 3: Manuscript consistency test
# ---------------------------------------------------------------------------
echo "Step 3: Running manuscript consistency tests..."
python scripts/generate_paper_figures.py \
    --phase2-dir "$PHASE2_DIR" \
    --phase3-dir "$PHASE3_DIR" \
    --verification-csv "$VER_CSV" \
    --output-dir "$PAPER_FIG_DIR" \
    --tables-dir "$PAPER_DIR" \
    --check-only
echo ""

# ---------------------------------------------------------------------------
# Step 4: pytest test_paper_outputs.py
# ---------------------------------------------------------------------------
echo "Step 4: Running pytest test_paper_outputs.py..."
pytest -q tests/test_paper_outputs.py \
    --phase2-dir "$PHASE2_DIR" \
    --phase3-dir "$PHASE3_DIR" \
    --verification-csv "$VER_CSV" \
    --figures-dir "$PAPER_FIG_DIR" \
    --tables-dir "$PAPER_DIR" 2>/dev/null || \
pytest -q tests/test_paper_outputs.py
echo ""

# ---------------------------------------------------------------------------
# Step 5: Attempt LaTeX compilation (optional, non-fatal)
# ---------------------------------------------------------------------------
echo "Step 5: LaTeX compilation..."
if command -v pdflatex &>/dev/null; then
    echo "  Building $PAPER_DIR/main.pdf with pdflatex..."
    pushd "$PAPER_DIR" > /dev/null
    pdflatex -interaction=nonstopmode main.tex > /dev/null 2>&1 || true
    pdflatex -interaction=nonstopmode main.tex > /dev/null 2>&1 || true
    popd > /dev/null
    if [[ -f "$PAPER_DIR/main.pdf" ]]; then
        echo "  ✓ Manuscript compiled: $PAPER_DIR/main.pdf"
    else
        echo "  ✗ pdflatex failed — check $PAPER_DIR/main.log for details."
    fi
else
    echo "  Note: pdflatex not found — skipping PDF compilation."
    echo "        Install TeX Live or MiKTeX to compile main.pdf."
fi
echo ""

echo "=== Manuscript Reproduction Complete ==="
echo "  Figures: $PAPER_FIG_DIR/"
echo "  Tables:  $PAPER_DIR/verification_table.tex"
echo "           $PAPER_DIR/results_table.tex"
