# Reviewer 2 — round1 response draft

**Status:** Partial response covering C01, C02, C09 and C12. Other comments remain tracked in the consolidated revision list; this is not a completed submission response.

## Prior work, paper scope and MOGA comparison (C12)

The revised Introduction explicitly states that this paper investigates MOBO by comparing its constraint-aware and unconstrained variants with scalarized BO. It cites the completed JINST MOGA optimization, the JKPS error-analysis study and the separate NAPAC2025 BO/MOGA publication. ICABU contributions are identified as presentations.

We distinguish the JINST abstract summary from its section 4.3 tracked setting, and identify differences in controls, objective definitions, acceptance limits and source evidence. The published results provide context for the physical trade-offs. The manuscript does not infer a matched-budget MOGA ranking or computational speedup.

The author has elected not to adopt new MOGA/NSGA-II benchmarks or fresh tracking of the published MOGA setting: those simulations fall outside the present MOBO study, and the MOGA study is already published. This is an explicit scope decision, not a claim that the requested runs were performed or that the reviewer has accepted their omission. The revised claims are limited accordingly.

**Locations:** Introduction; Discussion, Relation to previous KLS injector studies; C12 evidence report. Related acceptance, phase and numerical-evidence limitations are documented separately under C01, C02 and C09.

## Engineering acceptance reference (C01)

We now cite the official Korea-4GSR Technical Design Report, 4GSR-I-DE-TDR-001 (October 2025), section 2.1.4 F and Tables 2.1.4.4/2.1.4.6. The revised constraint table distinguishes its published optimization inequalities from the broader computational profile used for the completed comparison. The production limits are not presented as engineering limits that supersede the TDR.

A separate post-hoc reclassification of the retained observations finds two constraint-aware observations and none from either baseline satisfying the TDR optimization inequalities. Both also pass its relative energy-spread specification. This does not certify all beam specifications or downstream injection acceptance, and filtering the archived records does not reproduce adaptive optimization under revised constraints. Original labels, budgets and measured outcomes remain unchanged.

**Locations:** Injector model and optimization problem; constraint table and following acceptance comparison; C01 evidence report with exact TDR pages and source hash.

## Phase-domain interpretation (C02)

The archived decks use absolute phases with automatic phasing disabled. The manuscript gives the actual angular windows and nominal coordinates, describes common phase controls for each structure pair, and identifies the unequal percentage-derived windows as inherited search bounds. Prior published off-crest values cannot calibrate the current trajectories. The upper-quarter coverage result is descriptive only. We retain this limitation and do not undertake a crest scan or altered-domain campaign in this revision; algorithm conclusions apply only to the recorded domain.

The author has closed this revision item with these limitations explicitly retained. The original validation request is not represented as fulfilled, and reviewer acceptance of this scope decision is not presumed.

**Locations:** Methods and Discussion, Limitations; C02 evidence report and consolidated disposition.

## Numerical-resolution evidence (C09)

The manuscript cites Kim et al., JINST 19 P01023 for the reported particle-count scale, cylindrical grid and image-charge treatment. The inspected publication does not supply a refinement-error bound or establish all current Cartesian/transition settings. We retain the author confirmation of prior convergence work without inventing missing quantitative evidence. No repeat convergence study is undertaken. Numerical uncertainty relative to objective differences or narrow feasibility margins remains unquantified; GP regularization is not an error estimate.

The author has closed this revision item with these limitations explicitly retained. The original validation request is not represented as fulfilled, and reviewer acceptance of this scope decision is not presumed.

**Locations:** Methods and Discussion, Limitations; C09 evidence report and consolidated disposition.
