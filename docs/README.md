# Documentation map

Each topic has one home. Run instructions live in the guides; scientific definitions live in `methods/` and `physics/`; software design lives in `architecture/`.

## How to run
- [simulation_guide.md](simulation_guide.md): the reference procedure (campaigns, benchmark, robustness, verification, manuscript reproduction).
- [full_production_guide.md](full_production_guide.md): the end-to-end launcher `scripts/run_full_production.sh`.
- [../scripts/production/README.md](../scripts/production/README.md): the step-by-step paper production scripts.
- [strategic_simulation_campaign_plan.md](strategic_simulation_campaign_plan.md): the proposed production campaign budget and order.

## Scientific definitions
- [methods/metric_definitions.md](methods/metric_definitions.md): hypervolume, reference points and reporting metrics.
- [methods/benchmark_protocol.md](methods/benchmark_protocol.md): the paired multi-seed benchmark protocol.
- [methods/budget_and_batch_size.md](methods/budget_and_batch_size.md): evaluation budget, iterations and batch size.
- [physics/objective_and_unit_conventions.md](physics/objective_and_unit_conventions.md), [physics/constraint_rationale.md](physics/constraint_rationale.md), [physics/robustness_rationale.md](physics/robustness_rationale.md).
- [verification/pareto_verification_protocol.md](verification/pareto_verification_protocol.md): independent reruns of Pareto candidates.

## Architecture
- [architecture/repo_review.md](architecture/repo_review.md): the module overview.
- [architecture/data_flow.md](architecture/data_flow.md) and [architecture/risk_register.md](architecture/risk_register.md).
- [architecture/current_state.md](architecture/current_state.md): the historical pre-refactor baseline. The package layers are enforced by `tests/test_package_layout.py`.

## Results, manuscript and website
- `paper/` (manuscript), `consolidated_report/`. `mobo-linac compare` writes `results/mobo_validation_report.md` here locally; like all results, it is not versioned.
- Website: the source is `index.html` and `style.css`; `site/` is the generated bundle (`python tools/sync_site.py`).

## Task records
- `exec-plans/completed/`: one summary per executed task (TASK_NN, continuous numbering).
- `00_…` through `05_…` refactor-plan folders are local planning material and are not versioned.
