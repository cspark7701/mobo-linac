# Strategic simulation campaign plan for the 200 MeV injector

Prepared 2026-10-09. This is an execution proposal, not a record of new physical
results. It uses the current refactored campaign, benchmark, verification and
robustness services. The [simulation guide](simulation_guide.md) remains the
reference for artifact formats and physics contracts.

## Scientific objective and frozen protocol

Establish whether constraint-aware qLogNEHVI produces a better *feasible* Pareto
front per attempted candidate evaluation than unconstrained qLogNEHVI and
balanced scalarized BO. Separately characterize useful operating points and
their sensitivity to applied lattice jitter.

Use `configs/publication_200MeV.yaml` as the nominal protocol. Freeze its bytes,
repository commit, Python environment, ASTRA/generator executable hashes, input
particle distribution and field-map hashes before the first physical pilot.
Keep the six configured controls, their bounds/cavity coupling, three objective
units/signs and all seven constraint channels unchanged across compared runs.
The nominal requirements include 195–205 MeV mean kinetic energy, transmission
at least 0.90, and the configured transverse/longitudinal limits. Do not relax
these requirements after observing algorithm performance.

Predeclare one reporting reference: physical `(1.5 um rad, 1.5 um rad, 1.5 MeV)`;
for these minimizing SI objectives its model-space vector is
`(-0.0000015, -0.0000015, -1500000)`. All ordinary pipeline phases explicitly
receive that reference. Benchmark runs use the equivalent normalized reference
from the benchmark configuration. Reporting scales, names, order, units, signs,
and constraint profiles must match before comparing runs. Acquisition references
may evolve independently; they do not define published hypervolume.

## Staged allocation and decision gates

| Stage | Campaign allocation | Candidate evaluation budget | Exit gate |
|---|---|---:|---|
| 0: software readiness | Command previews, mock workflows and affected regression tests | 0 physical evaluations | Config/reference validation, journals, checkpoint recovery and artifact loading succeed |
| 1: physical pilot | Balanced scalarized, unconstrained and constrained; seed 42; 8 initial samples, 2 batches of 4 | 48 | Valid exit-plane measurements and audited attempts; enough observed rows for fitting; feasible candidates available for audits |
| 2: paired screening | Three algorithms; seeds 42, 43, 44; budget 40 each, 8 initial samples, batch 4 | 360 | Compatible completed runs; failure causes and fallback/fit outcomes understood; no unresolved scientific contract mismatch |
| 3: primary experiment | Same three algorithms; seeds 42–51; budget 160 each, 16 initial samples, batch 8 | 4,800 | Full per-seed results with uncertainty, matched budgets and feasibility accounting |
| 4: independent candidate audit | Feasible representatives from selected completed campaigns | Reruns plus `roles × perturbations` | Measured rerun agreement, provenance and lattice-jitter scores documented |
| Optional: acquisition ablation | Add `qlogehvi` to the primary experiment with ten seeds | 1,600 extra | Apply only after the primary comparison and its cost are assessed |
| Optional: operational weight survey | Full launcher defaults: five Option 2 cases and two MOBO runs | 1,232 | Descriptive operating-point coverage; keep its unequal algorithm budgets visible |

Budgets count initial samples and failed candidate evaluations. Retries create
additional physical attempts and must be costed separately. Verification and
robustness evaluations are outside the optimization budget. The primary experiment
is a separate campaign from screening: do not pool pilot/screening results into
its endpoint estimate or choose favorable seeds afterward.

The full launcher defaults to 16 initial samples plus 20 batches of 8: 176
candidates per run, or 880 across the five scalarized cases and 176 in each MOBO
phase. Their common reporting reference permits scientific convention checks,
but the five-case aggregate has five times the MOBO evaluation budget and case
seeds offset by 100. Its pooled front is a descriptive survey, not a paired,
equal-budget algorithm comparison. Use the benchmark dispatcher for that claim.

## Executable sequence

Activate the installed linac environment and run commands from the repository
root. Use a fresh, descriptive output directory for each experiment. Set
`PYTHON_BIN` to that environment's interpreter for the shell launcher; its default
is `python3`. Existing executable environment overrides are respected.

```bash
python -m mobo_linac.cli validate-config --config configs/publication_200MeV.yaml

# Preview all pipeline commands; creates no run directory and starts no ASTRA.
bash scripts/run_full_production.sh --dry-run --p1-case balanced \
  --initial-samples 8 --iterations 2 --batch-size 4 --workers 4 \
  --perturbations 10 --output-dir results/pilot_200MeV_seed42

# Stage 1: execute the physical pilot only after reviewing the preview.
bash scripts/run_full_production.sh --p1-case balanced \
  --initial-samples 8 --iterations 2 --batch-size 4 --workers 4 \
  --perturbations 10 --output-dir results/pilot_200MeV_seed42 --quiet

# Stage 2: paired screening, including failures in the fixed budget.
python -m mobo_linac.cli run-benchmark \
  --config configs/publication_200MeV.yaml \
  --algorithms constrained_qlognehvi unconstrained_qlognehvi scalarized_bo \
  --seeds 42 43 44 --budget 40 --n-sobol-init 8 --batch-size 4 \
  --num-workers 4 --device cpu --output-dir results/screening_200MeV

# Stage 3: primary experiment. Review a --dry-run preview before execution.
python -m mobo_linac.cli run-benchmark \
  --config configs/publication_200MeV.yaml \
  --algorithms constrained_qlognehvi unconstrained_qlognehvi scalarized_bo \
  --seeds 42 43 44 45 46 47 48 49 50 51 \
  --budget 160 --n-sobol-init 16 --batch-size 8 \
  --num-workers 4 --device cpu --output-dir results/primary_200MeV

python -m mobo_linac.cli analyze-benchmark --output-dir results/primary_200MeV
```

