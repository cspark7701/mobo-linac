# Task Completion Summary: Task 00298

## Summary
Consolidated round3 task C3-06: restrict the RF-amplitude estimate to what it estimates (Reviewer 1 M4), and compare it with the TDR energy margins of the two candidates (Reviewer 2 minor 2).

## Key Changes
- **Sec. V I, RF-amplitude paragraph.**
  - It names the reference setting: the re-evaluated MOGA-derived nominal, with gains of 4.1, 93.3 and 102.8 MeV.
  - It states the approximation (each gain scales linearly with its amplitude at fixed phase) and the two correlation assumptions.
  - 0.28 and 0.40 MeV RMS are now described as a conditional, linearized estimate of the mean-energy effect only, and "not a bound". "Bounds their effect" is removed.
  - The headroom comparison is restated as "about an eighth of the 3.11 MeV headroom".
  - The inference that the representatives keep their production-profile classification is removed. The paragraph now states what the estimate does not cover: the bunch-length and upper-energy margins, and changes in phase slippage, focusing, chirp and transverse diagnostics.
  - The sentence scaling σ_E by the same fraction (about 0.8 keV) is removed.
- **Sec. V I, TDR-candidate jitter paragraph.** Adds that the TDR lower-energy margins of A and B (0.31 and 0.14 MeV) are comparable to the 0.28–0.40 MeV estimate. This is stated as an indication of further TDR failures.
- **Discussion (JKPS comparison).** It now describes the RF-gradient errors as "estimated by linearization for the mean energy alone".
- **Task list:** C3-06 is ticked.

## Validation Results
- `tests/test_paper_outputs.py` passed (53).
- `latexmk` builds `main.pdf` (54 pages) without errors, undefined references or overfull boxes.

## Status
Completed and committed locally. No push performed.
