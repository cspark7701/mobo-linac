"""
Structured Evaluation Result Module for mobo_linac.

Defines EvaluationResult dataclass and FailureCategory enum to cleanly separate
simulation validity, physical beam feasibility, and objective values.
"""

from dataclasses import asdict, dataclass, field
from numbers import Real
from typing import Any, Dict, List, Optional

from mobo_linac.config import MoboConfig
from mobo_linac.constraints import ConstraintEvaluator
from mobo_linac.diagnostics import DIAGNOSTIC_CHANNELS, DIAGNOSTIC_NAMES, finite_measurement, normalize_diagnostics, valid_channel_measurement
from mobo_linac.result_schema import ResultSchema
from mobo_linac.status import FAILURE_CATEGORY_BY_STATUS, FailureCategory, SimulationStatus, decode_status

__all__ = ["EvaluationResult", "FailureCategory", "SimulationStatus", "create_evaluation_result"]

# Archived results stored final-position telemetry under several diagnostic aliases.
_LEGACY_Z_FINAL_KEYS = ("z_final_m", "z_final", "z_stop_m")
TELEMETRY_NAMES = ("z_final_m", "n_particles_initial", "n_particles_final")


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
    simulation_valid: Optional[bool] = False
    physically_feasible: Optional[bool] = False
    failure_category: str = FailureCategory.UNHANDLED_EXCEPTION.value
    failure_reason: Optional[str] = None
    runtime_s: float = 0.0
    work_dir: str = ""
    attempt_id: Optional[str] = None
    manifest_path: Optional[str] = None
    attempt_history: List[Dict[str, Any]] = field(default_factory=list)
    telemetry: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert result object to dictionary representation."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvaluationResult":
        """Reconstruct result object from dictionary."""
        return cls(**data)


def _split_telemetry(raw_diags: Dict[str, Any], raw_telemetry: Dict[str, Any]):
    """Keep canonical channels as diagnostics; decode archived telemetry aliases."""
    telemetry = {}
    for name in ("n_particles_initial", "n_particles_final"):
        value = raw_telemetry.get(name, raw_diags.get(name))
        if value is not None:
            telemetry[name] = value
    for key in ("z_final_m",) + _LEGACY_Z_FINAL_KEYS:
        value = raw_telemetry.get(key, raw_diags.get(key))
        if value is not None:
            telemetry["z_final_m"] = value
            break
    diagnostics = {name: raw_diags[name] for name in DIAGNOSTIC_NAMES if name in raw_diags}
    return diagnostics, telemetry


def _as_float(value):
    return float(value) if isinstance(value, Real) and not isinstance(value, bool) else float("nan")


