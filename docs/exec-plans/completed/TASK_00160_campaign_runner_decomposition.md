# Task Completion Summary: Task 155

## Summary
Implemented TASK_29 from `docs/05_refactor_tasks/`. Plan resolution, resume merging and loop execution are now separate in `MoboCampaignRunner`, global random and dtype changes are confined to `run()`, proposal strategies are typed objects, and ASTRA template inputs no longer depend on the working directory.

## Key Changes
- **Plan resolution**:
  - The constructor records explicit requests in a frozen `CampaignOverrides` (replacing eleven `_requested_*` shadows).
  - `_resolve_plan` fills omitted options from `config.campaign` and validates them. The resume-with-qLogNEI mode inference is now an explicit, documented step.
  - `_resolve_run_directory` derives the run identity from the directory name.
- **Resume merge**: `campaigns.state.merge_with_checkpoint(state, overrides, config)` returns the resumed `CampaignSpec` (batch size, workers and iteration target), or raises one error listing every incompatibility. The runner applies the spec with `_apply_spec`.
- **No global side effects at construction**: `campaign_numeric_scope(seed)` seeds torch, NumPy and Python random and sets double precision only for the duration of `run()`. The previous default dtype is restored; generator state continues as campaign state, matching the checkpoint.
- **`CampaignLoop`** holds explicit session state and has these steps, each under 60 lines:
  - `prepare_outputs`
  - `restore` / `_restore_session`
  - `run_initial_design`
  - `propose`
  - `evaluate`, which streams completions to the journal
  - `record_iteration`, `export`, `persist_model`, `snapshot` and `commit`

  No `nonlocal` remains.
- **Strategies**: a `ProposalStrategy` protocol with `ScalarizedProposal` and `MultiObjectiveProposal`, built by `make_strategy`, replaces the string-keyed dependency dictionary. Dependencies are imported in `campaigns.strategies`. Optimizer budgets come from a typed `AcquisitionSettings.from_execution`, and the `getattr` defaults are gone.
- **Evaluation identities**: they use the shared `format_eval_id`, in both the runner and resume validation.
- **Template directory**: the new `execution.template_dir` (default: project root; relative paths resolve against it) is resolved by `astra.runner.resolve_template_dir`. It is passed as an absolute path to the default backend and recorded in `config_source.json`.
- **Figures**: `campaign_figures()` registers `(stem, plot)` pairs, and `finalize_campaign` iterates them instead of a positional four-tuple.

## Acceptance Criteria
- [x] Constructing a runner changes no global RNG or dtype state (tested). `run()` restores the default dtype (tested).
- [x] `run()` and every extracted method are under 60 lines and no `nonlocal` remains (AST test).
- [x] Mock campaign, resume, interruption-recovery and benchmark tests pass unchanged, including the uninterrupted-vs-resumed equivalence tests.
- [x] The template directory, and therefore the generated ASTRA inputs, is identical from another working directory (tested).

## Validation Results
Relevant modules pass:
- checkpoint/resume (65)
- CLI (43)
- benchmark campaign
- GP/acquisition
- config and scalarized suite
- visualizations and configuration boundaries
- package layout (8, including 4 new tests)
- workdirs and parallel evaluation

No ASTRA campaign, push or remote query was performed.

## Scope and Limitations
- The public `MoboCampaignRunner(...).run()` signature and the runner attributes read by callers are unchanged.
- Tests that stub surrogate components now patch `mobo_linac.campaigns.strategies`.

## Status
Completed.
