# Task Completion Summary: Task 200

## Summary
Updated computing-time estimates for production stages 05–07 on 2026-10-22, assuming the current RTX A5000, CUDA optimization, eight ASTRA workers, default scientific budgets, and sequential execution without competing heavy workloads.

## Key Findings
- Stage 05 performs seven 176-evaluation optimization campaigns (five scalarized cases and two MOBO modes), six nominal verification reruns, and 300 jitter simulations. Estimated wall time: 15–20 hours.
- Stage 06 performs six nominal reruns and 300 jitter simulations with no acquisition optimization. Estimated wall time: 2–3 hours.
- Stage 07 generates figures/tables, runs the manuscript consistency check, stages artifacts, and inventories campaigns without new ASTRA simulations. Planning allowance: 5–20 minutes; no measured full-stage reporting runtime is available.
- Combined sequential planning allowance is approximately 17–24 hours, or about one day. Set `WORKERS=8` explicitly for stages 05/06; their shared default is four workers, which increases the simulation portion of elapsed time.

## Validation Results
Read stage budgets and the latest scheduler completion records: ten constrained campaigns averaged 3.351 hours, ten unconstrained campaigns averaged 2.392 hours, and nine scalarized campaigns averaged 1.226 hours at the 160-evaluation primary budget. Scaling the seven stage-05 campaigns to 176 evaluations gives approximately 13.06 hours of optimization. This is an approximation because later proposals and different scalarized weights may change costs. Pilot robustness attempts averaged 200.02 seconds each, yielding a 2.13-hour ideal eight-worker lower estimate for 306 simulation runs, before scheduling, stragglers, and report overhead. No scripts, settings, running processes, or archived outputs were modified. This documentation-only task requires no application tests; checked staged whitespace before the required local commit.

## Status
Completed. Estimates preserve existing physical validation and remain provisional until these stages run.
