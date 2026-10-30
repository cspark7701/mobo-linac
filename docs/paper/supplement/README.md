# Supplement S1: evidence map for the manuscript

This supplement is the `mobo-linac` repository snapshot supplied with the manuscript
"Multi-objective Bayesian optimization of a 200 MeV injector-linac model derived from the
Korea Light Source design" for review. Outside review it is available from the author on
request, as stated in the manuscript's Data availability section. The snapshot is identified
by the commit hash recorded in the review package (the revision overview and its
changed-file inventory). It identifies, for each result reported in the article, the
file that holds it, the script that computes that file, and the run-level inputs.
Item numbers S1.1–S1.15 are the identifiers the manuscript cites. Internal task numbers are
not needed to use it.

Nothing in this map has been uploaded or deposited publicly.

## Software identity

| Role | Identity |
|---|---|
| Package | `mobo_linac` 1.0.0 (`pyproject.toml`); Python 3.11.10, PyTorch 2.5.0+cu124, BoTorch 0.17.0, GPyTorch 1.15.2, NumPy 2.4.1, pandas 3.0.0, SciPy 1.17.1 |
| Tracking code | `bin/astra`, SHA-256 `bf62ae2e28fb1e4e…` |
| Static inputs | `astra.in`, `gun.dat`, `PAL_SOL_A.dat`, `TWS_Sband.dat`, `pal_photo2.ini`; SHA-256 values in each step record |
| Production configuration | `configs/publication_200MeV.yaml`, SHA-256 `458a28d1acec14e8…` |
| TDR-profile configuration (revision runs) | `configs/revision_tdr_200MeV.yaml` |

### Production code and analysis code

The **production code** is the commit from which each campaign was started. It is recorded
in that step's `step_record_*.json`, and every listed commit was clean (no uncommitted
changes):

| Step | Commit | What it produced |
|---|---|---|
| Primary benchmark (30 matched campaigns) | `8ad6c2c` | All primary comparisons |
| Operating-point survey | `239c466` | Appendix C |
| Candidate audit and lattice jitter; paper outputs | `f6ce000` | Robustness results, verification tables |
| Revision simulations (MOGA-derived reference, TDR-candidate jitter, TDR-profile campaigns, Sobol arm) | `bfb0be0` and later | Listed per stage in `results/revision_round2/run_record.jsonl` |

The **revision-analysis code** comprises the `scripts/analyze_revision_*.py`,
`scripts/prepare_revision_*.py` and `docs/paper/revisions/evidence/c0*_audit.py` scripts.
They read the completed run ledgers, verify each ledger's SHA-256 against its run's
completion marker, and write the evidence files. They never modify a run directory. The
analysis code is the version in this snapshot, not the production commit.

### Command-line settings that override the configuration

The configuration's `benchmark:` block holds development defaults: budget 40, 10 initial
points, batch 4 and four algorithms. The production steps overrode them on the command
line. The overrides are recorded in each step record:

- **Primary benchmark:**
  - `--algorithms constrained_qlognehvi unconstrained_qlognehvi scalarized_bo`;
  - `--seeds 42 … 51`, `--budget 160`, `--n-sobol-init 16`, `--batch-size 8`;
  - eight workers, `--device cuda:0`, one campaign at a time.
- **Operating-point survey:** 16 initial points, 20 iterations, batch 8, seed 42, all five weighting cases and 50 perturbations.
- **Candidate audit:** primary run `constrained_qlognehvi_seed_42`, 50 perturbations, robustness seed 42.
- **Revision runs:** the TDR-profile campaigns use the same primary overrides with seeds 42–44. The Sobol arm uses `run-unconstrained --num-initial-samples 160 --n-iterations 0`. Both are listed in `scripts/run_revision_round2_simulations.sh`.

## What is and is not distributed

- **Distributed:** code, configurations, field maps and source distribution, every evidence
  file below, the manuscript source and `ledger_manifest.json`.
- **Not distributed, because of size:** the run directories under `results/` (about 44 GB
  for production and about 2 GB for the revision runs). They hold the ASTRA input and output
  snapshots, the GP checkpoints and the logs. They are immutable and available from the
  author.
- **Not archived:** the BoTorch sampler base draws and acquisition objects. Saved GP
  snapshots and training sets allow the surrogates to be restored and the next-batch
  predictions to be checked. Bitwise replay of the proposals is not possible.

### Reproduction levels and their inputs

The evidence files do not all need the same inputs. `input_inventory.csv` lists, for every
generator in `evidence_map.csv`, its input classes, the run files it reads and its level:

