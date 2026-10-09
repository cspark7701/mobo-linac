# Task Completion Summary: Task 158

## Summary
Implemented TASK_32 from `docs/05_refactor_tasks/`. Surrogate settings are now one typed object, fitted state is kept beside the BoTorch modules instead of on them, acquisition construction is table driven, and the optimizer's fallback budgets are configuration recorded in proposal metadata.

## Key Changes
- **`SurrogateSettings`** (frozen, built by `from_config(GpModelConfig)`) holds kernel, noise mode, fixed/relative/minimum noise and per-objective variances. It validates on construction, and `for_output(index)` selects one output's noise.
- **`build_output_gp(train_X, train_Y, bounds, settings, *, train_Yvar, device)`** replaces the misnamed `build_scalarized_gp_model`.
  - Construction is a single `SingleTaskGP` call (`train_Yvar=None` for inferred noise).
  - The `"fixed"` alias is rejected by settings; configurations and archived artifacts migrate it to `deterministic_fixed`.
  - `build_gp_models(..., settings, per_output_noise=...)` builds the model list; constraint models use the scalar noise settings.
- **Fitted state in a side table**: `ChannelRecord` entries (training tensors, settings, effective noise, fit outcome) live in a weak-key side table, read through `channel_record`, `fit_outcomes` and `output_models`.
  - No `artifact_metadata`, `fit_outcomes`, `training_ids` or `campaign_metadata` attribute is assigned on BoTorch/GPyTorch modules.
  - `load_model_artifact` returns a `LoadedSurrogate(model, training_ids, metadata)`.
- **`SurrogatePipeline(bounds, settings, ...)`**:
  - `from_config(config, bounds)` is used by the multi-objective strategy.
  - Artifacts store `asdict(settings)`; archived flat settings (including `fixed`) still load.
  - The model payload format is unchanged.
- **Acquisition**:
  - The constructor table is keyed by the `Acquisition` enum, with one construction call.
  - `ProposalResult` no longer emulates a tuple; strategies use its attributes.
- **`FallbackPolicy`**: the retry/CPU tier budgets and the CUDA batch limit come from new `execution.acqf_retry_*` and `execution.acqf_cuda_batch_limit` fields (defaults equal the former constants). The policy is recorded as `fallback_policy` in proposal metadata, and the CUDA batch limit is applied in one place.
- **Device handling**: device normalization uses `get_device(device)` directly, and model device discovery uses the shared `utils.device.module_device`.

## Acceptance Criteria
- [x] No `artifact_metadata`, `fit_outcomes`, `training_ids` or `campaign_metadata` attributes are assigned on BoTorch/GPyTorch objects (tested on fitted and restored models).
- [x] A new GP setting requires editing only `GpModelConfig`, `SurrogateSettings` (`from_config`) and `build_output_gp`.
- [x] Saved model artifacts from before the change still load. This is tested with an archived flat-settings pipeline artifact using the `fixed` alias; the GP payload format is unchanged.

## Validation Results
Relevant modules pass:
- GP models (21), surrogate pipeline (19), GP/acquisition (26)
- benchmark campaign, checkpoint/resume (65), config
- logger, scalarized BO, configuration boundaries
- package layout, CLI, comparison, visualizations

No ASTRA campaign, push or remote query was performed.

## Scope and Limitations
- Kernels, transforms, noise formulas, acquisition defaults and fallback budgets are numerically identical.
- Proposal metadata gains a `fallback_policy` entry.

## Status
Completed.
