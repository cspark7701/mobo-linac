# Task Completion Summary: Task 153

## Summary
Implemented TASK_27 from `docs/05_refactor_tasks/`. Constraint configuration is now generated from the diagnostic channel registry, each load validates once, exit-plane geometry has its own section, acquisition names come from one enum, provenance is a declared attribute, and the duplicate configuration file was removed.

## Key Changes
- **Channel-driven constraints**:
  - `DiagnosticChannel` declares its bound attribute names, defaults (`lower_default`/`upper_default`) and `description`.
  - `ConstraintsConfig` is generated from the registry with `make_dataclass`, keeping the same field names and defaults.
  - Field rules (`exclusiveMinimum` from the physical minimum, `maximum` from the physical maximum), the generic lower ≤ upper check and the Markdown constraint rows all derive from the channels.
  - The invalid-escape f-strings were removed; `python -W error -c "import mobo_linac.config"` succeeds.
- **Validate once**:
  - Every configuration class has `validate()` (fields, then relations) and `check_relations()`.
  - `config_from_dict` validates the raw tree's fields once, constructs, then checks relations once.
  - The types-only pre-pass, the manual checks duplicating field rules and the re-validation in `get_parameter_bounds_tensor` were removed.
  - The dataclass schema is cached.
- **`tracking` section**: `TrackingConfig(z_stop_m, z_loss_tolerance_m)` replaces the exit-plane fields in `execution`. `migrate_legacy_layout` moves archived values on load.
- **Nominal profile**: the top-level `constraints` section is the nominal profile. A redundant `sensitivity_profiles.nominal` identical to it is dropped on load; a different one is rejected. `publication_200MeV.yaml` no longer repeats it.
- **Optional sections**:
  - `benchmark:` (a `BenchmarkConfig`) supplies run-benchmark defaults; explicit arguments still override. The publication configuration declares it.
  - `perturbations:` is validated through `PerturbationSpecification.from_dict(...).validate_for(config)` and used by robustness when present.
- **Acquisition enum**: `mobo_linac.campaign_options` holds the `Acquisition` enum, `MULTIOBJECTIVE_ACQUISITIONS`, `OPTIMIZATION_MODES` and `decode_acquisition`, which maps the legacy `scalarized_qLogNEI` alias. The configuration schema, CLI choices, checkpoint validation, the acquisition factory error and tuning defaults all use it.
- **Moved helpers**:
  - `normalize_scalar_weights`, `resolve_campaign_options` and `validate_campaign_options` moved to `campaign_options`.
  - `validate_evaluation_settings` moved to `execution.requests`, with the `SOURCE_SETTINGS` name list.
- **Provenance**: `MoboConfig.source_path` is a declared `ClassVar` attribute, never serialized. It replaces the monkey-patched `resolved_path`; `config_source.json` keeps its key.
- **Display-only metadata**: labels and display units are marked as display-only. `MoboConfig.scientific_dict()` excludes them, and checkpoint compatibility (now also covering `tracking`) uses it, so archived checkpoints without labels still resume.
- **Removed duplicate file**: `configs/publication.yaml` was deleted (it was identical to `mobo_200MeV.yaml` apart from the description) and dropped from the default search order.

## Acceptance Criteria
- [x] A synthetic eighth constraint channel needs only a registry entry and YAML values. Tested in a subprocess: the field, schema rule, documentation row and validation all follow.
- [x] `python -W error -c "import mobo_linac.config"` succeeds (tested).
- [x] Each load validates fields once and relations once (call-count test).
- [x] Existing YAML files and archived layouts load (exit plane in `execution`, redundant nominal profile) and serialize to the new layout (tested).

## Validation Results
Relevant modules pass:
- config (96)
- checkpoint/resume (65)
- CLI (43)
- benchmark and benchmark campaign
- physics specification and constraints
- robustness, workdirs and parallel evaluation
- configuration boundaries, docs sync and scalarized suite
- GP/acquisition and surrogate pipeline
- package layout and candidate evaluator
- run data, paper outputs and visualizations
- result serialization, verification, durable I/O and LaTeX

No ASTRA campaign, push or remote query was performed.

## Scope and Limitations
- All thresholds, nominal values and defaults are numerically identical.
- Configuration dataclasses remain mutable: callers that modify a configuration in memory call `validate()` at their boundary. Freezing them would change many call sites and is left out.
- The repository `configs/` fallback in default resolution is unchanged; packaging of configuration data is addressed in TASK_38.

## Status
Completed.
