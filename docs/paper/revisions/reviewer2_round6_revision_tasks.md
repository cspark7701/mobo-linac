# Revision tasks for Reviewer 2 — round6

**Source report:** [reviewer2_round6_report.md](../reviews/reviewer2_round6_report.md)
**Previous round:** [reviewer2_round5_revision_tasks.md](reviewer2_round5_revision_tasks.md), [consolidated_round5_revision_tasks.md](consolidated_round5_revision_tasks.md)
**Reviewed manuscript revision:** `9fd076a`
**Recommendation:** Accept. V1 should be corrected before acceptance and can be checked by the editor. No new simulations and no further review round are needed.

Each task lists the review item it answers, the work involved, and what counts as done.
- **Priority:** **P1** requested before acceptance, **P2** editorial, **P3** optional.
- **Ground rules:**
  - Keep the rewritten prose; change only the sentences named.
  - Archived production results and evidence files are not rewritten.
  - Acknowledgments and data availability remain author decisions.

---

## P1 — Requested before acceptance

### V1. Define the weighted-sum cost (comment 1)
- [ ] Sec. III B: restore the definition of the baseline's target, e.g. "fits a single GP to the scalarized cost $g(\mathbf{x}) = \sum_m w_m f_m(\mathbf{x})/s_m$, which it minimizes, where $s_m$ are the reporting scales … and $w_m = 1/3$".
- [ ] Check that "weighted cost" (Sec. V C) and "scalarized cost" (Sec. V G) refer to this definition.
- **Done when:** the baseline's optimization target is defined by one equation or an exact sentence, and every later use of "cost" refers to it.

---

## P2 — Editorial

### V2. Undercoverage hypotheses (comment 2)
- [ ] Either restore kernel misspecification as a hypothesis in Sec. V G, e.g. "A stationary kernel with one length scale per control may not represent both the smooth interior response and the sharp changes near energy loss or beam-size growth", or remove "kernel misspecification" from Appendix D.
- **Done when:** every hypothesis named in Appendix D is introduced in Sec. V G, and none is stated categorically.

### V3. Abstract scope signals (comment 3)
- [ ] Restore "specified" in "We compare specified Bayesian optimization pipelines…", or confirm its removal deliberately.
- [ ] Restore the closing scope sentence, e.g. "These findings hold within the nominal numerical model and acceptance profile and are not a physically resolved injector optimization", or confirm the new wording deliberately.
- [ ] Keep the abstract free of numbers and keep Reviewer 1's "persists in the tested diagnostic-shift scenarios".
- **Done when:** the abstract states the scope as precisely as the round-5 version, or the response explains the deliberate change.

---

## P3 — Optional

### V4. Source line breaks in Sec. V G (comment 4)
- [ ] Re-wrap the paragraph "Several mechanisms could explain the undercoverage" to the surrounding line length. Whitespace only.

### V5. Pre-empting the convergence question (comment 5)
- [ ] Optional, and only with the author's approval because it needs new ASTRA runs: re-track a sample at the medium level. Take a few matched groups per method, including infeasible and baseline observations near the production limits. Report whether the feasible classifications, and the paired feasible-fraction differences on that sample, are preserved.
- [ ] If not done, no manuscript change is needed. The limitation is already stated in Secs. II A, V B, VI C and the Conclusions.
- This is advice for the journal submission, not a condition of acceptance.

---

## Closing

### V6. Response and validation
- [ ] Write `docs/paper/reviews/reviewer2_round6_response.md`, mapping comments 1–5 to the changes or to reasoned non-adoption.
- [ ] Build the two-column PDF without errors, undefined references or overfull boxes. Run `pytest tests/test_manuscript_hygiene.py tests/test_paper_outputs.py tests/test_docs_links.py`.
- [ ] Regenerate the upload folder with `python scripts/build_prab_submission.py --compile`.
- **Done when:** every comment has a traceable disposition and the validation status is reported. Closing the tasks does not establish journal acceptance.

## Suggested order
1. V1 (the only item requested before acceptance).
2. V2–V3 (one editorial pass).
3. V4, and V5 if the author approves new runs.
4. V6.
