# Grid × particle convergence matrix — protocol

**Status: FROZEN at the commit that adds this file together with `rm_specification.json` and `rm_settings.csv` (2026-11-12).** The author authorized step 2 of the follow-up on 2026-11-12. This is a new study after round 6, not a continuation of C6-06. The round 6 protocol ([r6_protocol.md](../evidence/r6_protocol.md)) and its results are unchanged, and the manuscript and supplement are not modified by this study.

## Question and rationale

Round 6 left the emittances unconverged: fine and medium differ by a median 5.5 % (x) and 7.4 % (y). The earlier one-factor checks give the following picture:

| Change (median) | Source | ε change |
|---|---|---|
| Step: production → half | r2, 10 settings, 10k | −13.8 % |
| Step: half → quarter | r2, 10k | about −1 % |
| Grid 32 → 48 / 64, production step | r2, 10k | −7.7 % / −4.2 % (non-monotone) |
| Grid 48 → 64 with step half → quarter | r6, 387 settings, 10k | −5.5 % / −7.4 % |
| Particles 10k → 40k at fine | r6, 387 settings (source also regenerated) | −2.0 % / −2.3 % |

The template uses 3D space charge after z = 5.25 m, with a cylindrical grid before that. A 64³ grid holds about 262k cells, so 10k–40k particles leave 0.04–0.15 particles per cell. Grid and particle count are therefore likely coupled, and refining either alone may not converge.

**Question.** At half step, is there a grid and particle count at which one more refinement of either changes both emittances by at most 1 % for most settings? Is half step adequate at 64 cells?

## Sample

- **Source:** 15 settings from the frozen round 6 sample of 387 (`r6_sampling_manifest.csv`, checked against the round 6 specification and ledgers).
- **Selection:** for each method, one setting from each production-feasibility × boundary cell, plus one more drawn at random from that method's remaining settings.
  - Seed `20261112`; rows sorted by `setting_id`.
  - The exact inclusion probability within the 387 is recorded in `rm_settings.csv`.
- **No outcome used:** no round 6 refinement outcome is used in selection.
- **Scope:** the 15 settings show resolution behaviour across methods and feasibility states. They are not a population sample: no feasible fraction or method comparison is estimated.

## Levels (11 per setting, 165 attempts)

| Level | Step (h_max / h_min) | Grid (nrad = nlong_in = nxf = nyf = nzf) | Particles |
|---|---|---|---|
| `half_g{32,48,64}_n{40,160,640}k` (9 levels) | 5 mm / 0.5 mm (half) | 32, 48, 64 | 40k, 160k, 640k |
| `quarter_g64_n40k` (gate) | 2.5 mm / 0.25 mm | 64 | 40k |
| `quarter_g64_n640k` | 2.5 mm / 0.25 mm | 64 | 640k |

- **Sources.** All are quasi-random, from ASTRA `generator` with the round 6 deck, changing only `IPart` and `FNAME`.
  - 40k is the round 6 file itself, copied and checked (SHA-256 `a63673af…1425`).
  - 160k and 640k are generated at the freeze, and their hashes are in the specification.
- **Other inputs.** The production template, field maps and binary are unchanged, with the hashes from the round 6 specification. Only the namelist overrides above change.
- **Feasibility check (not a study outcome).** On 2026-11-12, a 640k source was generated, and a 2 cm ASTRA run on the 64-cell grid accepted 640,000 particles with 71 MB of memory. No physics output was used.

## Gate and execution

1. **Reproduction gate.**
   - `quarter_g64_n40k` runs first for all 15 settings. It must reproduce the round 6 combined-fine record of the same setting for every objective and diagnostic (rtol 1e-9, atol 1e-12).
   - A mismatch or invalid run blocks the matrix. The attempt is kept.
2. **Matrix.**
   - The other 10 levels run, longest first.
   - There are no automatic retries or physics changes. Invalid attempts stay in every denominator.
3. **Resources.**
   - 22 workers, one thread per process. Tracking timeout 24 h per attempt.
   - At least 100 GiB free disk at stage boundaries.
4. **Output and freeze.**
   - Outputs go to `results/convergence_matrix/`: an append-only checksummed journal, a pending list for interrupted attempts, and a completion record.
   - The runner refuses to start unless the specification and settings are committed, and the template matches its hashes.

## Endpoints (predeclared; analysis code `scripts/analyze_convergence_matrix.py` committed with the freeze)

For each setting and objective, the relative change across each refinement in the matrix is computed:
- **particles ×4** at a fixed grid, half step (6 refinements);
- **next grid** at fixed particles, half step (6 refinements);
- **half → quarter step** at 64 cells, for 40k and 640k (2 refinements).

**Primary: 1 %-adequate points.**
- A half-step point (G, N) is adequate if, for every refinement available from it, at least 80 % of the 15 settings (12) change both ε_x and ε_y by at most 1 %.
- An invalid comparison counts as not within 1 %.
- The point (64, 640k) has only the step refinement. It is reported as terminal, with the step-check result, because its grid and particle count cannot be assessed inside the matrix.
- The study reports every adequate point and the cheapest one.

**Secondary:**
- **Change summaries:** median signed and absolute changes per refinement for ε_x, ε_y and σ_E.
- **Diagnostics:** the share of settings within the round 6 diagnostic tolerances per refinement.
- **Feasibility:** classification changes per refinement.
- **Particle extrapolation:** per grid, the ratio of successive ×4 particle changes and a geometric estimate of the change still remaining at 640k. This is made only where both changes have the same sign and the ratio is below 1; otherwise the setting is reported as not extrapolable.
- **Ranking:** Spearman correlation of each level with `half_g64_n640k` (15 settings, descriptive).

**Interpretation rules, fixed now.**
- **Candidate resolution:** an adequate point is a candidate converged resolution for these 15 settings only. Confirming it on a larger sample (step 3) needs separate authorization.
- **No adequate point:** if no point is adequate, absolute emittance convergence stays unresolved within this matrix. Levels are not added after outcomes are seen.
- **Fixed design:** no setting, level, tolerance or share is changed after the freeze.
- **Manuscript:** it changes only by the author's separate decision.

## Budget (planning estimate, not a deadline)

- **Range:** cost estimates bracket the runtime between two extremes.
  - **Upper bound:** linear-in-particles extrapolation from the round 6 timings, which were measured under 22-worker load. It gives about 26k s per run at quarter step, 64 cells and 640k.
  - **Lower bound:** the 2026-11-12 probe on an idle host. Over the first 2 cm, 16× the particles cost about 2.7× per step.
  - **Total:** about 390 CPU-h at most, giving roughly **10–25 h on 22 workers**. The planning value is about 20 h, including the gate (about 1 h).
- **Disk:** at most about 100 MB per run, 15 GB in total. 741 GiB was free.
