# Unified Simulation Procedure and Publication Workflow Guide

This document provides a single, comprehensive reference for the simulation procedure, accelerator physics specifications, Multi-Objective Bayesian Optimization (MOBO) architecture, statistical benchmark campaign protocol, robustness analysis, independent Pareto candidate verification, and manuscript reproduction workflow for the **200 MeV S-Band Electron Injector Linac**.

---

## 1. Accelerator Physics & Design Specifications

### 1.1 Injector Linac Architecture
The 200 MeV electron injector linac consists of:
- **RF Photo-Gun**: S-band 1.5-cell RF gun with photocathode driven by a UV laser pulse ($Q = 250\text{ pC}$, $N = 10,000$ macroparticles).
- **Solenoid Magnet**: Peak solenoidal focusing field $B_{\text{sol}}$ for transverse emittance compensation.
- **Accelerating Structures**: Four S-band traveling-wave structures (ACC1--ACC4) arranged in two coupled RF phase pairs ($\phi_{\text{acc1/2}}$ and $\phi_{\text{acc3/4}}$).
- **Quadrupole Doublets**: Two quadrupole magnets ($G_{q1}$ and $G_{q2}$) for final beam envelope matching.

### 1.2 Continuous 6D Design Variables
The optimization controls six accelerator parameters written into `astra.in`:

| Variable | Description | ASTRA Keyword | Bounds | Unit |
| :--- | :--- | :--- | :--- | :---: |
| $B_{\text{sol}}$ | Solenoid Peak Field | `solenoid:maxb(1)` | $[0.097400, 0.292200]$ | T |
| $G_{q1}$ | Quadrupole 1 Gradient | `quadrupole:q_grad(1)` | $[0.643300, 1.929800]$ | T/m |
| $G_{q2}$ | Quadrupole 2 Gradient | `quadrupole:q_grad(2)` | $[-4.330028, -1.443343]$ | T/m |
| $\phi_{\text{gun}}$ | RF Gun Phase | `cavity:phi(1)` | $[32.05800, 39.18200]$ | deg |
| $\phi_{\text{acc1/2}}$ | ACC1/2 Coupled Phase | `cavity:phi(2,3)` | $[-43.46100, -35.55900]$ | deg |
| $\phi_{\text{acc3/4}}$ | ACC3/4 Coupled Phase | `cavity:phi(4,5)` | $[279.0450, 341.0550]$ | deg |

*Note: Quad 2 bounds are strictly ordered $L \le U$ ($[-4.330028, -1.443343]$).*

### 1.3 Objective Functions
Three beam quality metrics are simultaneously minimized at the linac exit plane ($s = 16.20\text{ m}$):
1. **Horizontal Normalized Emittance** ($\varepsilon_{n,x}$): $[\text{m}\cdot\text{rad}]$
2. **Vertical Normalized Emittance** ($\varepsilon_{n,y}$): $[\text{m}\cdot\text{rad}]$
3. **RMS Energy Spread** ($\sigma_E$): $[\text{eV}]$

*Model Space Transformation*: $\mathbf{y}_{\text{model}} = -\mathbf{y}_{\text{phys}}$ for BoTorch maximization.

### 1.4 Beam Quality Constraints
Beams must satisfy 8 physical constraints to be classified as physically feasible:
- $\sigma_x, \sigma_y \le 1.0\text{ mm}$
- $\sigma_{x'}, \sigma_{y'} \le 1.0\text{ mrad}$
- Longitudinal bunch length $\sigma_z \le 1.0\text{ mm}$
- Mean Kinetic Energy $195.0\text{ MeV} \le E_{\text{kin}} \le 205.0\text{ MeV}$
- Beam Transmission Fraction $\eta_{\text{trans}} \ge 90\%$

---

## 2. ASTRA Simulation & Execution Procedure

### 2.1 Process-Isolated Working Directories
To eliminate file race conditions during multi-core parallel evaluations, every ASTRA simulation executes inside a dedicated working directory:
$$\mathcal{D}_i = \text{\texttt{results/<run\_id>/work/eval\_00000i/attempt\_<uuid>/}}$$

Each directory contains:
- Regenerated `astra.in`
- Clean copies of static field maps and particle distributions (`gun.dat`, `PAL_SOL_A.dat`, `TWS_Sband.dat`, `pal_photo2.ini`)
- Isolated simulation log and output files (`astra.Log`, `astra.out`)

