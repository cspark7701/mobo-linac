# Task Completion Summary: Task 00270

## Summary
Complete the required parts of consolidated round2 task C2-01: make the study target and acceptance population consistent and reframe the paper's KLS relevance around the TDR result. The optional TDR-constrained campaigns (seeds 42–44) are still running. Their results will be added in a follow-up commit.

## Key Changes
- **Origin of the production limits.** Traced to `docs/physics/constraint_rationale.md`, written at the configuration freeze on 2026-07-24, before the campaigns. Section 2.2 now describes the limits as a deliberately relaxed computational acceptance profile, not a KLS engineering requirement. It records that earlier near-TDR limits produced a high rate of infeasible early space-filling samples in this domain, and that the production transverse limits are 3–4 times looser than the TDR's. This replaces "The TDR does not justify replacing its requirements…".
- **Title.** "Multi-objective Bayesian optimization of a 200 MeV injector-linac model derived from the Korea Light Source design".
- **Abstract.** Without numbers: a pipeline comparison on a fixed-lattice model derived from the KLS design, with feasibility from a relaxed computational profile, and the TDR requirements met by only a few settings at the edge of the explored domain.
- **Population wording.** "All archived observations" becomes "the 4,800 primary evaluations" (648/251/200 production-feasible, 2/0/0 TDR).
- **New table of the two TDR candidates** (stable labels A and B), with objectives, relative spread and signed physical margins from `evidence/c01_tdr_candidates.csv`. The text states that both are marginal and come from different matched runs, that they are not jitter representatives, and that two against none is coverage, not a ranking.
- **New Discussion subsection** on reaching the TDR region: it lies at the edge of the six-control domain; the MOGA-derived nominal misses it by 2.7 µrad in vertical divergence and 12 of its 50 jittered neighbours pass; the full TDR linac has controls fixed here.
- **Conclusions** state the limited engineering conclusion.

## Validation Results
- Every table value was recomputed from `c01_tdr_candidates.csv`. The abstract passes the no-number test.
- `latexmk` built a 33-page PDF without undefined references or overfull boxes. `tests/test_paper_outputs.py`: 53 passed.

## Status
Required parts completed and committed locally. The optional TDR-constrained campaigns are pending. No push performed.
