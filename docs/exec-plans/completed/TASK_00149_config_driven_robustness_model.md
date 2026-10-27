# Task Completion Summary: Task 144

## Summary
Implemented TASK_18 from `docs/05_refactor_tasks/`. Perturbation channels are declared per configured design variable in a validated specification. Robustness summaries now use the configured objectives and the active constraint profile, and substitute no values.

## Key Changes
- **Specification** (`configs/perturbation_config.yaml`, version 2):
  - Each `lattice` channel declares channel, design_variable, kind (`relative`/`absolute`), distribution (`normal`), std, unit and basis.
  - Each `source` channel declares channel, setting and std.
  - The file also sets `num_perturbations`, `seed`, `seed_policy` (`common`/`candidate_offset`) and `fragility_threshold`.
  - Unknown fields, distributions, source settings, duplicate channels and unknown design variables are rejected. Every declared field is either used or rejected.
  - Version-1 flat files load through `PerturbationSpecification.legacy_200MeV`.
- **Sampling**: `generate_perturbed_machine_states(nominal_by_name, spec, ...)` draws lattice, then source channels, in specification order. A golden test confirms the 200 MeV channels reproduce the former positional draws bit for bit. The positional six-vector, the canonical-name check and `generate_perturbed_parameters` were removed.
- **Applied-perturbation audit**: requests carry `channel_targets`. `applied_lattice_perturbations` derives namelist targets from the configured `astra_key`/`coupled_targets`, replacing the private channel table in the runner.
- **Summaries**:
  - nominal/mean/std/p5/p95 for every configured objective, with objective order and units;
  - threshold-normalized margins for every channel of the active profile, plus the worst channel;
  - degradation ratios in each objective's preferred direction;
  - a configurable fragility threshold.
  - Missing data yields NaN and `summary_issues`; the fabricated `[1e-6, 1e-6, 1e6]` nominal, growth 2.0, transmission 1.0 and fixed 0.90 threshold were removed.
- **Workflow**: all representatives are evaluated in one plan using the specification's seed policy; the default `common` policy reproduces the historical per-role seed. The caption lists the unsupported source channels, and the LaTeX robustness table includes every configured objective (ε_y was previously missing).
- **Documentation**: the simulation guide and robustness rationale were updated.

## Acceptance Criteria
- [x] No positional six-vector or channel-name table remains in robustness or runner code.
- [x] Summaries use the active profile; a stringent fixture changes the reported margin.
- [x] Missing nominal data produces NaN with a recorded reason.
- [x] Every declared perturbation field is used or rejected by validation.

## Validation Results
Relevant tests pass: robustness (18), candidate evaluator, CLI (37), package layout, latex, config and parameter mapping. No ASTRA campaign, push or remote query was performed.

## Scope and Limitations
Robust scores now include every constraint channel, not transmission alone, so regenerated values may differ from archived ones. Source jitter remains explicitly unsupported.

## Status
Completed.
