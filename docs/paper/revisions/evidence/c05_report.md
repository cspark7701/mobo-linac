# C05 — Executed acquisition and GP audit

## Scope and reproducibility

This audit reads all 30 primary campaigns under `results/paper_production/04_primary/benchmark/per_seed`, their proposal histories and all 540 fitted surrogate artifacts. It does not fit models, propose candidates, track particles or change production artifacts. Run:

```bash
/home/cspark/Work/simulation_codes-working/miniforge3/envs/linac-opt/bin/python docs/paper/revisions/evidence/c05_audit.py
```

The script uses `torch.load(..., weights_only=True)` and publishes derived CSV/JSON evidence here. It verifies configuration and proposal-history hashes against the authoritative completion markers. Artifact SHA-256 hashes and source-code hashes are retained in `c05_artifacts.csv` and `c05_audit.json`. The installed BoTorch 0.17.0 and GPyTorch 1.15.2 match all archived environment records. The analysis distinguishes explicit settings, observed saved state and defaults reconstructed from matching installed source. Library source is inspected locally rather than presumed from current online documentation.

## Acquisition equation and feasibility

The manuscript's previous equation multiplies whole-batch HVI by a single product over eight constraints. That is not an exact expression for batch constrained qLogNEHVI. The included `c05_methods.tex` supplies an explicitly labelled ideal criterion using a feasible candidate subset and feasible sampled baseline, followed by the actual implementation description. Include candidate-wise feasibility weights in each inclusion–exclusion contribution; a low-feasibility candidate does not uniformly suppress every other candidate's improvement. BoTorch's baseline partitioning uses posterior-sampled feasibility. Log-space ReLU/min/max relaxations mean the implemented acquisition is a smooth approximation, not the exact logarithm of hard-constraint HVI.

`MultiObjectiveProposal._surrogate` concatenates three independent objective GPs and seven independent diagnostic GPs. The shared energy diagnostic supplies lower and upper residual functions, so ten GPs support eight inequalities. Unconstrained MOBO has three objective GPs; scalarized BO has one GP for the dimensionless weighted objective. The `SliceObjective` selects only the three objective coordinates for HVI. `SurrogatePipeline.predict_feasibility` separately computes analytical normal-CDF channel probabilities, including one interval probability for energy. It is not used as the acquisition's feasibility weight; production qLogNEHVI uses sampled residual callables.

## Settings: explicit versus reconstructed

| Quantity | Result | Evidence class |
|---|---|---|
| Batch and effective budget | 16 initial points, 18 batches of 8, 160 evaluations per campaign | Campaign manifest and histories |
| ASTRA concurrency | Eight workers per campaign; one concurrent campaign | Manifest; saved `config.json` still contains nominal defaults |
| Acquisition optimizer | 10 restarts, 1,024 raw samples, maximum 200 iterations; CUDA batch limit 1 | All 540 saved proposal attempts |
| Proposal device/tier | All 540 proposals primary CUDA tier; no retry/CPU/Sobol proposal fallback | Proposal histories |
| Numeric precision | Float64 training data, states and effective noise | Model artifacts and call sites |
| Posterior MC samples | 128 for qLogNEHVI; 512 for scalarized qLogNEI | Inherited `_default_sample_shape` at the call sites in matching BoTorch source |
| Sampler | Normal Sobol QMC for the Gaussian posterior and recorded dimensions | Matching `get_sampler` source; no custom sampler at call sites |
| Baseline pruning | Enabled explicitly for MOBO and scalarized BO | Acquisition constructors |
| Feasibility indicator | Fat-tailed sigmoid, `fat=True`, `eta=1e-3` | Matching BoTorch constructor and safe-math source |
| Positive-part relaxation | `tau_relu=1e-6` | Matching BoTorch defaults |
| Extremum relaxation | MOBO `tau_max=1e-3`; scalarized `tau_max=1e-2` | Matching BoTorch defaults |

The maximum baseline before a proposal is 152 points; including the eight candidates and ten outputs is well below the Sobol maximum dimension of 21,201. Acquisitions, retained pruning sets, sampler base draws and sampler seeds were not persisted. Thus sample counts are implementation reconstructions, not direct inspection of serialized samplers. The audit must not claim to recover the exact retained baseline cardinality. Internal pruning can use its own default draw count; that is distinct from the acquisition MC count and the optimizer's raw initialization budget.

## Reference basis and formula

The proposal reference uses every valid observed objective, including physically infeasible observations. In model/maximization space $y_m=-f_m$, the code computes

`r_m = min(y_m) - 0.05 * (max(y_m) - min(y_m) + 1e-8)`.

