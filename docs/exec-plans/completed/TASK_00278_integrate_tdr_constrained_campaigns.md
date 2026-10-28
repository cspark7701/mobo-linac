# Task Completion Summary: Task 00278

## Summary
Complete consolidated round2 task C2-13: analyze the three constraint-aware campaigns that used the KLS TDR optimization inequalities as constraints (seeds 42–44, primary protocol, 160 evaluations each), and integrate the result into the manuscript, the supplement and the task list.

## Key Changes
- **Analysis (`scripts/analyze_revision_tdr_campaigns.py`, `tests/test_revision_tdr_campaigns.py`).**
  - Verifies each ledger against its completion marker.
  - Classifies every observation with the acceptance-profile masks of the primary reclassification.
  - Reports, per campaign, the TDR, production and NAPAC counts, the closest observation, its binding channel and the violated-channel shares.
  - Compares the campaigns descriptively with the TDR-reclassified primary runs of the same seeds, and checks whether any TDR-feasible point dominates the MOGA-derived reference.
  - The worst margin is taken over the six beam diagnostics. Transmission is 1 everywhere, so its 10⁻⁴ margin would otherwise always rank as the closest.
- **Evidence:** `docs/paper/revisions/evidence/r2_tdr_campaign_{runs,violations,feasible}.csv` and `r2_tdr_campaign_metadata.json`.
- **Result.**
  - None of the 480 evaluations meets the TDR inequalities. The campaigns have 58, 52 and 55 production-feasible and 4, 2 and 1 NAPAC-feasible observations.
  - Closest observations: −4.2 % in σ_y′; −0.42 % in σ_x and −0.41 % in σ_y′ (about 1.3 µm and 1.1 µrad); −3.6 % in σ_x.
  - The production-profile constraint-aware runs of the same seeds contain candidate A and otherwise miss by 2.3 % and 9.4 %. Targeting the TDR inequalities did not raise TDR coverage at this budget.
  - After initialization, σ_x had the worst relative margin in 62 % of the targeted campaigns' evaluations, and σ_y′ in 24 %.
  - Recorded feasibility labels agree with the TDR mask in 160/160 evaluations of each campaign.
- **Manuscript (`docs/paper/main.tex`).**
  - New paragraph in "Reach of the TDR acceptance region".
  - One qualitative clause in the abstract (no numbers).
  - One sentence in the Conclusions.
- **Supplement:** the four evidence files are mapped to S1.4 (`evidence_map.csv`, README table), and `ledger_manifest.json` is rebuilt with the completed revision ledgers.
- **Task list:** the C2-13 section, the status table and the simulation table are updated. The seed-43 closest observation is added to the C2-12 settings, because a 0.4 % miss needs a resolution check before it is called infeasible.
- The reviewer responses (C2-11) were also updated, but remain uncommitted drafts until C2-11 is finalized.

## Validation Results
- `ruff check src scripts tests tools` and `scripts/verify_docs_sync.py` passed.
- `tests/test_cli.py`, `tests/test_supplement_map.py` and `tests/test_revision_tdr_campaigns.py` passed.
- `scripts/build_supplement_manifest.py` check passed.
- `latexmk` built `main.pdf` (36 pages) without undefined references.

## Status
Completed and committed locally. No push performed. C2-12 (resolution check) starts after the Sobol arm (C2-14) finishes.
