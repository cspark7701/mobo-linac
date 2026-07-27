# Accelerator Beam Quality Constraint Rationale

## 1. Executive Summary

This document establishes the physical, diagnostic, and engineering rationale behind the beam quality constraint thresholds used in the Multi-Objective Bayesian Optimization (MOBO) framework for the 200 MeV S-band electron injector linac.

The optimization framework enforces six diagnostic constraints alongside beam dynamics tracking in ASTRA.

---

## 2. Constraint Threshold Specifications

| Diagnostic Quantity | Explicit Field Name | Unit | Nominal Threshold | Stringent Profile | Relaxed Profile | Physical Source / Rationale |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Transverse Beam Size X** | `sigma_x_m` | m | $\le 1.0 \times 10^{-3}$ (1.0 mm) | $\le 0.3$ mm | $\le 2.0$ mm | Vacuum chamber stay-clear aperture & quadrupole beamline acceptance. |
| **Transverse Beam Size Y** | `sigma_y_m` | m | $\le 1.0 \times 10^{-3}$ (1.0 mm) | $\le 0.3$ mm | $\le 2.0$ mm | Transverse beam envelope control avoiding beam scrape. |
| **Transverse Divergence X**| `sigma_xp_rad` | rad | $\le 1.0 \times 10^{-3}$ (1.0 mrad) | $\le 0.3$ mrad | $\le 2.0$ mrad | Downstream transfer line matching and chromatic aberration suppression. |
| **Transverse Divergence Y**| `sigma_yp_rad` | rad | $\le 1.0 \times 10^{-3}$ (1.0 mrad) | $\le 0.3$ mrad | $\le 2.0$ mrad | Quadrupole lattice focusing limit and beam envelope growth prevention. |
| **Bunch Length (RMS)** | `sigma_z_m` | m | $\le 1.0 \times 10^{-3}$ (1.0 mm) | $\le 0.3$ mm | $\le 2.0$ mm | Downstream RF compression efficiency & time-resolved experiment target. |
| **Mean Kinetic Energy** | `mean_kinetic_energy_eV` | eV | $[195, 205] \times 10^6$ | $[198, 202]$ MeV | $[190, 210]$ MeV | Nominal 200 MeV linac energy window ($\pm 2.5\%$). |
| **Beam Transmission** | `transmission_fraction` | dimensionless | $\ge 0.90$ (90%) | $\ge 99.99\%$ | $\ge 80\%$ | Charge preservation and radiation protection threshold. |

---

## 3. Resolution of Historical Threshold Discrepancies

Prior initial studies utilized tight idealized constraints ($0.3\text{ mm}$ beam size, $0.3\text{ mrad}$ divergence, $99.99\%$ transmission). During full tracking campaigns across the full 6D search space (with $\pm 50\%$ magnet variations and $\pm 10\%$ RF phase variations), overly tight thresholds caused a high rate of unfeasible classifications during early Sobol sampling.

### Resolution & Justification:
1. **Nominal Operational Baseline ($1.0\text{ mm} / 1.0\text{ mrad} / 90\%$ transmission)**: Adopted as the primary publication baseline. This reflects realistic operational beam acceptance in S-band electron linac injectors before downstream collimation.
2. **Sensitivity Profiles (Stringent, Nominal, Relaxed)**: Implemented directly in `configs/publication_200MeV.yaml` to enable systematic constraint-sensitivity analyses comparing hypervolume coverage and Pareto front shift across tight vs nominal vs relaxed design spaces.

---

## 4. Diagnostic Validation & Failure Semantics

1. **Finite Value Check**: Every diagnostic must be finite ($\text{NaN} / \text{Inf}$ values cause immediate failure classification as `NAN_INF_DIAGNOSTICS`).
2. **Non-Negative RMS Quantities**: Transverse size ($\sigma_x, \sigma_y$), divergence ($\sigma_{x'}, \sigma_{y'}$), bunch length ($\sigma_z$), and energy spread ($\sigma_E$) must be $\ge 0.0$.
3. **Explicit Transmission Validation**: Transmission is computed directly from ASTRA particle counts:
   $$\text{transmission\_fraction} = \frac{N_{\text{final}}}{N_{\text{initial}}}$$
   Missing transmission is never defaulted to $100\%$; evaluations missing transmission data are classified as invalid simulations (`MISSING_OUTPUT`).
