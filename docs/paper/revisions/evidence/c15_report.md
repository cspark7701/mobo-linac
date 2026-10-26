# C15 — Figure clarity and independent survey histories

## Status
Completed. All figures remain based on measured records; no smooth Pareto curves, new simulations or invented constraints were introduced.

## Reproduction
Run `python scripts/prepare_revision_figures.py` after the original paper asset-copy steps. The script verifies all 37 input campaign CSV completion hashes. It emits vector primary/survey feasibility plots and revised primary/survey constraint panels, plus matching constraint PNG previews. c15_metadata.json identifies input hashes, bootstrap conventions and each independent survey curve's 176-observation length. Full original all-case comparison books remain in the results tree; they are not overwritten.

## Presentation changes
The five scalarized weighting campaigns are five independent curves, not one 880-evaluation trajectory. Their lines share the scalarized method color with distinct line styles and weighting labels. MOBO colors/markers match the primary Pareto/constraint views. The primary feasibility figure uses medians and pointwise percentile bootstrap bands over ten runs, with 1,000 common resample index sets; the caption identifies these as confidence intervals rather than interquartile spreads.

Main constraint views preserve full-range size/divergence/energy-length panels and add transverse accepted-region insets with identical physical units. Open markers remain jointly infeasible and filled markers jointly feasible. Shading applies only to displayed inequalities. Constant transmission is explicitly annotated with observation count, measured value and production threshold instead of consuming an empty fourth panel. No energy-spread acceptance bound is invented. Each original campaign's complete diagnostics remain available in companion artifacts.

The unequal-budget survey's detailed tables and figures move to an appendix, with a brief main-text result and clear cross-reference. C03 attainment views and C08 complete representative controls remain included. The existing two-dimensional Pareto scatter views retain grid lines and shared coordinate limits across projections; no connecting front lines are introduced.
