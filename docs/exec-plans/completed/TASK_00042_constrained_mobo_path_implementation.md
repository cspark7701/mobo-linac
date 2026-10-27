# Task 41 Summary: Real Constrained MOBO Campaign Path Implementation (Codex Task 01)

## Summary

Task 41 implemented a dedicated, mathematically rigorous **Constrained MOBO Campaign Path** (`constrained=True`), making `run-constrained` scientifically distinct from `run-unconstrained`.

## Accomplishments

1. **8 Continuous Constraint Tensor Functions (`src/mobo_linac/constraints.py`)**:
   - Expanded `get_botorch_constraint_functions(config)` to construct all 8 continuous constraint functions ($c_j(Y) \le 0$):
     - $\sigma_x \le 1.0\text{ mm} \rightarrow Y[..., 3] - 1.0\text{e-}3 \le 0$
     - $\sigma_y \le 1.0\text{ mm} \rightarrow Y[..., 4] - 1.0\text{e-}3 \le 0$
     - $\sigma_{x'} \le 1.0\text{ mrad} \rightarrow Y[..., 5] - 1.0\text{e-}3 \le 0$
     - $\sigma_{y'} \le 1.0\text{ mrad} \rightarrow Y[..., 6] - 1.0\text{e-}3 \le 0$
     - $\sigma_z \le 1.0\text{ mm} \rightarrow Y[..., 7] - 1.0\text{e-}3 \le 0$
     - $E_{\text{kin}} \ge 195.0\text{ MeV} \rightarrow 195.0\text{e}6 - Y[..., 8] \le 0$
     - $E_{\text{kin}} \le 205.0\text{ MeV} \rightarrow Y[..., 8] - 205.0\text{e}6 \le 0$
     - $\text{transmission} \ge 0.90 \rightarrow 0.90 - Y[..., 9] \le 0$
2. **Constraint Tensor Extraction (`src/mobo_linac/io/results.py`)**:
   - Added `get_constraint_tensors(results, exclude_invalid=True)` to extract $(N, 7)$ diagnostic metrics $[\sigma_x, \sigma_y, \sigma_{x'}, \sigma_{y'}, \sigma_z, E_{\text{kin}}, \text{transmission}]$ from all numerically valid ASTRA evaluations (`res.simulation_valid == True`).
3. **Multi-Output Objective Slicing & Acquisition (`src/mobo_linac/acquisition/mobo.py`)**:
   - Added `SliceObjective(IdentityMCMultiOutputObjective)` to slice $Y[..., :3]$ (the 3 objectives) for hypervolume improvement while evaluating soft feasibility weighting over joint 10-channel models.
   - Updated `build_acquisition_function` to accept `constraints` and `objective` kwargs, passing them directly to BoTorch acquisition constructors (`qLogNEHVI`, `qLogEHVI`, `qNEHVI`, `qEHVI`).
4. **Constrained Campaign Runner Workflow (`src/mobo_linac/campaigns/runner.py`)**:
   - Updated `MoboCampaignRunner` to explicitly distinguish constrained vs unconstrained execution:
     - **Unconstrained (`constrained=False`)**: Fits objective surrogates (`ModelListGP`) and constructs standard $q\text{LogNEHVI}$ on 3 objectives.
     - **Constrained (`constrained=True`)**: Fits objective surrogates AND constraint surrogates using `SurrogatePipeline.fit(train_X, train_Y, train_constraints)`, builds a joint 10-output `ModelListGP`, and constructs feasibility-weighted constrained $q\text{LogNEHVI}$ with BoTorch tensor constraints.
5. **Unit Tests & Verification**:
   - Added `test_constrained_acquisition_construction()` in `tests/test_gp_and_acquisition.py`.
   - Updated `test_get_botorch_constraint_functions()` in `tests/test_constraints.py` for 8 constraint functions.
   - Executed `pytest -v -m "not integration"`: **81/81 unit tests passed** in 14.00s.

## Status

**Completed**. Real constrained MOBO campaign path implemented, unit tests passed, and execution summary saved.
