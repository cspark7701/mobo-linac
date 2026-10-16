# Task Completion Summary: Task 194

## Summary
Explained why the live primary benchmark is slow and assessed whether GPU execution could help, without changing the running experiment.

## Key Findings
- The primary launch record explicitly selects CPU, two concurrent controllers, one PyTorch CPU thread per controller, batch size eight, ten acquisition restarts, 1,024 raw initial samples, and up to 200 optimizer iterations.
- Completed seed-42 MOBO campaigns took 61–63 hours while their summed individual ASTRA runtimes were only 6–7 hours. Four evaluation workers per campaign overlap simulations, so most elapsed time lies outside the ASTRA evaluations. Exact attribution between acquisition construction, proposal optimization, GP fitting, and other overhead requires profiling.
- The acquisition engine jointly proposes eight candidates in six dimensions (48 candidate coordinates) using qLogNEHVI, double precision, and an observed baseline that grows with evaluations. Late observed batches took hours, unlike the smaller pilot.
- The host has an NVIDIA RTX A5000 with approximately 24 GB VRAM. At inspection, GPU memory use was 263 MiB and utilization 6%; the recorded primary job selects CPU.
- Official BoTorch documentation identifies GPU acceleration for qLogNEHVI and related MOBO acquisitions. GPU execution is a credible speedup opportunity for the optimization bottleneck, but no measured speedup or GPU ETA is established for this hardware and workload. ASTRA itself remains a separate CPU executable in the current workflow.
- The project's CUDA acquisition policy defaults to one restart per optimizer batch; two simultaneous GPU campaigns share VRAM. These details can affect speed and memory, so a saved late-stage workload should be benchmarked in isolation before choosing a migration plan.

## Validation Results
Read recorded production parameters, acquisition construction and optimization code, scheduler thread setup, NVIDIA device information, and the completed campaign timing evidence from Task 193. Consulted official BoTorch documentation: https://botorch.org/docs/multi_objective and https://botorch.org/docs/v0.17.2/tutorials/multi_objective_bo . No timing benchmark, GPU proposal, ASTRA execution, or live configuration change was performed.

## Status
Completed. GPU acceleration remains an unmeasured recommendation for a separate benchmark and planned transition.
