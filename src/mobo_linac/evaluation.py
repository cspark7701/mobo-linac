"""
Structured Evaluation Result Module for mobo_linac.

Defines EvaluationResult dataclass and FailureCategory enum to cleanly separate
simulation validity, physical beam feasibility, and objective values.
"""

from dataclasses import asdict, dataclass, field
from enum import Enum
import math
from typing import Any, Dict, List, Optional, Sequence, Union
import torch

from mobo_linac.config import MoboConfig, load_config
from mobo_linac.constraints import ConstraintEvaluator
from mobo_linac.objectives import transform_to_model_space


class FailureCategory(str, Enum):
    """Categories of evaluation status."""

    SUCCESS = "SUCCESS"
    INFEASIBLE_BEAM = "INFEASIBLE_BEAM"
    ASTRA_TIMEOUT = "ASTRA_TIMEOUT"
    NONZERO_RETURN = "NONZERO_RETURN"
    MISSING_OUTPUT = "MISSING_OUTPUT"
    EMPTY_OUTPUT = "EMPTY_OUTPUT"
    NAN_INF_DIAGNOSTICS = "NAN_INF_DIAGNOSTICS"
    INVALID_TRANSMISSION = "INVALID_TRANSMISSION"
    UNHANDLED_EXCEPTION = "UNHANDLED_EXCEPTION"


@dataclass
class EvaluationResult:
    """
    Structured, typed evaluation result separating simulation validity,
    beam quality feasibility, and objective values.
    """

    evaluation_id: str
    run_id: str
    x_physical: List[float]
    objectives_physical: Optional[List[float]] = None
    objectives_model: Optional[List[float]] = None
    diagnostics: Dict[str, float] = field(default_factory=dict)
    simulation_valid: bool = False
    physically_feasible: bool = False
    failure_category: str = FailureCategory.UNHANDLED_EXCEPTION.value
    failure_reason: Optional[str] = None
    runtime_s: float = 0.0
    work_dir: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert result object to dictionary representation."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvaluationResult":
        """Reconstruct result object from dictionary."""
        return cls(**data)


