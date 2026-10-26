# C11 — Chronological surrogate validation

## Status
Completed with recorded undercoverage and a constant-transmission discrimination limitation. No refitting, new simulation or production change was made.

## Protocol and reproduction
Run `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python scripts/analyze_revision_predictions.py` in the production environment. Restore all 540 hashed saved pre-proposal models on CPU in float64. Every training identity and input/output row is checked against the preceding chronological ledger prefix. Each model predicts the following eight observations, yielding 1,440 unseen observations per method, with 2,520 channel fits in total. Scalarized targets are reconstructed from saved weights/scales and negation; MOBO objective predictions are returned to positive physical units. Diagnostics retain recorded physical units. All observations were valid; no invalid observation is silently excluded.

We report per-observation errors, physical RMSE/MAE, standardized errors and nominal 95% Gaussian coverage. Observation intervals add the saved effective likelihood noise in output units to latent covariance; this regularization remains distinct from a measured numerical/physical error. No hyperparameter refitting or hindsight training is used. Pooling is descriptive: adaptive batches and repeated runs are not independent identically distributed calibration samples. Each method predicts its own selected observations rather than a common test set, so these errors are not comparative surrogate-performance proof.

## Physical-unit variance accessor effect
The installed GPyTorch variance accessor rounds small physical-unit variances up to its absolute float64 minimum (1e-10), emitting its generic negative-variance warning even when the underlying covariance diagonal is positive but small. The analysis therefore uses the unmodified posterior covariance diagonal and checks it is nonnegative. It separately retains API-floored intervals and their coverage. For constrained horizontal emittance the API convention yields 96.04% coverage but covariance-based coverage is 78.61%; for bunch length it is 97.43% versus 87.43%. This diagnostic distinction changes no saved surrogate, acquisition or production output. Restored fixed-noise floor warnings and variance-accessor warnings are inventoried in the metadata. They are not simulation failures.

## Results and boundaries
Constraint-aware objective coverage is 78.61%, 79.65% and 88.75%; unconstrained is 78.06%, 81.11% and 87.08%; scalarized cost is 81.25%. Gaussian uncertainty is generally underdispersed on these selected batches. This limits interpretation of model-derived feasibility probabilities even though final physical feasibility is evaluated directly by ASTRA.

The diagnostic boundary subset is selected post hoc by observed distance: 10% of the absolute threshold for size/divergence/length/transmission, and 0.5 MeV from either energy bound. Individual counts are 51–1,258 and coverage is about 80.2–89.2%. No transmission point enters its boundary subset and all observed transmissions equal one. No loss-discrimination metric, ROC/AUC or failure calibration can be inferred from that constant channel. Full-unit errors and both variance conventions are retained in c11_predictive_summary.csv and c11_next_batch_predictions.csv.

C05 records 91 Adam recoveries among the 2,520 saved channel fits, with no restored-prior fits. Those outcomes establish fitted-model availability, not predictive calibration or numerical convergence. The paper now distinguishes these claims.
