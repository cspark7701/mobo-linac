"""
Robustness and Sensitivity Analysis Evaluator for Linac MOBO.

Perturbation channels are declared per configured design variable (lattice) or per
source setting (photocathode/laser) in a validated specification. Summaries use the
configured objectives and the active constraint profile; missing observations stay
unknown and are never replaced by favorable defaults.
"""

from dataclasses import asdict, dataclass, field
import math
from pathlib import Path
import uuid
from typing import Any, Dict, List, Optional, Sequence, Union

import numpy as np
import yaml

from mobo_linac.astra.workdir import read_evaluation_manifest, validate_component
from mobo_linac.utils.durable import write_once_json
from mobo_linac.config import MoboConfig, resolve_config_path
from mobo_linac.perturbations import (  # noqa: F401  (public through the robustness package)
    DISTRIBUTIONS, KINDS, SEED_POLICIES, SOURCE_MAPPING_REASON, SUPPORTED_SOURCE_SETTINGS,
    LatticeChannel, PerturbationSpecification, SourceChannel,
)
from mobo_linac.constraints import ConstraintEvaluator
from mobo_linac.diagnostics import DIAGNOSTIC_CHANNELS, constraint_sides, normalize_diagnostics, valid_channel_measurement
from mobo_linac.evaluation import EvaluationResult
from mobo_linac.execution.candidate_evaluator import CandidateEvaluatorBase, EvaluationTask
from mobo_linac.result_schema import ResultSchema


@dataclass
class PerturbedMachineState:
    """One perturbed accelerator state: design values by name and source scales."""

    parameters: Dict[str, float]
    source_settings: Dict[str, float] = field(default_factory=dict)
    channel_deltas: Dict[str, float] = field(default_factory=dict)


def load_perturbation_spec(config_path: Optional[Union[str, Path]] = None) -> PerturbationSpecification:
    """Resolve omitted defaults separately from explicit requested perturbation files."""
    return PerturbationSpecification.from_yaml(resolve_config_path(config_path, default_names=("perturbation_config.yaml",)))


def configured_perturbation_spec(config) -> PerturbationSpecification:
    """The configuration's ``perturbations`` section, else the default perturbation file."""
    if getattr(config, "perturbations", None) is not None:
        return PerturbationSpecification.from_dict(config.perturbations)
    return load_perturbation_spec()


def generate_perturbed_machine_states(
    nominal: Dict[str, float],
    spec: PerturbationSpecification,
    num_perturbations: int = 50,
    seed: int = 42,
) -> List[PerturbedMachineState]:
    """
    Draw perturbed machine states. Each sample draws lattice channels, then source
    channels, in specification order, so draws do not depend on design-variable order.
    """
    if num_perturbations < 0:
        raise ValueError("num_perturbations must be nonnegative")
    missing = [c.design_variable for c in spec.lattice if c.design_variable not in nominal]
    if missing:
        raise ValueError(f"Nominal design is missing perturbed variables: {missing}")
    rng = np.random.default_rng(seed)
    states: List[PerturbedMachineState] = []
    for _ in range(num_perturbations):
        deltas, parameters, sources = {}, dict(nominal), {}
        for channel in spec.lattice:
            delta = float(rng.normal(0.0, channel.std))
            deltas[channel.channel] = delta
            parameters[channel.design_variable] = channel.apply(float(nominal[channel.design_variable]), delta)
        for channel in spec.source:
            delta = float(rng.normal(0.0, channel.std))
            deltas[channel.channel] = delta
            sources[channel.setting] = float(1.0 + delta)
        states.append(PerturbedMachineState(parameters, sources, deltas))
    return states


def _channel_margins(evaluator: ConstraintEvaluator, diagnostics: Dict[str, Any]) -> Dict[str, float]:
    """Signed margins normalized by each threshold: positive inside, negative violated, NaN unknown."""
    normalized = normalize_diagnostics(diagnostics)
    margins = {}
    for index, side, threshold, _ in constraint_sides(evaluator.config):
        channel = DIAGNOSTIC_CHANNELS[index]
        value = normalized.get(channel.name)
        key = f"{channel.name}:{side}"
        if not valid_channel_measurement(channel, value) or threshold == 0:
            margins[key] = float("nan")
        else:
            margins[key] = float((value - threshold) / abs(threshold) if side == "lower"
                                 else (threshold - value) / abs(threshold))
    return margins


