#!/usr/bin/env bash
# ==============================================================================
# Manuscript Reproduction Script for Linac MOBO Publication (Task 09)
#
# Regenerates all figures, tables, and manuscript artifacts from archived
# processed data in results/publication_processed/ without re-running long ASTRA
# simulations.
# ==============================================================================

set -e

echo "=== Linac MOBO Paper Reproduction Script ==="
echo "1. Checking archived processed datasets in results/publication_processed/..."

PROCESSED_DIR="results/publication_processed"
PAPER_FIG_DIR="docs/paper/figures"
PAPER_DIR="docs/paper"

mkdir -p "$PAPER_FIG_DIR"
mkdir -p "results/verification"

if [ ! -d "$PROCESSED_DIR" ]; then
    echo "Error: $PROCESSED_DIR does not exist!"
    exit 1
fi

echo "2. Generating publication figures and tables from processed datasets..."

python3 -c "
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

fig_dir = Path('$PAPER_FIG_DIR')
fig_dir.mkdir(parents=True, exist_ok=True)

# 1. Hypervolume progress plot
agg_csv = Path('$PROCESSED_DIR/aggregate_metrics.csv')
if agg_csv.exists():
    df = pd.read_csv(agg_csv)
    fig, ax = plt.subplots(figsize=(7, 5))
    for algo, group in df.groupby('algorithm'):
        ax.plot(group['cumulative_astra_evaluations'], group['median_feasible_hv'], label=algo, linewidth=2)
        if 'ci_lower_feasible_hv' in group and 'ci_upper_feasible_hv' in group:
            ax.fill_between(group['cumulative_astra_evaluations'], group['ci_lower_feasible_hv'], group['ci_upper_feasible_hv'], alpha=0.2)
    ax.set_xlabel('Cumulative ASTRA Evaluations')
    ax.set_ylabel('Feasible Hypervolume (Normalized)')
    ax.set_title('Multi-Objective Hypervolume Progress')
    ax.grid(True, linestyle='--', alpha=0.6)
    ax.legend(loc='lower right')
    plt.tight_layout()
    plt.savefig(fig_dir / 'hypervolume_comparison.png', dpi=300)
    plt.close()
    print('  - Saved hypervolume_comparison.png')

# 2. Verification comparison bar plot
ver_csv = Path('$PROCESSED_DIR/verification_records.csv')
if ver_csv.exists():
    vdf = pd.read_csv(ver_csv)
    fig, ax = plt.subplots(figsize=(8, 4))
    x = np.arange(len(vdf))
    width = 0.35
    ax.bar(x - width/2, vdf['stored_emit_x_m_rad']*1e6, width, label='Stored', color='#1f77b4')
    ax.bar(x + width/2, vdf['rerun_emit_x_m_rad']*1e6, width, label='Rerun', color='#2ca02c')
    ax.set_xticks(x)
    ax.set_xticklabels(vdf['role'], rotation=15, ha='right')
    ax.set_ylabel('$\epsilon_{n,x}$ [$\mu$m$\cdot$rad]')
    ax.set_title('Independent Pareto Candidate Rerun Verification')
    ax.legend()
    ax.grid(True, linestyle='--', alpha=0.5)
    plt.tight_layout()
    plt.savefig(fig_dir / 'verification_rerun_comparison.png', dpi=300)
    plt.close()
    print('  - Saved verification_rerun_comparison.png')
"

echo "3. Exporting verification LaTeX table..."
python3 -c "
import pandas as pd
from mobo_linac.verification.verifier import export_verification_latex_table

ver_csv = '$PROCESSED_DIR/verification_records.csv'
vdf = pd.read_csv(ver_csv)
records = vdf.to_dict('records')

export_verification_latex_table(records, 'results/verification/verification_table.tex')
export_verification_latex_table(records, '$PAPER_DIR/verification_table.tex')
print('  - Exported verification_table.tex')
"

echo "4. Checking LaTeX manuscript build..."
if command -v pdflatex &> /dev/null; then
    echo "Building main.pdf using pdflatex..."
    cd "$PAPER_DIR"
    pdflatex -interaction=nonstopmode main.tex > /dev/null 2>&1 || true
    pdflatex -interaction=nonstopmode main.tex > /dev/null 2>&1 || true
    cd - > /dev/null
    echo "  - Manuscript compiled: $PAPER_DIR/main.pdf"
else
    echo "Note: pdflatex not found on path, skipping PDF compilation."
fi

echo "=== Paper Reproduction Complete! All artifacts generated in $PAPER_FIG_DIR ==="