def create_evaluation_result(
    raw_res: Dict[str, Any],
    config: MoboConfig,
    constraint_evaluator: Optional[ConstraintEvaluator] = None,
) -> EvaluationResult:
    """
    Classify one raw worker result into a structured EvaluationResult.

    The simulator status decides simulation-level failures through the single
    ``FAILURE_CATEGORY_BY_STATUS`` table. For successful simulations, measurement
    validity uses the canonical diagnostic channel limits, and feasibility uses the
    configured constraints.

    Args:
        raw_res: Result dictionary returned by run_astra_eval or a worker task.
        config: The campaign's MoboConfig; never loaded implicitly.
        constraint_evaluator: Optional ConstraintEvaluator instance.
    """
    if not isinstance(config, MoboConfig):
        raise TypeError("create_evaluation_result requires the campaign MoboConfig.")

    if constraint_evaluator is None:
        constraint_evaluator = ConstraintEvaluator(config.constraints)

    manifest = raw_res.get("manifest", raw_res)
    eval_id = str(raw_res.get("eval_id", manifest.get("eval_id", "eval_000000")))
    run_id = str(raw_res.get("run_id", manifest.get("run_id", "default_run")))
    x_phys = [float(x) for x in raw_res.get("parameters", manifest.get("parameters", []))]
    work_dir = str(raw_res.get("eval_dir", manifest.get("eval_dir", "")))

    timestamps = manifest.get("timestamps", {})
    runtime_s = float(timestamps.get("duration_sec", raw_res.get("execution_time_sec", 0.0)))

    status = decode_status(raw_res.get("status", manifest.get("status")))
    error_msg = raw_res.get("error", manifest.get("error"))

    raw_objs = raw_res.get("objectives", manifest.get("objectives"))
    raw_diags = raw_res.get("diagnostics", manifest.get("diagnostics"))
    raw_diags = normalize_diagnostics(raw_diags) if isinstance(raw_diags, dict) else {}
    raw_telemetry = raw_res.get("telemetry", manifest.get("telemetry")) or {}
    diagnostics, telemetry = _split_telemetry(raw_diags, raw_telemetry)

    schema = ResultSchema.from_config(config)
    objs_phys = schema.extract(raw_objs)
    objs_model = schema.transform(objs_phys).tolist() if objs_phys is not None else None

    simulation_valid = False
    physically_feasible = False

    if status is not SimulationStatus.SUCCESS:
        category = FAILURE_CATEGORY_BY_STATUS[status]
        reason = error_msg or f"Simulation status {status.value}"
    elif objs_phys is None:
        category, reason = FailureCategory.MISSING_OUTPUT, error_msg or "Configured objective observations missing"
    elif not all(finite_measurement(value) for value in objs_phys) or any(
            name in diagnostics and not finite_measurement(diagnostics[name]) for name in DIAGNOSTIC_NAMES):
        category, reason = FailureCategory.NAN_INF_DIAGNOSTICS, "Objectives or diagnostics contain NaN, infinite, or non-numeric values"
    else:
        target_z = float(config.execution.z_stop_m) - float(config.execution.z_loss_tolerance_m)
        z_final = telemetry.get("z_final_m")
        if z_final is None and isinstance(raw_res.get("stats"), dict) and len(raw_res["stats"].get("z", [])) > 0:
            z_final = raw_res["stats"]["z"][-1]
        missing = [name for name in DIAGNOSTIC_NAMES if name not in diagnostics]
        unphysical = [channel.name for channel in DIAGNOSTIC_CHANNELS
                      if channel.name in diagnostics and not valid_channel_measurement(channel, diagnostics[channel.name])]
        if z_final is not None and float(z_final) < target_z:
            category = FailureCategory.PREMATURE_BEAM_LOSS
            reason = f"Premature tracking termination at z = {float(z_final):.3f} m (expected exit plane >= {target_z:.3f} m)"
        elif missing:
            category, reason = FailureCategory.MISSING_OUTPUT, "Required diagnostic observations missing: " + ", ".join(missing)
        elif "transmission_fraction" in unphysical:
            category = FailureCategory.INVALID_TRANSMISSION
            reason = f"Transmission fraction ({diagnostics['transmission_fraction']}) out of physical bounds [0.0, 1.0]"
        elif unphysical:
            category, reason = FailureCategory.NAN_INF_DIAGNOSTICS, "Unphysical diagnostic observations: " + ", ".join(unphysical)
        else:
            simulation_valid = True
            physically_feasible = constraint_evaluator.check_feasibility(diagnostics)
            if physically_feasible:
                category, reason = FailureCategory.SUCCESS, None
            else:
                violated = sorted(name for name, amount in constraint_evaluator.compute_violations(diagnostics).items() if amount > 0)
                category = FailureCategory.INFEASIBLE_BEAM
                reason = "Beam diagnostics violated constraint thresholds: " + ", ".join(violated)

    return EvaluationResult(
        evaluation_id=eval_id,
        run_id=run_id,
        x_physical=x_phys,
        objectives_physical=objs_phys,
        objectives_model=objs_model,
        diagnostics={key: _as_float(value) for key, value in diagnostics.items()},
        simulation_valid=simulation_valid,
        physically_feasible=physically_feasible,
        failure_category=category.value,
        failure_reason=reason,
        runtime_s=runtime_s,
        work_dir=work_dir,
        attempt_id=raw_res.get("attempt_id", manifest.get("attempt_id")),
        manifest_path=raw_res.get("manifest_path"),
        attempt_history=raw_res.get("attempt_history", []),
        telemetry={key: _as_float(value) for key, value in telemetry.items()},
    )
