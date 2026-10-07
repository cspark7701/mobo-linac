"""
Robustness and Sensitivity Analysis Evaluator for Linac MOBO (Task 07).

Evaluates machine and beam perturbation sensitivity across representative Pareto candidates,
computing mean, standard deviation, percentile intervals, probability of feasibility,
worst constraint margins, and identifying robust operating points.
"""

from dataclasses import asdict, dataclass, field
from pathlib import Path
import uuid
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import numpy as np
import pandas as pd
import torch
import yaml

from mobo_linac.astra.workdir import validate_component, write_once_json
from mobo_linac.io.results import DESIGN_VAR_COLUMNS
from mobo_linac.config import MoboConfig, load_config, resolve_config_path
from mobo_linac.evaluation import EvaluationResult, create_evaluation_result
from mobo_linac.execution.candidate_evaluator import (
    CandidateEvaluatorBase,
    EvaluationOutcome,
    EvaluationTask,
)
from mobo_linac.metrics.pareto import (
    select_representative_pareto_candidates,
    extract_pareto_sets,
    detect_and_report_candidate_duplicates,
)
from mobo_linac.metrics.reporting import normalize_objectives_physical


SOURCE_CHANNELS = {
    "bunch_charge_relative_jitter": "bunch_charge_scale",
    "laser_spot_size_relative_jitter": "laser_spot_scale",
    "laser_pulse_duration_relative_jitter": "laser_pulse_duration_scale",
}
SOURCE_MAPPING_REASON = (
    "The ASTRA template reads a fixed particle distribution; no verified source-generation "
    "mapping applies this scale. The source distribution is unchanged."
)


