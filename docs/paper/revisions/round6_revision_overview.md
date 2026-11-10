# Round6 revision overview

> **Execution status — 2026-11-10:** both adopted studies are complete and integrated into the manuscript (A6-08, Task 00378). All 1,935 numerical and 3,200 scaling attempts were valid. Re-tracking changed 4 of 387 classifications (all infeasible to feasible, constraint-aware) and kept the feasible-sampling advantage positive in all ten groups, but the emittances still differ by a median 5.5–7.4 % between medium and fine levels (adverse: not converged). The normalized-residual convention lowered the feasible fraction by 0.118 (95 % interval 0.099–0.136), in all ten groups (adverse to the convention). Evidence: S1.16. Reviewer responses and final validation (C6-09/A6-09) remain. This note supersedes the restart and pause notes below.

> **Restart status — 2026-11-04:** the author authorized the restart. Worker ceiling raised to 22 by [amendment 01](evidence/r6_protocol_amendment_01.md); the two interrupted attempts were retained and re-tracked in isolation (`evidence/r6_recovery_01.json`); the pause marker is archived. The journal holds 433 of 1,935 numerical results (387 production, 46 combined-fine). Remaining refinement and scaling have not started. This note supersedes the pause note below.

> **Execution status — 2026-11-02: PAUSED by user request.** The chain and its ASTRA workers are stopped. The checkpoint preserves 387 nominal and 44 fine-resolution results; two interrupted attempts require recovery inspection before any authorized restart. Scaling campaigns and final integration remain pending. See [the pause and restart record](round6_pause_status.md). This administrative update supersedes earlier running/queued status below; reviewer assessments and frozen scientific evidence remain unchanged.

Reviewed manuscript baseline: `9fd076a`; execution baseline: `79cecb9`.