Every retry and independent rerun uses a new UUID attempt ID beneath a stable logical evaluation ID. Existing preparation destinations and manifest files are rejected instead of overwritten. Failed attempts retain their own outputs, preventing stale files from entering a retry. Resume reuses accepted journal/checkpoint records and does not prepare their workdirs again.

Retained provenance lives at `results/<run_id>/provenance/<eval_id>/<attempt_id>/`:

- `attempt_started.json` records reservation, logical identity, retry index, parameters, and start time.
- `inputs/` contains copies of effective input bytes, including dereferenced field maps/distributions, before execution.
- `inputs_after_execution/` records those input files after the simulator returns.
- `manifest.json` records status, parameters/overrides, timing, objectives, diagnostics, workdir, input/output SHA-256 hashes, and the resolved executable path/hash when available. Unknown executable hashes remain unknown.

Candidate CSV/JSON, journals, and checkpoints link the exact accepted `attempt_id` and `manifest_path`; worker results also retain every retry's manifest link. Successful cleanup removes only the workdir after its final manifest exists, preserving input snapshots and hashes. Output files are disposable when cleanup is requested; their hashes remain. Interrupted attempts can retain a start record without a final manifest and must not be treated as completed evaluations. Provenance capture failures produce failed evaluations and retain the workdir.

`read_evaluation_manifest(path)` accepts an exact manifest file or a directory containing `manifest.json`, including the old `work/<eval_id>/manifest.json` layout. It does not guess which attempt was accepted. Cleanup of a legacy workdir with a manifest first retains the old manifest and file snapshots under `provenance/<eval_id>/legacy/`; historical archives are not rewritten automatically. Old evaluation records remain readable with unknown attempt links.

Independent verification retains unique rerun records and report sessions under `verification_runs/verification_<uuid>/`. Returned report paths identify that archived session. Root `verification_summary.csv`, `verification_manifest.json`, and `verification_table.tex` remain compatibility views of the latest completed report, while earlier sessions remain intact.

### 2.2 Strict Evaluation Failure Semantics
Numerical simulation validity (`simulation_valid`) is strictly separated from physical beam feasibility (`physically_feasible`).

The simulator adapter reports a typed `SimulationStatus` (`mobo_linac.status`). Execution exceptions are classified by exception type and the runtime's recorded run information, never by message text. The status is stored unchanged in worker results and attempt manifests; archived lowercase `success`/`timeout`/`failed` values are still decoded. Each non-success status maps to one `FailureCategory`:

| Simulation status | Failure category | Retried by default |
| --- | --- | --- |
| `TIMEOUT` | `ASTRA_TIMEOUT` | yes |
| `WORKER_CRASH` | `WORKER_CRASH` | yes |
| `PROVENANCE_ERROR` | `PROVENANCE_FAILURE` | yes |
| `UNHANDLED_EXCEPTION` | `UNHANDLED_EXCEPTION` | yes |
| `RUN_FAILED` (started, no finished simulation) | `NONZERO_RETURN` | no |
| `PREMATURE_LOSS` | `PREMATURE_BEAM_LOSS` | no |
| `CHARGE_ZERO` (complete loss) | `EMPTY_OUTPUT` | no |
| `NUMERICAL_ERROR` | `NAN_INF_DIAGNOSTICS` | no |
| `OUTPUT_MISSING` / `FILE_CORRUPTED` | `MISSING_OUTPUT` / `CORRUPTED_OUTPUT` | no |

`execution.retry_statuses` selects which statuses start a fresh attempt (bounded by `execution.retries`); each attempt-history entry records whether it was retried. The configured `execution.timeout_sec` is passed to the ASTRA runtime for every attempt.

For successful simulations, measured values are then classified:
- **`MISSING_OUTPUT`**: a configured objective or a canonical diagnostic channel was not observed $\implies$ Invalid simulation.
- **`PREMATURE_BEAM_LOSS`**: tracking terminated before the exit screen ($z_{\text{final}} < Z_{\text{stop}} - \Delta z_{\text{tol}}$, both from configuration) $\implies$ Invalid simulation.
- **`NAN_INF_DIAGNOSTICS`**: non-finite objectives or canonical diagnostics, or values outside a channel's physical range (e.g. negative RMS size) $\implies$ Invalid simulation.
- **`INVALID_TRANSMISSION`**: transmission $< 0\%$ or $> 100\%$ $\implies$ Invalid simulation.
- **`INFEASIBLE_BEAM`**: valid simulation violating configured beam quality constraints, including transmission below `min_transmission`; the reason lists the violated channels $\implies$ Valid simulation, infeasible beam.

