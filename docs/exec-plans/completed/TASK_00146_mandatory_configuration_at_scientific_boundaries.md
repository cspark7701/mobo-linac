# Task Completion Summary: Task 141

## Summary
Implemented TASK_15 from `docs/05_refactor_tasks/`. Scientific APIs now take the campaign configuration (or an explicit `ResultSchema`). They no longer fall back silently to the six-variable, three-objective 200 MeV layout or load a default YAML from disk.

## Key Changes
- **Schema boundary**: `ResultSchema.from_config(None)` raises `TypeError`. A named `legacy_200MeV_schema()` factory is the only compatibility layout for archived pre-schema artifacts. The schema also carries the configured empty-data reference (`empty_reference`), replacing the table of hard-coded legacy reference values in `compute_reference_point`.
- **Removed constants**: `DEFAULT_OBJECTIVE_NAMES`, `EXPLICIT_OBJECTIVE_NAMES`, `PARAMETER_NAMES`, `DESIGN_VAR_COLUMNS`, `PHYSICAL_OBJ_COLUMNS`, `MODEL_OBJ_COLUMNS`, `DEFAULT_ENGINEERING_SCALES`, `DEFAULT_REPORTING_SCALES` and the hidden `DEFAULT_REPORTING_REF_POINT_MODEL_NORM`.
- **Required configuration**: these now require the configuration and never call `load_config()` implicitly:
  - transforms, objective extraction and the ASTRA parser;
  - `ConstraintEvaluator` and the BoTorch constraint functions;
  - `SliceObjective(num_objectives)`;
  - `HypervolumeTracker` and the reporting normalizations, which now require explicit scales and references;
  - result data frames, training tensors, the journal, the artifact writer and candidate loading;
  - `create_evaluation_result`, metric deltas, candidate analyses, robustness and verification;
  - ASTRA parameter mapping and `run_astra_eval`.
- **ASTRA mapping**: the default six-parameter namelist mapping has been removed; parameters are always mapped through the configured design variables.
- **Objective-agnostic parser and mock**: the parser recognizes any configured objective statistics, and still records archived diagnostic copies when the historical statistics are present. `MockBatchEvaluator(config=...)` produces synthetic values for every configured objective; the historical names keep their previous values.
- **Benchmarks**: `BenchmarkConfig.reporting_ref_point` defaults to 1.5 normalized units *per configured objective* via `resolved_reporting_ref_point()`, instead of a fixed three-element list.
- **Interim plotting**: plotting modules that still draw the archived layout bind columns through the explicit legacy schema. TASK_24 replaces these functions.
- **Other updates**: tests, the validation script, CLI mock construction and the comparison notebook now pass the configuration explicitly. New `tests/test_configuration_boundaries.py` covers:
  - a five-variable, four-objective configuration (including a maximized objective) running unconstrained, constrained and scalarized mock campaigns end to end, with exports and summaries;
  - a check that importing the library never loads a default configuration;
  - benchmark reference sizing.

## Acceptance Criteria
- [x] No hard-coded six-variable or three-objective defaults remain outside the named legacy factory; plotting uses it explicitly until TASK_24.
- [x] Library functions raise clear errors when the scientific configuration is missing.
- [x] A four-objective, five-variable synthetic configuration runs a mock campaign, export and report without code edits.
- [x] The archived 200 MeV layout is reproduced exactly by `legacy_200MeV_schema()`, and equals the schema derived from `configs/mobo_200MeV.yaml`.

## Validation Results
- Used the `linac-opt` environment with `PYTHONPATH=src` and one BLAS thread per process. Ran every unit test module as its own pytest process (integration tests excluded).
- All modules pass: 38 existing modules plus the new boundary module. Before the test updates, the first full run showed 237 failures and 19 errors, all from implicit-configuration call sites; those were then updated.
- No production ASTRA campaign was run, and no push or remote workflow query was performed.

## Scope and Limitations
- Beam physics, thresholds, units, signs, seeds and the archived output formats are unchanged. The column order of exported result tables now follows the canonical diagnostic layout, with transmission before particle counts; columns are read by name.
- Robustness still requires the six canonical 200 MeV design names until TASK_18 makes perturbations configuration-driven.

## Status
Completed.
