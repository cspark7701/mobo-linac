# C01 — acceptance definitions and archived-profile comparison

## Scope and source basis

The author identifies C. Kim et al., JINST 19 (2024) P01023 as the injector-design reference. The present configuration is a fixed-lattice derivative, identified by the archived input/configuration hashes in c01_metadata.json, rather than an independently certified current KLS engineering revision. The wider production thresholds originate in the recorded publication configuration. The cited paper does not establish that those widened limits supersede its requirements. Machine-level acceptance therefore remains unverified; manuscript feasibility is explicitly defined relative to this computational profile.

Primary sources: [JINST](https://doi.org/10.1088/1748-0221/19/01/P01023), sections 4.1/4.3 and Table 4 (article text inspected in a [hosted copy](https://www.scribd.com/document/883194285/iop-mo)); [JKPS](https://doi.org/10.1007/s40042-024-01232-2), Table 2; [NAPAC WECN03](https://doi.org/10.18429/JACoW-NAPAC2025-WECN03), Constraints and Feasibility. JINST text and Table 4 disagree on pulse-duration values and do not establish an RMS convention for conversion; no conversion to the present RMS bunch length is invented.

## Objective definition

The configured sigma_energy objective is the last recorded ASTRA Zemit RMS energy-spread column. The installed lume-astra parser multiplies its keV value by 1,000 to obtain eV. It separately retains longitudinal-energy covariance; the objective extraction never subtracts that correlation or performs slice analysis. Thus this is projected total RMS energy spread, including correlated structure, not slice/uncorrelated spread. The emittances are normalized RMS quantities. JKPS's geometric emittance is not substituted directly for them. Relative RMS energy spread is evaluated as sigma_energy/mean_kinetic_energy for the JINST necessary subset. Energy spread is an objective, not a production feasibility cutoff.

## Profiles

| Quantity | Production | NAPAC | JINST necessary subset | JKPS necessary subset |
|---|---|---|---|---|
| Each transverse RMS size | ≤1 mm | <0.30 mm | <0.20 mm | ≤0.20 mm |
| Each RMS divergence | ≤1 mrad | <0.30 mrad | Omitted: numerical bound unavailable | Not specified |
| RMS bunch length | ≤1 mm | <1 mm | Omitted: duration convention ambiguous | ≤0.90 mm |
| Mean kinetic energy | 195–205 MeV | 195–205 MeV | ≥200 MeV | ≥200 MeV |
| Transmission | ≥0.90 | >0.9999 | >0.9999 | Not specified |
| RMS energy spread | Minimized, no cutoff | Fractional objective, no cutoff | ≤0.2% of mean energy | ≤0.5 MeV |
| Geometric emittance | Not a constraint | Not a constraint | Omitted | Omitted |

The scalar transverse-size limits in the journal tables are applied to both planes. Journal-profile outputs are necessary-subset classifications, never full acceptance certificates. No ambiguous pulse-duration or geometric-emittance conversion is used. Boundary strictness is explicit in the generator.

## Results and reproduction

Run `python scripts/analyze_revision_acceptance.py` using the linac-opt environment. The generator checks 30 completed campaigns of 160 unique observations, reproduces every original feasibility label, verifies the common recorded constraint profile, and writes independent derived summaries. Source hashes cover evaluation ledgers, configurations and completion markers.

| Method | Original production feasible | NAPAC profile | JINST subset | JKPS subset |
|---|---:|---:|---:|---:|
| Constraint-aware MOBO | 648 | 12 | 1 | 0 |
| Unconstrained MOBO | 251 | 0 | 0 | 0 |
| Scalarized BO | 200 | 0 | 0 | 0 |

Each method has 1,600 valid evaluations. One JINST-subset success cannot be called fully accepted, because omitted conditions remain unchecked. No JKPS-subset success means none can satisfy the full requirements under the stated both-plane size interpretation. These post-hoc filters do not estimate adaptive performance under changed search constraints. Existing production labels are retained.

## Validation and remaining issue

Two focused tests verify inclusive production and strict published boundaries, invalid/nonfinite exclusion, and the distinction between objective and feasibility constraints. The manuscript now states all eight production inequalities and limits acceptance claims to the defined model. Establishing that these limits represent current KLS booster/transport acceptance still needs engineering evidence; the author-designated JINST reference has different limits. C01 is therefore implemented for the bounded reference-model comparison, with engineering acceptance confirmation explicitly open.
