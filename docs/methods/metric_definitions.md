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

## 5. Cross-Run Compatibility Verification

Comparison functions enforce strict validation before comparing metrics between runs:
- Verification of identical objective normalization scale factors $\mathbf{S}$.
- Verification of identical fixed reporting reference points $R_{\text{reporting}}$.
- Verification of identical physical constraint specifications.
