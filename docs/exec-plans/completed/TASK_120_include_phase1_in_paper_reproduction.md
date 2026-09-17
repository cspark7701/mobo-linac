# TASK_120: Integrate Phase 1 Scalarized BO Results into Paper Reproduction Pipeline

## 1. Motivation & User Request
The manuscript reproduction script [`scripts/reproduce_paper.sh`](file:///home/cspark/Work/projects/mobo-linac/scripts/reproduce_paper.sh) and figure generation module [`scripts/generate_paper_figures.py`](file:///home/cspark/Work/projects/mobo-linac/scripts/generate_paper_figures.py) previously only considered Phase 2 (Unconstrained MOBO) and Phase 3 (Constrained MOBO).

The user requested that [`scripts/reproduce_paper.sh`](file:///home/cspark/Work/projects/mobo-linac/scripts/reproduce_paper.sh) include Phase 1 (Scalarized BO), and that the paper ([`docs/paper/main.tex`](file:///home/cspark/Work/projects/mobo-linac/docs/paper/main.tex), figures, and data-driven LaTeX tables) also comprehensively include results from Phase 1.

## 2. Implementation Details

### 1. Paper Figure & Table Generation (`scripts/generate_paper_figures.py`)
- **CLI & Auto-Detection**:
  - Added `--phase1-dir` option to `_parse_args()`.
  - Added auto-detection in `main()`: if not passed, automatically inspects `results/full_production/phase1_scalarized` and sibling paths next to Phase 2.
- **Figure 1 (`plot_hypervolume_comparison`)**:
  - Added Phase 1 hypervolume curve (purple triangles, dotted line) alongside Phase 2 and Phase 3.
  - Dynamically annotates final Phase 1 feasible hypervolume ($0.019029$).
- **Figure 2 (`plot_pareto_front_comparison`)**:
  - Added Phase 1 Pareto points across all three objective projection planes ($\varepsilon_{n,x}$ vs $\varepsilon_{n,y}$, $\varepsilon_{n,x}$ vs $\sigma_E$, and $\varepsilon_{n,y}$ vs $\sigma_E$).
- **Figure 4 (`plot_feasible_fraction`)**:
  - Added Phase 1 feasible beam fraction trajectory across cumulative ASTRA evaluations.
- **Table 2 (`export_results_summary_latex_table`)**:
  - Dynamically exports a comprehensive 3-phase comparative summary in [`docs/paper/results_table.tex`](file:///home/cspark/Work/projects/mobo-linac/docs/paper/results_table.tex) containing columns for `Phase 1 (Scalarized)`, `Phase 2 (Unconstrained)`, and `Phase 3 (Constrained)`.
  - Computes exact values for Total Evaluations, Simulation Validity, Feasible Evaluations, Unconstrained Hypervolume, Feasible Hypervolume, Final Pareto Size, Min $\varepsilon_{n,x}$, Min $\varepsilon_{n,y}$, and Min $\sigma_E$.
- **Consistency Verification (`check_manuscript_consistency`)**:
  - Checks existence of required CSV outputs (`hypervolume.csv`, `pareto.csv`, `train_X.csv`, `train_Y.csv`, `config.yaml`) across all three phases.

### 2. Manuscript Reproduction Script (`scripts/reproduce_paper.sh`)
- Added `--phase1-dir DIR` CLI parameter and auto-detection checking `results/full_production/phase1_scalarized` and `results/phase1_scalarized_*`.
- Enhanced auto-detection for `PHASE2_DIR`, `PHASE3_DIR`, and `VER_CSV` to prioritize `results/full_production/`.
- Passes `--phase1-dir` into:
  - Step 1: Figure and LaTeX table generation (`scripts/generate_paper_figures.py`).
  - Step 3: Manuscript consistency check (`scripts/generate_paper_figures.py --check-only`).
  - Step 4: Verification test suite (`pytest tests/test_paper_outputs.py`).
- Compiles [`docs/paper/main.pdf`](file:///home/cspark/Work/projects/mobo-linac/docs/paper/main.pdf) with `pdflatex`.

### 3. Manuscript LaTeX Updates (`docs/paper/main.tex`)
- Updated Section 4 (Computational Results) introductory narrative to explicitly describe the 3-phase comparison framework.
- Updated Section 4.1 (Phase 1: Scalarized Bayesian Optimization Performance) to report exact data-driven findings from the 176-evaluation campaign (100% validity, 1.1% feasibility, $0.019029$ feasible hypervolume vs $0.020258$ in Phase 3).
- Updated Figure 1 & Figure 2 captions to reference all three optimization phases.
- Integrated Figure 4 (`figures/feasible_fraction.png`) into the manuscript to visually illustrate feasible beam fraction evolution across Phases 1, 2, and 3.

### 4. Test Suite Extensions (`tests/conftest.py` & `tests/test_paper_outputs.py`)
- Registered `--phase1-dir` in `pytest_addoption` ([`tests/conftest.py`](file:///home/cspark/Work/projects/mobo-linac/tests/conftest.py)).
- Added `phase1_dir` session fixture in [`tests/test_paper_outputs.py`](file:///home/cspark/Work/projects/mobo-linac/tests/test_paper_outputs.py).
- Added 9 new unit tests:
  - `test_phase1_result_files_exist[hypervolume.csv/pareto.csv/train_X.csv/train_Y.csv/config.yaml]`
  - `test_hypervolume_csv_columns_phase1`
  - `test_pareto_csv_has_data_phase1`
  - `test_pareto_emittance_values_physical_range_phase1`
  - `test_pareto_energy_spread_physical_range_phase1`
- Added assertion verifying `results_table.tex` contains the `Phase 1 (Scalarized)` column.
- Fixed `test_verification_table_produced_from_csv` working directory to reference `project_root`.

## 3. Verification

1. **Unit Test Suite**:
   ```bash
   pytest tests/test_paper_outputs.py -v
   ```
   - **Result**: `47 passed in 17.10s` (0 failures, 0 skips).

2. **Full End-to-End Reproduction Script**:
   ```bash
   bash scripts/reproduce_paper.sh
   ```
   - **Result**: Succeeded with exit code 0:
     - Auto-detected Phase 1, Phase 2, and Phase 3 run directories.
     - Generated all 4 figures (`hypervolume_comparison.png`, `pareto_front_comparison.png`, `verification_rerun_comparison.png`, `feasible_fraction.png`).
     - Exported data-driven LaTeX tables (`results_table.tex` and `verification_table.tex`).
     - Consistency checks passed.
     - All 47 pytest tests passed.
     - `pdflatex` compiled [`docs/paper/main.pdf`](file:///home/cspark/Work/projects/mobo-linac/docs/paper/main.pdf) successfully.

3. **Documentation Sync Audit**:
   ```bash
   python scripts/verify_docs_sync.py
   ```
   - **Result**: `SUCCESS: All documentation tables and web page parameters are 100% synchronized!`.
