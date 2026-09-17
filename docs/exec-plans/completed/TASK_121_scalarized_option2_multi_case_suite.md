# TASK_121: Implement Phase 1 Option 2 Multi-Case Scalarized BO Suite & Paper Integration

## 1. Motivation & User Request
The Phase 1 Scalarized Bayesian Optimization workflow previously operated on a single weight case (`[1.0, 1.0, 1.0]` normalized to `[1/3, 1/3, 1/3]`).
The user requested implementing **Option 2** (representative operational linac archetypes) so that:
1. Phase 1 in the full production pipeline simulates multiple distinct weight cases corresponding to Option 2.
2. These Option 2 results are aggregated and seamlessly integrated into the manuscript figures, tables, and text.

---

## 2. Option 2 Physical & Mathematical Specification

Option 2 defines five representative linac operating modes spanning the multi-objective Pareto trade-off surface:

| Case ID | Operating Mode Archetype | Normalized Weights $\mathbf{w} = [w_x, w_y, w_E]$ | Physical Objective & Machine Rationale |
| :--- | :--- | :--- | :--- |
| `balanced` | Balanced Linac Operation | $[0.333, 0.333, 0.334]$ | Equal compromise across transverse emittances and energy spread |
| `high_brightness` | High-Brightness FEL Mode | $[0.450, 0.450, 0.100]$ | Transverse-dominant emittance minimization for maximum FEL peak brightness |
| `low_energy_spread` | Low Energy Spread Mode | $[0.100, 0.100, 0.800]$ | Longitudinal-dominant energy spread minimization for spectrometer transport |
| `x_dominant` | Horizontal-Dominant Optics | $[0.600, 0.200, 0.200]$ | Quadrupole doublet asymmetry prioritizing horizontal emittance waist |
| `y_dominant` | Vertical-Dominant Optics | $[0.200, 0.600, 0.200]$ | Quadrupole doublet asymmetry prioritizing vertical emittance waist |

---

## 3. Implementation Details

### 1. Objective Normalization in GP Scalarization (`src/mobo_linac/campaigns/runner.py`)
- **Scaling Fix**: In `MoboCampaignRunner.run()`, unscaled raw physical units ($\varepsilon_{n,x/y} \sim 10^{-6}\text{ m}\cdot\text{rad}$ vs. $\sigma_E \sim 10^6\text{ eV}$) caused energy spread to numerically overwhelm emittance by $10^{11}$.
- **Resolution**: Scaled `train_Y_dev` by canonical reference scales `DEFAULT_REPORTING_SCALES = [1.0e-6, 1.0e-6, 1.0e6]` before weighted summation:
  $$\tilde{Y} = Y / [10^{-6}, 10^{-6}, 10^6]$$
  $$y_{\text{scalar}} = \sum_{m=1}^3 w_m \tilde{Y}_m$$
  ensuring weights act as true physical percentage allocations.

### 2. Multi-Case Suite Architecture (`src/mobo_linac/campaigns/scalarized_suite.py`)
- **Case Registry**: Defined canonical `OPTION_2_CASES` dictionary with weights, descriptions, and LaTeX symbols.
- **Suite Orchestration (`run_scalarized_suite`)**:
  - Iterates over specified cases (or all 5 Option 2 cases).
  - Isolates case runs into dedicated subdirectories (`<output_dir>/<case_id>/`).
  - Supports checkpoint resumption per case.
  - Automatically triggers post-run aggregation.
- **Multi-Case Result Aggregator (`aggregate_scalarized_cases`)**:
  - Discovers case runs within the suite root directory.
  - Merges evaluations into unified root datasets (`evaluations.csv`, `candidate_history.csv`, `train_X.csv`, `train_Y.csv`).
  - Computes global non-dominated Pareto front across all cases (`pareto.csv`, `pareto_all.csv`, `pareto_feasible.csv`).
  - Constructs cumulative hypervolume progression across evaluations (`hypervolume.csv`).
  - Generates `cases_summary.csv` and `cases_summary.json` reporting per-case evaluations, validity, feasibility, single-channel minimums, and hypervolume.
- **LaTeX Table Exporter (`export_phase1_cases_latex_table`)**:
  - Produces publication-grade [`docs/paper/phase1_cases_table.tex`](file:///home/cspark/Work/projects/mobo-linac/docs/paper/phase1_cases_table.tex).

### 3. CLI & Production Script Upgrades
- **Unified CLI (`src/mobo_linac/cli/commands/run.py` & `src/mobo_linac/cli/__init__.py`)**:
  - Added `--suite option2` and `--case [all|balanced|high_brightness|low_energy_spread|x_dominant|y_dominant]` to `mobo-linac run-scalarized`.
  - Added dedicated subcommand `mobo-linac run-scalarized-suite`.
- **Standalone Production Runner (`scripts/run_scalarized_suite.py`)**:
  - Added direct command-line executable for running the Option 2 suite.
- **Phase 1 Script (`scripts/run_scalarized_bo.py`)**:
  - Added `--suite`, `--case`, and `--resume` flags.
- **Full Production Pipeline (`scripts/run_full_production.sh`)**:
  - Upgraded Step 2 to execute Option 2 suite (`--suite option2 --case ${P1_CASE}`).
  - Added `--p1-case CASE` CLI flag to optionally select a single case or `all` (default: `all`).

### 4. Manuscript & Reproduction Integration
- **Figure & Table Generation (`scripts/generate_paper_figures.py`)**:
  - Added automated detection and export of `Table 3: Phase 1 Option 2 cases LaTeX table` to [`docs/paper/phase1_cases_table.tex`](file:///home/cspark/Work/projects/mobo-linac/docs/paper/phase1_cases_table.tex).
- **Manuscript Text (`docs/paper/main.tex`)**:
  - Updated Section 4.1 to formally introduce the Option 2 five-archetype scalarized formulation.
  - Added `\input{phase1_cases_table}` displaying the multi-case performance breakdown.
  - Successfully compiled [`docs/paper/main.pdf`](file:///home/cspark/Work/projects/mobo-linac/docs/paper/main.pdf) with `pdflatex`.

---

## 4. Verification & Testing

1. **Unit Test Suite for Scalarized Suite (`tests/test_scalarized_suite.py`)**:
   - Tested Option 2 definitions, weight sum unity, single case retrieval, and invalid case error handling.
   - Tested mock multi-case execution with `CliMockEvaluator`, verifying case subdirectories, merged root files, `cases_summary.csv`, and LaTeX table export.
   - Tested CLI argument parsing for `--suite` and `--case`.
   - **Result**: `4 passed in 44.52s`.

2. **Full Paper Outputs Test Suite (`tests/test_paper_outputs.py`)**:
   - Ran all 47 tests verifying consistency across Phase 1, Phase 2, and Phase 3 data, tables, and figures.
   - **Result**: `47 passed in 32.07s`.

3. **End-to-End Paper Reproduction Pipeline (`scripts/reproduce_paper.sh`)**:
   - Executed full reproduction script:
     - Generated Figures 1, 2, 3, 4
     - Generated Tables 1, 2, and Table 3 (`phase1_cases_table.tex`)
     - Passed manuscript pre-flight consistency check
     - Compiled [`docs/paper/main.pdf`](file:///home/cspark/Work/projects/mobo-linac/docs/paper/main.pdf) (8 pages, zero compilation errors).
   - **Result**: Complete success with exit code 0.