`diagnostics` contains only the seven canonical constraint channels. Auxiliary observations (`z_final_m`, particle counts) are stored separately as `telemetry`.

---

## 3. Multi-Objective Bayesian Optimization Architecture

```text
               Parameter Vector (6D)
                        │
                        ▼
       Isolated Working Directory Setup
                        │
                        ▼
               Parallel ASTRA Run
                        │
                        ▼
      Extract Beam Statistics & Diagnostics
                        │
                        ▼
     Evaluate Objectives & Constraint Status
                        │
                        ▼
  Update Independent ARD Matérn-5/2 GP Surrogates
   (Relative Noise Scaling: σ_obs² = η · Var(Y))
                        │
                        ▼
  Optimize qLogNEHVI / qLogEHVI Acquisition Function
   (Multi-Tier Resilient Retry & Sobol Fallback)
                        │
                        ▼
      Propose Next Candidate Batch (q = 4)
                        │
                        ▼
  Atomic POSIX Checkpoint State Persistence
```

### 3.1 Surrogate Modeling & Feasibility
- **Kernel**: Independent Matérn-5/2 ARD kernel ($\nu = 2.5$) for each objective and constraint diagnostic.
- **Relative Noise Scaling**: Empirical variance-scaled observation noise $\sigma_{\text{obs}}^2 = \max(\eta \cdot \text{Var}(Y_m), \sigma_{\text{floor}}^2)$ with $\eta = 10^{-6}$ and floor $10^{-24}$, preventing over-smoothing across disparate physical scales ($\mu\text{m}\cdot\text{rad}$ vs $\text{MeV}$).
- **Analytical Feasibility ($P_{\text{feas}}$)**: Exact multi-channel Normal CDF formulation in `SurrogatePipeline`:
  $$P_{\text{feas}}(\mathbf{x}) = \prod_{i=1}^5 \Phi\left(\frac{\text{max}_i - \mu_i}{\sigma_i}\right) \cdot \left[\Phi\left(\frac{E_{\text{max}} - \mu_E}{\sigma_E}\right) - \Phi\left(\frac{E_{\text{min}} - \mu_E}{\sigma_E}\right)\right] \cdot \Phi\left(\frac{\mu_T - T_{\text{min}}}{\sigma_T}\right)$$
- **Resilient Acquisition Optimization**: Configurable multi-restart L-BFGS budget with automatic adaptive retry and quasi-random Sobol fallback on numerical singularities.
- **Atomic Checkpoint Serialization**: Atomic POSIX replace (`_atomic_torch_save`) preventing checkpoint corruption from process termination.

#### Diagnostic Observation Policy

`mobo_linac.diagnostics.DIAGNOSTIC_CHANNELS` defines the physical diagnostic layout. Configured thresholds and the existing analytical feasibility formulas are preserved.

| Order | Canonical name | Legacy alias | Unit | Configured constraint |
| --- | --- | --- | --- | --- |
| 0 | `sigma_x_m` | `sigma_x` | m | upper RMS size |
| 1 | `sigma_y_m` | `sigma_y` | m | upper RMS size |
| 2 | `sigma_xp_rad` | `sigma_xp` | rad | upper divergence |
| 3 | `sigma_yp_rad` | `sigma_yp` | rad | upper divergence |
| 4 | `sigma_z_m` | `sigma_z` | m | upper bunch length |
| 5 | `mean_kinetic_energy_eV` | `mean_kinetic_energy` | eV | lower and upper energy |
| 6 | `transmission_fraction` | `transmission` | dimensionless | lower transmission |

Aliases normalize to canonical names at ingestion; conflicting canonical/alias values are invalid. Missing measurements remain absent, invalid supplied measurements remain nonfinite, and empty ASTRA arrays never become observed zero RMS values. Transmission remains derived from measured particle counts when available, with explicit transmission statistics as the existing fallback. New evaluations require all seven finite channels; missing observations invalidate the evaluation. Negative RMS values and transmission outside `[0, 1]` are invalid observations, while complete measurements outside configured quality thresholds remain valid but infeasible.

