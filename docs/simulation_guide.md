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
$$\mathcal{D}_i = \text{\texttt{results/<run\_id>/work/eval\_00000i/}}$$

Each directory contains:
- Regenerated `astra.in`
- Clean copies of static field maps and particle distributions (`gun.dat`, `PAL_SOL_A.dat`, `TWS_Sband.dat`, `pal_photo2.ini`)
- Isolated simulation log and output files (`astra.Log`, `astra.out`)

### 2.2 Strict Evaluation Failure Semantics
Numerical simulation validity (`simulation_valid`) is strictly separated from physical beam feasibility (`physically_feasible`):
- **`MISSING_OUTPUT`**: ASTRA failed to write output particles $\implies$ Invalid simulation.
- **`PREMATURE_BEAM_LOSS`**: Particle tracking terminated prematurely before exit screen ($z_{\text{final}} < Z_{\text{stop}} - \Delta z_{\text{tol}}$) due to core collimation or loss $\implies$ Invalid simulation.
- **`NAN_INF_DIAGNOSTICS`**: Negative or non-finite RMS beam sizes/emittances $\implies$ Invalid simulation.
- **`INVALID_TRANSMISSION`**: Transmission $< 0\%$ or $> 100\%$ $\implies$ Invalid simulation.
- **`INFEASIBLE_BEAM`**: Valid simulation violating beam quality constraints $\implies$ Valid simulation, Infeasible beam.

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

### 3.2 Phase 1: Scalarized Bayesian Optimization Procedure
- **Objective Scalarization**: Linear weighted sum formulation:
  $$f(\mathbf{x}) = \sum_{i=1}^3 w_i \cdot y_{i,\text{norm}}(\mathbf{x}) = w_1 \varepsilon_{n,x} + w_2 \varepsilon_{n,y} + w_3 \sigma_E$$
  where weight combinations $\mathbf{w} \in \Delta^2$ control the optimization priority along the Pareto trade-off curve.
- **Single-Objective GP Surrogate**: Single `SingleTaskGP` with Matérn-5/2 ARD kernel modeling the scalarized merit function.
- **Acquisition Function**: `qLogNoisyExpectedImprovement` (`qLogNEI`) for parallel candidate selection ($q \ge 1$).
- **Interactive Notebook**: [`notebooks/phase1_scalarized_bo.ipynb`](file:///home/cspark/Work/projects/mobo_linac/notebooks/phase1_scalarized_bo.ipynb).
- **Execution Script**: [`scripts/run_scalarized_bo.py`](file:///home/cspark/Work/projects/mobo_linac/scripts/run_scalarized_bo.py).

---

## 4. Benchmark, Robustness, Verification, & Publication Workflow

### 4.1 Seed-Paired Benchmark Campaign Protocol
- **Supported Algorithms**: `constrained_qlognehvi`, `unconstrained_qlognehvi`, `qlogehvi`, `scalarized_bo`, `nsga2`, `sobol`.
- **Seed Pairing**: Identical initial Sobol candidate points generated per seed $s$.
- **Statistical Aggregation**: Median hypervolume trajectories and 95% bootstrap confidence intervals ($B = 1000$ resamples).

### 4.2 Machine & Beam Perturbation Robustness Analysis
- **Perturbation Specifications**: RF phase jitter ($\pm 0.10^\circ$), magnet field calibration errors ($\pm 0.10\%$), bunch charge & laser spot size jitters ($\pm 1.00\%$).
- **Candidate Selection**: 5 representative Pareto candidates ($\min \varepsilon_{n,x}$, $\min \varepsilon_{n,y}$, $\min \sigma_E$, `knee_point`, `balanced`).
- **Robust Operating Point**: Knee Point recommended as robust baseline ($P_{\text{feas}} \ge 95\%$, emittance growth $< 3\%$).

### 4.3 Independent Pareto Candidate Rerun Verification
- **7 Selection Roles**: `min_emit_x`, `min_emit_y`, `min_sigma_energy`, `knee_point`, `crowding_distance_max`, `balanced_feasible`, `robust_recommended`.
- **Checksums**: SHA-256 hashes recorded for input files and static field maps.
- **Status Classification**: `VERIFIED` ($\text{Error}_{\text{max}} < 10^{-3}\%$), `CONDITIONALLY_VERIFIED` ($< 0.10\%$), `REJECTED` ($\ge 0.10\%$).
- **LaTeX Export**: Automated export to `verification_table.tex`.

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
