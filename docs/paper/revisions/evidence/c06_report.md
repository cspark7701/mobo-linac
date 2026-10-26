# C06 — Offline constraint scaling sensitivity

## Status
Completed for the author's explicit existing-simulation scope. A corrected acquisition arm is not run; no physical-performance claim is made for it. Original code, models and production observations are preserved.

## Reproduction and protocol
Run `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python scripts/analyze_revision_scaling.py`. Use the prescribed primary constraint-aware run's iterations 1, 9 and 18, restore recorded float64 objective/diagnostic GPs on CPU without fitting, and evaluate qLogNEHVI at 32 fixed six-dimensional Sobol candidates with q=1 and 128 common normal posterior samples. Candidate/sampler seed identities and model hashes are retained in c06_metadata.json. The full historical baseline is held fixed with pruning disabled so the experiment isolates residual scaling, not changed baseline membership. It is not a replay of production q=8 optimization and does not estimate its next candidate.

## Physical scales
Original raw eta=0.001 means 1 mm for sizes/length, 1 mrad for divergences, 0.001 eV for energy and 0.001 transmission fraction. These cannot represent equal relative softness. The same eta after changing diagnostic representation to mm/mrad/MeV therefore changes physical smoothing.

The dimensionless sensitivity convention divides size/divergence/length residuals by their upper bounds, both energy residuals by the 5 MeV half-band, and transmission residual by the permitted loss fraction 0.1. Dividing residual and scale in any equivalent units preserves their ratio. Eta=0.01 then corresponds to 0.01 mm, 0.01 mrad, 50 keV and 0.001 transmission fraction. These profile-relative scales are explicit analysis choices, not validated machine tolerances or optimized temperatures. Eta=0.001/0.01/0.1 is a sensitivity grid, not a hyperparameter-selection claim. Physical scales are exported in c06_smoothing_scales.csv.

## Measured sensitivity
Equivalent raw-unit representations have ranking correlations 0.792522, 0.851540 and 0.879765 with the native-unit original, retaining 3, 4 and 3 of its top five candidates. The dimensionless eta=0.01 convention has correlations 0.804985, 0.887097 and 0.895528 with original ranks; its native/display-unit evaluations agree within 1.49214e-13 in log acquisition. The highest-ranked probe candidate is unchanged in all variants. The complete 576 acquisition values and 18 comparison rows are exported. This is evidence of ranking sensitivity and numerical unit invariance, not evidence that an optimized proposal or physical outcome improves.

## Scope disposition and future comparison
The author selected retaining existing simulations and documenting non-adoption of new controls. A corrected constraint-aware arm would need matched initial designs, seeds, total budget, precision and physical checks before any efficacy claim. The historical results remain those of raw-residual weighting; offline normalization must not be retroactively labelled as the performed method. No new MOGA or BO/control simulations were launched. The response explicitly distinguishes the quantified sensitivity from the reviewer's unperformed corrected-arm request.
