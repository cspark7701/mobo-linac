# Round6 revision overview — execution in progress

Reviewed manuscript baseline: `9fd076a`; execution baseline: `79cecb9`.

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
