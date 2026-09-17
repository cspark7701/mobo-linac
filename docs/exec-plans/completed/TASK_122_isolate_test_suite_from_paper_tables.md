# TASK_122: Isolate Test Suite Execution from Publication Paper Tables

## 1. Motivation & User Request
The user reported:
> "pytest modify docs/paper/phase1_cases_table.tex. I do not want it"

Running `pytest tests/test_scalarized_suite.py` was unintentionally modifying [`docs/paper/phase1_cases_table.tex`](file:///home/cspark/Work/projects/mobo-linac/docs/paper/phase1_cases_table.tex), replacing real production linac data (176 evaluations, 1.1% feasibility) with mock test fixtures (2 cases, 6 evaluations, 100.0% feasibility).

---

## 2. Root Cause Analysis
In [`src/mobo_linac/campaigns/scalarized_suite.py`](file:///home/cspark/Work/projects/mobo-linac/src/mobo_linac/campaigns/scalarized_suite.py) inside `run_scalarized_suite()`:
```python
# Old implementation:
paper_tab = Path("docs/paper/phase1_cases_table.tex")
if Path("docs/paper").is_dir():
    export_phase1_cases_latex_table(base_out / "cases_summary.csv", paper_tab)
```
Whenever `run_scalarized_suite()` executed—even when invoked with a temporary test directory (`tmp_path`) and a mock evaluator—it checked whether the relative directory `docs/paper/` existed in the current working directory. Because the test suite was executed from the repository root, `docs/paper` always existed, causing `run_scalarized_suite()` to silently overwrite the live publication LaTeX table with synthetic test artifacts.

---

## 3. Implementation Details

### 1. Decouple Suite Run from Publication Directory
In [`src/mobo_linac/campaigns/scalarized_suite.py`](file:///home/cspark/Work/projects/mobo-linac/src/mobo_linac/campaigns/scalarized_suite.py):
- Removed the hardcoded check and write to `docs/paper/phase1_cases_table.tex`.
- Restricted default table export strictly to the run's own output directory (`base_out / "phase1_cases_table.tex"`).
- Added an optional parameter `export_paper_table_dir: Optional[Union[str, Path]] = None`, which only writes to an external directory if explicitly requested by caller scripts.
- Preserved publication table generation in [`scripts/generate_paper_figures.py`](file:///home/cspark/Work/projects/mobo-linac/scripts/generate_paper_figures.py), which explicitly uses `--tables-dir` targeting production data.

### 2. Restore Authentic Production Data in Manuscript Table
Restored [`docs/paper/phase1_cases_table.tex`](file:///home/cspark/Work/projects/mobo-linac/docs/paper/phase1_cases_table.tex) using authentic production metrics from `results/full_production/phase1_scalarized/cases_summary.csv`:
```latex
\begin{table}[t]
\centering
\caption{Phase 1 Scalarized Bayesian Optimization multi-case summary across operational linac archetypes.}
\label{tab:phase1_cases}
\resizebox{\columnwidth}{!}{%
\begin{tabular}{llcccccc}
\toprule
\textbf{Case} & \textbf{Operating Mode} & $\mathbf{w} = [w_x, w_y, w_E]$ & \textbf{Evals} & \textbf{Feas. (\%)} & \textbf{Min} $\varepsilon_{n,x}$ [$\mu$m] & \textbf{Min} $\varepsilon_{n,y}$ [$\mu$m] & \textbf{Min} $\sigma_E$ [MeV] \\
\midrule
\texttt{balanced} & Balanced Linac Operation & $[0.33, 0.33, 0.33]$ & 176 & 2 (1.1\%) & 2.9102 & 4.9287 & 0.2769 \\
\bottomrule
\end{tabular}}
\end{table}
```

### 3. Add Regression Test Assertion
In [`tests/test_scalarized_suite.py`](file:///home/cspark/Work/projects/mobo-linac/tests/test_scalarized_suite.py):
- Validated LaTeX export inside the isolated test directory (`tmp_path / "test_table.tex"`).
- Added an explicit test assertion confirming that [`docs/paper/phase1_cases_table.tex`](file:///home/cspark/Work/projects/mobo-linac/docs/paper/phase1_cases_table.tex) retains its genuine production evaluation count (`"176"`) and is never touched during test execution.

---

## 4. Verification & Validation

1. **Unit Test Suite Execution**:
   ```bash
   pytest tests/test_scalarized_suite.py
   ```
   Result: **4/4 passed in 24.17s**.
2. **Paper Output Integration Tests**:
   ```bash
   pytest tests/test_paper_outputs.py
   ```
   Result: **47/47 passed in 30.26s**.
3. **Immutability Check**:
   Verified via `git diff docs/paper/phase1_cases_table.tex` that only the authentic production data was restored and subsequent `pytest` runs produced zero modifications to any file under `docs/paper/`.
