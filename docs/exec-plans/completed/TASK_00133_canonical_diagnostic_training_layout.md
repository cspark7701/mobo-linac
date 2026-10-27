# Task Completion Summary: Task 128

## Summary
Implemented Task 04 from `docs/05_refactor_tasks/`: centralized the seven measured diagnostic channels, removed favorable missing-data defaults, aligned constrained training rows by evaluation identity, and derived feasibility, GP probability, and acquisition constraint indexing from the canonical layout.

## Key Changes
- **`src/mobo_linac/diagnostics.py`**: Added immutable channel specifications with canonical names, aliases, units, configured lower/upper bounds, violation names, and physical observation ranges. Alias normalization preserves absence and invalidity; conflicting aliases cannot become favorable measurements. Shared helpers validate finite numeric observations and expose canonical constraint sides.
- **`src/mobo_linac/constraints.py`**: Derived observed feasibility and eight violation channels from the specifications. Missing/nonfinite/unphysical observations fail feasibility and produce infinite unknown violations. Acquisition output offsets derive from the configured or explicitly supplied objective count; nominal inequality order and thresholds are preserved.
- **`src/mobo_linac/astra/parser.py`**: Removed zero RMS/energy substitutions. Empty or absent arrays remain unobserved, canonical statistics and legacy aliases are supported, and malformed/nonfinite count/transmission data receive explicit invalid statuses. Existing count-based transmission and premature-loss/zero-charge classification remain in place.
- **`src/mobo_linac/evaluation.py`**: Normalized diagnostic aliases at ingestion and required all seven observed channels for new valid evaluations. Invalid supplied values are recorded safely rather than causing conversion errors or favorable defaults. NumPy real numeric observations are accepted. Nominal objectives, thresholds, and physical units are unchanged.
- **`src/mobo_linac/io/results.py` and I/O exports**: Added `TrainingObservations` and `get_training_observations` with stable run/evaluation identities and one selection for design, objective, feasibility, and optional diagnostic matrices. Constrained selection uses complete finite physical observations without imputation. Objective-only training retains finite archived objective records. CSV diagnostic normalization uses the same alias rules.
- **`src/mobo_linac/campaigns/runner.py`**: Uses the shared complete-case selection for constrained GP/acquisition training. Fewer than two complete observations follow the existing Sobol proposal branch. Objective slicing and diagnostic acquisition offsets use the actual objective tensor width.
- **`src/mobo_linac/models/pipeline.py`**: Rejects invalid/misaligned matrices before GP construction. Canonical channel bounds drive the existing analytical Normal CDF formulas. Generic residual constraints explicitly select `constraint_layout="residual"`, removing posterior-width-based interpretation.
- **Tests and documentation**: Extended constraint, surrogate, parser, and transmission tests with missing/nonfinite/conflicting channels, objective reordering/count changes, row identity checks, recording GP inputs, explicit residual interpretation, and parser edge cases. README and simulation guide document the policy; local ignored task documents reflect completion.

## Acceptance Criteria
- [x] Nominal complete observations retain feasibility, violation magnitudes, physical thresholds, units, and analytical probability formulas.
- [x] Missing or nonfinite measurements never become apparently observed favorable values.
- [x] Canonical and legacy aliases normalize consistently; contradictory aliases fail validity.
- [x] Reordered objective definitions and two/three/four-output layouts retain correct constraint indexing.
- [x] Filtered constraint rows remain aligned with design/objective rows and stable evaluation identities.
- [x] Invalid observations fail before GP construction, while measured infeasible observations remain usable training data.

## Validation Results
Used `/home/cspark/Work/simulation_codes-working/miniforge3/envs/linac-opt/bin/python` with `OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1`.

- Initial nominal regression run: **46 passed**, 2.76 seconds.
- Diagnostic/checkpoint/configuration run: **198 passed, 1 skipped**, 23.01 seconds.
- Broader affected run: `python -m pytest tests/test_constraints.py tests/test_surrogate_pipeline.py tests/test_astra_parser.py tests/test_transmission_and_diagnostics.py tests/test_evaluation_result.py tests/test_result_serialization.py tests/test_checkpoint_resume.py tests/test_config.py tests/test_cli.py tests/test_benchmark_campaign.py tests/test_benchmark.py tests/test_scalarized_bo.py tests/test_gp_models.py -q` — **267 passed, 1 skipped**, 66.32 seconds.
- Final diagnostic-focused run after NumPy numeric-input normalization: `python -m pytest tests/test_constraints.py tests/test_surrogate_pipeline.py tests/test_astra_parser.py tests/test_transmission_and_diagnostics.py tests/test_evaluation_result.py tests/test_result_serialization.py -q` — **140 passed**, 3.15 seconds.
- CUDA continuation was skipped because CUDA is unavailable. Tests used mock evaluation data and temporary output directories; no production ASTRA campaign or remote workflow queries were performed.
- `git diff --check` passed. This is affected regression coverage, not a claim that the entire repository suite passed.

## Scope and Limitations
- Nominal beam settings, configured engineering thresholds, objective definitions/signs/units, field maps, source distributions, seeds, and archived simulation/publication artifacts are preserved.
- Constrained training intentionally excludes entire rows with incomplete or invalid diagnostic observations. No per-channel imputation or independently missing-channel GP model is introduced.
- Objective-only selection can retain finite archived objective observations without complete diagnostics; saved validity/feasibility metadata and archives are not rewritten. New incomplete evaluations are invalid.
- Constraint violation infinity denotes an unknown/invalid observation, not a measured finite violation.
- Generic zero-threshold surrogate constraints must explicitly use `constraint_layout="residual"`. Default physical diagnostic layout requires seven measured channels; generic seven-output residuals no longer silently use physical thresholds.
- End-to-end config-derived objective extraction, objective aliases, empty tensor dimensions, scalarization/export conventions, and legacy CSV feasibility contracts remain Task 05 and subsequent tasks.
- `docs/05_refactor_tasks/` remains ignored by the existing `.gitignore`; its local task-status edits do not appear in the ordinary commit file list.

## Status
Completed.