`get_training_observations(..., require_diagnostics=True)` returns one complete-case selection containing run/evaluation identities and aligned design, objective, feasibility, and diagnostic tensors. Missing or invalid channels exclude the entire row from constrained fitting without imputation. Fewer than two complete rows use the campaign's existing Sobol low-data branch. Objective-only selection can retain finite archived objective observations even if their diagnostics were not saved; stored archives and their metadata are not rewritten. `get_constraint_tensors` returns only complete diagnostic rows, so callers needing matching designs/objectives should use the shared selector.

Observed feasibility requires complete diagnostics. Violation reports use positive infinity for missing or invalid channels rather than a fabricated measured violation. Acquisition constraint offsets come from the objective output count; the eight inequalities retain their existing order. `SurrogatePipeline` defaults to `constraint_layout="diagnostics"` and rejects nonfinite, unphysical, or misaligned training matrices before GP construction. Generic zero-threshold constraints must explicitly select `constraint_layout="residual"`; their interpretation no longer changes merely because there happen to be seven outputs.

The full config-derived objective/extraction/export schema, including noncanonical empty tensor shapes, remains Task 05. This diagnostic refactor does not change nominal beam settings, engineering thresholds, objective definitions, or units.

### 3.2 Phase 1: Scalarized Bayesian Optimization Procedure
- **Objective Scalarization**: Linear weighted sum formulation:
  $$f(\mathbf{x}) = \sum_{i=1}^3 w_i \cdot y_{i,\text{norm}}(\mathbf{x}) = w_1 \varepsilon_{n,x} + w_2 \varepsilon_{n,y} + w_3 \sigma_E$$
  where weight combinations $\mathbf{w} \in \Delta^2$ control the optimization priority along the Pareto trade-off curve.
