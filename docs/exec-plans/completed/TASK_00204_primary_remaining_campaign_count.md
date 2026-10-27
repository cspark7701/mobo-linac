# Task Completion Summary: Task 199

## Summary
Checked stage-04 progress on 2026-10-20 at 10:51 KST: seven of 30 campaigns completed, leaving 23 unfinished campaigns.

## Key Findings
- Completed all algorithms for seeds 42 and 43, plus constrained MOBO for seed 44.
- Unconstrained MOBO seed 44 is the current incomplete campaign, with 136 / 160 recorded evaluations.
- Remaining count includes that campaign and 22 campaigns not yet started.

## Validation Results
Read scheduler completion records and append-only evaluation journals. No simulations, settings, or processes were modified. Checked staged whitespace before the required local documentation commit.

## Campaign Inventory at 10:52 KST
Each cell represents one campaign with a budget of 160 evaluations (30 campaigns total).

| Seed | Constrained qLogNEHVI | Unconstrained qLogNEHVI | Scalarized BO |
| --- | --- | --- | --- |
| 42 | Complete | Complete | Complete |
| 43 | Complete | Complete | Complete |
| 44 | Complete | In progress: 136/160 | Queued |
| 45 | Queued | Queued | Queued |
| 46 | Queued | Queued | Queued |
| 47 | Queued | Queued | Queued |
| 48 | Queued | Queued | Queued |
| 49 | Queued | Queued | Queued |
| 50 | Queued | Queued | Queued |
| 51 | Queued | Queued | Queued |

## Per-Campaign Wall-Time Estimates at 10:54 KST
Measured times below are completed campaign wall times. Estimates are the mean completed GPU campaign duration for each algorithm, rounded to the nearest minute: constrained 3 h 24 min (three completed seeds), unconstrained 2 h 14 min (two seeds), scalarized 1 h 13 min (two seeds). All campaigns retain a 160-evaluation budget; execution uses one GPU campaign and eight ASTRA workers. These are total per-campaign durations, not queue waiting times.

| Seed | Constrained qLogNEHVI | Unconstrained qLogNEHVI | Scalarized BO |
| --- | --- | --- | --- |
| 42 | Actual: 3 h 34 min | Actual: 2 h 16 min | Actual: 1 h 13 min |
| 43 | Actual: 3 h 04 min | Actual: 2 h 12 min | Actual: 1 h 13 min |
| 44 | Actual: 3 h 35 min | Running: 1 h 59 min elapsed; approximately 2 h 14 min total estimated | Estimated: 1 h 13 min |
| 45 | Estimated: 3 h 24 min | Estimated: 2 h 14 min | Estimated: 1 h 13 min |
| 46 | Estimated: 3 h 24 min | Estimated: 2 h 14 min | Estimated: 1 h 13 min |
| 47 | Estimated: 3 h 24 min | Estimated: 2 h 14 min | Estimated: 1 h 13 min |
| 48 | Estimated: 3 h 24 min | Estimated: 2 h 14 min | Estimated: 1 h 13 min |
| 49 | Estimated: 3 h 24 min | Estimated: 2 h 14 min | Estimated: 1 h 13 min |
| 50 | Estimated: 3 h 24 min | Estimated: 2 h 14 min | Estimated: 1 h 13 min |
| 51 | Estimated: 3 h 24 min | Estimated: 2 h 14 min | Estimated: 1 h 13 min |

The active journal had 139 / 160 observations during this snapshot, including an unfinished batch. Mean-duration extrapolation yields approximately 49.5 hours remaining, with a central finish estimate of October 22 at 12:25 KST before final reporting overhead. Seed-dependent optimizer behavior and competing workloads can change this estimate; it is not a promised deadline. No application code or running process was changed.

## Status
Completed. The production experiment continues.
