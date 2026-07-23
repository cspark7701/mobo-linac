# Optimization Data Flow Architecture

## Overview

This document describes the complete data pipeline from candidate selection to surrogate update in `mobo_linac`.

---

## Data Flow Diagram

```
                 Candidate Design Parameters x ∈ ℝ⁶
                                │
                                ▼
               Modify ASTRA Input File (astra.in)
                                │
                                ▼
               Execute ASTRA Simulation Engine
                                │
                                ▼
              Extract Beam Diagnostics & Statistics
                                │
                                ▼
             Evaluate Objectives & Feasibility Constraints
                                │
                                ▼
               Negate Objectives for BoTorch Maximization
                                │
                                ▼
             Update Gaussian Process Surrogates (ModelListGP)
                                │
                                ▼
             Optimize Acquisition Function (qLogNEHVI)
                                │
                                ▼
                Generate Next Candidate Batch x_next
```

---

## Detailed Data Transformations

### 1. Candidate Generation ($\mathbf{x} \in \mathbb{R}^6$)
- Parameters represent physical accelerator settings:
  - $x_0$: Solenoid peak field [T]
  - $x_1$: Quadrupole 1 gradient [T/m]
  - $x_2$: Quadrupole 2 gradient [T/m]
  - $x_3$: RF gun phase [deg]
  - $x_4$: ACC1 & ACC2 common phase [deg]
  - $x_5$: ACC3 & ACC4 common phase [deg]

### 2. ASTRA Input Modification & Simulation Execution
- Parameter values are mapped into the `Astra` Python object.
- Values are formatted and written into `astra.in`.
- `astra_sim.run()` executes the external `astra` executable binary.

### 3. Output Parsing & Diagnostics Extraction
- ASTRA generates output file `astra.emit` and returns `stats` dictionary.
- Final slice statistics are extracted at the end of the linac ($z \approx 18.5\text{ m}$):
  - Normalized emittance $\varepsilon_{n,x}, \varepsilon_{n,y}$
  - RMS energy spread $\sigma_E$
  - Transverse sizes $\sigma_x, \sigma_y$, divergence $\sigma_{x'}, \sigma_{y'}$
  - Bunch length $\sigma_z$
  - Mean kinetic energy $E_{\text{kin}}$

### 4. Objective Transformation & Feasibility Logic
- **Feasibility Evaluation**:
  - Feasible if all 7 diagnostic thresholds are met ($\sigma_x, \sigma_y, \sigma_z, \sigma_{x'}, \sigma_{y'} \le 1.0\text{ mm/mrad}$ and $195 \le E_{\text{kin}} \le 205\text{ MeV}$).
- **Objective Negation**:
  - Physical minimization objectives $(\varepsilon_{n,x}, \varepsilon_{n,y}, \sigma_E)$ are negated:
    $$\mathbf{y}_{\text{BoTorch}} = [-\varepsilon_{n,x}, -\varepsilon_{n,y}, -\sigma_E]$$

### 5. Gaussian Process Model Update
- `SingleTaskGP` models fit each outcome:
  - Input normalization via `Normalize(bounds)`
  - Outcome standardization via `Standardize()`
- Combined into `ModelListGP`.

### 6. Acquisition Function Optimization & Candidate Batching
- Reference point calculated or fixed in negated objective space.
- Acquisition function (`qLogNoisyExpectedHypervolumeImprovement` or `qExpectedHypervolumeImprovement`) is optimized using `optimize_acqf`.
- Produces $q$ new candidate parameter vectors for the next iteration batch.
