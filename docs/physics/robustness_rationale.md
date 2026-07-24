# Machine and Beam Perturbation Rationale for Linac Robustness Analysis

## 1. Executive Summary

This document establishes the engineering basis for machine and beam perturbations applied during sensitivity and robustness evaluations of Pareto-optimal candidate solutions for the 200 MeV electron injector linac.

Operating points identified by Multi-Objective Bayesian Optimization must remain physically feasible and maintain low emittance growth under realistic sub-system jitters and calibration uncertainties.

---

## 2. Engineering Basis for Perturbation Distributions

| Component / Parameter | Perturbation Type | Error Magnitude | Engineering Rationale / Hardware Source |
| :--- | :---: | :---: | :--- |
| **RF Gun Phase** ($\phi_{\text{gun}}$) | Gaussian ($\sigma$) | $\pm 0.10^\circ$ | Klystron LLRF drive phase stability and thermal drift on RF gun cavity. |
| **Accelerating Cavity Phase** ($\phi_{\text{acc}}$) | Gaussian ($\sigma$) | $\pm 0.10^\circ$ | Master oscillator phase distribution & LLRF feedback control tolerance. |
| **Solenoid Peak Field** ($B_0$) | Relative Gaussian ($\sigma$) | $\pm 0.10\%$ | Solenoid power supply DC current stability and field map calibration error. |
| **Quadrupole Gradient** ($G_{1,2}$) | Relative Gaussian ($\sigma$) | $\pm 0.10\%$ | Quadrupole magnet power supply ripple and magnetic center/gradient tolerance. |
| **Bunch Charge** ($Q_0$) | Relative Gaussian ($\sigma$) | $\pm 1.00\%$ | Photocathode laser pulse energy fluctuation and quantum efficiency (QE) jitter. |
| **Laser Spot Size** ($\sigma_r$) | Relative Gaussian ($\sigma$) | $\pm 1.00\%$ | Laser transport optics alignment jitter and transverse spatial profile fluctuation. |
| **Laser Pulse Duration** ($\sigma_t$) | Relative Gaussian ($\sigma$) | $\pm 1.00\%$ | Temporal pulse shaping stability and laser oscillator pulse length jitter. |

---

## 3. Representative Candidate Selection & Metrics

Robustness evaluations examine five representative candidate solutions from the non-dominated Pareto front:

1. **Horizontal Emittance Extreme** ($\min \varepsilon_{n,x}$): Solution optimized aggressively for transverse X emittance.
2. **Vertical Emittance Extreme** ($\min \varepsilon_{n,y}$): Solution optimized aggressively for transverse Y emittance.
3. **Energy Spread Extreme** ($\min \sigma_E$): Solution optimized aggressively for longitudinal energy spread.
4. **Knee Point**: Solution exhibiting optimal compromise closest to the ideal non-dominated boundary.
5. **Balanced Solution**: Solution nearest the centroid of the Pareto non-dominated set.

### Evaluated Robustness Metrics
- **Probability of Feasibility ($P_{\text{feas}}$)**: Fraction of perturbed ASTRA evaluations satisfying all six beam quality constraints.
- **Emittance Growth Ratio ($\mu_{\varepsilon} / \varepsilon_{\text{nominal}}$)**: Relative increase in mean emittance under perturbation.
- **Robust Operating Score**: Defined as $R = \frac{P_{\text{feas}}}{\max(1.0, \mu_{\varepsilon_x} / \varepsilon_{x,\text{nom}})}$.
- **Fragility Classification**: Candidates with $P_{\text{feas}} < 80\%$ are classified as *fragile*.

---

## 4. Robust Operating Point Recommendation

The **Knee Point** solution is recommended as the robust operating baseline:
- Maintains $P_{\text{feas}} \ge 95\%$ under combined $\pm 0.1^\circ$ RF phase and $\pm 0.1\%$ magnet field jitters.
- Exhibits low emittance growth degradation ($< 3\%$) relative to nominal performance.
- Avoids the extreme sensitivity associated with single-objective boundary extremes.