def create_evaluation_result(
    raw_res: Dict[str, Any],
    config: Optional[MoboConfig] = None,
    constraint_evaluator: Optional[ConstraintEvaluator] = None,
) -> EvaluationResult:
    """
    Factory function to convert raw worker output into a structured EvaluationResult.

    Args:
        raw_res: Result dictionary returned by run_astra_eval or worker task.
        config: Optional MoboConfig instance.
        constraint_evaluator: Optional ConstraintEvaluator instance.

    Returns:
        Populated EvaluationResult object.
    """
    if config is None:
        config = load_config()

    if constraint_evaluator is None:
        constraint_evaluator = ConstraintEvaluator(config.constraints)

    manifest = raw_res.get("manifest", raw_res)
    eval_id = str(raw_res.get("eval_id", manifest.get("eval_id", "eval_000000")))
    run_id = str(raw_res.get("run_id", manifest.get("run_id", "default_run")))
    x_phys = [float(x) for x in raw_res.get("parameters", manifest.get("parameters", []))]
    work_dir = str(raw_res.get("eval_dir", manifest.get("eval_dir", "")))

    timestamps = manifest.get("timestamps", {})
    runtime_s = float(timestamps.get("duration_sec", raw_res.get("execution_time_sec", 0.0)))

    status = raw_res.get("status", manifest.get("status", "failed"))
    error_msg = raw_res.get("error", manifest.get("error"))

    raw_objs = raw_res.get("objectives", manifest.get("objectives"))
    raw_diags = raw_res.get("diagnostics", manifest.get("diagnostics"))

    # Determine failure category and simulation validity
    simulation_valid = False
    physically_feasible = False
    failure_category = FailureCategory.UNHANDLED_EXCEPTION.value
    failure_reason = error_msg

    if status == "timeout" or (error_msg and "timeout" in error_msg.lower()):
        failure_category = FailureCategory.ASTRA_TIMEOUT.value
        failure_reason = error_msg or "ASTRA execution timed out"
    elif not raw_objs or not raw_diags:
        failure_category = FailureCategory.MISSING_OUTPUT.value
        failure_reason = error_msg or "Simulation output or diagnostics missing"
    else:
        # 1. Check for NaN or Inf in objectives and diagnostics first
        all_vals = list(raw_objs.values()) + list(raw_diags.values())
        has_nan_inf = any(
            v is None or not isinstance(v, (int, float)) or math.isnan(float(v)) or math.isinf(float(v))
            for v in all_vals
        )

        # 2. Check for missing transmission
        transmission_val = raw_diags.get("transmission_fraction", raw_diags.get("transmission"))

        if has_nan_inf:
            failure_category = FailureCategory.NAN_INF_DIAGNOSTICS.value
            failure_reason = "Diagnostics contain NaN, Infinite, or non-numeric values"
        elif transmission_val is None:
            failure_category = FailureCategory.MISSING_OUTPUT.value
            failure_reason = "Required transmission_fraction diagnostic is missing"
        else:
            transmission = float(transmission_val)
            # Check for negative RMS quantities or unphysical transmission range
            rms_vals = [
                raw_diags.get("sigma_x_m", raw_diags.get("sigma_x", 0.0)),
                raw_diags.get("sigma_y_m", raw_diags.get("sigma_y", 0.0)),
                raw_diags.get("sigma_xp_rad", raw_diags.get("sigma_xp", 0.0)),
                raw_diags.get("sigma_yp_rad", raw_diags.get("sigma_yp", 0.0)),
                raw_diags.get("sigma_z_m", raw_diags.get("sigma_z", 0.0)),
                raw_diags.get("sigma_energy_eV", raw_diags.get("sigma_energy", 0.0)),
            ]
            has_negative_rms = any(float(v) < 0.0 for v in rms_vals)

            if has_negative_rms:
                failure_category = FailureCategory.NAN_INF_DIAGNOSTICS.value
                failure_reason = "Diagnostics contain negative RMS beam parameters"
            elif transmission < 0.0 or transmission > 1.0:
                failure_category = FailureCategory.INVALID_TRANSMISSION.value
                failure_reason = f"Transmission fraction ({transmission}) out of physical bounds [0.0, 1.0]"
            else:
                # Simulation is numerically valid
                simulation_valid = True

                if transmission < config.constraints.min_transmission:
                    physically_feasible = False
                    failure_category = FailureCategory.INVALID_TRANSMISSION.value
                    failure_reason = f"Transmission ({transmission:.3f}) below minimum threshold ({config.constraints.min_transmission:.3f})"
                else:
                    # Evaluate full physical beam feasibility
                    is_feasible = constraint_evaluator.check_feasibility(raw_diags)
                    if is_feasible:
                        physically_feasible = True
                        failure_category = FailureCategory.SUCCESS.value
                        failure_reason = None
                    else:
                        physically_feasible = False
                        failure_category = FailureCategory.INFEASIBLE_BEAM.value
                        failure_reason = "Beam diagnostics violated constraint thresholds"

    # Extract physical and model objectives if valid/available
    objs_phys: Optional[List[float]] = None
    objs_model: Optional[List[float]] = None

    if raw_objs and isinstance(raw_objs, dict):
        norm_emit_x = float(raw_objs.get("norm_emit_x", raw_objs.get("emit_x", 1e-3)))
        norm_emit_y = float(raw_objs.get("norm_emit_y", raw_objs.get("emit_y", 1e-3)))
        sigma_energy = float(raw_objs.get("sigma_energy", 1e8))
        objs_phys = [norm_emit_x, norm_emit_y, sigma_energy]
        objs_model_tensor = transform_to_model_space(objs_phys, config)
        objs_model = objs_model_tensor.tolist()
    elif isinstance(raw_objs, (list, tuple)):
        objs_phys = [float(v) for v in raw_objs]
        objs_model_tensor = transform_to_model_space(objs_phys, config)
        objs_model = objs_model_tensor.tolist()

    diags_clean: Dict[str, float] = {}
    if raw_diags and isinstance(raw_diags, dict):
        diags_clean = {k: float(v) for k, v in raw_diags.items()}

    return EvaluationResult(
        evaluation_id=eval_id,
        run_id=run_id,
        x_physical=x_phys,
        objectives_physical=objs_phys,
        objectives_model=objs_model,
        diagnostics=diags_clean,
        simulation_valid=simulation_valid,
        physically_feasible=physically_feasible,
        failure_category=failure_category,
        failure_reason=failure_reason,
        runtime_s=runtime_s,
        work_dir=work_dir,
    )
