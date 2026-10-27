# Multi-Objective Bayesian Optimization for a 200 MeV Electron Injector Linac

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0+-ee4c2c.svg)](https://pytorch.org/)
[![BoTorch](https://img.shields.io/badge/BoTorch-0.10+-red.svg)](https://botorch.org/)
[![ASTRA](https://img.shields.io/badge/Simulation-ASTRA-green.svg)](https://www.desy.de/~mprue/Astra/)

## Overview

This repository develops a Machine Learning framework for optimizing a **200 MeV S-band electron injector linac** using **Bayesian Optimization (BO)** and **Multi-Objective Bayesian Optimization (MOBO)** powered by [BoTorch](https://botorch.org/) and [lume-astra](https://github.com/linac-group/lume-astra).

The accelerator beam dynamics are simulated using **ASTRA** (*A Space Charge Tracking Algorithm*). Optimization variables modify the ASTRA input file (`astra.in`), execute parallel simulations, extract beam quality metrics, update Gaussian Process (GP) surrogate models, and optimize acquisition functions to learn the Pareto front.

Research on initial scalarized Bayesian Optimization was presented at **ICABU 2025**, and the framework has been extended to true parallel multi-objective optimization via `qLogNEHVI` / `qEHVI` and explicit constraint modeling.

---

## Quick Links & Documentation

- 📖 **[Unified Simulation Procedure & Publication Workflow Guide](docs/simulation_guide.md)**: Master guide for ASTRA simulation procedure, MOBO architecture, benchmark protocol, robustness analysis, Pareto verification, and paper reproduction.
- 📄 **[Journal Paper Draft (LaTeX)](docs/paper/main.tex)**: Journal manuscript draft, figures, and compiled PDF in `docs/paper/`.
- 📋 **[Completed Milestone Execution Plans](docs/exec-plans/completed/TASK_00021_final_audit.md)**: Refactoring and publication task logs (Tasks 01--20).

---

## Repository Structure

```
mobo-linac/
├── README.md                          # Project documentation
├── AGENTS.md                          # Developer & agent design specifications
├── pyproject.toml                     # Package dependencies & CLI entry points
├── bin/                               # Integrated local ASTRA binaries (astra, generator)
│
├── src/mobo_linac/                    # Core Python package
│   ├── acquisition/                   # Resilient qLogNEHVI / qLogEHVI acquisition functions
│   ├── astra/                         # Isolated workdir manager & dynamic runner
│   ├── campaigns/                     # Unified MoboCampaignRunner execution engine
│   ├── execution/                     # ProcessPoolExecutor parallel batch evaluator
│   ├── config.py                      # Centralized YAML configuration parser
│   ├── evaluation.py                  # EvaluationResult & FailureCategory schema
│   ├── objectives.py                  # Physical <-> Model space conversions
│   ├── constraints.py                 # Dynamic beam quality constraint evaluator
│   ├── metrics/                       # Fixed reference hypervolume, Pareto & LaTeX reporting
│   ├── models/                        # Multi-scale Gaussian Processes & SurrogatePipeline
│   ├── robustness/                    # Full-chain photocathode/laser perturbation analysis
│   ├── io/                            # Results dataframes, journal & typed v3 checkpoints (io/checkpoint.py)
│   └── plotting/                      # Pareto, hypervolume, & diagnostic figures
│
├── configs/
│   ├── mobo_200MeV.yaml               # Centralized configuration file
│   ├── publication_200MeV.yaml        # Canonical publication configuration
│   └── perturbation_config.yaml       # Robustness (jitter) specification
│
├── docs/
│   ├── simulation_guide.md            # Step-by-step execution guide
│   ├── paper/                         # LaTeX journal manuscript (main.tex, main.pdf)
│   ├── exec-plans/                    # Active and completed task plans
│   ├── 04_refactor_tasks/             # Refactoring specifications (Tasks 01--23; local planning, not versioned)
│   ├── 05_refactor_tasks/             # Refactoring specifications (Tasks 01--40; local planning, not versioned)
│   ├── site/                          # Standalone mobo-linac.github.io web portal files
│   └── index.html                     # Project technical web portal
│
├── scripts/                           # Thin campaign, comparison & reporting entry points (CLI wrappers)
│   └── production/                    # Step-by-step paper production (01_preflight.sh ... 07_paper_outputs.sh)
├── tools/                             # Maintainer tooling (local CI check, cleanup, site sync)
├── notebooks/                         # Interactive analysis notebooks
├── tests/                             # Pytest suite (unit tests; ASTRA runs are marked `integration`)
└── results/                           # Optimization run output directories
```

### Package layering

Modules import only from their own or lower layers (enforced by `tests/test_package_layout.py`):

| Layer | Packages / modules |
| :--- | :--- |
| 0 core | `config`, `result_schema`, `diagnostics`, `display`, `conventions`, `perturbations`, `requests`, `evaluation`, `objectives`, `constraints`, `status`, `campaign_options`, `utils` (incl. `utils.durable`) |
| 1 storage | `io` (results, journal, checkpoints, run data, completion marker) |
| 2 analysis | `models`, `acquisition`, `metrics` (incl. `metrics.exports` run-artifact writer) |
| 3 backends & figures | `astra`, `execution`, `plotting` |
| 4 workflows | `campaigns`, `robustness`, `verification` |
| 5 interface | `cli` |

Function-level package imports are limited to CLI subcommands (each loads its workflow on demand)
and Matplotlib-backed plotting, which is imported only where figures are exported, so
`import mobo_linac.campaigns` does not load Matplotlib.


---

## Optimization Problem Formulation

### Design Variables (6)

The optimization controls six accelerator design parameters, which are written into `astra.in` before each ASTRA simulation:

| Index | Parameter Description | ASTRA Input Variable | Units / Details |
|:-----:|-----------------------|---------------------|-----------------|
| 1 | Solenoid Peak Field | `solenoid:maxb(1)` | Peak magnetic field [T] |
| 2 | Quadrupole 1 Gradient | `quadrupole:q_grad(1)` | Gradient [T/m] |
| 3 | Quadrupole 2 Gradient | `quadrupole:q_grad(2)` | Gradient [T/m] |
| 4 | RF Gun Phase | `cavity:phi(1)` | Phase [deg] |
| 5 | ACC1/ACC2 Common Phase | `cavity:phi(2)` & `cavity:phi(3)` | Common phase [deg] |
| 6 | ACC3/ACC4 Common Phase | `cavity:phi(4)` & `cavity:phi(5)` | Common phase [deg] |

---

### Objectives (3 Minimize)

The optimization simultaneously minimizes three primary beam quality metrics:

1. **Horizontal Normalized Emittance** ($\varepsilon_{n,x}$)
2. **Vertical Normalized Emittance** ($\varepsilon_{n,y}$)
3. **RMS Energy Spread** ($\sigma_E$)

*Note: Objective values are negated internally because BoTorch assumes maximization.*

---

### Constraints & Beam Diagnostics

Beam quality metrics and physical boundaries determine simulation feasibility:

* **Transverse RMS Beam Sizes**: $\sigma_x \le 1.0\text{ mm}$, $\sigma_y \le 1.0\text{ mm}$
* **Transverse RMS Divergence**: $\sigma_{x'} \le 1.0\text{ mrad}$, $\sigma_{y'} \le 1.0\text{ mrad}$
* **Longitudinal RMS Bunch Length**: $\sigma_z \le 1.0\text{ mm}$
* **Mean Kinetic Energy**: $195\text{ MeV} \le E_{\text{kin}} \le 205\text{ MeV}$

In **Phase 2**, feasibility is recorded and reported (feasible Pareto fronts and hypervolume), but constraint violations add no penalty and are not modeled. In **Phase 3**, constraints are explicitly modeled using separate Gaussian Process surrogate models for Probability of Feasibility computation.

The seven diagnostic channels share one canonical layout for parsing, feasibility, GP training, and acquisition constraints. Missing, conflicting, or nonfinite measurements are never replaced with favorable defaults. Constrained fitting uses complete measured rows with matching design/objective identities; see the [diagnostic observation policy](docs/simulation_guide.md#diagnostic-observation-policy).

Campaign results follow the configured design-variable and objective order through evaluation, streaming, tensors, checkpoints, and exports. Mixed minimize/maximize objectives retain their physical values in Pareto CSV files; missing objective measurements never receive synthetic defaults. Optional objective aliases and reporting scales are described in the [result schema contract](docs/simulation_guide.md#objective-and-result-schema-contract).

---

## Simulation & Optimization Workflow

```
         Parameter Vector (6D)
                  │
                  ▼
         Modify ASTRA Input File (astra.in)
                  │
                  ▼
         Run Parallel ASTRA Simulations
                  │
                  ▼
         Extract Beam Quality Statistics
                  │
                  ▼
         Evaluate Objectives & Constraints
                  │
                  ▼
         Update GP Surrogates (BoTorch)
                  │
                  ▼
         Optimize Acquisition Function (qLogNEHVI)
                  │
                  ▼
         Generate Next Candidate Batch
```

---

## Output Directory Structure

Each optimization run automatically generates a timestamped directory under `results/`:

```
results/YYYYMMDD_HHMMSS/
├── config.json            # Configuration parameters and runtime settings
├── train_X.csv            # Evaluated design parameter vectors
├── train_Y.csv            # Evaluated objective values
├── pareto.csv             # Compatibility alias of all-valid Pareto points
├── pareto_all.csv         # All-valid non-dominated points
├── pareto_feasible.csv    # Feasible-only non-dominated points
├── hypervolume.csv        # Fixed-reference raw hypervolume over iterations
├── metrics_history.csv    # Normalized hypervolume and measured runtime metrics
├── reporting_metadata.json # Reference, units, scales, signs and constraints
├── run_complete.json      # Completion marker with artifact checksums
├── candidate_history.csv  # Detailed history of candidate proposals
├── constraints.csv        # Diagnostic values and constraint statuses
├── work/eval_<id>/attempt_<uuid>/ # Fresh simulation inputs and outputs per attempt
├── provenance/eval_<id>/attempt_<uuid>/ # Retained manifests, input snapshots and hashes
├── gp_checkpoint/         # Saved PyTorch / GPyTorch GP model checkpoints
└── figures/               # Generated figures (Pareto front, hypervolume, etc.)
```

Each retry and independent rerun has a fresh attempt ID beneath its logical evaluation ID. Candidate records retain `attempt_id`, `manifest_path`, and retry history. Successful workdir cleanup retains provenance; resume uses completed journal/checkpoint records. Verification archives each run under `verification_runs/`, with root reports showing the latest completed verification. See the [attempt provenance contract](docs/simulation_guide.md#21-process-isolated-working-directories).

Run exports use one writer during iterations and finalization. `pareto.csv` always matches `pareto_all.csv`; use `pareto_feasible.csv` for feasible-only points. Reporting comparisons require matching recorded scientific conventions. Elapsed wall time is measured separately from summed simulation runtime, and completion is published after required datasets, checkpoints, and requested figures succeed. See the [artifact and reporting contract](docs/simulation_guide.md#run-artifact-and-reporting-contract).

---

## Prerequisites & Installation

The repository is self-contained with **pre-bundled ASTRA binaries** in `./bin/` and automated **`lume-astra` Python interface integration**.

### 1. Quick Setup (Single Command)

Clone the repository and install the package with all Python dependencies (including `lume-astra` directly from source):

```bash
git clone https://github.com/cspark7701/mobo-linac.git
cd mobo-linac
pip install -e .
```

### 2. ASTRA Binary Executables

The compiled ASTRA simulation binaries are integrated into the local `./bin/` directory:
- `bin/astra`: Main ASTRA tracking simulation executable.
- `bin/generator`: Particle distribution generator executable.

The executable, template input, static field/distribution files and template directory
are configuration data (`simulation:` section; relative paths are resolved against the
configuration file):

```yaml
simulation:
  template_dir: ".."
  input_template: astra.in
  static_files: [gun.dat, PAL_SOL_A.dat, TWS_Sband.dat, pal_photo2.ini]
  executable: "../bin/astra"
```

The executable is resolved from `simulation.executable`, then `$ASTRA_BIN`, then `PATH`;
a missing executable fails before any attempt directory is reserved. The resolved path is
passed to lume-astra explicitly and recorded (with its SHA-256) in every attempt manifest;
the process environment is never modified. To use an external build, point
`simulation.executable` at it (or remove that key and set `ASTRA_BIN`).

---

## Usage Examples & CLI Commands

The framework provides a unified console entry point `mobo-linac` (or `python -m mobo_linac.cli`). Omitted campaign options (initial samples, iterations, batch size, seed, acquisition) come from the configuration's `campaign` section and the worker count from `execution.max_workers`; the scripts under `scripts/` are thin wrappers with identical options and defaults. `run-validation` writes to `<output-dir>/validation_<timestamp>/`, and `analyze` exports the standard figures of a recorded run.

### 1. Run Phase 2 Unconstrained MOBO
```bash
mobo-linac run-unconstrained --config configs/publication_200MeV.yaml --n-iterations 300 -q 8 --num-workers 12
```

### 2. Run Phase 3 Constrained MOBO (Feasibility-Aware)
```bash
mobo-linac run-constrained --config configs/publication_200MeV.yaml --n-iterations 300 -q 8 --num-workers 12
```

### 3. Run Paired Multi-Seed Benchmark Campaign
```bash
mobo-linac run-benchmark --config configs/publication_200MeV.yaml --seeds 42 43 44 --budget 40 --num-workers 12
```

The benchmark dispatcher supports `constrained_qlognehvi`, `unconstrained_qlognehvi`, `qlogehvi`, and `scalarized_bo`; choose a subset with `--algorithms`. NSGA-II and Sobol-only benchmark executors are not implemented and are rejected. The budget includes initial samples and failed evaluations, with a smaller final batch when needed. Runs are skipped only when `benchmark_state.json` and persisted evaluation/metric counts confirm completion. The dispatcher does not automatically resume incomplete experiments or reconcile their benchmark completion markers; incomplete or incompatible outputs require a new output directory.

Independent algorithm/seed campaigns can run in spawned processes without changing their
scientific budgets or batch sizes. For two campaigns with four ASTRA workers each:

```bash
mobo-linac run-benchmark --config configs/publication_200MeV.yaml \
  --num-workers 4 --max-concurrent-campaigns 2 --total-workers 8 --campaign-threads 1 --device cpu
```

`--num-workers` caps workers per campaign; `--total-workers` is the global ASTRA cap
(defaults to `--num-workers`). The scheduler divides that cap across campaign slots,
rounding down, so allocated workers never exceed it. Sequential execution remains the
default. `--campaign-threads` limits PyTorch CPU threads in each spawned controller;
the global worker cap does not reserve GPU memory or limit custom evaluator internals.
Each child writes only its own run; the parent validates completion, maintains the manifest,
records PIDs/timings/errors in `scheduler.json`, and aggregates results after all jobs succeed.
An exclusive POSIX lock rejects competing schedulers/analysis for the same root. After a
failure, active jobs finish, new jobs remain pending, and failed artifacts are retained.
Completed runs can be skipped on a later invocation; incomplete runs still require investigation.
Custom evaluators used concurrently must be serializable; child-local changes are not reflected
back into the parent evaluator object. Process isolation preserves seeded RNG streams, while
floating-point fitting/proposal results may depend on device and thread configuration.

### 4. Run Robustness & Engineering Sensitivity Analysis
```bash
mobo-linac run-robustness --config configs/publication_200MeV.yaml --num-perturbations 50 --num-workers 12
```

Robustness CLI and script runs share complete evaluation requests and honor configured lattice mappings. Charge, laser spot-size, and pulse-duration jitter are sampled and retained as requested source scales, but are explicitly unsupported for the fixed `pal_photo2.ini` source; current physical scores cover applied lattice jitter. Request archives record seeds, requested/applied settings, unsupported channels, and exact attempt links. See the [robustness execution contract](docs/simulation_guide.md#42-machine--beam-perturbation-robustness-analysis).

### 5. Run Independent Pareto Candidate Verification Reruns
```bash
mobo-linac run-verification --config configs/publication_200MeV.yaml --output-dir results/verification
```

Verification uses the configured lattice mapping, exit checks, timeout, workers, and template. Pass `--num-workers`, `--timeout`, or `--template-dir` to override execution settings. Production mode requires measured candidate history; missing metrics and undefined relative errors cannot yield `VERIFIED`. Input snapshots and executable hashes are audited against each retained attempt. Explicit mocks use `MOCK_*` statuses and unknown physical hashes. See the [verification contract](docs/simulation_guide.md#43-independent-pareto-candidate-rerun-verification).

### 6. Resume Interrupted Campaign from Checkpoint
```bash
mobo-linac resume --run-dir results/<run_id>
```

Version 2 checkpoints restore the saved configuration, optimization mode, scalar weights, initial design, worker count, iteration plan, metric history, and proposal RNG state. Each batch's proposal and candidate IDs are saved before submission. Resume merges durable JSONL completions with checkpoint history, evaluates only missing candidates, and restores the original candidate order, including after interruption during the initial design. `--n-iterations` sets the total BO iteration target; `--batch-size` changes only batches proposed after the pending batch is recovered. Campaigns with a fixed evaluation budget retain that budget and adjust the remaining batch count.

Legacy version 1 checkpoints require an explicit `--n-iterations` target and, for scalarized BO, `--legacy-scalar-weights` containing the original weights. Their migration assumes fixed-size completed batches and cannot guarantee exact historical fallback or GPU RNG continuation. Legacy flat JSONL records are decoded directly; work beyond a checkpoint without a saved proposal is rejected rather than silently discarded. See [checkpoint continuation](docs/simulation_guide.md#33-checkpoint-continuation) for journal authority and corruption handling.

> **Tip**: Pass `--dry-run` to preview planned execution details without starting ASTRA simulations, or `--mock-evaluator` for fast CI testing without an ASTRA binary.


---

### Scripts and notebooks

The `scripts/run_*.py`, `scripts/run_comparison_and_verification.py` and
`scripts/generate_paper_figures.py` files are thin wrappers of the `mobo-linac` subcommands
(`run-*`, `run-robustness`, `run-verification`, `compare`, `paper-figures`) with identical
options. Candidate inputs use `--input` (`--history-path`/`--pareto-csv` are deprecated aliases).
The notebooks in `notebooks/` read recorded run directories (set by environment variables such
as `MOBO_PHASE2_DIR`) and call package functions; objective names, units, scales and weights
come from the recorded configuration. `tests/test_notebooks.py` executes them against mock runs.

### Logging

All package modules log through standard `logging` under the `mobo_linac` logger. The CLI flags
select the console level: `--quiet` (warnings and errors only), default INFO, `--verbose` (INFO
with timestamps) and `--debug` (DEBUG). Every campaign directory receives a `run.log` with
timestamps, levels and module names. Data-quality conditions that callers may assert (a
truncated journal tail, best-effort legacy resume, implicit run selection) are additionally
raised as Python warnings.

### Local validation

Install the development dependencies with `pip install -e ".[dev]"`, then run:

```bash
python -m pytest -m "not integration" --tb=short \
  --cov=mobo_linac --cov-report=term-missing --cov-fail-under=100
```

CI and `bash tools/check_github_actions.sh` require 100% package line coverage from
the non-integration suite. Tests use temporary campaign directories, mock evaluators
and recorded simulator fixtures; CUDA control paths are tested with mocks on CPU.
Real ASTRA and GPU execution require separate integration or hardware validation.

## Development Roadmap

- [x] **Phase 1: Scalarized BO**
  - Scalarized BO with multiple weight combinations
  - Comparison with MOGA
  - Parallel ASTRA execution & GP surrogate
- [x] **Phase 2: True Multi-Objective BO**
  - Independent GP models per objective (`ModelListGP`)
  - Pareto front optimization using `qLogNEHVI` / `qEHVI`
  - Hypervolume tracking & candidate history logging
- [x] **Phase 3: Constraint-Aware MOBO & High-Fidelity Refactoring (v1.0.0)**
  - Exact analytical Normal CDF multi-constraint feasibility modeling ($P_{\text{feas}}$)
  - Relative fixed noise variance scaling for multi-scale GP surrogates ($\mu\text{m}\cdot\text{rad}$ vs $\text{MeV}$)
  - Dynamic parameter mapping to arbitrary ASTRA namelists & cavity decoupling
  - Longitudinal exit-plane loss detection & premature beam loss trapping (`PREMATURE_BEAM_LOSS`)
  - Full-chain photocathode & laser jitter robustness modeling (7 physical noise channels)
  - Multi-tier resilient acquisition proposal engine with adaptive retry & Sobol fallback
  - Atomic POSIX crash-proof checkpoint serialization (`mobo_linac.io.durable`)
  - Centralized publication-grade LaTeX reporting module (`mobo_linac.metrics.latex`)
- [ ] **Phase 4: Distributed High-Performance Optimization**
  - Distributed ASTRA evaluations via Ray / Dask / MPI on multi-node clusters
- [ ] **Phase 5: Advanced Surrogate Architectures**
  - MultiTaskGP, SAASBO, TuRBO trust-region BO, Deep Kernel Learning

---

## Reproducibility

For comprehensive instructions on reproducing all computational benchmarks, verification results, and figures, please see the [REPRODUCIBILITY.md](REPRODUCIBILITY.md) guide.

---

## Citation & Conference Presentation

Preliminary scalarized Bayesian Optimization results were presented at **ICABU 2025**:
* *Multi-Objective Bayesian Optimization for a 200 MeV Electron Injector Linac*, ICABU 2025.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

### GP noise, fit outcomes, and saved models

GP observation variances use squared model-output units. `train_Yvar` must match
`train_Y` as `(N, M)`, contain finite strictly positive values, and takes precedence
over per-output variances and scalar fixed noise. `Standardize` scales both outcomes
and variances. The `fixed` alias and nominal deterministic relative formula remain
`max(1e-6 * Var(Y), 1e-24)`. `measured_fixed` requires explicit tensor or fixed noise;
`inferred` rejects explicit noise instead of ignoring it. Constraint observations
have their own `train_constraints_var` tensor; objective noise is never reused for
constraints. GPyTorch may clamp very small standardized noise for numerical stability;
artifacts retain both supplied output-space and effective standardized noise.

`fit_gp_models` keeps returning the model and exposes per-channel `fit_outcomes`:
`lbfgs`, `adam`, or `restored_prior`, plus errors and the available optimizer status.
Each optimizer starts from the same saved state. If both fail, that state is restored
and finite predictions are verified; an unusable prior raises. `pipeline.is_fitted`
means predictions are available; `is_optimized` excludes a restored prior. An Adam
step-limit stop remains visible in `optimizer_status`; it is not a convergence claim.

Campaigns save version-1 tensor/state artifacts under `gp_checkpoint/model_iter_*.pt`
before proposing a batch. Observation checkpoints separately record `model_artifact`
with its absolute path, SHA-256, and proposal iteration. Each artifact contains training
identities, inputs/outcomes, transforms, kernel/likelihood state, effective noise, fit
outcomes, and campaign metadata. It represents the observations used for that proposal,
which precede the new evaluations in the completed observation checkpoint. Random-only
runs have no model artifact. Resume keeps the recorded reference and continues the
existing observation-based refitting policy; it does not implicitly load saved models.
When moving a run, resolve the recorded artifact path to its new location explicitly.

Reload a pipeline without fitting or running ASTRA:

```python
from mobo_linac.models import SurrogatePipeline
pipeline = SurrogatePipeline.load_artifact("results/run/gp_checkpoint/model_iter_01_ID.pt", device="cpu")
mean, variance = pipeline.predict_objectives(X)
```

For individual scalarized GPs, use `save_model_artifact` and `load_model_artifact`
from `mobo_linac.models`. Artifacts use tensor/state dictionaries and `weights_only=True`
loading; unsupported versions fail. Prediction reproduction assumes a compatible
PyTorch/BoTorch/GPyTorch environment; full software environments are not bundled.

### Configuration resolution and validation

An omitted `--config` uses one discovery policy: search `./configs` first, then the
repository's `configs` directory, preferring `publication_200MeV.yaml`, then
`mobo_200MeV.yaml`. An explicit path must exist and never selects a fallback.
`resolve_config_path()` returns the actual absolute path; `load_config()` records it
in the declared provenance attribute `config.source_path` (never serialized). New campaigns write this
source separately in `config_source.json`; scientific configuration JSON/YAML and
checkpoint dictionaries retain their dataclass fields. Installed environments without
bundled configurations must supply a path. Explicit perturbation files use the same
resolver; omitted perturbation settings discover `perturbation_config.yaml`.

Dataclass annotations/defaults and shared field rules generate runtime field validation,
the exported JSON Schema, and the generated Markdown field inventory. Supported optional
fields retain `null` values, including fixed noise, per-objective noise vectors, coupling
targets, reporting scales, and the configuration name. Unknown fields fail instead of being
ignored. YAML unquoted scientific notation such as `195.0e6` is parsed as a number;
quoted numeric strings, booleans in numeric fields, NaN/Inf, and fractional counts fail.
JSON Schema describes field types/ranges; runtime validation additionally checks relations
such as bound ordering, objective signs/alias collisions, and noise-vector dimensions.
Always use `load_config()` or `config.validate()` before execution; loading validates
every field once and then the relational rules once.

Constraint bounds are generated from the diagnostic channel registry
(`mobo_linac.diagnostics.DIAGNOSTIC_CHANNELS`): each channel declares its bound field
names, defaults and admissible range, so adding a constraint channel needs only a registry
entry and YAML values; schema, documentation rows and figures follow. The nominal profile
is the top-level `constraints` section (`sensitivity_profiles` holds only the alternatives).
The exit plane lives in `tracking` (`z_stop_m`, `z_loss_tolerance_m`); archived layouts with
these fields under `execution` are migrated on load. Optional `benchmark:` (run-benchmark
defaults) and `perturbations:` (robustness specification, validated against the design
variables) sections are part of the schema. Acquisition names come from one enum
(`mobo_linac.campaign_options.Acquisition`).

Design bounds must be finite and **strictly increasing**. Fixed machine settings belong
in the ASTRA template, outside the optimization vector, until explicit fixed-variable
support is added. Optimizer budgets/workers/timeouts must be positive integers;
iterations and retries can be zero. Exit-plane distance must be positive and its loss
tolerance nonnegative. Scalar weights follow configured objective order and must be
finite, nonnegative, have matching dimensions, and contain a positive value; normalization
handles very large finite weights without overflow. The scalarized CLI accepts any
configured objective count. Suite cases are configuration data (`scalarized_cases`: label,
weights in objective order, stable `seed_offset`); a case's seed is `seed + seed_offset`, so it is
identical whether the case runs alone or in the full suite.
`qLogNEI` belongs to scalarized BO; scalarized BO does not support `constrained=True`.

Runner and CLI preflight rejects invalid settings before creating campaign output or
starting GP/ASTRA work. Evaluation requests validate finite parameter dimensions,
namelist override keys/values, and the three known positive source scales before
reserving ASTRA attempts. Valid source scales remain recorded as unsupported for the
fixed input particle distribution, as described in the robustness execution contract.

```bash
mobo-linac validate-config --config configs/mobo_200MeV.yaml \
  --export-schema /tmp/mobo_schema.json --export-docs /tmp/mobo_config.md
```

### Device selection and proposal recovery

`get_device()` and new campaigns share one CPU/CUDA policy. `None`, `auto`, and an
empty string select the current CUDA device when available, otherwise CPU. `cpu`
selects CPU; `cuda` selects the current CUDA index; `cuda:0` selects index zero.
String and `torch.device` inputs behave alike. Explicit CUDA requests fall back to
CPU with a logger warning when CUDA is unavailable. On available CUDA hardware,
an out-of-range index fails. Other device types are unsupported. Resume retains
the checkpoint device and CUDA RNG topology: `auto` uses that saved placement,
and an explicit different or unavailable device fails before artifact writes.
Legacy unindexed CUDA checkpoints retain the existing index-zero interpretation.

Objective transforms and reporting normalization preserve floating tensor dtype
and device, including reference points and sign/scale constants. Integer tensors
and sequence inputs use double precision. Campaign GP fitting and acquisition
optimization continue to use double precision on the resolved campaign device.

`generate_next_candidates()` returns a `ProposalResult`; existing
`candidates, acq_values = result` unpacking and two-value indexing still work.
`result.metadata` records the selected method, output/optimizer devices, each
attempt's effective restart/sample/options budget and outcome, failure reasons,
and Sobol positions. Candidate shape, finite values, and bounds are checked after
optimizer success; invalid output enters the same retry path as an exception.
The tiers are primary optimization, a reduced-budget retry, an isolated CPU copy,
then Sobol exploration. CPU fallback never moves the supplied acquisition or GP.
If a custom acquisition or BoTorch cache cannot be copied, that failure is recorded
and the Sobol tier remains available. `retry_on_failure=False` raises the primary
failure. Sobol acquisition values are zero placeholders for exploration proposals.

Campaigns use their seeded Sobol stream and persist its position together with
pending candidates and `proposal_history` in checkpoints. `proposal_history.json`
is an atomic, derived export with one entry per proposed batch, including the
initial design and low-data exploration. Recovery reuses pending metadata without
adding a duplicate entry. Older checkpoints may lack metadata; their history is
left unknown rather than inferred. Standalone calls without an owned stream use
`fallback_seed=0` by default, or a supplied seed, so repeated fallback calls are
reproducible independently of global random draws. Supply an owned engine to
continue a stream across calls.

Campaign/suite progress, device warnings, and GP/acquisition fallback messages use
the shared logger. `configure_logging(quiet=True)` suppresses progress and debug
messages while retaining warnings/errors; debug mode reports successful proposal
tiers. CLI verbosity flags configure the same logger.

### Publication reports and recorded run data

`mobo_linac.io.run_data.read_run_data()` loads configuration, measured candidate
history, `reporting_metadata.json`, and `hypervolume.csv`. JSON history takes
precedence over candidate-history CSV, then evaluations CSV. Reports preserve
recorded `(run_id, evaluation_id)` identities and feasibility; they do not infer
successful or feasible beams from `train_X.csv`, `train_Y.csv`, or a Pareto filename.
Existing completion markers are checked against their artifact checksums. Recorded
hypervolume references/counts must agree with metadata and measured history.

`RunData.pareto()` reconstructs the all-valid front; `RunData.pareto(feasible=True)`
reconstructs the feasible front. Paper Pareto plots consistently use the feasible
front and tables identify both cardinalities. `campaign_summary()` uses all history
for evaluation counts and feasibility percentages, and feasible observations for
objective extrema and knee solutions. It also exposes the fraction of valid
observations that are feasible. The feasible-fraction plot retains that latter
quantity and labels its denominator and valid-observation axis explicitly.
Option 2 case summaries retain separate all-valid and feasible extrema, with
feasibility percentages calculated over all evaluations.

`read_comparable_runs()` rejects differing reference points, scales, objective
names/order/signs/units, design columns, and constraint profiles before generating
comparison artifacts. Older campaigns without reporting metadata require a complete
convention supplied explicitly to `read_run_data(..., legacy_reporting_metadata=...)`;
pass the resulting `RunData` objects to package campaign-table services. Archived
outputs are never automatically migrated. The paper CLI requires recorded metadata,
and includes Phase 1 only when `--phase1-dir` is supplied.

Shared publication statistics and Markdown/campaign tables live in
`mobo_linac.metrics.publication`; verification, robustness, and Option 2 LaTeX
renderers live in `mobo_linac.metrics.latex`. Script exporters delegate to these
services and retain manuscript labels and filenames. Hypervolume is formatted in
scientific notation; absent measurements render as `--`. Canonical SI measurements
use explicit emittance/energy conversions; custom objectives retain recorded units.
Dynamic LaTeX text uses `escape_latex()`. Captions with deliberate math/commands can
use the explicit trusted `RawLatex` wrapper; role, case, and status strings are
escaped as text. Verification records retain failed, unknown, and `MOCK_*` statuses
without automatic reproducibility claims.

Robustness and verification entry points share candidate discovery: explicit missing
inputs fail; omitted inputs select the newest measured run history with the same
JSON/CSV preference. Explicit Pareto CSV inputs join sibling history to recover
identities and statuses. Bare legacy Pareto CSVs retain unknown validity/feasibility
and are not silently promoted to measured feasible candidates. The comparison script
uses the existing audited verification service. Report generation does not modify
source campaigns or aggregate missing case files into archived directories; tests
generate manuscript artifacts under temporary paths.

### Production launcher and campaign planning

The [strategic simulation campaign plan](docs/strategic_simulation_campaign_plan.md)
defines pilot gates, paired seed/budget comparisons, candidate audits and resource
accounting. For the paper campaign, run the
[step scripts](scripts/production/README.md) `scripts/production/01_preflight.sh` through
`07_paper_outputs.sh` one at a time. They write logs and outputs to
`results/paper_production/` and enforce the stage order, a clean tree and free disk space.
`scripts/run_full_production.sh` runs the Option 2 suite, unconstrained
and constrained MOBO, comparison/verification, then feasible-candidate robustness.
It uses one explicit reporting reference and configuration across phases, respects
custom executable overrides, retains step logs, and accepts `--dry-run` for a
command preview without outputs. Set `PYTHON_BIN` to the installed environment's
interpreter. `--resume` uses saved-state continuation; `--iterations` sets the total
target. Analysis uses the saved Phase 3 configuration on continuation.

```bash
bash scripts/run_full_production.sh --dry-run --p1-case balanced \
  --iterations 2 --initial-samples 8 --batch-size 4 \
  --output-dir results/pilot_200MeV_seed42
```

New-run CLI commands accept `--reporting-ref-point` in model-space units and
configured objective order. The nominal shared reference is
`-0.0000015 -0.0000015 -1500000`; custom objective conventions require a matching
reference. Option 2 cases share the supplied reference. Their aggregate has a
larger evaluation budget than either MOBO phase; use paired benchmarks for an
equal-budget algorithm comparison.

Campaign imports and mock/report workflows do not initialize ASTRA, discover
executables into environment variables, or patch distgen. Real attempts initialize
the optional backend inside the isolated worker. `resolve_executable_path()` is a
read-only discovery helper. Evaluators share serializable `EvaluationRequest`
objects and typed `EvaluationCompletion` records through
`mobo_linac.execution.contracts.evaluate_requests()`. Every backend implements one
protocol, `evaluate(requests, run_id, on_complete)`: `ProcessPoolEvaluator` (ASTRA,
persistent process pool of spawned workers, so the threaded parent is never forked; every worker
count is process-isolated, `in_process=True` is an explicit debugging opt-in), `MockEvaluator` (deterministic responses for any
configured objective/diagnostic layout) and `FunctionEvaluator` (adapts a per-request
callable while preserving submitted identities). Campaigns, robustness and verification
accept the same evaluator object. The adapter validates candidate identity/parameters,
rejects conflicting completions and returns request order.
