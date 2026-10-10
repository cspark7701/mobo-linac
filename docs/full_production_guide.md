# Full Production Pipeline Guide

[`scripts/run_full_production.sh`](../scripts/run_full_production.sh) runs the three optimization phases and the audited analysis with one shared configuration and one fixed reporting reference. Every step is a `mobo-linac` CLI command, so the launcher adds no optimization logic of its own. For staged budgets and decision gates, see the [strategic simulation campaign plan](strategic_simulation_campaign_plan.md).

## Steps

| Step | Command | Output |
|---|---|---|
| Phase 1 | `run-scalarized-suite --cases …` (the configuration's `scalarized_cases`; each case seed is the base seed plus its `seed_offset`) | `phase1_scalarized/<case>/` plus the aggregate in `phase1_scalarized/` |
| Phase 2 | `run-unconstrained` (qLogNEHVI) | `phase2_unconstrained/` |
| Phase 3 | `run-constrained` (constraint-weighted qLogNEHVI) | `phase3_constrained/` |
| Comparison | `compare`: comparison report, figures and independent nominal reruns of the six representative roles | `analysis/` |
| Robustness | `run-robustness` on the measured feasible Phase 3 front (six roles × `--perturbations`) | `analysis/robustness/` |

Before creating any output, the launcher validates the configuration, campaign settings, reference length and finiteness, the requested Phase 1 case, and the ASTRA executable. The executable is resolved from `simulation.executable`, then `$ASTRA_BIN`, then `PATH`. Each launch then writes `logs/launch_<timestamp>.json`, which records the git commit and dirty flag, the configuration path and SHA-256, the executable path and SHA-256, the package and Python versions, and all options.

## Usage

```bash
export PYTHON_BIN=/path/to/linac-env/bin/python      # default: python3

# 1. Preview: validated commands only; no output directory, no ASTRA
bash scripts/run_full_production.sh --dry-run --output-dir results/production_v1

# 2. Rehearse every step with the mock evaluator (fast, no ASTRA; NOT physical evidence)
bash scripts/run_full_production.sh --mock-evaluator --quiet --device cpu \
  --initial-samples 4 --iterations 1 --batch-size 2 --perturbations 2 --output-dir /tmp/rehearsal

# 3. Physical run
bash scripts/run_full_production.sh --quiet --output-dir results/production_v1
```

A new run refuses an existing output root. Interrupted runs continue with `--resume`. `--iterations` is the total target. Saved configuration, seed, device topology, initial design, batch size and pending candidates remain authoritative. The selected Phase 1 cases are resumed individually and re-aggregated, and the analysis uses Phase 3's saved configuration:

```bash
bash scripts/run_full_production.sh --resume --iterations 30 --output-dir results/production_v1 --quiet
```

## Options

| Option | Default | Meaning |
|---|---|---|
| `--config PATH` | `configs/publication_200MeV.yaml` | Shared configuration (ignored on `--resume`; Phase 3's saved copy is used) |
| `-o, --output-dir DIR` | `results/full_production` | Pipeline root |
| `-i, --iterations N` | 20 | BO batches after the initial design (total target on resume) |
| `-b, --batch-size Q` | 8 | Candidates per batch |
| `--initial-samples N` | 16 | Sobol initial design |
| `-w, --workers N` | 4 | ASTRA and audit worker processes |
| `--seed N` | 42 | Base seed |
| `-d, --device D` | `auto` | `auto`, `cpu`, `cuda` or `cuda:N` (CPU is the reproducibility baseline) |
| `--p1-case CASE` | `all` | `all` or one configured `scalarized_cases` id |
| `--reference RX RY RE` | `-1.5e-6 -1.5e-6 -1.5e6` | Reporting reference in model space and configured objective order (physical 1.5 µm·rad, 1.5 µm·rad, 1.5 MeV) |
| `--perturbations N` | 50 | Robustness samples per representative role |
| `-r, --resume` | off | Continue existing runs from their checkpoints |
| `-q, --quiet` | off | Step names on screen; full output in `logs/<step>.log` |
| `--dry-run` | off | Print the validated commands only |
| `--mock-evaluator` | off | Rehearse all steps without ASTRA |

With the defaults, each run evaluates 16 + 20 × 8 = 176 candidates: 880 across the five configured scalarized cases and 176 in each MOBO phase. The Phase 1 aggregate is therefore a descriptive operating-point survey, not an equal-budget algorithm comparison. Use `run-benchmark` for paired comparisons.

## Output layout

```
<root>/
├── logs/                    # launch_<timestamp>.json and one <step>.log per step
├── phase1_scalarized/
│   ├── <case>/              # one complete campaign run directory per case
│   ├── cases_summary.csv/.json, phase1_cases_table.tex
│   └── evaluations.csv, pareto*.csv, hypervolume.csv, ...  # aggregate over cases (shared reference)
├── phase2_unconstrained/    # campaign run directory
├── phase3_constrained/      # campaign run directory
└── analysis/
    ├── comparison_report.md
    ├── figures/             # Pareto-front and verification rerun comparisons
    ├── verification/        # representatives.json, verification_summary.csv/_table.tex, manifest, reruns
    └── robustness/          # representatives.json, robustness_summary.csv, robustness_table.tex, runs
```

A campaign run directory holds the resolved configuration and its source, `reporting_metadata.json`, the evaluation journal, CSV exports (`evaluations`, `failures`, `constraints`, `train_X/Y`, `pareto`, `pareto_all`, `pareto_feasible`, `hypervolume`, `metrics_history`), `candidate_history`, `proposal_history.json`, `representatives.json`, `checkpoints/`, `gp_checkpoint/`, `provenance/` (ASTRA attempts), `figures/`, `run.log` and the completion marker `run_complete.json`.

## Interpreting results

A zero exit status means the pipeline executed. Scientific acceptance depends on the verification statuses, the measured constraints and the recorded provenance. Mock outputs never support physical claims. Source-jitter channels (charge, laser spot and pulse duration) are sampled and archived but not applied to the fixed `pal_photo2.ini` distribution, so robustness scores describe lattice jitter only.

The interactive mirror is [`notebooks/full_production_pipeline.ipynb`](../notebooks/full_production_pipeline.ipynb), which calls the same package functions.
