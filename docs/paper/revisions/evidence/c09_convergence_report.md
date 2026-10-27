# C09 — Previous numerical-convergence evidence

## Status
Closed by explicit author instruction on 2026-10-26, with the unresolved scientific limitations retained. The author closes C09 with the cited JINST resolution correspondence and an explicit absence of a traceable numerical-error bound. No repeat convergence campaign or full solver-equivalence claim is adopted. Closure is administrative scope disposition, not new validation evidence.

## Identified reference and source boundary
The author identifies C. Kim et al., JINST 19 (2024) P01023, DOI [10.1088/1748-0221/19/01/P01023](https://doi.org/10.1088/1748-0221/19/01/P01023), as the prior study. Its bibliographic entry `Kim2024KLSMOGA` is already in the manuscript. The actual paper text in [the hosted article copy](https://www.scribd.com/document/883194285/iop-mo), section 4.3, printed page 13, specifies 10,000 macroparticles, 32 radial cells, at most 32 longitudinal cells and mirror charges. These are consistent with the corresponding current settings. This comparison uses the paper body, not the host's AI summary.

No particle/grid refinement sweep or residual numerical-error estimate was found in the inspected article text. Its discussion of increasing optimizer generations concerns algorithm convergence and cannot be substituted for tracking-discretization convergence. The paper does not establish the Cartesian grid or the 2D/3D transition settings used here.
The [JKPS author-hosted full text](https://kuacc.korea.ac.kr/bbs/kuacc/993/174430/download.do) reports tracking and physical error propagation, not a particle/grid numerical-convergence dataset. It cannot establish the missing settings equivalence or residual-error values. Physical error amplitudes are not numerical uncertainty estimates.

[Task 221](../../../exec-plans/completed/TASK_00227_record_completed_convergence_study.md) records the author's confirmation that the numerical-convergence work is already done. That confirmation is retained. It does not include the exact source passage, uncertainty values or original input files, so those details must not be inferred from it.

## Verified current settings
The read-only [C02 audit](c02_phase_audit.json) checked all 4,800 archived primary input decks; all use the following settings:

| Item | Current archived value | Verified prior-study equivalent |
|---|---|---|
| Distribution records | 10,000 in each of 30 inspected source copies; identical SHA-256 | 10,000 macroparticles stated in section 4.3; exact source identity unverified |
| Counted tracked particles | 9,999 initial particles in each evaluation record; the first distribution record is the reference particle | Not established from retrieved source |
| Cylindrical grid | `Nrad=32`, `Nlong_in=32` | Consistent with section 4.3: 32 radial and at most 32 longitudinal cells |
| Cartesian grid | `Nxf=Nyf=Nzf=32` | Not established from retrieved source |
| Solver transition | `L2D_3D=True`, `z_trans=5.25` m | Not established from retrieved source |
| Cathode image charge | `Lmirror=True` | Included in section 4.3 |
| Integration settings | `H_max=0.01`, `H_min=0.001` | Not established from retrieved source |

The distribution count distinction is important: a 10,000-record ASTRA file does not imply 10,000 counted physical macroparticles in transmission accounting. The audit records file hashes and paths to support future exact-input comparison.

## Fixed noise and resolution
Repeatable outputs from a fixed particle distribution justify treating this pipeline as deterministic for fitting purposes. A fixed GP likelihood variance is regularization, not an estimate of the tracking discretization error. Thus identical settings across methods and deterministic repeats do not quantify the absolute accuracy of their objective differences or feasibility margins. C05 separately audits the effective library noise floors.

No residual numerical uncertainty is quoted here because a traceable value has not been found. It is not scientifically valid to infer that value from the physical jitter spread, the number of decimal places in ASTRA outputs, the configured GP noise, or a method-to-method difference.

## Evidence needed for stronger future claims
Locate the existing numerical-validation record underlying the author confirmation, with particle/mesh scans and a residual uncertainty estimate, together with enough input settings to establish the remaining solver equivalence. The cited article provides baseline resolution, but no quantitative refinement bound was found there. Then compare those existing uncertainty values with reported method effects and representative constraint margins. No repeat convergence campaign is requested.

The [manuscript snippet](c09_convergence.tex) cites the identified prior injector study and documents the verified resolution correspondence while deliberately not claiming an unverified uncertainty bound or full solver equivalence. C09 is closed by scope decision; quantitative accuracy remains unestablished unless those source details become available.
