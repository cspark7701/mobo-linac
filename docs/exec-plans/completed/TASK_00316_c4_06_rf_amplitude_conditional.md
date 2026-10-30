# Task Completion Summary: Task 00316

## Summary
C4-06 of the round4 revision (Reviewer 1 C2). The RF-amplitude implication for the two TDR candidates is now a conditional, scale-based risk statement, not a demonstrated failure.

## Key Changes
- **Removed.** The claim that the comparison "indicates that amplitude jitter would cause further TDR failures".
- **Added (Sec. V D, robustness results):**
  - the 0.28–0.40 MeV RMS shift is estimated from the energy gains of the MOGA-derived nominal reference, not from a tracked amplitude response of candidates A and B;
  - because it is comparable to their 0.31 and 0.14 MeV lower-energy margins, the omitted amplitude errors could reduce their TDR acceptance further and merit a candidate-specific study;
  - no failure count or probability is inferred.
- **Kept.** The comparison itself (Reviewer 2, round3 minor 2), the lattice-only counts 36/50 and 44/50 and their exact intervals, and the statement that the marginal settings do not provide jitter-tolerant TDR operation under the lattice-only model.
- Task C4-06 is marked done in the consolidated round4 task list.

## Validation Results
- Every "amplitude" occurrence in `main.tex` was checked; no other passage attributes failures to amplitude jitter.

## Status
Completed and committed locally. No push performed. No simulation was run.
