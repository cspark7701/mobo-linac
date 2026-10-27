# Task Completion Summary: Task 134

## Summary
Implemented Task 10 from `docs/05_refactor_tasks/`: explicit GP observation-noise inputs, verified fit fallback state, structured per-channel outcomes, and separately reloadable model artifacts linked to campaign observation checkpoints.

## Key Changes
- **Noise contract**: Scalar and multi-output factories propagate observation variances in squared model-output units. Precedence is observation tensor, per-output variances, scalar fixed noise, then deterministic relative noise. Tensors must match observation dimensions and contain finite strictly positive values. Per-output lists must cover every output. `measured_fixed` requires explicit noise and `inferred` rejects supplied fixed noise. Input/outcome/bounds validation fails clearly. Standardize continues scaling outcomes and noise together; the nominal deterministic formula and `fixed` alias are unchanged.
- **Separate constraint noise**: `SurrogatePipeline.fit` accepts `train_constraints_var` independently from objective noise and accepts row-aligned training identities. Measured constraint models require their own tensor or explicit scalar noise; objective variances are not silently reused.
- **Fit outcomes and restoration**: `fit_gp_models` retains its model-returning interface and exposes immutable per-channel `FitOutcome` records with optimizer path, errors, and available optimizer status. L-BFGS and Adam each start from the same saved state. The snapshot explicitly includes fixed likelihood noise, which GPyTorch does not include in state_dict. Failed optimization cannot leave mutated parameters/noise in the advertised prior fallback. Finite parameters and posterior predictions are verified; an unusable prior raises. Stale outcomes are cleared before refitting.
- **Pipeline state**: `is_fitted` denotes prediction availability; `is_optimized` distinguishes optimized channels from a verified `restored_prior`. Adam step-limit status remains explicit rather than claiming convergence.
- **Model artifacts**: Added version-1 tensor/state persistence with atomic writes, weights-only loading, CPU-default reconstruction, and unknown-version rejection. Artifacts store original inputs/outcomes/bounds, transform/kernel/likelihood state, supplied output-space and effective standardized noise, fitting evidence, training identities, and campaign metadata. Single/scalarized and objective/constraint pipeline models reload without optimization or simulation.
- **Campaign linkage**: Each fitted proposal saves a uniquely named artifact under `gp_checkpoint/`; pending/completed observation checkpoints separately record its absolute path, SHA-256, and proposal iteration. Training identities identify the observations actually used for that proposal. Metadata records objective schema, scalar weights, and reporting scales. Resume preserves the saved reference and continues its existing observation-based refitting policy. Random-only runs have no model artifact.
- **Documentation and tests**: README documents noise precedence, units/scaling, fallback semantics, artifact loading, checkpoint relationships, and relocation/environment limits. Existing campaign test doubles implement persistence without weakening production behavior. Added heteroscedastic-noise, invalid-noise, parameter/noise mutation restoration, unusable prior, version rejection, objective/constraint prediction roundtrip, explicit pipeline fallback, and real mock-campaign linkage coverage for all three fitted optimization modes.

## Acceptance Criteria
- [x] Heteroscedastic train_Yvar reaches each GP likelihood with the correct outcome-transform scaling; measured_fixed cannot silently select relative noise.
- [x] Nominal deterministic relative noise remains numerically unchanged, including the existing multi-scale regression.
- [x] Injected optimizer failures expose per-channel outcomes and restore verified parameter and fixed-noise snapshots before fallback predictions.
- [x] Reloaded single and pipeline model artifacts reproduce posterior means/variances and constraint probabilities without ASTRA reruns or refitting.

## Validation Results
Used `/home/cspark/Work/simulation_codes-working/miniforge3/envs/linac-opt/bin/python`, source-tree `PYTHONPATH`, and `OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1`.

- Broader command: `python -m pytest tests/test_gp_models.py tests/test_gp_and_acquisition.py tests/test_surrogate_pipeline.py tests/test_checkpoint_resume.py tests/test_benchmark_campaign.py tests/test_result_serialization.py tests/test_reporting_metrics.py tests/test_package_layout.py -q --tb=short -m 'not integration' -k 'not test_compare_acquisition_functions and not test_tune_acquisition_hyperparameters and not test_tune_full_optimization_pipeline'` — **178 passed, 1 skipped, 3 deselected**, 47.62 seconds.
- Final focused command after explicitly snapshotting fixed likelihood noise and adding fallback/version coverage: `python -m pytest tests/test_gp_models.py tests/test_surrogate_pipeline.py tests/test_gp_and_acquisition.py::test_single_gp_artifact_preserves_fallback_predictions tests/test_gp_and_acquisition.py::test_campaign_checkpoint_links_reloadable_model -q --tb=short` — **41 passed**, 10.89 seconds.
- Earlier focused new-contract tests — **14 passed**, 2.85 seconds; real fitted mock-campaign artifact/link tests for scalarized, constrained, and unconstrained modes — **3 passed**, 5.31 seconds.
- Two superseded broad runs were stopped while expensive existing acquisition-tuning comparisons were still running. They are not counted as completed suites. The completed broader suite explicitly excludes those three unrelated tuning benchmarks and includes the existing configurable acquisition-budget and Sobol-fallback regressions.
- Prediction roundtrips cover measured heteroscedastic and inferred objective/constraint likelihoods, and a restored-prior single model. CPU predictions agree within tight floating-point tolerances; training identities, fit outcomes, and effective noise survive reload.
- The CUDA continuation test was skipped because CUDA is unavailable. Mock campaigns use synthetic evaluation results and real GP fitting/persistence, with a deterministic proposal adapter; no ASTRA binary or production campaign is launched.
- `git diff --check` passed. No archived results were rewritten, no git push was performed, and no remote workflow status was queried. This is affected regression coverage, not a claim that the entire repository suite passed.

## Scope and Limitations
- Nominal 200 MeV beam physics, thresholds, objective units/signs, random seeds, and archived outputs are unchanged. Unique artifact filenames use UUIDs independently of scientific random streams.
- Positive noise values remain subject to GPyTorch's existing standardized numerical floor. Saved effective noise reproduces that floor; supplied output-space noise remains separately recorded.
- A verified prior fallback is usable for prediction but is explicitly unoptimized. An Adam step-limit stop is exposed in optimizer_status, and is_optimized indicates an optimizer-produced usable model, not a proof of global optimality or convergence.
- Model artifacts represent proposal training observations, which precede the newly evaluated batch in a completed observation checkpoint. They do not replace evaluation/RNG/recovery checkpoints, automatically accelerate resume, or archive an entire software environment.
- Artifact prediction reproduction assumes compatible PyTorch/BoTorch/GPyTorch versions. Reload defaults to CPU; CPU-to-CUDA equivalence was not tested. Artifact references use absolute paths and need explicit resolution after moving a run. The checkpoint hash records identity; the standalone loader does not implicitly locate or audit a campaign checkpoint.
- The scalarized factory accepts variances for the already scalarized output. No covariance-free rule is invented to project multi-objective measured variances into scalarized noise. Constrained measured campaigns must define constraint noise explicitly rather than silently substituting deterministic noise.
- Artifact persistence supports repository factory-built models with recorded reconstruction metadata; general arbitrary custom GP architectures are outside this task.
- `docs/05_refactor_tasks/` remains ignored; local task/index completion edits do not appear in the ordinary git file list.

## Status
Completed.