@dataclass
class PerturbationSpecification:
    """
    Specification of machine and photocathode laser jitter distributions for linac robustness analysis.
    Reflects the 7 physical noise channels from configs/perturbation_config.yaml.
    """
    gun_phase_std_deg: float = 0.10
    cavity_phase_std_deg: float = 0.10
    solenoid_field_relative_std: float = 0.001
    quad_gradient_relative_std: float = 0.001
    bunch_charge_relative_std: float = 0.010
    laser_spot_size_relative_std: float = 0.010
    laser_pulse_duration_relative_std: float = 0.010

    def __post_init__(self):
        for name, value in vars(self).items():
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not np.isfinite(value) or value < 0:
                raise ValueError(f"{name} must be finite and nonnegative.")

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PerturbationSpecification":
        """Constructs specification from dictionary (e.g., perturbation_config.yaml)."""
        perts = d.get("perturbations", d)

        def extract_std(key: str, default: float) -> float:
            if key in perts:
                val = perts[key]
                if isinstance(val, dict) and "std" in val:
                    return float(val["std"])
                elif isinstance(val, (int, float)):
                    return float(val)
            return default

        return cls(
            gun_phase_std_deg=extract_std("gun_phase_error_deg", 0.10),
            cavity_phase_std_deg=extract_std("cavity_phase_error_deg", 0.10),
            solenoid_field_relative_std=extract_std("solenoid_field_relative_error", 0.001),
            quad_gradient_relative_std=extract_std("quad_gradient_relative_error", 0.001),
            bunch_charge_relative_std=extract_std("bunch_charge_relative_jitter", 0.010),
            laser_spot_size_relative_std=extract_std("laser_spot_size_relative_jitter", 0.010),
            laser_pulse_duration_relative_std=extract_std("laser_pulse_duration_relative_jitter", 0.010),
        )

    @classmethod
    def from_yaml(cls, yaml_path: Union[str, Path]) -> "PerturbationSpecification":
        """Loads specification from a YAML configuration file."""
        p = resolve_config_path(yaml_path)
        with open(p, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return cls.from_dict(data)


@dataclass
class PerturbedMachineState:
    """
    Represents a full-chain perturbed accelerator state across 6 design parameters
    and photocathode/laser jitter dimensions.
    """
    parameters: List[float]  # [solenoid, quad1, quad2, gun_phase, acc1_2_phase, acc3_4_phase]
    bunch_charge_scale: float = 1.0
    laser_spot_scale: float = 1.0
    laser_pulse_duration_scale: float = 1.0
    channel_deltas: Dict[str, float] = field(default_factory=dict)


def load_perturbation_spec(config_path: Optional[Union[str, Path]] = None) -> PerturbationSpecification:
    """Resolve omitted defaults separately from explicit requested perturbation files."""
    path = resolve_config_path(config_path, default_names=("perturbation_config.yaml",))
    return PerturbationSpecification.from_yaml(path)


def generate_perturbed_machine_states(
    nominal_x: Sequence[float],
    num_perturbations: int = 50,
    seed: int = 42,
    spec: Optional[Union[PerturbationSpecification, Dict[str, Any]]] = None,
) -> List[PerturbedMachineState]:
    """
    Generates full-chain perturbed machine states including 6D lattice parameters and
    photocathode/laser jitter dimensions.

    Args:
        nominal_x: Nominal 6D design vector [solenoid, quad1, quad2, gun_phase, acc1_2_phase, acc3_4_phase].
        num_perturbations: Number of perturbation samples.
        seed: Random seed.
        spec: PerturbationSpecification or config dictionary.

    Returns:
        List of PerturbedMachineState objects.
    """
    if spec is None:
        pert_spec = load_perturbation_spec()
    elif isinstance(spec, dict):
        pert_spec = PerturbationSpecification.from_dict(spec)
    else:
        pert_spec = spec

    if len(nominal_x) != 6:
        raise ValueError("The established jitter model requires six canonical lattice parameters")
    if num_perturbations < 0:
        raise ValueError("num_perturbations must be nonnegative")
    if any(not np.isfinite(value) or value < 0 for value in asdict(pert_spec).values()):
        raise ValueError("Jitter standard deviations must be finite and nonnegative")
    rng = np.random.default_rng(seed)
    nominal_arr = np.array(nominal_x, dtype=np.float64)

    states: List[PerturbedMachineState] = []
    for _ in range(num_perturbations):
        # 1. Magnet field relative errors
        sol_rel = rng.normal(0.0, pert_spec.solenoid_field_relative_std)
        q1_rel = rng.normal(0.0, pert_spec.quad_gradient_relative_std)
        q2_rel = rng.normal(0.0, pert_spec.quad_gradient_relative_std)

        # 2. RF phase errors (degrees)
        gun_dphi = rng.normal(0.0, pert_spec.gun_phase_std_deg)
        acc12_dphi = rng.normal(0.0, pert_spec.cavity_phase_std_deg)
        acc34_dphi = rng.normal(0.0, pert_spec.cavity_phase_std_deg)

        # 3. Photocathode & laser jitter channels
        charge_rel = rng.normal(0.0, pert_spec.bunch_charge_relative_std)
        spot_rel = rng.normal(0.0, pert_spec.laser_spot_size_relative_std)
        duration_rel = rng.normal(0.0, pert_spec.laser_pulse_duration_relative_std)

        perturbed_x = [
            float(nominal_arr[0] * (1.0 + sol_rel)),
            float(nominal_arr[1] * (1.0 + q1_rel)),
            float(nominal_arr[2] * (1.0 + q2_rel)),
            float(nominal_arr[3] + gun_dphi),
            float(nominal_arr[4] + acc12_dphi),
            float(nominal_arr[5] + acc34_dphi),
        ]

        channel_deltas = {
            "solenoid_field_relative_error": float(sol_rel),
            "quad1_gradient_relative_error": float(q1_rel),
            "quad2_gradient_relative_error": float(q2_rel),
            "gun_phase_error_deg": float(gun_dphi),
            "cavity_phase_acc12_error_deg": float(acc12_dphi),
            "cavity_phase_acc34_error_deg": float(acc34_dphi),
            "bunch_charge_relative_jitter": float(charge_rel),
            "laser_spot_size_relative_jitter": float(spot_rel),
            "laser_pulse_duration_relative_jitter": float(duration_rel),
        }

        state = PerturbedMachineState(
            parameters=perturbed_x,
            bunch_charge_scale=float(1.0 + charge_rel),
            laser_spot_scale=float(1.0 + spot_rel),
            laser_pulse_duration_scale=float(1.0 + duration_rel),
            channel_deltas=channel_deltas,
        )
        states.append(state)

    return states


def generate_perturbed_parameters(
    nominal_x: Sequence[float],
    num_perturbations: int = 50,
    seed: int = 42,
    phase_std_deg: Optional[float] = None,
    field_relative_std: Optional[float] = None,
    spec: Optional[Union[PerturbationSpecification, Dict[str, Any]]] = None,
) -> List[List[float]]:
    """
    Generates perturbed parameter vectors around a nominal design vector.

    Args:
        nominal_x: Nominal 6D design vector.
        num_perturbations: Number of perturbed samples to generate.
        seed: Random seed.
        phase_std_deg: Optional override for RF phase jitter (degrees).
        field_relative_std: Optional override for magnet relative field jitter (dimensionless).
        spec: Optional PerturbationSpecification or config dictionary.

    Returns:
        List of 6D perturbed parameter vectors.
    """
    if spec is not None:
        if isinstance(spec, dict):
            pert_spec = PerturbationSpecification.from_dict(spec)
        else:
            pert_spec = spec
    elif phase_std_deg is not None or field_relative_std is not None:
        pert_spec = PerturbationSpecification(
            gun_phase_std_deg=phase_std_deg if phase_std_deg is not None else 0.10,
            cavity_phase_std_deg=phase_std_deg if phase_std_deg is not None else 0.10,
            solenoid_field_relative_std=field_relative_std if field_relative_std is not None else 0.001,
            quad_gradient_relative_std=field_relative_std if field_relative_std is not None else 0.001,
        )
    else:
        pert_spec = load_perturbation_spec()

    states = generate_perturbed_machine_states(
        nominal_x=nominal_x,
        num_perturbations=num_perturbations,
        seed=seed,
        spec=pert_spec,
    )
    return [s.parameters for s in states]


def compute_robustness_summary(
    candidate_label: str,
    nominal_result: EvaluationResult,
    perturbed_results: List[EvaluationResult],
) -> Dict[str, Any]:
    """
    Computes statistical robustness metrics for a Pareto candidate across perturbed runs.

    Args:
        candidate_label: Candidate name (e.g. 'knee_point').
        nominal_result: Nominal EvaluationResult.
        perturbed_results: List of perturbed EvaluationResult records.

    Returns:
        Dictionary of robustness metrics.
    """
    total_evals = len(perturbed_results)
    valid_results = [r for r in perturbed_results if r.simulation_valid and r.objectives_physical]
    feasible_results = [r for r in valid_results if r.physically_feasible]

    prob_feasibility = float(len(feasible_results)) / float(total_evals) if total_evals > 0 else 0.0

    if valid_results:
        emit_x_vals = [r.objectives_physical[0] for r in valid_results]
        emit_y_vals = [r.objectives_physical[1] for r in valid_results]
        sigma_e_vals = [r.objectives_physical[2] for r in valid_results]

        mean_emit_x = float(np.mean(emit_x_vals))
        std_emit_x = float(np.std(emit_x_vals))
        p5_emit_x = float(np.percentile(emit_x_vals, 5))
        p95_emit_x = float(np.percentile(emit_x_vals, 95))

        mean_emit_y = float(np.mean(emit_y_vals))
        std_emit_y = float(np.std(emit_y_vals))

        mean_sigma_e = float(np.mean(sigma_e_vals))
        std_sigma_e = float(np.std(sigma_e_vals))
    else:
        mean_emit_x = std_emit_x = p5_emit_x = p95_emit_x = np.nan
        mean_emit_y = std_emit_y = np.nan
        mean_sigma_e = std_sigma_e = np.nan

    # Robust score: feasibility probability, 3-objective degradation, and worst constraint margin
    nom_objs = nominal_result.objectives_physical if nominal_result.objectives_physical else [1e-6, 1e-6, 1e6]
    growth_x = mean_emit_x / nom_objs[0] if not np.isnan(mean_emit_x) and nom_objs[0] > 0 else 2.0
    growth_y = mean_emit_y / nom_objs[1] if not np.isnan(mean_emit_y) and nom_objs[1] > 0 else 2.0
    growth_e = mean_sigma_e / nom_objs[2] if not np.isnan(mean_sigma_e) and nom_objs[2] > 0 else 2.0

    mean_degradation = float((growth_x + growth_y + growth_e) / 3.0)

    margins = []
    for r in valid_results:
        trans = r.diagnostics.get("transmission_fraction", 1.0)
        margin = (trans - 0.90) / 0.90
        margins.append(margin)

    worst_margin = float(min(margins)) if margins else 0.0
    margin_factor = float(max(0.5, 1.0 + worst_margin))

    robust_score = float((prob_feasibility * margin_factor) / max(1.0, mean_degradation))

    return {
        "candidate_label": candidate_label,
        "evaluation_id": nominal_result.evaluation_id,
        "probability_of_feasibility": prob_feasibility,
        "robust_score": robust_score,
        "worst_constraint_margin": worst_margin,
        "mean_objective_degradation": mean_degradation,
        "nominal_emit_x": nom_objs[0],
        "mean_emit_x": mean_emit_x,
        "std_emit_x": std_emit_x,
        "p5_emit_x": p5_emit_x,
        "p95_emit_x": p95_emit_x,
        "nominal_emit_y": nom_objs[1],
        "mean_emit_y": mean_emit_y,
        "std_emit_y": std_emit_y,
        "nominal_sigma_energy": nom_objs[2],
        "mean_sigma_energy": mean_sigma_e,
        "std_sigma_energy": std_sigma_e,
        "is_fragile": prob_feasibility < 0.80,
    }


class RobustnessEvaluator(CandidateEvaluatorBase):
    """
    Robustness and jitter analysis engine evaluating machine perturbations
    across representative Pareto candidates.
    """

    def __init__(
        self,
        config: Optional[MoboConfig] = None,
        base_output_dir: Union[str, Path] = "results/robustness",
        num_workers: int = 1,
        timeout: int = 30,
        spec: Optional[PerturbationSpecification] = None,
    ):
        super().__init__(
            config=config,
            base_output_dir=base_output_dir,
            num_workers=num_workers,
            timeout=timeout,
        )
        self.spec = spec or load_perturbation_spec()

    def generate_evaluation_plan(
        self,
        candidates: Sequence[EvaluationResult],
        num_perturbations: int = 50,
        seed: int = 42,
        roles: Optional[Sequence[str]] = None,
    ) -> List[EvaluationTask]:
        """Generates perturbed machine state evaluation tasks for each candidate."""
        design_names = [dv.name for dv in self.config.design_variables]
        if len(design_names) != 6 or set(design_names) != set(DESIGN_VAR_COLUMNS):
            raise ValueError("Robustness jitter requires the six canonical design-variable names")
        if roles is not None and len(roles) != len(candidates):
            raise ValueError("roles must match candidates")
        source_stds = {
            "bunch_charge_relative_jitter": self.spec.bunch_charge_relative_std,
            "laser_spot_size_relative_jitter": self.spec.laser_spot_size_relative_std,
            "laser_pulse_duration_relative_jitter": self.spec.laser_pulse_duration_relative_std,
        }
        tasks: List[EvaluationTask] = []
        for c_idx, cand in enumerate(candidates):
            if len(cand.x_physical) != len(design_names):
                raise ValueError("Candidate parameters must match the configured design layout")
            c_label = roles[c_idx] if roles is not None else f"cand_{c_idx+1}"
            validate_component(c_label)
            nominal_by_name = dict(zip(design_names, cand.x_physical))
            p_states = generate_perturbed_machine_states(
                nominal_x=[nominal_by_name[name] for name in DESIGN_VAR_COLUMNS],
                num_perturbations=num_perturbations,
                seed=seed + c_idx * 100,
                spec=self.spec,
            )
            for p_idx, p_state in enumerate(p_states):
                task = EvaluationTask(
                    task_id=f"pert_{c_label}_sample_{p_idx+1:03d}",
                    role=f"{c_label}_pert_{p_idx+1:03d}",
                    parameters=[p_state.parameters[DESIGN_VAR_COLUMNS.index(name)] for name in design_names],
                    source_settings={name: getattr(p_state, name) for name in SOURCE_CHANNELS.values()},
                    nominal_result=cand,
                    metadata={
                        "candidate_label": c_label,
                        "sample_idx": p_idx,
                        "seed": seed + c_idx * 100,
                        "nominal_evaluation_id": cand.evaluation_id,
                        "nominal_run_id": cand.run_id,
                        "nominal_parameters": list(cand.x_physical),
                        "perturbation_specification": asdict(self.spec),
                        "unsupported_channels": {channel: SOURCE_MAPPING_REASON for channel, std in source_stds.items() if std > 0},
                        "channel_deltas": p_state.channel_deltas,
                    },
                )
                tasks.append(task)
        return tasks

    def evaluate_candidates(
        self,
        candidates: Sequence[EvaluationResult],
        num_perturbations: int = 50,
        seed: int = 42,
        custom_evaluator: Optional[Any] = None,
        request_evaluator: Optional[Any] = None,
        roles: Optional[Sequence[str]] = None,
        batch_evaluator: Optional[Any] = None,
    ) -> List[Dict[str, Any]]:
        """
        Executes robustness evaluation plan and computes statistical summaries.
        """
        if num_perturbations <= 0:
            raise ValueError("Robustness evaluation requires at least one perturbation")
        tasks = self.generate_evaluation_plan(candidates, num_perturbations=num_perturbations, seed=seed, roles=roles)
        if batch_evaluator is not None:
            if custom_evaluator is not None or request_evaluator is not None:
                raise ValueError("Choose one robustness backend")
            raw_results = batch_evaluator.evaluate_requests([task.to_request() for task in tasks], run_id="candidate_eval")
            if len(raw_results) != len(tasks):
                raise ValueError("Backend returned an incomplete robustness batch")
            outcomes = [EvaluationOutcome(task, create_evaluation_result(raw, self.config), execution_details=raw)
                        for task, raw in zip(tasks, raw_results)]
        else:
            outcomes = self.evaluate_plan_parallel(tasks, custom_evaluator=custom_evaluator,
                                                  request_evaluator=request_evaluator)
        session = self.base_output_dir / "robustness_runs" / ("robustness_" + uuid.uuid4().hex)
        session.mkdir(parents=True, exist_ok=False)
        request_records = []
        for outcome in outcomes:
            evidence = outcome.execution_details.get("manifest", {})
            request_records.append({
                "request": outcome.task.to_request().to_dict(),
                "result": outcome.evaluated_result.to_dict(),
                "execution_kind": outcome.execution_details.get("execution_kind", "astra" if evidence else "unconfirmed"),
                "applied_perturbations": evidence.get("applied_perturbations", {}),
                "applied_namelist_overrides": evidence.get("applied_namelist_overrides", {}),
                "applied_namelist_values": evidence.get("applied_namelist_values", {}),
                "source_application": evidence.get("source_application", {}),
            })
        request_path = write_once_json(session / "robustness_requests.json", {"config": asdict(self.config),
                            "perturbation_specification": asdict(self.spec), "records": request_records})

        # Group by candidate
        by_cand: Dict[str, List[EvaluationResult]] = {}
        cand_map: Dict[str, Optional[EvaluationResult]] = {}
        for outcome in outcomes:
            c_lbl = outcome.task.metadata.get("candidate_label", "cand_1")
            if c_lbl not in by_cand:
                by_cand[c_lbl] = []
                cand_map[c_lbl] = outcome.task.nominal_result
            by_cand[c_lbl].append(outcome.evaluated_result)

        summaries = []
        for c_lbl, pert_res_list in by_cand.items():
            nom_res = cand_map[c_lbl]
            if nom_res is None:
                continue
            summary = compute_robustness_summary(
                candidate_label=c_lbl,
                nominal_result=nom_res,
                perturbed_results=pert_res_list,
            )
            records = [record for record in request_records if record["request"]["metadata"]["candidate_label"] == c_lbl]
            unsupported = {channel: reason for record in records
                           for channel, reason in record["request"]["metadata"]["unsupported_channels"].items()}
            evaluated = sorted({channel for record in records if record["result"]["simulation_valid"]
                                and record["execution_kind"] == "astra"
                                for channel, delta in record["applied_perturbations"].items() if delta != 0})
            summary.update({
                "perturbation_scope": "supported_lattice_only" if unsupported else "supported_requests",
                "unsupported_channels": sorted(unsupported),
                "unsupported_channel_reasons": unsupported,
                "evaluated_channels": evaluated,
                "execution_kinds": sorted({record["execution_kind"] for record in records}),
                "full_requested_jitter_evaluated": bool(records) and not unsupported
                    and all(record["execution_kind"] == "astra" and record["result"]["simulation_valid"]
                            and all(record["applied_perturbations"].get(channel) == delta
                                    for channel, delta in record["request"]["metadata"]["channel_deltas"].items() if delta != 0)
                            for record in records),
                "request_manifest_path": str(request_path),
            })
            summaries.append(summary)
        write_once_json(session / "robustness_summary.json", {"summaries": summaries})

        return summaries


