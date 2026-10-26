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

## Source, geometry and operating-setting interpretation (C08)

We characterize the actual retained source file rather than assuming an undocumented generator model, and provide complete representative controls, objectives and all constraint margins. Both quadrupoles lie between accelerating structures. Saved trajectories show downstream growth of transverse asymmetry from nearly symmetric source moments, but cannot isolate chromatic, coupling, space-charge or discretization mechanisms. The projected energy spread includes chirp. Transmission and the upper energy bound were unviolated in the sample; neither is removed from validation. No measured nominal-lattice improvement or causal mechanism claim is made. Missing source-generation provenance and the need for controlled calculations for stronger causal claims remain explicit.

**Locations:** Beamline and simulation; Interpretation of selected settings; Selected operating settings appendix; C08 supporting records.

## Reliability uncertainty, margin convention and error coverage (C10)

We now report design-specific exact binomial intervals, objective-ratio changes and all constraint-margin components. The score audit reproduces every retained statistic: one pair of equal scores arises from clipping with equal recorded energy margins, and another pair is equal only after rounding. The revised main table therefore reports feasibility uncertainty, D and the limiting margin rather than treating the score as a physical ranking. The energy margin uses threshold normalization, not the band half-width; physical headroom is provided separately.

We identify each selected run and design in the supporting manifest, explain common random numbers across designs and identical cavity errors within each phase pair, and do not pool trials into a universal reliability estimate. We retain the existing small lattice-jitter scope. The requested RF-amplitude/JKPS/alignment extensions and ambiguous tolerance scan are not performed in this revision; broader machine-reliability or comparative robustness claims are therefore not made. This non-adoption is disclosed rather than represented as satisfying the requested expanded model. A future scan would require an explicit per-channel RMS error table before execution.

**Locations:** Robustness assessment and results; revised robustness table; C10 independent audit and per-design supporting statistics.

## Predictive surrogate validation (C11)

We restored every saved pre-proposal model and checked predictions against its next unseen batch, with explicit training-identity exclusion. The manuscript reports undercoverage of nominal Gaussian intervals and diagnostic-boundary performance. Covariance-based and library variance-floor intervals are separated to avoid artificial apparent calibration in small physical units. Constant transmission does not permit validation of loss discrimination. Fitting recovery remains distinct from calibration, and the analysis does not turn model feasibility into a calibrated machine-reliability claim.

**Locations:** Predictive checks on unseen batches; predictive appendix; C11 per-observation and aggregate evidence.

## Reproduction and computational cost (C13)

The supporting manifest now links the startup code, executable, static inputs, software, actual budgets, devices and worker settings to the saved campaigns and seed identities. Configuration defaults are distinguished from effective CLI/history settings. We report paired relative durations and an overlap-aware evaluation-interval union; summed parallel worker times are not used as wall-time fractions. The remainder is described as combined model/acquisition/orchestration overhead because the records do not separately time its components. Absolute durations remain outside the manuscript, and no universal speedup or GPU/CPU comparison is claimed.

**Locations:** Simulation validity and computational comparison; C13 reproduction and timing manifest; paper README.

## Baseline matrix and non-adopted controls (C07)

The revised Methods and supporting matrix identify the actual matched three-method comparison and separate the independently initialized unequal-budget weighting survey. The scalarized baseline is explicitly the equal-weight strategy. At the author's request we retain the existing simulations and do not add constrained scalarized BO, a full-budget Sobol control, a corrected-method campaign or any MOGA run. Therefore no vector-over-constrained-scalarization advantage, BO-over-space-filling advantage or matched MOGA ranking is asserted. These missing controls limit the scope of inference; their requested execution is not claimed complete. Reclassified observations and offline acquisition ranks do not stand in for adaptive campaigns under changed definitions.

**Locations:** Primary comparison protocol; C07 comparison matrix and scope report; Discussion limitations.

## Constraint-unit sensitivity and corrected-arm request (C06)

We quantify the original physical smoothing scales and evaluate frozen early/middle/late surrogates on common candidate/posterior samples. Equivalent raw-unit representations change acquisition ranks, whereas explicit dimensionless residuals preserve values to numerical precision. The highest-ranked candidate in this limited probe set is unchanged, so we do not overstate the sensitivity result. This is a q=1 offline comparison with an identical unpruned baseline, not production q=8 proposal replay or evidence of improved beam quality. At the author's explicit request we retain existing simulations and do not run a corrected arm. The paper therefore describes the original raw-residual implementation and limits its conclusions accordingly; the requested new physical-performance comparison remains unperformed.

**Locations:** Constraint handling and smoothing; Offline sensitivity of constraint smoothing; C06 scales, acquisition values and rank comparisons.

## Table populations, labels and units (C14)

Survey case extrema now use feasible observations consistently with the aggregate table, with explicit population and coordinate-minimum captions. Unsupported operational/FEL labels and internal Phase names are replaced by weighting and method names. Stale reference-point text is removed. Main tables use readable layouts rather than whole-table resizing; units use siunitx, and the robustness table reports the C10 components and uncertainty. Original data and archived tables are preserved.

**Locations:** Primary, survey, weighting-case and robustness tables; C14 derived population audit.

## Figure clarity and survey presentation (C15)

The scalarized survey now shows separate 176-evaluation histories for every weighting, not a concatenated 880-point trajectory. Method colors/markers are consistent and manuscript plots are vector outputs without redundant titles. Full-range constraint panels retain every observation and add transverse acceptance zooms; constant transmission is retained as an explicit count/value/threshold annotation. We do not invent an energy-spread constraint. The detailed unequal-budget survey moves to an appendix. The C03 attainment analyses and C08 representative settings supplement the existing scatter-only Pareto projections, which retain grid lines.

**Locations:** Primary feasibility/constraint figures; exploratory survey appendix; C15 plotting source and input manifest.