CPU is the proposed reproducibility baseline. If a pilot establishes a useful
CUDA improvement, freeze that device policy for the whole paired experiment and
retain its runtime/RNG topology. Keep four ASTRA workers initially; measure CPU,
RAM, storage throughput and simulator duration before changing concurrency.
Distributed MPI/Ray/Dask execution is future work, outside this plan.

Do not invoke the full launcher a second time with a new-run output path that
already exists. For its interrupted runs, use:

```bash
bash scripts/run_full_production.sh --resume --p1-case balanced \
  --iterations 2 --output-dir results/pilot_200MeV_seed42 --quiet
```

`--iterations` is the total target. The launcher resumes each selected scalarized
case and both MOBO runs through the saved-state CLI, then regenerates aggregate
reports. Saved configuration, seed, device, initial design, batch size and pending
candidate identities remain authoritative. Analysis uses Phase 3's saved
configuration. The selected cases must already have checkpoints; missing cases
require separate fresh campaigns. Logs are in `<root>/logs`; runtime outputs are
in the phase directories, and audits are under `analysis/`.

The benchmark dispatcher skips only validated complete runs. It does not
reconcile incomplete benchmark completion markers. Preserve incomplete benchmark
outputs and investigate them; use a new benchmark root for a replacement campaign.
A direct campaign resume recovers a run but does not automatically repair its
benchmark dispatcher state.

## Measurement and interpretation

Primary endpoints are feasible hypervolume versus total candidate evaluations,
final feasible hypervolume, and feasible-evaluation fraction using **all**
evaluations as denominator. Report per-seed endpoints and paired algorithm
contrasts before an aggregate mean/median. Retain all predeclared seeds, including
poor runs. Use a recorded, seeded paired bootstrap over seed-level contrasts for
uncertainty if publication analysis is extended; this is planned analysis, not a
claim that the current CLI computes that interval. Ten seeds provide a first
uncertainty assessment, not a guarantee of statistical power.

Secondary endpoints are all-valid hypervolume, feasible/all-valid Pareto sizes,
feasible objective extrema, first-feasible evaluation count, simulation failure
categories, GP fit outcomes, acquisition fallback frequency, summed simulator
runtime and elapsed wall time. Keep failed, infeasible and missing-observation
records distinct. An empty feasible front has no deployable candidate; investigate
physics/source/parser failures before increasing the optimization budget.

Use `read_run_data()` and `read_comparable_runs()` for reporting. The measured
history and recorded metadata are authoritative. Inspect `run_complete.json`,
`reporting_metadata.json`, `candidate_history.json`, `hypervolume.csv`,
`proposal_history.json`, checkpoints and retained attempt manifests. A successful
shell exit describes pipeline execution; verification status and measured
constraints determine scientific acceptance. A restored GP prior or Sobol fallback
is recorded behavior to quantify, not an optimizer convergence claim.

For cost forecasting, measure a pilot's median/p95 ASTRA duration and separate
GP/acquisition time. An approximate per-run wall-time model is
`ceil(N_initial/workers) × t_ASTRA + iterations × ceil(batch/workers) × t_ASTRA
+ sum(t_fit + t_acquisition) + t_IO`; add audit and retry costs. Sequential phase
execution makes campaign wall times additive. Do not infer wall time by dividing
summed simulator runtime alone by worker count. Retain outputs and estimate bytes
per attempt before committing the primary allocation; no cleanup should destroy
provenance needed by verification.

## Candidate verification, robustness and final deliverables

Use measured feasible Phase 3 history, or `pareto_feasible.csv` joined to sibling
history, to select representative candidates. The launcher runs independent,
audited nominal reruns through the shared verification service. Review each
`VERIFIED`, conditional, failed or unknown status and its hashes/attempt links;
mock statuses cannot support a physical reproducibility claim.

Robustness currently selects six representative roles (roles may share the same
physical candidate). Fifty perturbations per role require 300 candidate
evaluations; nominal verification currently selects seven roles, adding seven
reruns. The pilot's ten perturbations per role reduce that audit cost to 60 plus
seven. These counts assume a feasible front exists and no retries. Keep role
identities and repeated physical points explicit in analysis.

Evaluate applied lattice jitter at the configured engineering tolerances. Charge,
laser spot-size and pulse-duration scales are sampled and archived but are
**unsupported** for the fixed `pal_photo2.ini` source. Present the resulting scores
as lattice-jitter robustness. A full source-jitter study needs a separately
validated distribution-generation backend and new physics authorization.

If stringent/relaxed constraint profiles are explored, freeze each as a separate
configuration and compare algorithms within that profile. Do not pool their
hypervolumes with the nominal experiment. Extend the candidate audit to finalists
from other algorithms only after the main comparison, with the same audit protocol.

Deliver a campaign inventory with commit/config/environment hashes, all seed and
budget records, validated run artifacts, per-seed comparison tables and figures,
verification records, supported-channel robustness summaries, and a list of
unresolved failures. Generate manuscript figures/tables into a new staging
directory for review; existing `results/`, `release/` and paper archives remain
untouched by this planning task. Promote an operating point only when measured
nominal feasibility, independent rerun evidence and applied-jitter results justify
its intended use.