- **Single-Objective GP Surrogate**: Single `SingleTaskGP` with Matérn-5/2 ARD kernel modeling the scalarized merit function.
- **Acquisition Function**: `qLogNoisyExpectedImprovement` (`qLogNEI`) for parallel candidate selection ($q \ge 1$).
- **Interactive Notebook**: [`notebooks/phase1_scalarized_bo.ipynb`](file:///home/cspark/Work/projects/mobo_linac/notebooks/phase1_scalarized_bo.ipynb).
- **Execution Script**: [`scripts/run_scalarized_bo.py`](file:///home/cspark/Work/projects/mobo_linac/scripts/run_scalarized_bo.py).

---

### 3.3 Checkpoint Continuation

Version 2 campaign checkpoints record the run identity, full configuration, optimization mode and normalized scalar weights, initial sample count and physical design, actual Sobol draw position, CPU Torch/NumPy/Python and CUDA RNG states, evaluation batch membership, complete metric records, worker count, planned iterations, and optional evaluation budget. Failed evaluations remain in their original batches; valid-data filtering does not shift historical iteration boundaries.

```bash
# Recover pending work and continue the saved campaign plan.
mobo-linac resume --run-dir results/<run_id>

# Extend a campaign without a fixed evaluation budget to 20 total BO batches.
mobo-linac resume --run-dir results/<run_id> --n-iterations 20

# Override the size of batches proposed after pending work is recovered.
mobo-linac resume --run-dir results/<run_id> --batch-size 2
```

The checkpoint configuration is authoritative, including when the CLI runs outside the project directory. The runner rejects changes to design-variable order, bounds and ASTRA mappings, objective definitions/signs, constraints, model settings, execution settings other than worker count, reporting scales, or run identity before writing artifacts. Existing configuration and environment metadata are preserved. The default device restores the saved device; CPU/GPU transitions and incompatible CUDA topology are rejected. Exact continuation depends on the same numerical environment and deterministic proposal/evaluation behavior.

Explicit initial-count, seed, optimization-mode, acquisition, scalar-weight, and total-budget changes are rejected. Worker count can be overridden. Batch-size changes preserve completed batches and the already submitted pending proposal, affecting later proposals only. With a fixed evaluation budget, the runner computes the remaining batches from the actual evaluation count and saved pending count, including failures, and keeps a smaller final batch when needed; an explicit iteration target must agree with that budget and include the pending batch.

Version 1 migration is explicit and emits a warning. It infers initial count and batch membership using the old fixed-size completed-batch contract, reconstructs metrics from raw evaluation prefixes, and estimates Sobol consumption for the low-data branch. Supply the original planned iteration target with `--n-iterations`; scalarized checkpoints also require `--legacy-scalar-weights`, for example `0.6 0.3 0.1`. Legacy checkpoints did not record acquisition fallback draws, Python RNG, CUDA RNG, or the original device, so migration is best effort on CPU and cannot guarantee exact continuation.

Before submitting each batch, the runner atomically saves `checkpoints/pending_batch.pt`: the completed base history, proposal candidates and IDs, batch index, and post-proposal RNG/Sobol state. The initial pending snapshot uses iteration `-1` with empty completed history, allowing recovery before checkpoint 0. A pending proposal is removed only after its complete batch checkpoint is durable. If interruption occurs after the checkpoint commit but before removal, resume verifies that the checkpoint covers the proposal and clears it without repeating evaluations.

`evaluations_stream.jsonl` is authoritative for individual completions. Its version 1 envelope separates `evaluation` fields from `batch_idx` and `candidate_idx`. The reader also migrates legacy flat JSONL records in memory and never falls back to the lossy CSV view. Resume merges records by run/evaluation identity, verifies candidates and batch positions, and submits only missing IDs. Successful and failed completions both count as finished work. Completion order does not change the order of training data or metrics.

Identical duplicate records are deduplicated; conflicting duplicates, malformed interior JSON, invalid schemas, or records that disagree with the checkpoint/proposal raise errors before recovery writes or submissions. Only an incomplete, unterminated trailing JSON record is tolerated, with a warning, and its partial bytes are removed after validation before appending. A complete JSON record without a newline is retained and delimited before later appends. Legacy streamed work beyond a checkpoint without a durable proposal cannot be recovered safely and is rejected.

The campaign parent is the single journal writer. JSONL writes are flushed and synced before the CSV view is atomically regenerated; a stale or missing CSV cannot change recovery. Callback persistence errors propagate through sequential, process-pool, and mock evaluators and stop campaign completion. Evaluators without completion callbacks can still recover whole returned batches, but cannot journal individual results before their batch returns. Only durably journaled work is reused; a solver completion lost before its callback was persisted may need evaluation again. Concurrent campaign writers in the same directory are unsupported.

Benchmark dispatch still requires a new directory for incomplete experiments. Campaign resume does not automatically reconcile benchmark-level metrics or completion markers.

### Objective and result schema contract

`ResultSchema.from_config(config)` freezes the ordered design columns, physical and model objective columns, accepted aliases, signs, and engineering scales. The campaign carries that order through evaluation, complete-case training, streaming CSV, JSON history, checkpoints, Pareto exports, and objective plots. Pass `config=` (or the schema itself) to result I/O and tensor helpers for custom layouts; omitted configuration explicitly selects the legacy six-variable, three-objective linac contract, independent of the current directory.

Each objective accepts its `name`, `explicit_name`, and optional `aliases`. Canonical emittance objectives also accept `emit_x` and `emit_y`. Aliases must identify only one objective. Missing required objectives leave both objective vectors absent; nonfinite, nonnumeric, or conflicting supplied aliases invalidate the evaluation. ASTRA objective extraction uses observed final statistics with these names; aliases do not convert units.

Physical minimization uses `model_sign: -1`; maximization uses `model_sign: 1`. Both transformations validate the objective width and use the configured signs. Physical Pareto values and reference-point metadata restore those signs. Empty results retain configured tensor dimensions and CSV headers. Canonical model headers remain `model_emit_x_neg`, `model_emit_y_neg`, and `model_sigma_energy_neg`; custom objectives use `model_<name>_neg` or `model_<name>_pos`.

Scalarized BO defaults to equal weights across the configured objectives. Supplied weights must have that width, be finite and nonnegative, and have a positive sum. Optional `reporting_scale` is a finite positive engineering scale in the objective's physical units. The canonical objectives retain scales `1e-6`, `1e-6`, and `1e6` in configured order; other objectives default to `1.0` unless a scale is provided. Saved scales participate in resume compatibility checks. Hypervolume tracking retains its existing fixed, unnormalized campaign reference point.

CSV loading binds named columns and supports earlier named model headers and NumPy's `# ` header prefix. It never guesses values by position or infers validity/feasibility from a filename. Missing status fields remain `None` (unknown) and are excluded from default training and feasible selection. Use a campaign's candidate history for observed status metadata; robustness CLI directory inputs prefer that history over its compact Pareto CSV. Unknown feasibility requires fresh evidence before feasible-only analysis. JSON history and journal payload formats are preserved.

### Run artifact and reporting contract

`RunArtifactWriter` owns iteration and final datasets. `pareto_all.csv` contains the non-dominated set of valid finite objective observations; `pareto_feasible.csv` contains the non-dominated set of valid, observed feasible points. `pareto.csv` always aliases `pareto_all.csv`, preserving the previous completed-run meaning throughout the run. Physical objective signs and configured columns apply to both sets. CSV files use ordinary named headers and retain headers when empty; rewriting an empty set clears previous rows. The low-level `save_evaluation_results` helper delegates to this writer but does not certify campaign completion.

`reporting_metadata.json` records schema version, objective names, units, signs, scales, raw and normalized model-space reference points, design columns, constraint thresholds, reference origin, and hypervolume spaces. `hypervolume.csv` retains raw model-space hypervolume over iterations. `metrics_history.csv` reports dimensionless hypervolume at the same reference divided by the recorded engineering scales. Adaptive acquisition references remain independent and do not replace the reporting reference.

The scientific decision for this refactor is to preserve the existing reference conventions and make their scope explicit:

- Ordinary campaigns derive the reporting reference from initial observations with the existing 10% offset and then freeze it. A caller may supply an explicit model-space `reporting_ref_point`; resume must retain the saved reference.
- Benchmarks retain `BenchmarkConfig.reporting_ref_point`, interpreted in normalized physical space, and pass its signed, scaled model-space equivalent to the campaign. The canonical default `[1.5, 1.5, 1.5]` corresponds to `[1.5 μm·rad, 1.5 μm·rad, 1.5 MeV]`, not millimetre emittance values.
- New scalarized suites derive the reference from the first case's initial design and explicitly reuse that recorded value for subsequent cases. Suite aggregation no longer selects a new reference from pooled observations.
- The standalone normalized metric helper retains its legacy `[-10, -10, -10]` default for explicit compatibility use. Production campaign writers supply the recorded reference; the helper default is not a universal cross-run convention.

No new engineering scales or historical references are selected for archived data. Comparison and aggregation require complete matching metadata, including reference values, objective order, units, signs, scales, and constraints. Scale comparison is exact, avoiding an absolute tolerance that could hide differences in micrometre scales. Missing metadata is not filled from defaults. New benchmark/suite aggregation requires verified completion markers; archived outputs remain available to existing publication readers and are not rewritten or silently migrated. Reanalysis of legacy runs requires an explicitly established scientific reporting convention.

Wall time comes from a monotonic campaign timer, independently of `EvaluationResult.runtime_s`. Completion observations are recorded per logical evaluation; simultaneous workers can share a measured elapsed time while their runtimes sum separately. Checkpoints retain elapsed time and observations across active resume sessions. Shutdown downtime is excluded. Time lost after the last durable checkpoint cannot be reconstructed; legacy checkpoints without timing evidence label the observed resume session explicitly. Unknown wall time stays empty/NaN, including pooled suites; it is never replaced by worker-time sums. `metrics_history.csv` contains time measured at its export snapshot; the final marker records elapsed time through finalization.

`run_complete.json` is published atomically after required datasets, configuration, checkpoint, and requested figures exist. It records the evaluation count, final elapsed time, and SHA-256 checksums. Each new write/resume invalidates the preceding marker; failed exports or figures cannot leave a new completed marker. Consumers verify the registered artifacts before treating new runs as complete. The durable proposal/checkpoint/journal recovery protocol remains authoritative for optimization continuation.

## 4. Benchmark, Robustness, Verification, & Publication Workflow

### 4.1 Seed-Paired Benchmark Campaign Protocol
- **Supported Algorithms**: `constrained_qlognehvi`, `unconstrained_qlognehvi`, `qlogehvi`, `scalarized_bo`, `nsga2`, `sobol`.
- **Seed Pairing**: Identical initial Sobol candidate points generated per seed $s$.
- **Statistical Aggregation**: Median hypervolume trajectories and 95% bootstrap confidence intervals ($B = 1000$ resamples).

### 4.2 Machine & Beam Perturbation Robustness Analysis

The planner samples the existing seven noise sources from `configs/perturbation_config.yaml`: gun/cavity phases, solenoid/quadrupole fields, bunch charge, laser spot size, and pulse duration. Standard deviations and random draw order are unchanged. Lattice channels retain their degrees or relative-field interpretation. The six canonical design-variable names identify these channels; configured variable order, ASTRA keys, and coupled targets are honored. Other design layouts require an explicit jitter model and are rejected instead of assigning the six-channel model by position.

The template's `NEWRUN:Distribution` reads the fixed `pal_photo2.ini` particle distribution. The current executor has no verified source-generation mapping for `bunch_charge_scale`, `laser_spot_scale`, or `laser_pulse_duration_scale`. Those scales travel with the complete request and remain recorded, but charge, spot-size, and pulse-duration jitter are **unsupported** and do not alter the source distribution. The planner does not invent `charge:q_total` or generator keys. An explicit source-generation implementation and physical validation are required before these channels can be counted as evaluated.

`EvaluationRequest` carries parameters, evaluation identity, per-task namelist overrides, source settings, and perturbation metadata through sequential and process-pool execution. `EvaluationTask.to_request()` and `BatchEvaluator.evaluate_requests()` preserve that payload. Explicit overrides apply after configured lattice assignments; rejected overrides fail the attempt instead of being silently ignored. Manifests record successful namelist assignments, requested deltas, and applied lattice deltas only when all configured targets retain the requested value. Failed simulations do not contribute to the report's evaluated-channel list.

The CLI and `scripts/run_robustness_analysis.py` share one planner/executor/report workflow. Both load candidate history with the configured result schema, require measured validity/feasibility for Pareto selection, and never create synthetic nominal candidates for real execution. Directory inputs to the CLI prefer candidate history; the script accepts a candidate-history CSV through `--pareto-csv`. Compact Pareto CSVs without observed status are insufficient for feasible candidate selection. Both entry points expose `--dry-run` and `--mock-evaluator`.

Seeds are retained per candidate and sample. The historical CLI/script convention uses the supplied seed for each representative role. Direct multi-candidate `RobustnessEvaluator` plans retain `seed + candidate_index * 100`. Identical seeds/specifications produce identical complete requests; all-zero jitter leaves lattice values and source scales nominal. UUID attempt/report allocation is separate from these reproducible scientific draws.

Each evaluation session retains `robustness_runs/robustness_<uuid>/robustness_requests.json` and `robustness_summary.json`, recording configuration, specification, complete requested state, unsupported-channel reasons, applied settings, result/attempt links, and backend kind. CSV summaries include `perturbation_scope`, `unsupported_channels`, `evaluated_channels`, `execution_kinds`, `full_requested_jitter_evaluated`, and `request_manifest_path`. Root `robustness_summary.csv` and `robustness_table.tex` remain latest-report compatibility outputs; retained sessions are not replaced. LaTeX captions identify unsupported source jitter and synthetic mock execution.

Current physical scores describe **applied lattice jitter**, not full-chain source robustness. Mock or legacy custom backends without application evidence never claim evaluated physical channels. Legacy three-argument custom evaluators remain available for lattice parameters; tasks with overrides require the complete `request_evaluator(request, config=...)` interface. Existing nominal beam settings, thresholds, objective units, and archived outputs are preserved.

### 4.3 Independent Pareto Candidate Rerun Verification

`ParetoVerifier` is the shared service for planning, configured execution, attempt auditing, comparison, and report export. `run_verification_pipeline` and `run_independent_verification_rerun` are compatibility wrappers; CLI and `scripts/run_pareto_verification.py` use the same service. The class's plan runs through `CandidateEvaluatorBase` and `BatchEvaluator`, honoring configured worker count, timeout, retries, successful cleanup, lattice mappings, objective definitions, and longitudinal exit checks. CLI overrides are `--num-workers`, `--timeout`, `--template-dir`, and `--template-in`. Reports retain the actual settings and configuration.

Production verification requires measured candidate history with known validity and feasibility. Directory inputs prefer `candidate_history.json`, then `candidate_history.csv`, then a Pareto CSV. Missing explicit paths fail instead of falling back to another run. Without an explicit path, existing histories can be discovered; absent data fail before simulation submission. A compact Pareto CSV without measured status cannot supply feasible selection. `--dry-run` can show an empty plan; only explicit `--mock-evaluator` mode may create a synthetic nominal candidate.

Selection uses the shared `select_representatives` service (also used by robustness analysis and publication summaries), strictly within the observed feasible Pareto set: configured objective extremes (`min_emit_x`, `min_emit_y`, `min_sigma_energy` for the 200 MeV configuration), `knee_point`, `balanced`, and `crowding_distance_max`. The knee is the point nearest the ideal corner after direction-aware min–max normalization, the same definition for every configuration. The chosen identities are recorded in `representatives.json`. Pareto CSV exports carry `run_id`/`evaluation_id`, so readers join rows to history by identity; archived exports without identities fall back to exact recorded values.

Comparisons use every configured physical objective and observed transmission. Relative error is `abs(rerun - stored) / abs(stored) * 100`, including negative stored values. Missing/nonfinite observations, overflowing relative errors, and zero nominal denominators are unknown; even zero-to-zero has no defined relative error. No objective, diagnostic, transmission, or checksum receives a favorable fallback. The maximum error includes transmission. Verified outcomes also require complete measured diagnostic channels, known validity/feasibility, and unchanged feasibility classification.

Default tolerances preserve the existing relative settings: `tol_verified=1e-3` means strictly **less than 0.1%**, and `tol_conditional=0.10` means strictly **less than 10%**. These values do not change beam-quality constraint thresholds. The earlier guide's percent labels were incorrect.

- `VERIFIED` / `CONDITIONALLY_VERIFIED`: complete comparisons within tolerance, matching feasibility, and a successful rerun audit. A known failed original audit also prevents these statuses.
- `REJECTED`: excessive differences or changed feasibility, even with identical objectives.
- `COMPARISON_UNKNOWN`: required comparison evidence is missing/nonfinite/undefined or original validity is unknown.
- `RERUN_FAILED`: the rerun is not a valid simulation.
- `AUDIT_FAILED`: numerical comparison passes but required provenance or request identity does not.
- `MOCK_*`: explicit synthetic comparison statuses; these never certify physical execution or fabricate input/executable hashes.

Each immutable report session retains configuration/execution settings, original and rerun run/evaluation/attempt identities, exact manifest links, physical objectives in configured order/units, comparison issues, validity/diagnostic completeness, failure information, and separate original/rerun audits. Auditing verifies retained before/after input bytes, checks that their state did not change during execution, compares manifest observations/parameters/identities, and rehashes the recorded executable path. Cleanup can remove workdirs while snapshots and manifests remain. Missing or changed executable bytes prevent current audit certification; executable bytes themselves are not archived.

Legacy original records without modern retained provenance remain explicitly `UNKNOWN` rather than receiving invented hashes. Such records can still support a numerical comparison against an audited new rerun; this does not certify the historical source execution. New original provenance with failed checks prevents a verified result. Unknown comparisons remain visible in CSV/JSON and tables. Default emittance/energy table units remain compatible; custom objective tables use configured physical order and units.

Reports are archived under `verification_runs/verification_<uuid>/` before publishing root compatibility CSV/JSON/LaTeX files. Returned paths identify that exact session; previous reruns are never overwritten. Raw archives and publication artifacts are not migrated or rewritten automatically.

---

## 5. Command Reference Table

| Workflow Step | Command | Primary Outputs |
| :--- | :--- | :--- |
| **Run Phase 1 Scalarized BO** | `python scripts/run_scalarized_bo.py --weights 1.0 1.0 1.0` | `results/scalarized_YYYYMMDD_HHMMSS/` |
| **Run Constrained MOBO** | `mobo-linac run-constrained --config configs/publication_200MeV.yaml` | `results/run_YYYYMMDD_HHMMSS/` |
| **Run Unconstrained MOBO** | `mobo-linac run-unconstrained --config configs/publication_200MeV.yaml` | `results/run_YYYYMMDD_HHMMSS/` |
| **Run Benchmark Campaign** | `mobo-linac run-benchmark --config configs/publication_200MeV.yaml` | `results/publication_benchmark/` |
| **Analyze Benchmark** | `mobo-linac analyze-benchmark --output-dir results/publication_benchmark` | `aggregate_metrics.csv`, CIs |
| **Run Robustness Analysis** | `mobo-linac run-robustness --config configs/publication_200MeV.yaml` | `results/robustness/` |
| **Run Pareto Verification** | `mobo-linac run-verification --config configs/publication_200MeV.yaml` | `verification_table.tex` |
| **Reproduce Paper Artifacts** | `./scripts/reproduce_paper.sh` | Figures, `main.pdf` |
| **Run Unit Test Suite** | `pytest -m "not integration"` | 76 passed unit tests |
