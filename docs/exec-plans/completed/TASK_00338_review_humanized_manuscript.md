# Task Completion Summary: Task 00338

## Summary
Read the complete humanized manuscript again and reviewed its clarity, internal consistency and scientific interpretation. This is a review only: no manuscript wording, backup, figures, data or code was changed. The humanizer skill was used as a review checklist, without another rewriting pass.

## Review Findings

### 1. Medium: state the scalar GP target's sign explicitly
- Location: `docs/paper/main.tex:588` (weighted-sum baseline).
- The text says that the GP is fitted to the physical scalar cost `g(x) = sum_m w_m f_m(x)/s_m`, whose component objectives are minimized. It then names qLogNEI without stating the scalar model's maximization target.
- The global negation convention is described earlier, but this local definition can be read as fitting the positive cost directly. The archived production implementation at commit `8ad6c2c`, `src/mobo_linac/campaigns/strategies.py:72`, combines the negated training objectives and therefore fits `-g`. It passes that model to qLogNEI at line 82.
- Recommendation: explicitly connect the physical cost `g` to the modelled target `-g`. This is a methods-description ambiguity, not evidence that the executed baseline optimized the wrong sign.
- Present before the humanization pass.

### 2. Medium: restrict the local-convergence inference to the settings with demonstrated improvements
- Location: `docs/paper/main.tex:1144` through line 1149.
- The paragraph reports dominating perturbations for four representatives (14, 8, 2 and 1 trials), with none observed for the other two. It then says that "The selected settings are therefore not locally converged," which can be read as applying to all six.
- Recommendation: identify the four settings for which feasible dominating neighbours were observed. The absence of such a neighbour in 50 draws establishes neither convergence nor nonconvergence for the other two. The sampled perturbations also do not constitute a general local-optimality test.
- Present before the humanization pass; the observed counts were preserved.

### 3. Medium: keep the kernel explanation conditional
- Location: `docs/paper/main.tex:1061` through line 1068, especially line 1064.
- The paragraph introduces possible explanations for undercoverage and says that the check does not isolate them, but then states that a single Matérn-5/2 length scale per control "cannot represent both" response regimes. No kernel comparison or causal isolation is reported there; the following paragraph again describes kernel misspecification as a hypothesis.
- Recommendation: distinguish a proposed limitation of the stationary kernel from an established cause of the observed undercoverage. This does not call for changing the measured coverage values or the inferred-noise result.
- The categorical wording predates humanization and remains in the revised paragraph.

### 4. Low: correct an editing regression in capitalization
- Location: `docs/paper/main.tex:848`.
- The phrase "observations, and The full-reference calculation" incorrectly capitalizes "The" mid-sentence.
- Recommendation: lowercase it or use a sentence boundary. This error was introduced in the humanization pass and should be corrected in a subsequent authorized edit.

### 5. Low: separate the sensitivity paragraph's reasoning stages
- Location: `docs/paper/main.tex:882` through line 913.
- One uninterrupted paragraph combines the 27-scenario design, excluded changes, median ranges, paired effects, bunch-length sensitivity, three additional checks and the limits of the inference. Those are distinct steps, so the main finding is difficult to retain while reading the numeric details.
- Recommendation: separate scenario definition, results and interpretation into paragraphs while retaining all values and qualifications. This is a readability recommendation, not an objection to reporting the sensitivity limits.

## Validation Results
- Read `main.tex` from its front matter through the bibliography, including the abstract, main sections, captions and appendix prose. Checked that the referenced predictive-validation and selected-settings appendix labels are supplied by their included files.
- Inspected the archived production scalarization code with local `git show`; no remote service was queried.
- Rechecked numeric tokens, citations, inline mathematics, equation/table bodies and labels/references against `main.tex.before-humanizing-20261031.bak`; their content and order remain preserved after whitespace normalization.
- Confirmed that the reviewed manuscript exactly matches the committed humanized source. Its SHA-256 is `d59ae70d499e7da075b94f1aabb7907fd938aab90504a9d39553e5de7b4df70a`.
- `git diff --check` passed. Task 00338 is the next unique five-digit completion filename.

## Scope and Limitations
The findings distinguish scientific-description ambiguities from editorial issues and identify which existed before humanization. This was not an independent recalculation of results or a verification of external literature. No manuscript edits, builds, tests, simulations, remote GitHub Actions queries, pushes or uploads were performed for this review. Only this review record was added.

## Status
Review completed and recorded locally. Findings remain recommendations; none was applied to the manuscript.
