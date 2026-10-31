# Round6 revision overview — execution in progress

Reviewed manuscript baseline: `9fd076a`; execution baseline: `79cecb9`.

## Author disposition (C6-05)

On 31 October 2026 the author explicitly adopted representative numerical validation (C6-06/A6-01–03) and contemporaneous raw/normalized acquisition campaigns (C6-07/A6-04–06), and omitted the optional constraint-aware scalarized comparator (C6-08/A6-07). This supersedes the earlier nominal-model-only execution scope. Historical results and exploratory front-quality status remain unchanged. Neither reviewer recommendation is represented as consensus or journal acceptance.

The resource ceiling is **two CPU evaluation workers total**, across both workstreams. Execute the workstreams serially to enforce that ceiling; use CUDA for GP/acquisition work when available, retain double precision, and limit numerical-library CPU threads. Protocols, exact sample sizes, analysis choices and budgets must be frozen before new outcomes. No new ASTRA runs have started at this disposition step.

The author explicitly authorized a git push when the revision tasks are finished. This overrides the older no-push statements in the planning documents; it does not authorize remote GitHub Actions queries or public artifact deposition.

## Completed editorial work

- C6-01: defined minimization of the weighted sum of individually scaled physical objectives in prose, preserving equal weights and qLogNEI.
- C6-02: removed the appendix kernel hypothesis and retained conditional adaptive-test-point wording.
- C6-03: restored “specified” pipelines and a statement about the present findings, with a number-free abstract of 268 whitespace-delimited words.
- C6-04: rewrapped the undercoverage paragraph; whitespace-normalized tokens are identical.

Focused manuscript/link checks: **4 passed**. The two-column manuscript builds successfully to **31 pages**. Further code, simulation, scientific integration and final packaging checks remain pending.

## Remaining work

Freeze A6-01, implement/test and execute both adopted research branches, analyze all outcomes, integrate supported findings, and complete separately attributed reviewer responses and C6-09 validation. Numerical validation does not establish scaling efficacy, and scaling campaigns do not establish tracking convergence. Optional constrained scalarization is not adopted; retain that limitation.
