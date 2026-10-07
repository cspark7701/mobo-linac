# Task Completion Summary: Task 131

## Summary
Implemented Task 07 from `docs/05_refactor_tasks/`: separate logical evaluation identities from immutable attempt identities, preserve attempt provenance outside disposable simulation workdirs, and archive independent verification reruns and reports.

## Key Changes
- **Workdirs and reservations**: Each runner invocation receives a fresh UUID attempt directory under `work/<eval_id>/<attempt_id>/`. Workers generate independent identities for every retry. Exclusive directory and JSON creation reject accidental reuse, including an explicit attempt identity whose workdir was already cleaned. Concurrent invocations sharing a logical evaluation remain isolated. Run, evaluation, and attempt path components reject traversal.
- **Retained provenance**: `provenance/<eval_id>/<attempt_id>/` retains a start record, effective input copies before execution, input copies after execution, and a final versioned manifest. Snapshots dereference symlinks and flush retained files/directories. Manifests record parameters, overrides, status, timestamps, input/output hashes, and the resolved executable path/hash when available. Preparation failures receive final manifests; provenance capture failures mark the evaluation failed and retain the workdir.
- **Accepted result links**: Typed evaluation results retain the accepted attempt ID, manifest path, and worker retry history. CSV/JSON exports, streaming journals, and checkpoint result payloads preserve these links. Existing logical evaluation identities, candidate ordering, and journal-based resume remain intact. New metadata names are reserved against custom schema collisions.
- **Cleanup and compatibility**: Successful cleanup removes only the exact attempt workdir after its final manifest exists. Provenance remains. Legacy manifests are readable through an exact file or manifest-containing directory; old records receive unknown attempt links. Cleanup of a legacy directory with a manifest first preserves its manifest and files under a dedicated legacy provenance directory. Existing historical archives are not automatically migrated or rewritten.
- **Verification archives**: Independent reruns receive unique record directories. Pipeline and class verification share session creation/report export helpers and retain CSV, JSON, and LaTeX reports under `verification_runs/verification_<uuid>/`. Returned paths identify immutable sessions; root report filenames remain compatibility views of the latest completed report. Actual rerun checksums come from the retained attempt manifest.
- **Documentation and tests**: README and simulation guide describe the attempt/provenance layout, cleanup, compatibility, and verification reports. Tests cover failed/successful retry isolation, planted stale output, concurrent logical identities, reuse rejection, preparation/audit failures, symlink snapshot independence, serialization, and repeated pipeline/class verification. An existing verifier test mock now supplies the beam diagnostics required by the established validity contract.

## Acceptance Criteria
- [x] A failed first attempt and successful retry retain separate inputs, outputs, and manifests.
- [x] Stale output planted in the failed attempt is absent from the fresh successful attempt and its output hashes.
- [x] Repeated verification preserves earlier rerun records and report sessions.
- [x] Successful cleanup retains input snapshots, hashes, manifests, and accepted result links for audit.
- [x] Exact legacy manifest paths and legacy evaluation records remain readable.

## Validation Results
Used `/home/cspark/Work/simulation_codes-working/miniforge3/envs/linac-opt/bin/python` with `OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1` and source-tree `PYTHONPATH`.

- Broader affected regression command: `PYTHONPATH=/home/cspark/Work/projects/mobo-linac/src python -m pytest tests/test_astra_workdirs.py tests/test_parallel_evaluation.py tests/test_pareto_verification.py tests/test_astra_parser.py tests/test_result_serialization.py tests/test_evaluation_result.py tests/test_checkpoint_resume.py tests/test_candidate_evaluator.py tests/test_robustness_analysis.py tests/test_cli.py tests/test_objectives.py tests/test_reporting_metrics.py tests/test_parameter_mapping.py tests/test_package_layout.py -m 'not integration' -q --tb=short` — **197 passed, 1 skipped, 2 deselected**, 73.07 seconds.
- Workdir checks including two additional snapshot/audit-failure regressions: `python -m pytest tests/test_astra_workdirs.py -m 'not integration' -q --tb=short` — **16 passed, 1 deselected**, 1.91 seconds.
- Initial expanded checks found a missing required iteration in the new checkpoint fixture; corrected it. The first broader run found an older verification mock missing required diagnostics; updated the mock observations without relaxing production validity checks. Final checks passed.
- CUDA continuation was skipped because CUDA is unavailable. The two real ASTRA integration tests were excluded. Simulation retry tests used a stub simulator and temporary directories; no production campaign or archived output was modified.
- `git diff --check` passed. No git push or remote workflow query was performed. These results cover affected regressions, not the entire repository suite.

## Scope and Limitations
- Nominal beam physics, configured objective definitions/units/signs, thresholds, optimization seeds, and archived outputs are preserved. UUID allocation does not consume optimizer random-number state.
- Provenance adds retained disk use for input snapshots, including static maps/distributions. Requested successful cleanup deletes generated output bytes while preserving their hashes and input evidence; full output retention still requires disabling cleanup.
- Executable hashes are recorded when a file can be resolved, without invented hashes for unknown executables. This does not archive executable bytes or certify a complete software environment.
- Abruptly interrupted attempts may have only a start record or partial snapshots. They cannot become accepted records without a completed evaluation. Existing checkpoint/journal reconciliation continues to govern resume.
- Legacy records without attempt evidence remain unknown rather than inferred from the newest workdir. Legacy cleanup refuses to discard an evaluation containing child directories; explicit attempt cleanup is required.
- Root verification reports are replaceable compatibility views; archived session paths and record links provide the audit identity.
- General configured verification execution and lossless robustness overrides remain separate Tasks 09 and 08. This task does not change their physics or metric semantics.
- `docs/05_refactor_tasks/` is ignored by `.gitignore`; its local task/index completion edits are absent from the ordinary git file list.

## Status
Completed.
