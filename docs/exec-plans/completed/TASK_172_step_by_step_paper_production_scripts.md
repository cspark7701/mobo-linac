# Task Completion Summary: Task 172

## Summary
Added `scripts/production/`: seven numbered scripts that run the paper campaign one stage at a time with the campaign plan's parameters. Each script prints its progress, saves the same output to `results/paper_production/logs/`, and writes its outputs to `results/paper_production/<step>/`. The scripts only call existing `mobo-linac` commands and `scripts/run_full_production.sh`. Physics, optimization and the configuration are unchanged.

## Key Changes
- **Step scripts** (parameters at the top of each):

  | Script | Stage | Runs |
  |---|---|---|
  | `01_preflight.sh` | 0 | Environment and git report; `validate-config`; ASTRA executable and input hashes; unit suite (`--skip-tests`); one real ASTRA evaluation (`--skip-astra`); pilot preview; mock rehearsal of the launcher, its resume and the benchmark |
  | `02_pilot.sh` | 1 | Balanced scalarized, unconstrained and constrained runs; seed 42; 8 initial samples + 2 batches of 4; 10 perturbations |
  | `03_screening.sh` | 2 | Three algorithms × seeds 42–44; budget 40, 8 Sobol, batch 4 |
  | `04_primary.sh` | 3 | Three algorithms × seeds 42–51; budget 160, 16 Sobol, batch 8 |
  | `05_operating_points.sh` | survey | Full launcher defaults: five cases and both MOBO phases; 16 + 20 × 8; 50 perturbations |
  | `06_candidate_audit.sh` | 4 | Verification and 50-sample robustness for the predeclared primary run (constrained, seed 42) |
  | `07_paper_outputs.sh` | deliverables | `paper-figures` into a staging folder, consistency check, campaign inventory; `docs/paper/` is not modified |

- **`_common.sh`**: shared protocol (configuration, CPU device, 4 workers, the three algorithms) and the rules every step enforces:
  - Each step needs the previous one's `status/<step>.done` marker. A finished step refuses to run again.
  - Physical steps refuse uncommitted tracked changes (`ALLOW_DIRTY=1` overrides).
  - Steps check free disk space against a requirement (`ALLOW_LOW_DISK=1` overrides).
  - The interpreter must import `mobo_linac` from this checkout.
  - The mock evaluator may not write to the paper root.
- **`production_tools.py`**:
  - `record`: writes a step record with the commit and dirty flag, configuration, executable and static-input SHA-256 hashes, package versions and parameters.
  - `summarize`: per-run evaluations, validity, feasibility, failure categories, ASTRA runtime median/p95, disk use per evaluation and audit status counts. It enforces the exit gates: complete runs, valid and feasible evaluations, and, for the launcher steps, audit rows.
  - `forecast`: projects simulator wall time and disk use from the pilot's measurements.
  - `inventory`: indexes every stage's runs, completion-marker checksums and records.
- **Resumption**:
  - Steps 02 and 05 accept `--resume` (launcher checkpoints).
  - Steps 03 and 04 can be rerun; the dispatcher skips completed runs.
  - Steps 06 and 07 refuse to overwrite partial outputs.
- **Documentation**: `scripts/production/README.md`. The campaign plan, `README.md` and `docs/README.md` point to the scripts.
- **Tests**: `tests/test_production_scripts.py` covers:
  - numbering, executability and bash syntax;
  - help output with no side effects;
  - the mock guard and the step order;
  - forecast arithmetic for the primary experiment (4,800 evaluations, 100 h at 300 s);
  - the summary gate on synthetic runs, and counting Phase 1 case runs rather than their aggregate.

## Validation Results
- `tests/test_production_scripts.py`: 13 passed. `tests/test_docs_links.py` passes. Ruff and `scripts/verify_docs_sync.py` pass.
- End-to-end mock rehearsal of steps 01–07 with reduced budgets in a scratch root (`MOCK_EVALUATOR=1`). All gates passed; the pilot counted 3 runs and the survey 7; figures, tables and the inventory were produced.
- On this host, step 01 reports 15 GB free. That is below its 20 GB minimum, and the steps would refuse to start without `ALLOW_LOW_DISK=1`.

## Status
Completed.
