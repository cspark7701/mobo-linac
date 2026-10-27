# TASK_114: Fix AttributeError in plot_pareto_front_comparison for Step 5

## 1. Problem Statement
During Step 5 of the full production simulation pipeline (`scripts/run_comparison_and_verification.py`), the script crashed with:
```
File "/home/cspark/Work/projects/mobo-linac/src/mobo_linac/plotting/pareto.py", line 130, in plot_pareto_front_comparison
    for i, (label, res_list) in enumerate(results_dict.items()):
                                          ^^^^^^^^^^^^^^^^^^
AttributeError: 'list' object has no attribute 'items'
```

## 2. Root Cause
- In [`src/mobo_linac/plotting/pareto.py`](file:///home/cspark/Work/projects/mobo-linac/src/mobo_linac/plotting/pareto.py), the function signature is:
  ```python
  def plot_pareto_front_comparison(
      results_dict: Optional[Dict[str, List[EvaluationResult]]] = None,
      results_p2: Optional[List[EvaluationResult]] = None,
      results_p3: Optional[List[EvaluationResult]] = None,
      output_path: Optional[Union[str, Path]] = None,
  )
  ```
- In [`scripts/run_comparison_and_verification.py`](file:///home/cspark/Work/projects/mobo-linac/scripts/run_comparison_and_verification.py), the function was called with positional arguments:
  ```python
  plot_pareto_front_comparison(
      res_p2 if res_p2 else res_p1,
      res_p3 if res_p3 else res_p1,
      output_path=fig_dir / "pareto_front_comparison.png",
  )
  ```
  Passing `res_p2` as the first argument bound it to `results_dict` as a `list`. When `results_dict.items()` was subsequently invoked on line 130, Python raised `AttributeError: 'list' object has no attribute 'items'`.

## 3. Implementation Details
1. **Defensive Argument Handling in `mobo_linac.plotting.pareto`**:
   - In [`src/mobo_linac/plotting/pareto.py`](file:///home/cspark/Work/projects/mobo-linac/src/mobo_linac/plotting/pareto.py), added check for `isinstance(results_dict, list)`:
     ```python
     if isinstance(results_dict, list):
         if results_p2 is not None and isinstance(results_p2, list):
             results_p3 = results_p2
         results_p2 = results_dict
         results_dict = None
     ```
     This restores full backward-compatibility if callers pass positional lists `(res_p2, res_p3)`.
2. **Explicit Multi-Phase Dictionary in Caller**:
   - In [`scripts/run_comparison_and_verification.py`](file:///home/cspark/Work/projects/mobo-linac/scripts/run_comparison_and_verification.py), updated the invocation to supply a dictionary mapping all available phases:
     ```python
     pareto_comp_dict = {}
     if res_p1:
         pareto_comp_dict["Phase 1 (Scalarized)"] = res_p1
     if res_p2:
         pareto_comp_dict["Phase 2 (Unconstrained)"] = res_p2
     if res_p3:
         pareto_comp_dict["Phase 3 (Constrained)"] = res_p3

     plot_pareto_front_comparison(
         results_dict=pareto_comp_dict if pareto_comp_dict else None,
         output_path=fig_dir / "pareto_front_comparison.png",
     )
     ```
   - This cleanly visualizes Phase 1, Phase 2, and Phase 3 together on the same plot whenever results exist.
3. **Unit Tests**:
   - Extended [`tests/test_visualizations.py`](file:///home/cspark/Work/projects/mobo-linac/tests/test_visualizations.py) with test coverage verifying both the dictionary calling convention and the positional list calling convention.

## 4. Verification
- `pytest tests/test_visualizations.py -v`: All 7 visualization tests passed (100%).
- `python3 scripts/run_comparison_and_verification.py`: Generated `results/full_production/analysis/figures/pareto_front_comparison.png` (400 KB) without errors.