def compute_robustness_summary(
    candidate_label: str,
    nominal_result: EvaluationResult,
    perturbed_results: List[EvaluationResult],
    config: MoboConfig,
    fragility_threshold: float = 0.80,
) -> Dict[str, Any]:
    """
    Robustness statistics for one candidate across perturbed evaluations.

    Statistics use every configured objective; constraint margins use every configured
    channel of the active profile. Missing or invalid observations make the affected
    statistic NaN and are listed in ``summary_issues``.
    """
    schema = ResultSchema.from_config(config)
    evaluator = ConstraintEvaluator(config.constraints)
    issues: List[str] = []
    total = len(perturbed_results)
    valid = [r for r in perturbed_results if r.simulation_valid is True and schema.extract(r.objectives_physical) is not None
             and np.isfinite(schema.extract(r.objectives_physical)).all()]
    feasible = [r for r in valid if r.physically_feasible is True]
    probability = float(len(feasible)) / float(total) if total else float("nan")
    if not total:
        issues.append("no perturbed evaluations")

    summary: Dict[str, Any] = {
        "candidate_label": candidate_label,
        "run_id": nominal_result.run_id,
        "evaluation_id": nominal_result.evaluation_id,
        "objective_order": list(schema.physical_columns),
        "objective_units": {obj.explicit_name: obj.unit for obj in config.objectives},
        "num_perturbed": total,
        "num_valid": len(valid),
        "num_feasible": len(feasible),
        "probability_of_feasibility": probability,
    }
    nominal = schema.extract(nominal_result.objectives_physical)
    if nominal is None or not np.isfinite(nominal).all():
        issues.append("nominal objectives missing or nonfinite")
        nominal = [float("nan")] * len(schema.signs)
    values = np.asarray([schema.extract(r.objectives_physical) for r in valid], dtype=float).reshape(len(valid), len(schema.signs))
    growths = []
    for index, (column, sign) in enumerate(zip(schema.physical_columns, schema.signs)):
        column_values = values[:, index]
        stats = ({"mean": float(np.mean(column_values)), "std": float(np.std(column_values)),
                  "p5": float(np.percentile(column_values, 5)), "p95": float(np.percentile(column_values, 95))}
                 if len(column_values) else {key: float("nan") for key in ("mean", "std", "p5", "p95")})
        summary[f"nominal_{column}"] = float(nominal[index])
        for key, value in stats.items():
            summary[f"{key}_{column}"] = value
        # Degradation ratio in the objective's preferred direction (> 1 is worse).
        mean, base = stats["mean"], float(nominal[index])
        if not (math.isfinite(mean) and math.isfinite(base)) or mean <= 0 or base <= 0:
            growths.append(float("nan"))
            issues.append(f"degradation undefined for {column}")
        else:
            growths.append(mean / base if sign == -1 else base / mean)
    degradation = float(np.mean(growths)) if growths and np.isfinite(growths).all() else float("nan")

    margins = [_channel_margins(evaluator, r.diagnostics) for r in valid]
    channel_minima = {key: float(min(m[key] for m in margins)) for key in (margins[0] if margins else {})}
    if not margins:
        worst = float("nan")
        issues.append("no valid perturbed diagnostics")
    elif any(math.isnan(value) for value in channel_minima.values()):
        worst = float("nan")
        issues.append("constraint margins incomplete")
    else:
        worst = min(channel_minima.values())
    margin_factor = max(0.5, 1.0 + worst) if math.isfinite(worst) else float("nan")
    score = (probability * margin_factor / max(1.0, degradation)
             if all(math.isfinite(v) for v in (probability, margin_factor, degradation)) else float("nan"))
    summary.update({
        "robust_score": float(score),
        "worst_constraint_margin": worst,
        "worst_constraint_channel": min(channel_minima, key=channel_minima.get) if channel_minima and math.isfinite(worst) else None,
        "constraint_margins": channel_minima,
        "mean_objective_degradation": degradation,
        "fragility_threshold": float(fragility_threshold),
        "is_fragile": bool(probability < fragility_threshold) if math.isfinite(probability) else None,
        "summary_issues": sorted(set(issues)),
    })
    return summary


