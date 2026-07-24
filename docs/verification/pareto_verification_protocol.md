# Independent Pareto Candidate Verification Protocol

## 1. Executive Summary

This document formalizes the procedure for independent verification of reported Pareto-optimal candidate solutions. Verification ensures that all manuscript-highlighted points are 100% reproducible, eliminating artifacts from bookkeeping, sign conversion errors, stale files, or shared working directory collisions.

---

## 2. Candidate Selection (7 Distinct Roles)

Representative candidate solutions are selected from the feasible non-dominated Pareto set:

1. **Horizontal Emittance Extreme** (`min_emit_x`): Candidate minimizing $\varepsilon_{n,x}$.
2. **Vertical Emittance Extreme** (`min_emit_y`): Candidate minimizing $\varepsilon_{n,y}$.
3. **Energy Spread Extreme** (`min_sigma_energy`): Candidate minimizing $\sigma_E$.
4. **Normalized Knee Point** (`knee_point`): Candidate closest to origin in normalized objective space.
5. **Maximum Crowding Distance** (`crowding_distance_max`): Candidate in sparse Pareto region maximizing crowding distance.
6. **Balanced Feasible Solution** (`balanced_feasible`): Candidate nearest the centroid of the non-dominated set.
7. **Robust Recommended Solution** (`robust_recommended`): Recommended operational solution.

---

## 3. Independent Verification Procedure

For each selected candidate:

1. **Work Directory Isolation**: Create a fresh, dedicated work directory (`results/verification/candidate_inputs/<role>/`).
2. **Input Regeneration**: Regenerate candidate-specific `astra.in` directly from stored 6D parameters.
3. **Checksum Recording**: Compute SHA-256 hashes for `astra.in` and all static input data files (`gun.dat`, `PAL_SOL_A.dat`, `TWS_Sband.dat`, `pal_photo2.ini`).
4. **Independent Execution**: Rerun ASTRA simulation independently.
5. **Full State Comparison**: Compare stored and rerun parameters across:
   - 6 design variables ($\mathbf{x}$)
   - 3 physical objectives ($\varepsilon_{n,x}, \varepsilon_{n,y}, \sigma_E$)
   - 7 diagnostic fields ($\sigma_x, \sigma_y, \sigma_{x'}, \sigma_{y'}, \sigma_z, E_{\text{kin}}, \text{transmission}$)
   - Feasibility status
6. **Relative Percentage Error**:
   $$\text{Error}_{\text{max}} = \max_{j} \left| \frac{Y_{\text{rerun}, j} - Y_{\text{stored}, j}}{Y_{\text{stored}, j}} \right| \times 100\%$$
7. **Verification Classification**:
   - **`VERIFIED`**: $\text{Error}_{\text{max}} < 10^{-3}\%$ ($0.001\%$)
   - **`CONDITIONALLY_VERIFIED`**: $\text{Error}_{\text{max}} < 0.10\%$
   - **`REJECTED`**: $\text{Error}_{\text{max}} \ge 0.10\%$ (Candidate disqualified from Pareto claims in manuscript)

---

## 4. Output Artifacts

Outputs are written automatically to `results/verification/`:
- `verification_manifest.csv`: Detailed parameter and hash comparison table.
- `candidate_inputs/`: Isolated work directories containing regenerated `astra.in` and log files.
- `rerun_results.csv`: Rerun metrics and relative percentage errors.
- `verification_table.tex`: Publication-ready LaTeX table formatted for paper inclusion.
