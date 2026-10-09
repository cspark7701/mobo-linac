"""Scientific reporting conventions recorded with every run (core: used by I/O and metrics).

A run's ``reporting_metadata.json`` fixes the objective names, units, signs and scales, the
reporting reference point and the constraint profile; runs are compared only when these match.
"""

from dataclasses import asdict

import numpy as np

from mobo_linac.result_schema import ResultSchema


def reporting_metadata(config, reference_model, reference_policy="initial_design"):
    """Record the scientific convention without selecting a new reference or scale."""
    schema = ResultSchema.from_config(config)
    reference = np.asarray(reference_model, dtype=float)
    if reference.shape != (len(schema.signs),) or not np.isfinite(reference).all():
        raise ValueError("Reporting reference must match finite configured objectives.")
    return {
        "schema_version": 1,
        "objective_names": list(schema.physical_columns),
        "objective_units": [obj.unit for obj in config.objectives],
        "objective_signs": list(schema.signs),
        "objective_scales": list(schema.scales),
        "reporting_ref_point": reference.tolist(),
        "reporting_ref_point_normalized": (reference / np.asarray(schema.scales)).tolist(),
        "reference_space": "model",
        "reference_policy": reference_policy,
        "constraint_profile": asdict(config.constraints),
        "design_columns": list(schema.design_columns),
        "hypervolume_columns": {"hypervolume.csv": "physical_model", "metrics_history.csv": "normalized_model"},
        "pareto_alias": "pareto_all.csv",
    }


def validate_campaign_compatibility(meta_a, meta_b, atol=0.0, raise_on_incompatible=True):
    """Require complete matching scientific metadata before comparing measurements.

    Reference origin may differ when the actual recorded convention is identical.
    Default comparison is exact, including scales much smaller than 1e-6.
    """
    required = ("schema_version", "objective_names", "objective_units", "objective_signs",
                "objective_scales", "reporting_ref_point", "reporting_ref_point_normalized",
                "reference_space", "constraint_profile", "design_columns", "hypervolume_columns")
    def reject(message):
        if raise_on_incompatible:
            raise ValueError(message)
        return False
    for meta in (meta_a, meta_b):
        if not isinstance(meta, dict) or any(key not in meta for key in required):
            return reject("Incomplete reporting metadata; an explicit convention is required.")
        count = len(meta["objective_names"])
        if meta["schema_version"] != 1 or count == 0:
            return reject("Unsupported reporting schema.")
        for key in ("objective_scales", "reporting_ref_point", "reporting_ref_point_normalized", "objective_signs", "objective_units"):
            if len(meta[key]) != count:
                return reject("Reporting metadata objective dimensions disagree.")
        scales = np.asarray(meta["objective_scales"], dtype=float)
        ref = np.asarray(meta["reporting_ref_point"], dtype=float)
        norm = np.asarray(meta["reporting_ref_point_normalized"], dtype=float)
        if (not np.isfinite(scales).all() or (scales <= 0).any() or not np.isfinite(ref).all()
                or not np.array_equal(norm, ref / scales)):
            return reject("Invalid reporting reference or objective scales.")
    for key in required:
        if meta_a[key] != meta_b[key]:
            return reject(f"Incompatible reporting metadata: {key} differs.")
    return True
