# Task Completion Summary: Task 154

## Summary
Implemented TASK_28 from `docs/05_refactor_tasks/`. Campaign checkpoints now use a typed, nested v3 schema, with explicit v1→v2→v3 migration, no dictionary-style access shims, one checkpoint discovery function and a staged resume validator.

## Key Changes
- **`io/checkpoint.py`** (new) groups the state into records whose fields are all required at construction:
  - `CampaignSpec`: identity and plan.
  - `RngState`: torch, NumPy, Python and CUDA generator states, with `capture()`, `validate()` and `restore()`.
  - `ProgressState`: initial design, Sobol position, batch membership and timing.
  - `MetricState`: reporting reference, scales, metric history and hypervolumes.
  - `ProposalState`: proposal history and the pending batch.
  - `CheckpointState`: iteration, results, config, the five records, model reference and migration notes. `checkpoint_file` and `migrated_from` are runtime-only.
- **Migration and decoding**:
  - `migrate_v1_to_v2` holds the earlier v1 inference.
  - `migrate_v2_to_v3` groups the flat fields and rejects unknown legacy keys.
  - `CheckpointState.from_dict` migrates archived payloads and rejects unknown v3 keys and section fields.
  - `__getitem__`, `__contains__` and `get` were removed.
- **Saving**: `save_run_checkpoint(path, state)` takes the typed object; the 14-parameter signature and the `campaign_state` splat are gone. The runner builds the snapshot explicitly from typed records.
- **Discovery**: `find_checkpoint` (documented search order) and `run_directory` replace the separate resolutions in `load_run_checkpoint`, `campaigns/recovery.py` and the runner.
- **Staged resume**: `prepare_resume_state` now runs `check_configuration_compatibility`, `migrate_legacy_v1_state` (gaps that need the configuration), `validate_structure` and `validate_consistency`.
- **Device and RNG**: device canonicalization and the CUDA RNG topology check moved from a nested runner function to `campaigns.state.resolve_resume_device`. RNG validation and restoration live on `RngState`.
- **Version checks**: checks against the archived version use `migrated_from` (for example, best-effort v1 resumes).
- **Import moves**: `CheckpointState`, `save_run_checkpoint` and `load_run_checkpoint` moved from `io.results` to `io.checkpoint`, and `mobo_linac.io` re-exports them.

## Acceptance Criteria
- [x] `CheckpointState` has no `__getitem__`/`get`; all callers use attributes (tested).
- [x] Building a snapshot record with a missing field fails at construction (`TypeError`, tested).
- [x] v1 and v2 payloads migrate to identical v3 objects (tested). Resumed mock campaigns still match uninterrupted runs: partial-batch recovery, commit interruption and legacy v1 resume tests pass.

## Validation Results
Relevant modules pass:
- result serialization (29, including new schema, migration and discovery tests)
- durable I/O and checkpoint/resume (65)
- CLI (43)
- parallel evaluation, GP/acquisition and scalarized suite
- benchmark campaign and config
- package layout and configuration boundaries

No ASTRA campaign, push or remote query was performed.

## Scope and Limitations
- Archived v1/v2 checkpoints remain resumable through migration; new checkpoints are written as v3.
- The records are ordinary (mutable) dataclasses because legacy migration fills gaps in place; validation runs before any resume side effect.

## Status
Completed.
