# Optimization Metrics and Reporting Standards

## 1. Executive Summary

This document defines the metrics, reference point conventions, normalization scale factors, and compatibility verification standards used to compare Multi-Objective Bayesian Optimization (MOBO) algorithms, seeds, and campaign runs.

---

## 2. Objective Normalization & Engineering Scale Factors

To ensure scale-invariance and dimensionless hypervolume evaluation across physical objectives spanning different orders of magnitude, physical objectives are normalized using fixed engineering scales ($\mathbf{S}$):

$$\mathbf{S} = \begin{bmatrix} S_{\varepsilon_{n,x}} \\ S_{\varepsilon_{n,y}} \\ S_{\sigma_E} \end{bmatrix} = \begin{bmatrix} 1.0 \times 10^{-6} \text{ m}\cdot\text{rad} \\ 1.0 \times 10^{-6} \text{ m}\cdot\text{rad} \\ 1.0 \times 10^{6} \text{ eV} \end{bmatrix}$$

- **Normalized Physical Space** (Minimization):
  $$\bar{Y}_{\text{physical}} = \frac{Y_{\text{physical}}}{\mathbf{S}}$$

- **Normalized Model Space** (Maximization for BoTorch):
  $$\bar{Y}_{\text{model}} = -1 \times \bar{Y}_{\text{physical}} = -\frac{Y_{\text{physical}}}{\mathbf{S}}$$

> **Important**: Normalization scale factors are fixed globally across all runs and campaigns. Dynamic normalization using current-run extrema is prohibited to ensure hypervolume comparability.

---

## 3. Reference Points Specification

1. **Dynamic Acquisition Reference Point ($R_{\text{acq}}$)**: Calculated adaptively during acquisition function optimization based on current Pareto non-dominated sets (or fallback defaults).
2. **Fixed Reporting Reference Point ($R_{\text{reporting}}$)**: Immutable reference point used for hypervolume reporting across all iterations and campaigns:
   - **Normalized Physical Space**: $R_{\text{phys, norm}} = [10.0, 10.0, 10.0]$
   - **Normalized Model Space**: $R_{\text{model, norm}} = [-10.0, -10.0, -10.0]$
   - **Unnormalized Physical Space**: $R_{\text{phys}} = [10.0 \ \mu\text{m}\cdot\text{rad}, 10.0 \ \mu\text{m}\cdot\text{rad}, 10.0 \text{ MeV}]$

---

## 4. Standard Metric Definitions

Every optimization run exports a machine-readable history DataFrame with cumulative ASTRA evaluations as the primary x-axis:

| Metric Column Name | Description | Formula / Source |
| :--- | :--- | :--- |
| `cumulative_astra_evaluations` | Primary progress axis (total simulations executed) | Step counter $t = 1, \dots, N$ |
| `fixed_ref_all_valid_hv` | Dimensionless hypervolume of all valid simulations | $\text{HV}(\bar{Y}_{\text{valid}}, R_{\text{model, norm}})$ |
| `fixed_ref_feasible_hv` | Dimensionless hypervolume of physically feasible simulations | $\text{HV}(\bar{Y}_{\text{feasible}}, R_{\text{model, norm}})$ |
| `feasible_fraction` | Cumulative ratio of physically feasible candidates | $\frac{N_{\text{feasible}}}{N_{\text{total}}}$ |
| `first_feasible_eval_index` | 1-based index of the first feasible candidate found | $\min \{ t \mid \text{feasible}_t = \text{True} \}$ |
| `pareto_set_size` | Number of non-dominated feasible candidates on Pareto front | $| P_{\text{feasible}} |$ |
| `invalid_run_count` | Cumulative number of simulation failures / timeouts | $N_{\text{failed}}$ |
| `total_wallclock_s` | Cumulative elapsed wall-clock runtime (seconds) | $\sum \Delta t_{\text{wall}}$ |
| `total_simulation_runtime_s` | Cumulative sum of ASTRA execution durations | $\sum t_{\text{ASTRA}}$ |

---

## 4.1 Representative Candidates and Knee Definition

Representative candidates come from one service, `mobo_linac.metrics.selection.select_representatives`, applied to the measured feasible non-dominated set $P$. With direction-aware costs $c_{ij} = -s_j y_{ij}$ (minimized objectives unchanged, maximized ones negated), each objective is normalized over $P$:

$$\tilde c_{ij} = \frac{c_{ij} - \min_k c_{kj}}{\max_k c_{kj} - \min_k c_{kj}}$$

(a zero range leaves the column at zero). The **knee** minimizes $\lVert \tilde{\mathbf c}_i \rVert_2$, the distance to the ideal corner (policy `ideal_distance`); **balanced** minimizes the distance to the centroid of $\tilde{\mathbf c}$; **crowding_distance_max** maximizes the finite NSGA-II crowding distance of $\tilde{\mathbf c}$. The policy and selected identities are recorded in `representatives.json`.

---

## 5. Cross-Run Compatibility Verification

Comparison functions enforce strict validation before comparing metrics between runs:
- Verification of identical objective normalization scale factors $\mathbf{S}$.
- Verification of identical fixed reporting reference points $R_{\text{reporting}}$.
- Verification of identical physical constraint specifications.

---

## 6. Surrogate and Acquisition Settings Selection

`mobo_linac.models.tuning` ranks GP settings by the exact leave-one-out (LOO) mean log predictive density in standardized output units, computed in closed form for the fitted hyperparameters ($\mu_{-i} = y_i - [K^{-1}r]_i/[K^{-1}]_{ii}$, $\sigma^2_{-i} = 1/[K^{-1}]_{ii}$). In-sample RMSE and $R^2$ are reported but never used for ranking, since an interpolating GP fits its training data almost exactly. LOO RMSE and ±1σ/±2σ coverage are reported for calibration.

Acquisition types and optimizer budgets are ranked by the expected hypervolume improvement of their proposed batch, evaluated with one common non-log Monte Carlo estimator (fixed QMC sampler) at the campaign's recorded reporting reference, so log and non-log acquisitions are compared on the same scale. Candidate diversity and timing are diagnostics only. Failed candidates keep their error and are excluded from ranking. Measured-noise variance floors are relative to each objective's reporting scale.