| Level | What is reproduced | Inputs needed |
|---|---|---|
| 1 | Tables and figures from the distributed evidence files | This snapshot only |
| 2a | Evidence computed from the minimal ledgers | Each run's `evaluations.csv`, `config.json` and `run_complete.json` (about 10 MB; listed with SHA-256 in `ledger_manifest.json`) |
| 2b | Evidence that also needs other run records, GP checkpoints, tracking outputs or re-tracking records | The full run directories, available from the author |
| 3 | Re-tracking with ASTRA | The ASTRA executable, static inputs and configuration in this snapshot |

The input classes are `ledgers` (the minimal set), `run_records` (other run-level records such
as `proposal_history.json`, `metrics_history.csv`, robustness summaries and
`moga_reference.json`), `gp_checkpoints` (saved surrogate states, `*.pt`), `tracking_outputs`
(ASTRA output files such as `astra.Zemit.001`), `retracking_records` (the result streams, plans
and completion markers of re-tracking runs such as the resolution check) and `derived_evidence`.
Examples of level 2b are the next-batch predictions (GP checkpoints), the RF-amplitude estimate
(a retained `astra.Zemit.001`) and the resolution check (`convergence_results.jsonl`, its plan
and completion record). Proposals cannot be replayed bitwise (level 3 does not cover them).

`scripts/check_supplement_regeneration.py` tests level 2a: it assembles a scratch tree with
the scripts, the evidence files and only the minimal ledgers, runs representative ledger-only
generators there and compares their outputs with the committed evidence
(`r3_regeneration_check.json`). The manifest check below verifies the map, labels, inventory
and checksums; it does not regenerate evidence.

## Evidence map

The complete file-level map, with the manuscript label and generator of each file, is
`evidence_map.csv`. Its items are:

| Item | Content | Manuscript |
|---|---|---|
| S1.1 | Production configuration, step records, ledger checksums | Simulation study design |
| S1.2 | Primary front-quality histories, terminal values, directional coverage, empirical reference front, attainment | Primary comparison; Appendix B |
| S1.3 | Paired matched-group effects, initialization checks, effects with the reference rebuilt in every resample | Primary comparison; Appendix B |
| S1.4 | Reclassification under the production, NAPAC and TDR profiles; the two TDR candidates; the TDR-constrained campaigns | Section 2; table of TDR candidates; Reach of the TDR acceptance region |
| S1.5 | Attribution of the feasible-sampling gap by violated channel group, conditional feasibility, upper ACC3/4 quarter | Attribution subsection and figure |
| S1.6 | Space-filling reference: the shared initial designs and the budget-matched Sobol arm (ten runs) | Attribution subsection |
| S1.7 | Implementation audit: proposal tiers, fitting recovery, smoothing scales, residual-unit sensitivity, phase convention | Methods; Appendix A |
| S1.8 | Next-batch predictions, stage- and region-resolved coverage, fixed- versus inferred-noise refit | Predictive checks; predictive appendix |
| S1.9 | Six selected settings: controls, objectives, constraint activity, trajectories | Selected settings; settings appendix |
| S1.10 | Lattice jitter: margins, statistics, dominance by perturbed neighbours, RF-amplitude estimate, TDR-candidate jitter | Robustness results |
| S1.11 | MOGA-derived reference: provenance assessment, re-evaluation, epsilon to each front, jitter | MOGA-derived reference |
| S1.12 | Campaign wall-clock costs and paired ratios | Results (cost) |
| S1.13 | Numerical-resolution disposition, the refinement check of ten reported settings (150 runs; generator `scripts/evaluate_revision_convergence.py`) and the post-hoc diagnostic-shift scenarios of the feasible fractions | Section 2 (nominal resolution); Primary comparison; TDR reach |
| S1.14 | Exploratory operating-point survey | Appendix C |
| S1.15 | Revision bookkeeping: comparison matrix, prior-work notes, figure provenance, validation | none |

## Checking the map

```bash
python scripts/build_supplement_manifest.py          # check the map, labels and ledgers
python scripts/build_supplement_manifest.py --build  # rewrite ledger_manifest.json first
```

The check fails if a mapped file or generator is missing, if an evidence file is unmapped,
if a manuscript label is undefined, if a generator has no valid entry in
`input_inventory.csv`, or, when `results/` is present, if a ledger checksum has changed.

```bash
python scripts/check_supplement_regeneration.py      # regenerate level-2a evidence from the minimal ledgers
```
