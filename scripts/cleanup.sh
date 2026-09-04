#!/usr/bin/env bash
# ==============================================================================
# cleanup.sh - Cleanup transient output folders, caches, and logs for mobo-linac
# ==============================================================================
# Preserves:
#   - Core simulation input files (pal_photo2.ini, PAL_SOL_A.dat, TWS_Sband.dat, gun.dat, astra.in)
#   - Git tracked files, configurations, source code, and binaries
# Selectable targets:
#   - cache: __pycache__, .pytest_cache, *.pyc, *.pyo, *.pyd, build/, dist/, *.egg-info/
#   - results: results/* (campaign simulation and optimization outputs)
#   - results-notebooks: results_notebooks/*, results_notebook/* (interactive runs)
#   - img: img/* (generated figures and plots)
#   - docs: transient LaTeX build files (*.aux, *.bbl, *.blg, *.log, *.out, *.toc)
#   - all: all of the above
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

DRY_RUN=false
FORCE=false

# Targets to clean (default: all if none explicitly specified)
CLEAN_ALL=false
CLEAN_CACHE=false
CLEAN_RESULTS=false
CLEAN_RESULTS_NOTEBOOKS=false
CLEAN_IMG=false
CLEAN_DOCS=false

print_usage() {
    cat <<USG
Usage: ./scripts/cleanup.sh [OPTIONS] [TARGETS...]

Options:
  -n, --dry-run             Show what would be deleted without actually deleting.
  -f, --force               Do not prompt before deleting.
  -h, --help                Display this help message.

Target Flags:
  -a, --all                 Clean everything (default if no target flags/arguments given).
  --cache                   Clean Python bytecode, __pycache__, pytest cache, and build files.
  --results                 Clean optimization campaign outputs (results/*).
  --results-notebooks       Clean notebook execution results (results_notebooks/*, results_notebook/*).
  --img                     Clean generated figures/plots (img/*).
  --docs                    Clean LaTeX build artifacts (*.aux, *.log, *.out, etc.).

Positional Targets:
  You can also specify targets positionally:
  ./scripts/cleanup.sh cache results results_notebooks img docs all
USG
}

# Parse options and arguments
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
        -a|--all|all)
            CLEAN_ALL=true
            shift
            ;;
        --cache|cache)
            CLEAN_CACHE=true
            shift
            ;;
        --results|results)
            CLEAN_RESULTS=true
            shift
            ;;
        --results-notebooks|--results-notebook|results_notebooks|results_notebook|results-notebooks)
            CLEAN_RESULTS_NOTEBOOKS=true
            shift
            ;;
        --img|img|images)
            CLEAN_IMG=true
            shift
            ;;
        --docs|docs|paper|latex)
            CLEAN_DOCS=true
            shift
            ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        *)
            echo "Error: Unknown argument or option: $1"
            print_usage
            exit 1
            ;;
    esac
done

# If no specific target was requested, default to all
if [[ "${CLEAN_ALL}" == "false" && \
      "${CLEAN_CACHE}" == "false" && \
      "${CLEAN_RESULTS}" == "false" && \
      "${CLEAN_RESULTS_NOTEBOOKS}" == "false" && \
      "${CLEAN_IMG}" == "false" && \
      "${CLEAN_DOCS}" == "false" ]]; then
    CLEAN_ALL=true
fi

if [[ "${CLEAN_ALL}" == "true" ]]; then
    CLEAN_CACHE=true
    CLEAN_RESULTS=true
    CLEAN_RESULTS_NOTEBOOKS=true
    CLEAN_IMG=true
    CLEAN_DOCS=true
fi

echo "======================================================================"
echo " mobo-linac: Project Workspace Cleanup"
if [[ "${DRY_RUN}" == "true" ]]; then
    echo " MODE: Dry-run (no files will be deleted)"
else
    echo " MODE: Active cleanup"
fi
echo " TARGETS:"
echo "   - cache:             ${CLEAN_CACHE}"
echo "   - results:           ${CLEAN_RESULTS}"
echo "   - results-notebooks: ${CLEAN_RESULTS_NOTEBOOKS}"
echo "   - img:               ${CLEAN_IMG}"
echo "   - docs (latex):      ${CLEAN_DOCS}"
echo "======================================================================"

if [[ "${DRY_RUN}" == "false" && "${FORCE}" == "false" ]]; then
    read -r -p "Are you sure you want to proceed with cleanup? [y/N] " response
    case "$response" in
        [yY][eE][sS]|[yY])
            ;;
        *)
            echo "Cleanup aborted."
            exit 0
            ;;
    esac
fi

clean_directory_contents() {
    local dir="$1"
    if [[ -d "$dir" ]]; then
        local entries
        entries=$(find "$dir" -mindepth 1 -not -name ".gitkeep" 2>/dev/null || true)
        if [[ -n "$entries" ]]; then
            local count
            count=$(echo "$entries" | wc -l)
            if [[ "${DRY_RUN}" == "true" ]]; then
                echo "  [DRY-RUN] Would remove $count item(s) from $dir/"
            else
                find "$dir" -mindepth 1 -not -name ".gitkeep" -exec rm -rf {} +
                echo "  Removed contents of $dir/ ($count items cleaned)"
            fi
        else
            echo "  $dir/ is already empty/clean."
        fi
    else
        echo "  $dir/ does not exist (skipping)."
    fi
}

# --- Target 1: Results ---
if [[ "${CLEAN_RESULTS}" == "true" ]]; then
    echo "[*] Cleaning results directory..."
    clean_directory_contents "results"
fi

# --- Target 2: Results Notebooks ---
if [[ "${CLEAN_RESULTS_NOTEBOOKS}" == "true" ]]; then
    echo "[*] Cleaning results notebook directories..."
    clean_directory_contents "results_notebooks"
    clean_directory_contents "results_notebook"
fi

# --- Target 3: Img ---
if [[ "${CLEAN_IMG}" == "true" ]]; then
    echo "[*] Cleaning generated images directory..."
    clean_directory_contents "img"
fi

# --- Target 4: Caches and Bytecode ---
if [[ "${CLEAN_CACHE}" == "true" ]]; then
    echo "[*] Cleaning build, test, and Python caches..."
    for cdir in ".pytest_cache" "build" "dist"; do
        if [[ -d "$cdir" ]]; then
            if [[ "${DRY_RUN}" == "true" ]]; then
                echo "  [DRY-RUN] Would remove $cdir/"
            else
                rm -rf "$cdir"
                echo "  Removed $cdir/"
            fi
        fi
    done

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

    pycache_dirs=$(find . -type d -name "__pycache__" 2>/dev/null || true)
    if [[ -n "$pycache_dirs" ]]; then
        count=$(echo "$pycache_dirs" | wc -l)
        if [[ "${DRY_RUN}" == "true" ]]; then
            echo "  [DRY-RUN] Would remove $count __pycache__ directory(ies)"
        else
            find . -type d -name "__pycache__" -exec rm -rf {} +
            echo "  Removed $count __pycache__ directory(ies)"
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
fi

# --- Target 5: LaTeX and Documentation Artifacts ---
if [[ "${CLEAN_DOCS}" == "true" ]]; then
    echo "[*] Cleaning LaTeX transient build artifacts in docs/paper/..."
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
fi

echo "======================================================================"
echo " Cleanup completed successfully."
echo "======================================================================"
