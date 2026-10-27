# Task Completion Summary: Task 00273

## Summary
Complete consolidated round2 task C2-08, including its authorized optional run: interpret the lattice-jitter results conditionally, add the RF-amplitude estimate and the local-convergence (dominance) check, and assess the two TDR-passing observations under jitter against the TDR profile.

## Key Changes
- **Optional run** (driver from Task 00265): 50 lattice-jitter trials (common seed 42) for each of the two TDR candidates, classified with the TDR-profile configuration. Outputs are in `results/revision_round2/references/tdr_candidate_jitter/`.
- **Dominance check** (archived audit, no new runs): 14 and 8 of 50 perturbed settings Pareto-dominate the spread-extreme and centroid-distance nominals, and all of them are feasible; the other settings have 2, 1, 0 and 0. The selected settings are not locally converged along the jitter directions. Evidence: `r2_jitter_dominance.csv`.
- **RF-amplitude estimate.** The structure-pair gains from the re-evaluated nominal tracking are 4.1, 93.3 and 102.8 MeV. A 0.2 % amplitude error then shifts the mean energy by 0.28 MeV (independent pairs) to 0.40 MeV (correlated). That is about 10× the 0.014–0.046 MeV produced by the simulated phase jitter, and at least 7.8 σ below the 3.11 MeV headroom; the effect on σ_E is about 0.8 keV. Evidence: `r2_jitter_metadata.json`.
- **TDR candidates under jitter.** Both stay production-feasible in 50 of 50 trials, but only 36/50 (0.58–0.84) and 44/50 (0.76–0.95) meet the TDR inequalities, failing mainly on horizontal size, and also on vertical divergence for candidate B. Candidate A falls below the 0.8 fragility threshold. Evidence: `r2_tdr_candidate_jitter_{summary,trials}.csv`.
- **Manuscript.** The robustness results state that the classification is conditional on the lattice-only error model and is no reliability guarantee, and add the dominance, RF-amplitude and TDR-candidate paragraphs. The JKPS comparison paragraph points to the first-order amplitude estimate.

## Validation Results
- All 100 jitter runs are valid ASTRA executions. The counts were recomputed with `profile_masks`, and the bounds with the exact Clopper–Pearson helper.
- `tests/test_paper_outputs.py` and `tests/test_revision_jitter_checks.py` passed.
- `latexmk` built a 35-page PDF without undefined references or overfull boxes.

## Status
Completed and committed locally. No push performed.
