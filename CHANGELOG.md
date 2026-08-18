# Changelog

All notable changes to the Multi-Objective Bayesian Optimization for a 200 MeV Electron Injector Linac project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [v0.2.0] - 2026-08-07

### Codex Task Series (Tasks 41–50)

- **Task 41 (Codex 01)**: Constrained MOBO path — real 8-constraint GP-weighted qLogNEHVI acquisition.
- **Task 42 (Codex 02)**: Transmission & diagnostics integration — explicit transmission GP surrogate and constraint CSV.
- **Task 43 (Codex 03)**: Independent Pareto verification — fresh isolated workdir reruns with SHA-256 checksums.
- **Task 44 (Codex 04)**: Checkpoint/resume — robust mid-campaign resume from `gp_checkpoint/` and CSV state.
- **Task 45 (Codex 05)**: Operational CLI workflows — `run-constrained`, `run-unconstrained`, `resume`, `run-verification`, `run-robustness`, `run-benchmark`, `analyze-benchmark`.
- **Task 46 (Codex 06)**: Fixed-reference publication metrics — hypervolume always computed against fixed `r_rep` from initialization.
- **Task 47 (Codex 07)**: Fixed-noise GP treatment — explicit `FixedNoiseGaussianLikelihood` (σ²=1e-6) for deterministic ASTRA simulations.
- **Task 48 (Codex 08)**: Feasible Pareto candidate selection — 6-role selection strictly from feasible non-dominated set.
- **Task 49 (Codex 09)**: Paired multi-seed benchmark campaigns — `BenchmarkConfig`, shared Sobol init per seed, 95% bootstrap CI plots.
- **Task 50 (Codex 10)**: Manuscript regeneration — `generate_paper_figures.py` data-driven figure/table pipeline; 38-test `test_paper_outputs.py` suite; updated `main.tex` with corrected qLogNEHVI formula and no hard-coded results.

## [v1.0.0] - 2026-08-18

### Publication Release & Physics Refactor Highlights (Tasks 01–11 / Refactors A, B, C)
- **Multi-Scale Gaussian Process Relative Noise Scaling (Task 01)**: Dynamic empirical variance observation noise scaling ($\sigma_{\text{obs}}^2 = \max(\eta \cdot \text{Var}(Y_m), \sigma_{\text{floor}}^2)$ with $\eta=10^{-6}$ and floor $10^{-24}$), preventing numerical over-smoothing across disparate $\mu\text{m}\cdot\text{rad}$ and $\text{MeV}$ scales.
- **Config-Driven Dynamic Parameter Mapping (Task 02)**: Fully dynamic parameter mapping from YAML configuration to arbitrary ASTRA namelist paths (`solenoid:maxb(1)`, `cavity:phi(2,3)`, etc.) supporting cavity decoupling and custom parameter sets.
- **Longitudinal Exit-Plane Verification & Beam Loss Detection (Tasks 03 & 09)**: Real-time detection of premature beam loss at apertures and collimators ($z_{\text{final}} < Z_{\text{stop}} - \Delta z_{\text{tol}}$), categorizing failures under `PREMATURE_BEAM_LOSS` and protecting GP training data integrity.
- **Unified Campaign Execution Engine (Task 04)**: Consolidated scalarized, unconstrained, and constrained optimization loops into a centralized `MoboCampaignRunner`.
- **Pareto Diversity & Canonical Crowding Distance (Task 05)**: Boundary-preserving crowding distance computation, candidate duplicate detection, and CLI cleanup.
- **Full-Chain Photocathode & Laser Jitter Robustness Modeling (Task 06)**: Multi-channel jitter analysis incorporating spot size ($XY$), pulse length ($T$), laser energy/charge, and launch angle perturbations across 7 physical channels.
- **Type-Safe `CheckpointState` Schema & Schema Validation (Task 07)**: Strict dataclass schema validation with backward-compatible serialization.
- **Configurable Multi-Restart Optimization Budgets (Task 08)**: User-tunable L-BFGS multi-restart parameters (`acqf_num_restarts`, `acqf_raw_samples`, `acqf_maxiter`, `acqf_batch_limit`) and automatic GPU device placement.
- **Exact Analytical Normal CDF Feasibility Modeling ($P_{\text{feas}}$) (Task 09 / Refactor A)**: Exact multi-channel Normal CDF probability evaluation across 7 linac diagnostic channels in `SurrogatePipeline`.
- **Multi-Tier Resilient Acquisition & Atomic Checkpoints (Task 10 / Refactor B)**: Fault-tolerant acquisition optimization with adaptive budget reduction retry and scrambled Sobol exploration fallback; crash-proof atomic POSIX checkpoint serialization (`_atomic_torch_save`).
- **Centralized Publication LaTeX Table Reporting (Task 11 / Refactor C)**: Dedicated `mobo_linac.metrics.latex` module generating publication-grade LaTeX tables for Pareto verification, campaign comparisons, and robustness analysis.
- **Process-Safe Directory Isolation**: Per-evaluation isolated working directories (`results/<run_id>/work/eval_<id>/`) eliminating file overwrites and race conditions during parallel evaluations.
- **Strict Failure Semantics & Schema**: Explicit separation of numerical simulation validity (`simulation_valid`) from physical beam feasibility (`physically_feasible`).
- **Standardized Metric Reporting**: Fixed engineering scale factors and standardized reporting reference point $\mathbf{r}_{\text{rep}}$.
- **Independent Pareto Verification & Reproduction Suite**: 7-role candidate selection, SHA-256 checksum audit, fresh workdir reruns, automated LaTeX export, and `scripts/reproduce_paper.sh`.
