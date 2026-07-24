# Task 03 Summary: Freeze Constraints, Objectives, Units, and Design Space

## Canonical Publication Configuration
- Created canonical publication configuration `configs/publication_200mev.yaml`.
- Defined 6 design variables with ASTRA key mappings, units, nominal values, and bounds:
  1. `solenoid_field_T`: `solenoid:maxb(1)` $[0.097387, 0.292161]\text{ T}$
  2. `quad_1_gradient_T_m`: `quadrupole:q_grad(1)` $[0.643264, 1.929793]\text{ T/m}$
  3. `quad_2_gradient_T_m`: `quadrupole:q_grad(2)` $[-4.330028, -1.443343]\text{ T/m}$ (strictly ordered negative bounds)
  4. `gun_phase_deg`: `cavity:phi(1)` $[32.062479, 39.187475]^\circ$
  5. `acc1_acc2_phase_deg`: `cavity:phi(2)` $[-43.459933, -35.558127]^\circ$ (coupled to `cavity:phi(3)`)
  6. `acc3_acc4_phase_deg`: `cavity:phi(4)` $[279.048077, 341.058761]^\circ$ (coupled to `cavity:phi(5)`)

- Defined 3 physical minimization objectives and model-space negation transformation ($Y_{\text{model}} = -1 \times Y_{\text{physical}}$):
  1. `norm_emit_x_m_rad` [$\text{m}\cdot\text{rad}$]
  2. `norm_emit_y_m_rad` [$\text{m}\cdot\text{rad}$]
  3. `sigma_energy_eV` [$\text{eV}$]

- Defined constraint sensitivity profiles: `stringent`, `nominal` ($1.0\text{ mm} / 1.0\text{ mrad} / 90\%$), and `relaxed`.

## Documentation Deliverables
- Created [docs/physics/constraint_rationale.md](file:///home/cspark/Work/projects/mobo_linac/docs/physics/constraint_rationale.md): Technical note documenting constraint thresholds, physical sources, and resolution of historical threshold discrepancies.
- Created [docs/physics/objective_and_unit_conventions.md](file:///home/cspark/Work/projects/mobo_linac/docs/physics/objective_and_unit_conventions.md): Centralized document detailing 6D design space, minimization vs model maximization, and SI unit conventions.

## Tests & Verification
- Created `tests/test_physics_specification.py`:
  - `test_publication_config_loading`: Verified `publication_200mev.yaml` parsing.
  - `test_design_variable_bounds_and_negative_ordering`: Verified $L \le U$ ordering, including negative quadrupole 2 gradient bounds.
  - `test_coupled_phase_configurations`: Verified coupled phase target declarations.
  - `test_objective_transformations`: Verified minimization <-> model maximization roundtrips.
  - `test_sensitivity_profiles`: Verified `stringent`, `nominal`, and `relaxed` profile retrieval.
- Pytest suite executed successfully: 52/52 unit tests passed.

## Acceptance Criteria Status
- [x] No production script hard-codes objectives, constraints, or bounds.
- [x] Canonical publication configuration created and loaded by default.
- [x] Manuscript and code conventions synchronized.
- [x] Physical and model-space objective columns are unambiguous.
- [x] Negative parameter bounds are ordered correctly ($L \le U$).
- [x] Coupled phases tested and validated.