class RobustnessEvaluator(CandidateEvaluatorBase):
    """
    Robustness and jitter analysis engine evaluating machine perturbations
    across representative Pareto candidates.
    """

    def __init__(
        self,
        config: MoboConfig,
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
        self.spec = spec or configured_perturbation_spec(self.config)
        self.spec.validate_for(self.config)

    def candidate_seed(self, seed: int, index: int) -> int:
        return seed + 100 * index if self.spec.seed_policy == "candidate_offset" else seed

    def generate_evaluation_plan(
        self,
        candidates: Sequence[EvaluationResult],
        num_perturbations: int = 50,
        seed: int = 42,
        roles: Optional[Sequence[str]] = None,
    ) -> List[EvaluationTask]:
        """Generates perturbed machine state evaluation tasks for each candidate."""
        design_names = [dv.name for dv in self.config.design_variables]
        if roles is not None and len(roles) != len(candidates):
            raise ValueError("roles must match candidates")
        unsupported = {c.channel: SOURCE_MAPPING_REASON for c in self.spec.source if c.std > 0}
        tasks: List[EvaluationTask] = []
        for c_idx, cand in enumerate(candidates):
            if len(cand.x_physical) != len(design_names):
                raise ValueError("Candidate parameters must match the configured design layout")
            c_label = roles[c_idx] if roles is not None else f"cand_{c_idx+1}"
            validate_component(c_label)
            candidate_seed = self.candidate_seed(seed, c_idx)
            states = generate_perturbed_machine_states(
                dict(zip(design_names, cand.x_physical)), self.spec,
                num_perturbations=num_perturbations, seed=candidate_seed)
            for p_idx, state in enumerate(states):
                tasks.append(EvaluationTask(
                    task_id=f"pert_{c_label}_sample_{p_idx+1:03d}",
                    role=f"{c_label}_pert_{p_idx+1:03d}",
                    parameters=[state.parameters[name] for name in design_names],
                    source_settings=dict(state.source_settings),
                    nominal_result=cand,
                    metadata={
                        "candidate_label": c_label,
                        "sample_idx": p_idx,
                        "seed": candidate_seed,
                        "seed_policy": self.spec.seed_policy,
                        "nominal_evaluation_id": cand.evaluation_id,
                        "nominal_run_id": cand.run_id,
                        "nominal_parameters": list(cand.x_physical),
                        "perturbation_specification": self.spec.to_dict(),
                        "unsupported_channels": dict(unsupported),
                        "channel_deltas": state.channel_deltas,
                        "channel_targets": self.spec.channel_targets(),
                    },
                ))
        return tasks

    def evaluate_candidates(
        self,
        candidates: Sequence[EvaluationResult],
        num_perturbations: int = 50,
        seed: int = 42,
        roles: Optional[Sequence[str]] = None,
        evaluator: Optional[Any] = None,
        run_id: str = "candidate_eval",
    ) -> List[Dict[str, Any]]:
        """
        Executes the robustness plan with one evaluator (default: the ASTRA process pool)
        and computes statistical summaries.
        """
        if num_perturbations <= 0:
            raise ValueError("Robustness evaluation requires at least one perturbation")
        tasks = self.generate_evaluation_plan(candidates, num_perturbations=num_perturbations, seed=seed, roles=roles)
        outcomes = self.evaluate_plan_parallel(tasks, evaluator=evaluator, run_id=run_id)
        session = self.base_output_dir / "robustness_runs" / ("robustness_" + uuid.uuid4().hex)
        session.mkdir(parents=True, exist_ok=False)
        request_records = []
        for outcome in outcomes:
            # ASTRA completions reference their immutable attempt manifest.
            manifest_path = outcome.execution_details.get("manifest_path")
            evidence = read_evaluation_manifest(manifest_path) if manifest_path else {}
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
                            "perturbation_specification": self.spec.to_dict(), "records": request_records})

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
                config=self.config,
                fragility_threshold=self.spec.fragility_threshold,
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


