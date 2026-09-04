#!/usr/bin/env bash
# ==============================================================================
# cleanup.sh - Cleanup transient output folders, caches, and logs for mobo-linac
# ==============================================================================
# Preserves:
#   - Core simulation input files (pal_photo2.ini, PAL_SOL_A.dat, TWS_Sband.dat, gun.dat, astra.in)
#   - Git tracked files, configurations, source code, and binaries
# Removes:
#   - Simulation & campaign outputs: results/*, results_notebooks/*, results_notebook/*, img/*
#   - Python bytecode & cache: __pycache__, .pytest_cache, *.pyc, *.pyo, *.pyd
#   - Build & distribution artifacts: build/, dist/, *.egg-info/
#   - LaTeX transient files: *.aux, *.bbl, *.blg, *.log, *.out, *.toc
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

DRY_RUN=false
FORCE=false

print_usage() {
    cat <<USG
Usage: ./scripts/cleanup.sh [OPTIONS]

Options:
  -n, --dry-run   Show what would be deleted without actually deleting.
  -f, --force     Do not prompt before deleting.
  -h, --help      Display this help message.
USG
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -n|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -f|--force)
            FORCE=true
            shift
            ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            print_usage
            exit 1
            ;;
    esac
done

echo "======================================================================"
echo " mobo-linac: Project Workspace Cleanup"
if [[ "${DRY_RUN}" == "true" ]]; then
    echo " MODE: Dry-run (no files will be deleted)"
else
    echo " MODE: Active cleanup"
fi
echo "======================================================================"

# Target directories to clean contents of (preserve directory and .gitkeep if present)
OUTPUT_DIRS=(
    "results"
    "results_notebooks"
    "results_notebook"
    "img"
)

# Transient build / cache directories to completely remove
CACHE_DIRS=(
    ".pytest_cache"
    "build"
    "dist"
)

if [[ "${DRY_RUN}" == "false" && "${FORCE}" == "false" ]]; then
    read -r -p "Are you sure you want to clean output directories and caches? [y/N] " response
    case "$response" in
        [yY][eE][sS]|[yY])
            ;;
        *)
            echo "Cleanup aborted."
            exit 0
            ;;
    esac
fi

# 1. Clean output directories
echo "[1/5] Cleaning output directories..."
for dir in "${OUTPUT_DIRS[@]}"; do
    if [[ -d "$dir" ]]; then
        # Find entries inside dir, excluding .gitkeep
        entries=$(find "$dir" -mindepth 1 -not -name ".gitkeep" 2>/dev/null || true)
        if [[ -n "$entries" ]]; then
            count=$(echo "$entries" | wc -l)
            if [[ "${DRY_RUN}" == "true" ]]; then
                echo "  [DRY-RUN] Would remove $count item(s) from $dir/"
            else
                find "$dir" -mindepth 1 -not -name ".gitkeep" -exec rm -rf {} +
                echo "  Removed contents of $dir/ ($count items cleaned)"
            fi
        else
            echo "  $dir/ is already clean."
        fi
    fi
done

# 2. Clean build and test cache directories
echo "[2/5] Cleaning build and cache directories..."
for cdir in "${CACHE_DIRS[@]}"; do
    if [[ -d "$cdir" ]]; then
        if [[ "${DRY_RUN}" == "true" ]]; then
            echo "  [DRY-RUN] Would remove $cdir/"
        else
            rm -rf "$cdir"
            echo "  Removed $cdir/"
        fi
    fi
done

# 3. Clean egg-info directories
egg_infos=$(find . -maxdepth 3 -type d -name "*.egg-info" 2>/dev/null || true)
if [[ -n "$egg_infos" ]]; then
    while IFS= read -r egg_dir; do
        if [[ "${DRY_RUN}" == "true" ]]; then
            echo "  [DRY-RUN] Would remove $egg_dir"
        else
            rm -rf "$egg_dir"
            echo "  Removed $egg_dir"
        fi
    done <<< "$egg_infos"
fi

# 4. Clean Python bytecode and __pycache__ directories
echo "[3/5] Cleaning Python bytecode and __pycache__..."
pycache_dirs=$(find . -type d -name "__pycache__" 2>/dev/null || true)
if [[ -n "$pycache_dirs" ]]; then
    count=$(echo "$pycache_dirs" | wc -l)
    if [[ "${DRY_RUN}" == "true" ]]; then
        echo "  [DRY-RUN] Would remove $count __pycache__ directorie(s)"
    else
        find . -type d -name "__pycache__" -exec rm -rf {} +
        echo "  Removed $count __pycache__ directorie(s)"
    fi
else
    echo "  No __pycache__ directories found."
fi

find . -type f \( -name "*.pyc" -o -name "*.pyo" -o -name "*.pyd" \) 2>/dev/null | while IFS= read -r f; do
    if [[ "${DRY_RUN}" == "true" ]]; then
        echo "  [DRY-RUN] Would remove $f"
    else
        rm -f "$f"
    fi
done

# 5. Clean LaTeX build artifacts in docs/paper/
echo "[4/5] Cleaning LaTeX build artifacts in docs/paper/..."
if [[ -d "docs/paper" ]]; then
    latex_files=$(find docs/paper -type f \( -name "*.aux" -o -name "*.bbl" -o -name "*.blg" -o -name "*.log" -o -name "*.out" -o -name "*.toc" \) 2>/dev/null || true)
    if [[ -n "$latex_files" ]]; then
        count=$(echo "$latex_files" | wc -l)
        if [[ "${DRY_RUN}" == "true" ]]; then
            echo "  [DRY-RUN] Would remove $count LaTeX artifact(s) from docs/paper/"
        else
            find docs/paper -type f \( -name "*.aux" -o -name "*.bbl" -o -name "*.blg" -o -name "*.log" -o -name "*.out" -o -name "*.toc" \) -exec rm -f {} +
            echo "  Removed $count LaTeX artifact(s) from docs/paper/"
        fi
    else
        echo "  docs/paper/ has no transient LaTeX build artifacts."
    fi
fi

# 6. Clean root temporary logs and swap files
echo "[5/5] Cleaning editor swap files and root temporary logs..."
swp_files=$(find . -type f \( -name ".*.swp" -o -name "*~" \) 2>/dev/null || true)
if [[ -n "$swp_files" ]]; then
    while IFS= read -r swp; do
        if [[ "${DRY_RUN}" == "true" ]]; then
            echo "  [DRY-RUN] Would remove $swp"
        else
            rm -f "$swp"
            echo "  Removed $swp"
        fi
    done <<< "$swp_files"
fi

echo "======================================================================"
echo " Cleanup completed successfully."
echo "======================================================================"
