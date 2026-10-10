# Paper production, step by step

Run these scripts one at a time from any directory, after reviewing the output of the previous
step. Each step prints its progress, saves the same text in `results/paper_production/logs/`,
and writes its outputs to `results/paper_production/<step>/`. The parameters are written at the
top of each script and follow the [campaign plan](../../docs/strategic_simulation_campaign_plan.md).

| Script | Plan stage | What it runs | ASTRA evaluations | Time at ~300 s/run, 4 workers |
|---|---|---|---:|---|
| `01_preflight.sh` | 0 | Environment, `validate-config`, unit tests, one real ASTRA run, pilot preview, mock rehearsal | 1 | ~45 min |
| `02_pilot.sh` | 1 | Balanced scalarized, unconstrained and constrained MOBO, seed 42, 8 + 2×4 each; 10 jitter samples | 48 + 66 audit | ~2–3 h |
| `03_screening.sh` | 2 | 3 algorithms × seeds 42–44, budget 40 (8 Sobol, batch 4) | 360 | ~8 h |
| `04_primary.sh` | 3 | 3 algorithms × seeds 42–51, budget 160 (16 Sobol, batch 8) | 4,800 | ~4–5 days |
| `05_operating_points.sh` | survey | Full launcher: 5 scalarized cases + both MOBO phases, 16 + 20×8 each; 50 jitter samples | 1,232 + 306 audit | ~1.5 days |
| `06_candidate_audit.sh` | 4 | Reruns and 50 jitter samples for the predeclared primary run (constrained, seed 42) | 306 | ~7 h |
| `07_paper_outputs.sh` | deliverables | Manuscript figures and tables (staged), consistency check, campaign inventory | 0 | minutes |

Steps 03–05 print a forecast from the pilot's measured runtime and disk use before they start.
GP fitting adds to these times.

```bash
conda activate linac-opt            # or set PYTHON_BIN to that environment's python
scripts/production/01_preflight.sh
scripts/production/02_pilot.sh
# ...review, then the next step
```

## Rules the scripts enforce

- **Order.** A step starts only when the previous step finished; `results/paper_production/status/`
  holds the `<step>.done` markers.
- **Clean code.** Physical steps (02–06) refuse to start with uncommitted changes to tracked
  files, so the recorded commit describes the code that ran (`ALLOW_DIRTY=1` overrides and is recorded).
- **Records.** Every step writes `step_record_<time>.json` with the commit, configuration, ASTRA
  executable and input-file SHA-256 hashes, package versions and its parameters. The launcher
  steps also write `campaign/logs/launch_*.json`.
- **Immutable outputs.** A finished step refuses to run again. To repeat one, use a new root
  (`PRODUCTION_ROOT=results/paper_production_v2`).
- **Disk.** Steps 03–05 refuse to start when the forecast output size exceeds the free disk space
  (`ALLOW_LOW_DISK=1` overrides).
- **Gates.** Steps 02–05 check automatically that every run completed with valid and feasible
  evaluations (and, for 02 and 05, that audits produced rows). A failed gate stops before the
  step is marked done. The scientific review (failure causes, verification statuses, GP fit and
  fallback outcomes) remains yours.

## Interruptions

- `02_pilot.sh --resume` and `05_operating_points.sh --resume` continue their campaigns from
  the saved checkpoints.
- `03_screening.sh` and `04_primary.sh` can be run again: completed runs are kept and skipped.
  An incomplete benchmark run is reported and preserved for investigation.
- `06_candidate_audit.sh` and `07_paper_outputs.sh` refuse to overwrite earlier partial outputs;
  move them aside first.

## Rehearsing the scripts

`MOCK_EVALUATOR=1` replaces ASTRA with the mock evaluator and requires a separate root. The
budget variables named in each script (for example `PRIMARY_BUDGET`) shrink a rehearsal:

```bash
PRODUCTION_ROOT=/tmp/prod_rehearsal MOCK_EVALUATOR=1 WORKERS=2 \
  PILOT_INITIAL_SAMPLES=4 PILOT_ITERATIONS=1 PILOT_BATCH_SIZE=2 PILOT_PERTURBATIONS=2 \
  scripts/production/02_pilot.sh
```

Mock results are not physical evidence. Do not override budgets for the paper campaign.

## Notes

- `production_tools.py` implements the records, summaries, forecasts and inventory used by the steps.
- Step 7 stages figures and tables in `results/paper_production/07_paper_outputs/`: the manuscript
  phases, the primary comparison figures and summary, and the audit tables. After review, it prints
  the `scripts/reproduce_paper.sh` and copy commands that place them where `docs/paper/main.tex`
  includes them.
- `execution.retries` is 0 in `configs/publication_200MeV.yaml`, so a timed-out or failed ASTRA
  run consumes its budget slot and is reported as a failure.
