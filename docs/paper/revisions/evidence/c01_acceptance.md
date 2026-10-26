# C01 — acceptance definitions and archived-profile comparison

## Scope and source basis

The engineering source is now the official **Korea-4GSR Technical Design Report, 4GSR-I-DE-TDR-001, October 2025**, issued by Pohang Accelerator Laboratory and posted on the KLS website. The JINST paper remains the earlier injector-design reference. The current two-quadrupole fixed-lattice model is not asserted to reproduce the full TDR linac/matching system. The production thresholds are computational study choices recorded in the publication configuration; they differ from the TDR, and no supersession of the TDR limits is claimed.

The source-identification gap is resolved. C01 now explicitly distinguishes the production profile, the TDR optimization inequalities and the wider machine specifications. It documents acceptance compatibility of recorded diagnostics, not demonstrated injection into the booster.

Primary sources: [JINST](https://doi.org/10.1088/1748-0221/19/01/P01023), sections 4.1/4.3 and Table 4 (article text inspected in a [hosted copy](https://www.scribd.com/document/883194285/iop-mo)); [JKPS](https://doi.org/10.1007/s40042-024-01232-2), Table 2; [NAPAC WECN03](https://doi.org/10.18429/JACoW-NAPAC2025-WECN03), Constraints and Feasibility. JINST text and Table 4 disagree on pulse-duration values and do not establish an RMS convention for conversion; no conversion to the present RMS bunch length is invented.

## Official TDR edition and exact locations

- [Official document listing](https://kls.kbsi.re.kr/eng/sub0305) and [complete-report record](https://kls.kbsi.re.kr/eng/sub0305/view/id/63794).
- [Complete PDF](https://kls.kbsi.re.kr/_files/board/20260420/f0935668f91c7c3292fd1e843c1a9a25.pdf): 1,006 pages. Cover identifies October 2025; the website posting is April 2026. PDF SHA-256: `47b4218ace4bc8c1a5f166fb5523c7dd63e4962b5882217c1fac90a28126f40d`.
- Section 2.1.4 F, Table 2.1.4.4: printed p. 2-98 / PDF page 115 (one-based), general linac specifications.
- Table 2.1.4.6: printed p. 2-104 / PDF page 121, optimization objectives, seven strict constraint inequalities and control ranges.
- Table 2.1.4.9 and preceding text: printed p. 2-108 / PDF page 125, confirms geometric-emittance interpretation. Its unit labels contain inconsistencies, so they are not used to convert prior numerical results.
- The separately posted accelerator excerpt has different pagination (82, 88 and 91) but matching requirement tables; the manuscript cites the complete report edition. Both tables were checked visually in both PDFs. Full source PDFs remain local, outside Git.

### TDR profile versus production

| Diagnostic | Production | TDR Table 2.1.4.6 |
|---|---|---|
| Each transverse RMS size | ≤1 mm | <0.30 mm |
| Each RMS divergence | ≤1 mrad | <0.2663 mrad |
| RMS bunch length | ≤1 mm | <1 mm |
| Mean kinetic energy | 195–205 MeV | >200 MeV; no upper bound in this table |
| Transmission | ≥0.90 | >0.9999 |

Table 2.1.4.4 separately specifies ≤0.5% relative RMS spread, ≤10 nm geometric emittance and 6–8 ps single-bunch FWHM duration, with additional stability requirements. Reclassification checks the optimization inequalities and, separately, relative spread. It does not convert normalized emittance to geometric emittance or FWHM duration to RMS length without sufficient distribution evidence. The optimization-profile result is therefore not a full machine-specification certificate. The TDR's booster off-energy dynamic-aperture example is not treated as an alternative linac mean-energy tolerance.

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

## TDR reclassification and closure

The TDR optimization profile admits **2 constraint-aware observations, 0 unconstrained observations and 0 scalarized observations**. Both admitted observations also satisfy the separate relative-spread specification. See `c01_tdr_candidates.csv` for their identities and recorded diagnostics. Every original profile count remains unchanged.

Three focused tests verify inclusive production and strict published boundaries, invalid/nonfinite exclusion, the distinction between objectives and constraints, the TDR's absent upper energy bound and its separate relative-spread cutoff. Source hashes and original feasibility labels are verified during the analysis. No new simulations, altered labels or physics changes are involved.

C01's engineering-reference and reclassification work is complete. The documented result is a mismatch between the original production profile and the TDR optimization limits, not evidence that the broader profile meets TDR acceptance. Changing the optimization problem or making a full injector acceptance claim would require separately scoped work; this update does neither.
