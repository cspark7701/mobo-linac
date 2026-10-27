# Task Completion Summary: Task 138

## Summary
Implemented Task 14 from `docs/05_refactor_tasks/`: lazy ASTRA runtime initialization, a typed request/completion boundary, and incremental campaign proposal, storage and reporting service extraction.

## Key Changes
- **Backend initialization**: Importing campaign, analysis, execution or ASTRA helper modules no longer resolves binaries into environment variables, imports the external `astra`/`distgen` runtime, or patches distgen. `initialize_astra_backend()` performs this work inside a real isolated evaluation attempt. The public `Astra` injection seam remains usable by recording simulators. Executable discovery is read-only when called directly; production initialization retains the existing resolution hierarchy.
- **Evaluator contract**: `execution.contracts` defines `RequestEvaluator` and `EvaluationCompletion`, reusing serializable `EvaluationRequest` and scientific `EvaluationResult`. Its shared adapter validates unique canonical identities, parameters and run IDs, preserves ordered returns, streams each completion once, rejects conflicting duplicates and incomplete batches, and retains callback errors even when a backend swallows them. Identity normalization follows existing ASTRA `eval_` naming. Legacy batch evaluators remain supported for parameter-only requests; streaming is an explicit capability rather than signature inspection.
- **Mock and production backends**: Both advertise callback capability. Mock requests retain full settings and metadata before callback publication and identify synthetic execution. Process requests remain pickleable dictionaries; successful attempts, failed attempts, future crashes and submission failures retain the complete submitted request and candidate identity. ProcessPoolExecutor remains the only production parallel backend.
- **Campaign services**: Scalarized and multi-objective proposal implementations move into `campaigns.strategies`, using the same scientific transformations, fitting calls, acquisition budgets and Sobol stream. `campaigns.storage` owns model artifact persistence and durable checkpoint commit cleanup. `campaigns.reporting` owns final plots, required-artifact checks and completion publication. Existing recovery/state and artifact-writer services remain authoritative. Factory injection through the public runner module remains available for existing tests and clients. The runner constructor and `(results, tracker, run_dir)` return tuple are unchanged.
- **Candidate analyses**: Production candidate analysis and batch robustness use the same typed completion boundary. Analysis callbacks receive outcomes as candidates complete; returned outcomes retain request order. Legacy single-candidate callable adapters remain available. Typed EvaluationResult backends are consumed directly rather than reparsed as raw dictionaries.
- **Regression coverage**: A subprocess blocks external simulator imports while importing helpers and running mock campaigns in all three optimization modes, publication analysis, robustness and verification; executable environment values remain unchanged. Tests cover full-request mock callbacks, duplicate/mismatched/conflicting/incomplete completions, reverse completion order, serializable pool failures, typed candidate outcomes and existing recovery behavior.

## Acceptance Criteria
- [x] Mock campaigns and analysis helpers import and run without initializing ASTRA.
- [x] Public runner construction and its return tuple remain compatible.
- [x] Scalarized, constrained and unconstrained modes share storage and evaluator contracts.
- [x] Process workers receive serializable requests and preserve ordered failure records and candidate identities, including pool crashes.

## Validation Results
Used `/home/cspark/Work/simulation_codes-working/miniforge3/envs/linac-opt/bin/python` with `PYTHONPATH=src OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1` and excluded integration tests.

- Backend/layout/mock/parallel/checkpoint/launcher selection: **95 passed, 1 skipped, 1 deselected**, 117.39 seconds. CUDA recovery coverage was skipped on this CPU environment.
- Candidate/CLI/scalarized suite/comparison/verification/robustness selection: **82 passed**, 141.68 seconds.
- Expanded layout/mock/parallel/candidate/launcher/CLI selection: **78 passed, 1 deselected**, 154.19 seconds, including runtime-blocked mock audits, pool submission failures and reporting-reference CLI forwarding.
- Subsequent candidate/robustness/verification/checkpoint selection passed **104 tests**, with one CUDA skip, and found an assertion in the new typed-result test using nonexistent `is_valid`. It was corrected to the established `simulation_valid` field; final focused results are recorded below.
- Final focused layout/mock/parallel/candidate/launcher selection: **42 passed, 1 deselected**, 33.22 seconds. This includes the corrected typed-result assertion, simulator-blocked mock audits, future/submission crashes, and executable-override dispatch.
- Initial identity regressions in recording-simulator analyses were corrected by using the existing named-ID normalization contract.
- `git diff --check` passed. No changes to archived `docs/paper`, `results` or `release` artifacts were present. No production campaign, git push or remote workflow query was performed.

## Scope and Limitations
- Beam physics, configured thresholds, objective units/signs, campaign seeds, acquisition settings and immutable attempt evidence are preserved.
- This is incremental service extraction. The public runner still coordinates state, timing, pending proposals and iteration orchestration. It retains factory aliases as compatibility injection points.
- Legacy batch evaluators must advertise `supports_completion_callback = True` to stream and must implement that callback argument when advertising it. Without the capability, completions are processed on return. Complete overrides/source settings/metadata require a request evaluator. Legacy single-candidate analysis callables retain their compatibility path.
- Environment snapshots taken before a real attempt explicitly identify unset executables as uninitialized. Actual execution commands and hashes belong to attempt manifests.
- No distributed backend, new source-distribution model or simulator physics was added. Tests use mocks and disposable recording simulators, not production optimization.
- The associated production launcher and strategic plan are recorded separately in Task 139. `docs/05_refactor_tasks/` remains ignored; its completion/index updates are local.

## Status
Completed.
