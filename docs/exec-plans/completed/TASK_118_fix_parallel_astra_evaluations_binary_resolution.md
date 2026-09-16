# TASK_118: Fix Parallel ASTRA Evaluations and Binary Resolution

## 1. Issue Description
Running `pytest tests/test_parallel_evaluation.py -k test_real_parallel_astra_evaluations` failed with:
```text
FAILED tests/test_parallel_evaluation.py::test_real_parallel_astra_evaluations - AssertionError: assert 'failed' == 'success'
```
Inspecting the evaluation candidate result dictionary revealed:
```text
'error': 'ERROR: Command does not exist:/home/cspark/Work/projects/mobo-linac/bin/astra'
'status': 'failed'
```

## 2. Root Cause Analysis
1. **Missing Local Binaries in Git Workspace**:
   - The repository's `.gitignore` properly excludes binary executables (`bin/*`, with `!bin/.gitkeep`).
   - The pre-compiled ASTRA executables (`astra`, `generator`, `PAstra`, etc.) were present in the local installation (`/home/cspark/Work/simulation_codes-working/lume-astra/bin/`) but had not been populated in the workspace `./bin/` directory.
2. **Inflexible Binary Fallback in `mobo_linac.astra.runner`**:
   - The fallback logic in [`runner.py`](file:///home/cspark/Work/projects/mobo-linac/src/mobo_linac/astra/runner.py) previously assigned:
     ```python
     os.environ["ASTRA_BIN"] = str(_local_astra) if _local_astra.exists() else str(_PROJECT_ROOT / "bin" / "astra")
     ```
   - When `_local_astra.exists()` was False, it unconditionally set `ASTRA_BIN` to `.../bin/astra` (which did not exist), bypassing `PATH` discovery (`shutil.which`) and preventing `lume-astra` from finding `astra` on the system.
3. **Integration Test Precondition Guard**:
   - `test_real_parallel_astra_evaluations` in [`tests/test_parallel_evaluation.py`](file:///home/cspark/Work/projects/mobo-linac/tests/test_parallel_evaluation.py) only checked for template data files (`gun.dat`, `astra.in`) but did not verify the availability of the ASTRA binary, leading to a hard assertion failure rather than a clean test skip if the executable is missing.
   - The evaluation timeout was set to 30 seconds, which is tight for tracking 10,000 particles through the full 16.2 m lattice (~70–90 seconds per evaluation).

## 3. Implementation Details

1. **Populate Local `./bin/` Executables**:
   - Installed pre-bundled local ASTRA executables into `./bin/`:
     - `astra`, `generator`, `PAstra`, `pastra`, `fieldplot`, `lineplot`, `postpro`
   - Verified executable permissions (`chmod +x bin/*`).

2. **Hierarchical Executable Resolution (`mobo_linac.astra.runner`)**:
   - Implemented `resolve_executable_path(env_var, binary_name, ...)` providing resilient hierarchical discovery:
     1. Valid explicit environment variable (`ASTRA_BIN`, `GENERATOR_BIN`).
     2. Local project directory (`$PROJECT_ROOT/bin/<binary>`).
     3. System `PATH` search via `shutil.which`.
     4. Known fallback installation paths (`~/Work/simulation_codes-working/lume-astra/bin/<binary>`).
     5. Default project `./bin/<binary>` reference.
   - Automatically synchronizes `os.environ` so child processes and `lume-astra` commands reference valid executables.

3. **Robust Integration Test Guards & Headroom**:
   - Updated [`tests/test_parallel_evaluation.py`](file:///home/cspark/Work/projects/mobo-linac/tests/test_parallel_evaluation.py):
     - Added binary availability check to skip gracefully if neither `ASTRA_BIN` nor system `PATH` has `astra`.
     - Increased `timeout` parameter from 30s to 300s to support 10,000-particle tracking.
     - Added informative failure messages showing `res.get('error')`.
   - Updated [`tests/test_astra_workdirs.py`](file:///home/cspark/Work/projects/mobo-linac/tests/test_astra_workdirs.py) with identical binary check and 300s timeout.

## 4. Verification

1. **Targeted Integration Test**:
   ```bash
   pytest tests/test_parallel_evaluation.py -k test_real_parallel_astra_evaluations -v -s
   ```
   - **Result**: `PASSED` (2 parallel ASTRA simulations completed successfully, tracking 10k particles to 16.2 m, generating valid manifests and objective metrics).

2. **Isolated Workdir Concurrency Test**:
   ```bash
   pytest tests/test_astra_workdirs.py -v
   ```
   - **Result**: `7 passed in 138.90s` (including `test_real_astra_isolated_run`).

3. **Unit Test Suite**:
   ```bash
   pytest tests/test_parallel_evaluation.py -m "not integration" -v
   ```
   - **Result**: `5 passed, 1 deselected in 1.81s`.

4. **Documentation & Config Sync**:
   ```bash
   python scripts/verify_docs_sync.py
   ```
   - **Result**: `SUCCESS: All documentation tables and web page parameters are 100% synchronized!`.
