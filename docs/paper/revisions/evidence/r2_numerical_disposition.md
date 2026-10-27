# C2-04 — Numerical-resolution disposition (round2)

## Question
Both round2 reviewers ask the manuscript to report the completed convergence study (author confirmation, Tasks 00226–00227). That means quoting the resolutions tested and the residual changes in ε_n and σ_E at the adopted settings, or else restricting the claims to nominal resolution. Neither reviewer asks for a new convergence campaign.

## Search for the existing record (2026-10-27)
| Location | Result |
|---|---|
| `docs/paper/revisions/evidence/c09_convergence_report.md` (round1) | Kim et al., JINST 19 (2024) P01023, section 4.3, gives the settings (10,000 macroparticles, 32 radial and ≤ 32 longitudinal cells, mirror charges) but no refinement scan or residual. The JKPS study reports physical error propagation, not numerical convergence. |
| `/home/cspark/Work/projects/linac/beam_tracking/` and `.../cmkim/` | Every injector deck uses `Nrad=32`, `Nlong_in=32` and `Nxf=Nyf=Nzf=32`. No particle or mesh scan, and no residual table or notebook. The only resolution comments belong to a DC-gun template (`templates/dcgun`, an unrelated gun). |
| `mobo-linac` documents and git history | No convergence data; only the round1 records of the author's confirmation. |

## Disposition adopted in the manuscript
The fallback route of C2-04:
- Section 2.1 states that the resolution was adopted from the previous study of this injector, gives the settings correspondence, and says that no quantitative refinement residual is reproduced. All objective values, classifications and margins are labelled as nominal-resolution results.
- Section 6.2 states that small margins are not treated as numerically resolved. These are the TDR candidates' horizontal-size margins of about 2.47 and 8.93 µm and bunch-length margins of about 8.16 and 7.96 µm (from `c01_tdr_candidates.csv`), together with objective differences of order 0.1 µm·rad. The selected settings are not presented as numerically validated engineering settings.
- No deterministic repeat, GP likelihood variance, jitter spread or output precision is used as a substitute for discretization error.

## How to upgrade
If the author locates the original convergence record (resolutions tested and residuals in ε_n and σ_E), section 2.1 can quote it and section 6.2 can compare it with the margins above. No new convergence campaign is planned or requested.
