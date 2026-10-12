# Task Completion Summary: Task 181

## Summary
Resolved the reported CUDA failures in acquisition proposals and normalized hypervolume reporting. The acquisition comparison, tuning, CLI mock workflows, and notebook campaign fixtures shared the acquisition placement failure.

## Key Changes
- `src/mobo_linac/acquisition/mobo.py`: move the constructed acquisition to the model device. BoTorch 0.12.0 creates CPU bookkeeping buffers (`cache_pending`, `_max_iep`, and `incremental_nehvi`) even with a CUDA model. Construction now aligns those buffers before the proposal placement check, retaining the existing check and isolated CPU fallback behavior.
- `src/mobo_linac/metrics/front.py`: honor the supplied observation tensor's dtype and device for tensor reference inputs as well as sequences. Existing CPU reference tensors now follow CUDA observations.
- `tests/test_gp_and_acquisition.py`: test all four supported multi-objective acquisition constructors on CPU and CUDA, assert complete module placement, and evaluate finite acquisition values.
- Beam physics, optimization definitions, and reporting references were not changed.

## Validation Results
- Used the existing `linac-opt` environment: PyTorch 2.5.0+cu124, BoTorch 0.12.0, with CUDA available.
- Acquisition, reporting, CLI mock workflow, and notebook tests: 56 passed; four notebook executions initially failed because the machine's registered `python3` kernel lacked BoTorch. The original acquisition fixture errors were resolved.
- Executed all five notebook regression functions against the generated mock campaigns with a temporary `python3` kernelspec pointing to the project interpreter: all five passed. This validation changed no installed kernels or notebooks.
- Device-policy, hypervolume, and Pareto tests: 28 passed.
- All six originally reported failing tests passed, including both CUDA reporting dtypes; all five originally failing notebook cases executed successfully with the project interpreter.
- Ruff and `git diff --check` passed.
- No real ASTRA simulations, Git pushes, or remote workflow queries were performed. The entire test suite was not rerun.

## Status
Completed.
