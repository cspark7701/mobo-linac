# Changelog

All notable changes to the Multi-Objective Bayesian Optimization for a 200 MeV Electron Injector Linac project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [v1.0.0] - 2026-07-25

### Publication Release Highlights
- **Process-Safe Directory Isolation**: Per-evaluation isolated working directories (`results/<run_id>/work/eval_<id>/`) eliminating file overwrites and race conditions during parallel evaluations.
- **Strict Failure Semantics & Schema**: Explicit separation of numerical simulation validity (`simulation_valid`) from physical beam feasibility (`physically_feasible`). Zero tolerance for invalid transmission or out-of-bounds beam physics.
- **Canonical 200 MeV Physics Specification**: Frozen 6D design space, coupled RF cavity phase definitions (ACC1/ACC2 & ACC3/ACC4), ordered bounds ($L \le U$), 3 physical objectives ($\varepsilon_{n,x}, \varepsilon_{n,y}, \sigma_E$), and 8 strict constraints ($1.0\text{ mm} / 1.0\text{ mrad} / 90\%$).
- **Surrogate Modeling & Acquisition Alignment**: ARD Matérn-5/2 GP surrogates, configurable noise models ($\sigma_{\text{obs}}^2 = 10^{-6}$ fixed noise), and $q\text{LogNEHVI} / q\text{LogEHVI}$ acquisition function integration.
- **Standardized Metric Reporting**: Fixed engineering scale factors ($S = [10^{-6}, 10^{-6}, 10^6]$) and fixed reporting reference points ($[-10.0, -10.0, -10.0]$ in normalized model space).
- **Statistically Rigorous Benchmark Campaign Architecture**: Seed-paired initial Sobol design generator and 95% bootstrap confidence intervals ($B=1000$ resamples).
- **Robustness & Sensitivity Analysis**: Engineering perturbation evaluator ($\pm 0.1^\circ$ RF phase, $\pm 0.1\%$ magnet fields, $\pm 1\%$ charge/laser), probability of feasibility ($P_{\text{feas}}$), and Knee Point operating baseline recommendation.
- **Independent Pareto Candidate Verification**: 7-role candidate selection, SHA-256 input checksums, fresh workdir reruns, relative percentage error tolerances, and automated LaTeX table generation (`verification_table.tex`).
- **Manuscript Reproduction Suite**: Executable single-command reproduction script `scripts/reproduce_paper.sh` and archived processed benchmark datasets in `results/publication_processed/`.
