# Task Completion Summary: Task 197

## Summary
Inspected the live GPU primary experiment on 2026-10-19 at approximately 16:49–16:51 KST. The first constrained seed-42 campaign was progressing normally with confirmed CUDA proposals and substantially shorter observed batch times than the previous late-stage CPU execution.

## Key Findings
- Launch: approximately 15:47:50 KST; elapsed approximately 61 minutes at the initial snapshot. One campaign runs at a time with eight ASTRA workers, batch size eight, and `device=cuda:0`.
- Recorded progress: 64 / 160 evaluations in constrained seed 42, all 64 simulation-valid, 20 physically feasible; iteration 7 / 18 was in proposal generation. No full campaign had completed yet; 64 / 4,800 total planned evaluations were recorded.
- Six completed post-initialization proposals all recorded `primary` on `cuda:0`, with ten restarts, 1,024 raw samples, maxiter 200, batch limit one, and no recorded retry, CPU, or Sobol fallback.
- Initial 16 evaluations took 7.10 minutes. Subsequent eight-candidate batches took 7.95, 7.98, 8.08, 8.19, 8.72, and 8.86 minutes including proposal work and ASTRA execution. This supports the expected improvement, but first-campaign early batches do not establish a full-experiment speedup or reliable completion estimate.
- GPU snapshot: RTX A5000, approximately 1.39 GB memory used, 37% utilization. Utilization can vary because GP/proposal work alternates with CPU ASTRA evaluations. No process or output was modified.
- Seven saved GP artifacts contained 70 `lbfgs` channel fit outcomes, all with empty error lists; saved floating tensors were float64. The fit status does not certify a specific optimizer termination code.
- The log had no traceback, CUDA out-of-memory error, stage-failure marker, or unavailable-device fallback message at inspection. It did contain 56 negative-variance clipping warnings and 22 small-noise floor warnings. These were numerical stability adjustments, not observed execution failures; their scientific impact was not independently assessed in this live status review.
- Hypervolume remained zero under the fixed reporting reference, consistent with the previously documented reference limitation; this is not evidence of absent feasible evaluations.
- In single-campaign mode the CSV manifest stays at its previously written pending labels until a campaign completes; the per-run state, journals, checkpoints, and log are the evidence of activity. `CAMPAIGN_THREADS=1` is only applied by the isolated parallel-controller path; the serial scheduler records `campaign_threads: null`. The running job was left unchanged.

## Validation Results
Read live scheduler and manifest files, evaluation journals, metrics/proposal histories, the current stage log, saved GP artifacts, process activity, GPU utilization, and serial scheduler code. Used read-only CPU loading of saved artifacts. Did not initialize a competing GPU workload, rerun simulations, change settings, or query remote workflows.

## Commit Workflow
At the user's request, recorded the standing rule in `AGENTS.md`: automatically commit each new task completion document together with the task's other modified files, using the existing imperative subject, explanatory paragraphs, and `Files:` format. This documentation-only update requires no application tests; checked staged whitespace before committing.

## Status
Completed. The live experiment continues; no intervention is indicated by this operational snapshot. Reassess end-to-end throughput after the first full campaign finishes.
