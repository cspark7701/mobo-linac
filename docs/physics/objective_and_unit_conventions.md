# Objective Definitions, Model Transformations, and Unit Conventions

## 1. Executive Summary

This document formalizes the conventions for design variables, physical objectives, model-space transformations, and SI unit standards used across the `mobo_linac` framework.

---

## 2. Design Variables Specification (6D)

The optimization controls six accelerator design parameters written directly into `astra.in`:

| Index | Parameter Description | ASTRA Input Key | Unit | Nominal Value | Search Range (Bounds) | Coupled Behavior |
| :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| 1 | Solenoid Peak Field | `solenoid:maxb(1)` | T | 0.1947739 | $[0.097387, 0.292161]$ | Independent |
| 2 | Quadrupole 1 Gradient | `quadrupole:q_grad(1)` | T/m | 1.28652859 | $[0.643264, 1.929793]$ | Independent |
| 3 | Quadrupole 2 Gradient | `quadrupole:q_grad(2)` | T/m | -2.88668503 | $[-4.330028, -1.443343]$ | Independent (Negative bounds ordered: $L < U$) |
| 4 | RF Gun Phase | `cavity:phi(1)` | deg | 35.62497684 | $[32.062479, 39.187475]$ | Independent |
| 5 | ACC1/ACC2 Coupled Phase | `cavity:phi(2)` | deg | -39.50903029 | $[-43.459933, -35.558127]$ | Coupled to `cavity:phi(2)` & `cavity:phi(3)` |
| 6 | ACC3/ACC4 Coupled Phase | `cavity:phi(4)` | deg | 310.0534192 | $[279.048077, 341.058761]$ | Coupled to `cavity:phi(4)` & `cavity:phi(5)` |

---

## 3. Physical Objectives & Model Transformations

The framework simultaneously minimizes three primary physical beam quality metrics:

1. **Horizontal Normalized Emittance** ($\varepsilon_{n,x}$): Explicit field `norm_emit_x_m_rad` [$\text{m}\cdot\text{rad}$]
2. **Vertical Normalized Emittance** ($\varepsilon_{n,y}$): Explicit field `norm_emit_y_m_rad` [$\text{m}\cdot\text{rad}$]
3. **RMS Energy Spread** ($\sigma_E$): Explicit field `sigma_energy_eV` [$\text{eV}$]

### Model Space Negation for BoTorch

BoTorch acquisition functions (e.g. `qLogNEHVI`, `qEHVI`) assume objective **maximization**. The transformation between physical space and model space is defined as:

$$Y_{\text{model}} = \mathbf{T}(Y_{\text{physical}}) = -1 \times Y_{\text{physical}}$$

$$Y_{\text{physical}} = \mathbf{T}^{-1}(Y_{\text{model}}) = -1 \times Y_{\text{model}}$$

- **Physical Space**: Smaller values indicate superior beam quality (minimization).
- **Model Space**: Larger (less negative) values indicate superior beam quality (maximization).
- **Reference Points**: All reference points used for acquisition function optimization or hypervolume calculation are explicitly specified in model space coordinates ($R_{\text{model}} < Y_{\text{model}}$).

---

## 4. SI Unit Standards

All exported CSV dataframes, JSON evaluation manifests, and PyTorch tensors adhere to standard SI units:

- **Lengths & Position**: Meters ($\text{m}$)
- **Divergence & Angles**: Radians ($\text{rad}$) / Degrees ($\text{deg}$) for RF phases
- **Energy & Energy Spread**: Electron-Volts ($\text{eV}$)
- **Magnetic Field & Gradients**: Tesla ($\text{T}$) / Tesla per meter ($\text{T/m}$)
- **Particle Counts**: Integer macroparticles
