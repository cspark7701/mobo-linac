# Revision tasks for Reviewer 3 — round6

**Source report:** [reviewer3_round6_report.md](../reviews/reviewer3_round6_report.md)  
**Reviewed manuscript revision:** `9fd076a` / `79cecb9`  
**Recommendation:** Accept with minor editorial revisions.

Tasks are prioritized as follows:
- **P1:** Required before final acceptance (can be verified by editor).
- **P2:** Editorial and textual consistency.
- **P3:** Optional advice for submission.
- **Closing:** Verification and response documentation.

---

## P1 — Required Before Acceptance

### R3-1. Define the weighted-sum cost precisely (Comment 1)
- [ ] In [Sec. III B](file:///home/cspark/Work/projects/mobo-linac/docs/paper/main.tex#L611-L621), restore an exact definition of the baseline's scalarized target, stating that it is a weighted sum of scaled physical objectives and that it is minimized:  
  $$g(\mathbf{x}) = \sum_{m=1}^3 \frac{w_m f_m(\mathbf{x})}{s_m}$$  
  or an unambiguous one-line prose equivalent.
- [ ] Confirm that references to *"weighted cost"* ([Sec. V C](file:///home/cspark/Work/projects/mobo-linac/docs/paper/main.tex#L955-L1034)) and *"scalarized cost"* ([Sec. V G](file:///home/cspark/Work/projects/mobo-linac/docs/paper/main.tex#L1078-L1120)) point back consistently to this definition.
- **Done when:** The scalarized optimization target is defined unambiguously and downstream terminology is fully aligned.

### R3-2. Clarify RF phase convention and velocity bunching (Comment 2)
- [ ] In [Sec. II B](file:///home/cspark/Work/projects/mobo-linac/docs/paper/main.tex#L356-L400) (and/or Table I note), add 1–2 sentences clarifying:
  - The RF phase reference convention (i.e. whether $0^\circ$ denotes maximum acceleration crest or zero-crossing).
  - That operating ACC1/ACC2 off-crest ($\phi_{\text{acc1/2}} \approx -39.5^\circ$) provides velocity bunching and longitudinal phase compression for the $\sim 5\text{ MeV}$ beam exiting the gun.
- **Done when:** The physics mechanism of off-crest ACC1/ACC2 operation and phase conventions are clear to accelerator physicists.

---

## P2 — Editorial & Textual Consistency

### R3-3. Align undercoverage hypotheses (Comment 3)
- [ ] Resolve the inconsistency between [Sec. V G](file:///home/cspark/Work/projects/mobo-linac/docs/paper/main.tex#L1105-L1113) and [Appendix D](file:///home/cspark/Work/projects/mobo-linac/docs/paper/main.tex#L1697-L1698):
  - Option A (Recommended): Remove *"Kernel misspecification and"* from the Appendix D sentence so that only adaptive test points remain as a conditional hypothesis.
  - Option B: Briefly re-introduce kernel misspecification as an untested hypothesis in Sec. V G without categorical phrasing.
- **Done when:** Hypotheses cited in Appendix D are either introduced in the main text or pruned to match the main text.

### R3-4. Re-anchor scope qualifiers in Abstract (Comment 4)
- [ ] In the [Abstract](file:///home/cspark/Work/projects/mobo-linac/docs/paper/main.tex#L63-L88), re-insert *"specified"* into sentence 2:  
  *"We compare specified Bayesian optimization pipelines on a fixed-lattice S-band injector-linac model derived from the Korea Light Source design."*
- [ ] Adjust the final sentence of the abstract back to the definitive boundary phrasing:  
  *"These findings apply to the nominal numerical model and acceptance profile and are not a physically resolved injector optimization."*
- **Done when:** The abstract accurately reflects the agreed nominal-model scope without sounding like an unfulfilled promissory note.

---

## P3 — Optional Advice

### R3-5. Source text formatting in Sec. V G (Comment 5)
- [ ] Re-wrap the lines around line 1111 in [Sec. V G](file:///home/cspark/Work/projects/mobo-linac/docs/paper/main.tex#L1105-L1113) to remove awkward breaks (*"the reported / diagnostics remain"*). Whitespace only.

### R3-6. Optional medium-resolution re-tracking sample (Comment 6)
- [ ] *Optional (author's discretion):* Re-track a modest sample of 5–10 representative Pareto candidates at 50k macroparticles to provide pre-emptive evidence against future external reviewer questions.
- [ ] *If not adopted:* No text change needed; the existing disclosures in Sec. II A and Sec. VI C are sufficient.

---

## Closing Checks

### R3-7. Response and validation
- [ ] Write `docs/paper/reviews/reviewer3_round6_response.md` (or consolidate with R1/R2 responses).
- [ ] Compile [`docs/paper/main.pdf`](file:///home/cspark/Work/projects/mobo-linac/docs/paper/main.pdf) to verify zero errors, clean formatting, and no overfull boxes.
- [ ] Run hygiene and link tests: `pytest tests/test_manuscript_hygiene.py tests/test_paper_outputs.py tests/test_docs_links.py`.
- **Done when:** All items have documented dispositions and the PDF compiles cleanly.
