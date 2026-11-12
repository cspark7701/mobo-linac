# Task Completion Summary: Task 00381

## Summary
Drafted a protocol for a 60-setting particle-count convergence ladder, at the author's request after round 6 closed. Only the macroparticle count varies; the step and grid stay at the round 6 fine values, by the author's instruction. The draft is for approval and is not frozen; no run was started.

## Key Changes
- New `docs/paper/revisions/particle_ladder_protocol_draft.md`, covering:
  - **Scope:** a new study, not a continuation of C6-06. It tests particle-count convergence at one fixed discretization only, and cannot establish step/grid convergence.
  - **Sample:** 60 of the 387 round 6 settings, 5 per method × feasibility × boundary cell, seed 20261112. Selection uses no refinement outcome.
  - **Levels:** 10k, 20k, 40k, 80k, 160k and 320k particles, all from quasi-random sources generated with the round 6 deck, at fine step and grid. The 20k and 40k files are reused from round 6.
  - **Gate:** the 40k rerun must reproduce the round 6 combined-fine values (rtol 1e-9) before the other levels run.
  - **Endpoints:** the primary endpoint is the fraction of settings with |Δε_x| and |Δε_y| at most 1 % over 160k → 320k. The secondary endpoints are the changes per doubling, the diagnostic tolerances, the convergence rate with a conditional Richardson estimate, and feasibility changes.
  - **Budget:** 360 attempts, about 594 CPU-h, about 27 h on 22 workers (range 20–45 h), and at most about 25 GB of disk.
  - **Open author decisions:** a purposive set of the 4 round 6 flips, the top level (320k or 160k), and the worker ceiling.
- Analysis behind the draft: from the round 6 records, the step/grid change from medium to fine alone gave a median −5.5 %/−7.4 % in ε_x/ε_y, and 10k → 40k particles at fine gave −2.0 %/−2.3 %. Per-run costs come from the round 6 fine-level means.

## Validation Results
- `tests/test_docs_links.py`: 2 passed.
- Documentation only; no code or evidence changed, and no simulation was run.

## Status
Draft committed locally for author review. The study needs the author's approval, its driver and tests, and a committed freeze before any physical run. No push performed.