The epsilon is a raw-coordinate safeguard, not a dimensionless engineering tolerance. It is recomputed before each MOBO proposal and recorded in the proposal metadata with `basis=all_valid`. The audit compares this formula with the training observations in every saved MOBO artifact. This acquisition reference is distinct from the benchmark's frozen reporting reference and does not replace the original hypervolume endpoint. The noisy acquisitions receive the full valid observed baseline, with sampled feasibility and pruning handled inside BoTorch; the `train_feas_mask` argument does not pre-filter qLogNEHVI's baseline in this code path.

## Mean-only scaling, requested noise and effective noise

All outputs use input normalization and a Standardize outcome transform. For an observed standard deviation below `1e-8` in its recorded output unit, the outcome transform subtracts the mean and sets its scaling standard deviation to one; it cannot produce unit-variance data from a constant channel. This occurs in the transmission channel of all 180 saved constrained model fits. The saved transmission observations are one, their mean is one, and the transform standard deviation is one.

The requested physical-coordinate variance is `max(1e-6 * sample_variance(Y), 1e-24)`, unless an explicit variance overrides it. For nonconstant standardized channels this is about `1e-6` in standardized coordinates. GPyTorch additionally enforces a `1e-6` minimum fixed-noise variance for float64 by default. Consequently, constant transmission requests `1e-24` in raw and mean-only coordinates but has a saved **effective** likelihood variance of `1e-6`. Its effective raw-coordinate noise standard deviation is therefore 0.001 in transmission fraction, not `1e-12`. `c05_channels.csv` records requested raw and standardized variances, transform scaling and saved effective noise separately for every channel. A physical fixed-noise formula alone does not describe the effective likelihood. The manuscript should avoid asserting that every output is standardized to unit variance or that effective noise is always exactly the requested physical variance.

## Fitting recovery

The 540 saved model artifacts contain 2,520 channel fits. Outcomes are:

| Algorithm | L-BFGS fits | Adam recoveries | Restored priors |
|---|---:|---:|---:|
| Constraint-aware MOBO | 1,714 | 86 | 0 |
| Unconstrained MOBO | 535 | 5 | 0 |
| Scalarized BO | 180 | 0 | 0 |

These are counts of saved per-channel fit outcomes, not evaluation failures or candidate fallback events. Each Adam recovery records the preceding error. Both optimizers start from the same saved pre-fit snapshot; Adam is limited to 200 steps. Code contexts request Cholesky jitter of `1e-4` and `1e-3` for the first and second fitting tiers, respectively; the actual dtype-specific effective defaults are not inferred from those positional arguments alone. If both fail, the verified pre-fit snapshot can be retained, but no saved primary-channel fit used that last tier. No fit outcome establishes surrogate calibration by itself; predictive validation remains C11.

## Actual fat-tailed transitions

The smoothing code sums `log_fatmoid(-residual/eta)` over constraints. With `m=1/sqrt(3)`, the negative branch of `h(t)` is `(2/3)/(1+(t-m)^2)`; the positive branch is `1-(2/3)/(1+(t+m)^2)`. It has algebraic rather than logistic tails.

| Residual / eta | Feasibility indicator |
|---:|---:|
| -2 | 0.912771 |
| -1 | 0.808870 |
| 0 | 0.500000 |
| +1 | 0.191130 |
| +2 | 0.087229 |

See `c05_transitions.csv` for full precision and the separate ordinary-logistic comparison. The reviewer illustrations near 0.73 and 0.27 are logistic values; the recorded fat-tailed implementation gives approximately 0.809 and 0.191 for beam sizes zero and twice the limit. The concern about unequal physical smoothing scales remains.

Residuals use metres for sizes/bunch length, radians for divergences, electron-volts for energy and a dimensionless transmission fraction. The manuscript's unqualified “SI units” is inaccurate for energy. The common `eta=1e-3` corresponds to 1 mm, 1 mrad, 0.001 eV or 0.001 transmission fraction, respectively. These are scale parameters, not 10–90% widths. At one eV beyond the upper energy limit the indicator is about `6.66e-7`, illustrating its very sharp physical scale without claiming exactly zero gradients everywhere. `c05_physical_transitions.csv` records sample values calculated by the installed fatmoid itself. C06 remains responsible for unit-representation sensitivity and any corrected method.

## Integration checklist and limits

1. Replace the existing qLogNEHVI equation/explanation with `c05_methods.tex`, preserving the scalarized definition that follows.
2. Amend the GP paragraph to state mean-only behavior and the effective standardized fixed-noise floor, including transmission.
3. Add the saved per-channel L-BFGS/Adam counts in Methods or supporting material, distinguishing fitting recovery from proposal fallback.
4. Give the all-valid reference formula and its epsilon, and keep acquisition and reporting references separate.
5. Retain the scaling limitation in Discussion. This audit makes no new physical-performance claim for normalized constraints, revised domains or changed algorithms.

C05's audit and manuscript corrections can be completed from these records. No new simulations are required. It cannot supply retrospective serialized sampler or pruning state that was never saved. Root integration should retain that evidence limit rather than presenting reconstruction as direct acquisition-state inspection.