> **Closure — 2026-11-10 (Task 00379):** every C6 item has a disposition; see [Closure](#closure--2026-11-10) at the end. The sections between here and there are dated execution records kept as written.

## Author disposition (C6-05)

On 31 October 2026 the author explicitly adopted representative numerical validation (C6-06/A6-01–03) and contemporaneous raw/normalized acquisition campaigns (C6-07/A6-04–06), and omitted the optional constraint-aware scalarized comparator (C6-08/A6-07). This supersedes the earlier nominal-model-only execution scope. Historical results and exploratory front-quality status remain unchanged. Neither reviewer recommendation is represented as consensus or journal acceptance.

The resource ceiling is **two CPU evaluation workers total**, across both workstreams. Execute the workstreams serially to enforce that ceiling; use CUDA for GP/acquisition work when available, retain double precision, and limit numerical-library CPU threads. Protocols, exact sample sizes, analysis choices and budgets must be frozen before new outcomes. That statement described the disposition step; the nominal reproduction stage is now running under the frozen protocol.

The author explicitly authorized a git push when the revision tasks are finished. This overrides the older no-push statements in the planning documents; it does not authorize remote GitHub Actions queries or public artifact deposition.

## Completed editorial work

- C6-01: defined minimization of the weighted sum of individually scaled physical objectives in prose, preserving equal weights and qLogNEI.
- C6-02: removed the appendix kernel hypothesis and retained conditional adaptive-test-point wording.
- C6-03: restored “specified” pipelines and a statement about the present findings, with a number-free abstract of 268 whitespace-delimited words.
- C6-04: rewrapped the undercoverage paragraph; whitespace-normalized tokens are identical.

Focused manuscript/link checks: **4 passed**. The two-column manuscript builds successfully to **31 pages**. Further code, simulation, scientific integration and final packaging checks remain pending.

## Remaining work

A6-01 is frozen (387 sampled settings, 1,935 numerical attempts, 3,200 scaling attempts). The numerical runner and normalized acquisition are implemented, with nominal reproduction running. The sequential campaign/analysis chain is queued behind the initial regression run. It performs a fresh complete validation on the final code, then waits for the numerical worker lock before continuing refinement and matched campaigns. Finish both research branches, analyze all outcomes, integrate supported findings, and complete separately attributed reviewer responses and C6-09 validation. Numerical validation does not establish scaling efficacy, and scaling campaigns do not establish tracking convergence. Optional constrained scalarization is not adopted; retain that limitation.

## Optional comparator disposition (C6-08 / A6-07)

Completed as an explicit non-adoption decision, not as an executed comparison. The author requested both main validation studies and omitted the optional constrained-scalarized arm. Its absence remains a manuscript limitation; the new raw/normalized comparison cannot establish a unique benefit of vector-valued acquisition over constraint-aware scalarization.

## Research preparation checks

- Normalized acquisition/configuration: 159 focused checks passed, including real q=8 acquisition gradients on CPU and CUDA, signs/unit consistency and mode-preserving checkpoint restoration.
- Sampling and existing checkpoint/recovery tests: 117 passed.
- Expanded new-study runner/analysis tests: 12 passed; synthetic adverse outcomes and invalid receipts are included.
- Lint and documentation sync passed. Complete non-integration regression/coverage validation remains in progress.
- Initial completed nominal observations reproduce their archived values. The full 387-setting gate is not yet complete; no claim about refined outcomes is made.
- Measured level costs in the frozen protocol imply approximately three weeks (two-to-four-week planning range) at two workers, superseding the preliminary chat estimate.

## Persistent execution and pending completion

Nominal runner PID at launch: `1743216`; queued continuation PID: `1783242`. These are launch records, not permanent process identities. The continuation waits for the initial regression process, then runs the full stable-code validation/100% coverage gate before further physical work. It shares the two-worker lock with the nominal stage, checks all nominal reproductions before refinement, and runs scaling only after numerical tracking and analysis finish.

At the readiness snapshot, 10 of 387 nominal reproductions were complete and matched their archived values; two ASTRA child processes were active in round6 output directories. Snapshot and environment records are under `results/revision_round6/`. Updated counts must be read from the journal rather than inferred from this historical snapshot.

The chain writes a separate local completion-summary commit after each successfully verified validation, numerical-analysis and scaling-analysis stage. It verifies receipts/output hashes, preserves unrelated staged work, and does not push. The remaining scientific interpretation, manuscript/supplement integration, reviewer responses, upload-folder checks and final authorized push require completed evidence. None is marked complete in advance.

Latest focused preparation checks: nine normalized-mode tests and sixteen runner/analysis/commit-safety tests pass. Frozen sample/specification regeneration is byte-identical. The supplement map now identifies prospective protocol records without treating them as completed manuscript results. The first full regression run is still in progress at this record; the queued stable-source gate is authoritative for continuation readiness.

## Validation-gate correction and continuation retry

The initial broad regression run completed with 1,128 passes, one script-entry-point failure, and 99.60% measured coverage. Source refinements were made during that first run, so its coverage is not the final stable-source gate. The failure concerned the `run_*.py` CLI-wrapper naming contract. Standalone research drivers now use `evaluate_revision_round6_resolution.py` and `evaluate_revision_round6_scaling.py`; the architecture test itself is unchanged. All 26 focused entry-point, numerical and normalized-acquisition checks pass after the rename, and lint passes.

The redundant validation subprocess was stopped before further physical stages; the healthy nominal runner and its two ASTRA workers were not stopped. The aborted validation log was preserved. The continuation was restarted at commit `c7edd12` with launch PID `1795323`, recorded in `results/revision_round6/chain_launch_retry_1.json`. It is performing the final full regression/100% coverage gate on stable code. The original nominal process still reports its launch-time script name; its already-running workers are unaffected by the research-entry-point rename.

Latest observed nominal count at this handoff: 12/387. No refinement or scaling campaign has started. Final validation results and physical-study completion remain pending; no push has occurred.

## Results and manuscript integration — 2026-11-10

Execution after the restart: full test gate (1,157 passed, 100 % coverage; commit `2ba4806`), 1,502 refinement attempts at 22 workers over 40.3 h (`be8084f`), and 20 scaling campaigns over about 66 h at one campaign at a time (`596e676`). Task 00378 integrated the evidence:

| Study | Result | Direction |
|---|---|---|
| Re-tracking, feasibility | 4/387 classifications changed, all infeasible → feasible (constraint-aware, bunch length within 6.5 µm of the limit); constrained advantage 0.248/0.280 → 0.303/0.335, all ten groups | Supports the feasible-sampling comparison |
| Re-tracking, objectives | Emittance fine vs production median −21 %/−29 %; fine vs medium median 5.5 %/7.4 %; 1 % tolerance met by 3–7 % of settings | Adverse: not converged at the finest tested level |
| Residual scaling | Normalized − raw −0.118 [−0.136, −0.099] all attempts; −0.131 post-initialization; 0/10 groups positive | Adverse to the tested convention |

Manuscript: new subsections "Prospective validation studies", "Re-tracked sample of primary evaluations" and "Constraint-residual scaling" with three generated tables; abstract (still number-free), contribution list, discussion, limitations, conclusions and the smoothing appendix updated accordingly. Remaining: separately attributed reviewer responses, final validation and packaging (C6-09/A6-09).

## Closure — 2026-11-10

### Responses and change inventory

- [Reviewer 1 response](../reviews/reviewer1_round6_response.md): R6-01 and R6-02 adopted and completed (with their adverse findings), R6-03 retained, R6-04 not adopted, R6-05 closed.
- [Reviewer 2 response](../reviews/reviewer2_round6_response.md): comments 1–4 adopted; comment 5 answered with the completed studies.
- [Reviewer 3 response](../reviews/reviewer3_round6_response.md): comments 1, 3, 4 and 5 adopted; comment 2 in part (convention clarified, bunching statement not adopted); comment 6 answered with the completed re-tracking.
- [Manuscript source diff](round6_manuscript.diff): `main.tex`, `main_twocolumn.tex` and the bibliography against `9fd076a`. The bibliography is unchanged.
- [Analysis code diff](round6_analysis_code.diff): every change under `src/`, `scripts/`, `tests/` and `tools/` against `9fd076a`.
- [Changed-file inventory](round6_changed_files.json): every file changed relative to the baseline, with its current SHA-256 hash. It excludes the packaging files and the closing task summary.
- Supplement S1: the frozen protocol and execution records are in S1.15 and the study results in S1.16.

### Dispositions

| Item | Disposition | Sources |
|---|---|---|
| C6-01 | Scalarized cost defined in prose as a minimized weighted sum of scaled objectives | R2 1; R3 1 |
| C6-02 | Appendix kernel hypothesis removed | R2 2; R3 3 |
| C6-03 | "specified" restored; closing scope sentence; number-free abstract | R2 3; R3 4 |
| C6-04 | Undercoverage paragraph rewrapped | R2 4; R3 5 |
| C6-05 | Additional validation adopted; comparator declined | R1; R2 5 |
| C6-06 | Re-tracking completed: classifications and comparison stable, emittances unconverged | R1 R6-01; R2 5; R3 6 |
| C6-07 | Matched campaigns completed: tested normalized convention lowered feasible sampling | R1 R6-02 |
| C6-08 | Not adopted; limitation retained | R1 R6-04 |
| C6-09 | Responses, packaging and validation | R1 R6-03/R6-05; R2 V6; R3-7 |
| C6-10 | RF phase convention clarified; bunching statement declined | R3 2 |

### Residual scientific uncertainty

- **Objective values.** The emittances are not converged at the finest tested level: fine and medium differ by a median 5.5–7.4 %. The protocol does not allow refinement chosen after seeing the outcome.
- **Residual normalization.** Its effect alone is unknown, because the tested convention also changed the smoothing widths and no width-preserving arm was run.
- **Comparator.** No constraint-aware scalarized comparator was run.
- **Front quality.** The indicators remain exploratory and untested at a converged resolution.
- **Reviewers.** Reviewer 1's recommendation is not represented as changed. Closing this queue is not journal acceptance.

### Validation

- Full non-integration suite: 1,164 passed, 2 deselected, 100.00 % package line coverage (24 min).
- `ruff check src scripts tests`, `scripts/verify_docs_sync.py`, `scripts/build_supplement_manifest.py` and the documentation-link and supplement tests passed.
- `main.tex`: 61 pages. `main_twocolumn.tex`: 34 pages (31 before this round's additions). Both have no undefined references or overfull boxes, and the new tables were inspected in the two-column PDF.
- `scripts/build_prab_submission.py --compile` builds the flat upload folder; its manuscript compiles to 61 pages with no warnings of those kinds, and its bibliography check passes. The folder is local and was not uploaded.
- Not run: integration tests (ASTRA end-to-end, deselected by design) and any remote GitHub Actions query.

No push or upload was made. Funding and acknowledgments and `\finaltrue` remain author decisions.
