"""
Centralized Configuration Module for mobo_linac.

Defines declarative schemas, strict physical validation, JSON Schema exporter,
and Markdown documentation generator for accelerator Bayesian optimization.
"""

from dataclasses import MISSING, asdict, dataclass, field, fields, is_dataclass
import json
import math
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, get_args, get_origin, get_type_hints
import torch
import yaml

from mobo_linac.status import DEFAULT_RETRY_STATUSES, SimulationStatus
from mobo_linac.benchmark_algorithms import (
    SUPPORTED_BENCHMARK_ALGORITHMS,
    get_benchmark_algorithm,
)


@dataclass
class DesignVariableConfig:
    """Configuration for a single linac design variable."""

    name: str
    astra_key: str
    unit: str
    nominal_value: float
    ratio: float
    lower_bound: float
    upper_bound: float
    is_coupled: bool = False
    coupled_targets: Optional[List[str]] = None
    label: Optional[str] = None  # display label (LaTeX allowed) for figures and tables

    def validate(self) -> None:
        """Validate bounds ordering, nominal value validity, and coupling rules."""
        _validate_fields(self, types_only=True)
        if not self.name or not isinstance(self.name, str):
            raise ValueError("Design variable must have a non-empty name string.")
        if not self.astra_key or not isinstance(self.astra_key, str):
            raise ValueError(f"Design variable '{self.name}' must have a non-empty astra_key string.")
        if self.lower_bound >= self.upper_bound:
            raise ValueError(
                f"Invalid bounds for design variable '{self.name}': "
                f"lower_bound ({self.lower_bound}) >= upper_bound ({self.upper_bound}); fixed variables must be removed from the optimization vector"
            )
        if self.ratio < 0:
            raise ValueError(f"Design variable '{self.name}' has negative search ratio: {self.ratio}")
        if self.is_coupled and not self.coupled_targets:
            raise ValueError(
                f"Design variable '{self.name}' is marked coupled but has no coupled_targets."
            )
        if self.is_coupled and self.coupled_targets:
            for target in self.coupled_targets:
                if not target or not isinstance(target, str):
                    raise ValueError(
                        f"Design variable '{self.name}' contains invalid coupled target: '{target}'"
                    )
        _validate_fields(self)


@dataclass
class ObjectiveConfig:
    """Configuration for an optimization objective."""

    name: str
    explicit_name: str
    unit: str
    physical_direction: str  # "minimize" or "maximize"
    model_sign: int  # -1 for minimization (maximization in BoTorch), 1 for maximization

    aliases: List[str] = field(default_factory=list)
    reporting_scale: Optional[float] = None
    # Display metadata: figures show value / reporting scale in display_unit.
    label: Optional[str] = None
    display_unit: Optional[str] = None

    def validate(self) -> None:
        """Validate objective names, aliases, direction and normalization scale."""
        _validate_fields(self, types_only=True)
        if not isinstance(self.aliases, (list, tuple)) or any(not isinstance(a, str) or not a for a in self.aliases):
            raise ValueError("Objective aliases must be non-empty strings.")
        if self.reporting_scale is not None and (not isinstance(self.reporting_scale, (int, float)) or isinstance(self.reporting_scale, bool) or not 0 < self.reporting_scale < float("inf")):
            raise ValueError("Objective reporting_scale must be finite and positive.")
        if not self.name or not isinstance(self.name, str):
            raise ValueError("Objective must have a non-empty name string.")
        if not isinstance(self.explicit_name, str) or not self.explicit_name:
            raise ValueError("Objective must have a non-empty explicit_name string.")
        if self.physical_direction not in ("minimize", "maximize"):
            raise ValueError(
                f"Invalid physical_direction '{self.physical_direction}' for objective '{self.name}'. "
                "Must be 'minimize' or 'maximize'."
            )
        if self.model_sign not in (-1, 1):
            raise ValueError(
                f"Invalid model_sign '{self.model_sign}' for objective '{self.name}'. Must be -1 or 1."
            )
        if self.physical_direction == "minimize" and self.model_sign != -1:
            raise ValueError(f"Minimization objective '{self.name}' must have model_sign = -1.")
        if self.physical_direction == "maximize" and self.model_sign != 1:
            raise ValueError(f"Maximization objective '{self.name}' must have model_sign = 1.")
        _validate_fields(self)


@dataclass
class ConstraintsConfig:
    """Configuration for diagnostic beam constraints and physical thresholds."""

    max_sigma_x_m: float = 1.0e-3
    max_sigma_y_m: float = 1.0e-3
    max_sigma_xp_rad: float = 1.0e-3
    max_sigma_yp_rad: float = 1.0e-3
    max_sigma_z_m: float = 1.0e-3
    min_mean_kinetic_energy_eV: float = 195.0e6
    max_mean_kinetic_energy_eV: float = 205.0e6
    min_transmission: float = 0.90

    def validate(self) -> None:
        """Validate beam diagnostic thresholds and transmission ranges."""
        _validate_fields(self, types_only=True)
        if self.min_mean_kinetic_energy_eV > self.max_mean_kinetic_energy_eV:
            raise ValueError(
                f"Invalid kinetic energy constraints: min ({self.min_mean_kinetic_energy_eV}) > max ({self.max_mean_kinetic_energy_eV})"
            )
        if self.min_mean_kinetic_energy_eV <= 0:
            raise ValueError(
                f"min_mean_kinetic_energy_eV must be positive, got {self.min_mean_kinetic_energy_eV}"
            )
        if self.max_sigma_x_m <= 0 or self.max_sigma_y_m <= 0 or self.max_sigma_z_m <= 0:
            raise ValueError("Beam size constraints (sigma_x, sigma_y, sigma_z) must be strictly positive.")
        if self.max_sigma_xp_rad <= 0 or self.max_sigma_yp_rad <= 0:
            raise ValueError("Divergence constraints (sigma_xp, sigma_yp) must be strictly positive.")
        if not (0.0 < self.min_transmission <= 1.0):
            raise ValueError(
                f"min_transmission must be in (0.0, 1.0], got {self.min_transmission}"
            )
        _validate_fields(self)


@dataclass
class ExecutionConfig:
    """Execution runtime configuration."""

    timeout_sec: int = 30
    max_workers: int = 4
    retries: int = 0
    clean_on_success: bool = False
    acqf_num_restarts: int = 10
    acqf_raw_samples: int = 1024
    acqf_maxiter: int = 200
    acqf_batch_limit: int = 5
    z_stop_m: float = 16.2
    z_loss_tolerance_m: float = 0.1
    # Reference policy: the reporting reference is fixed once from the initial design with
    # this fractional range offset (unless supplied explicitly); the acquisition reference
    # is recomputed each iteration from the selected observations with its own offset.
    reporting_reference_offset: float = 0.10
    acquisition_reference_offset: float = 0.05
    acquisition_reference_basis: str = "all_valid"
    # Simulation statuses that start a fresh attempt (bounded by ``retries``).
    retry_statuses: List[str] = field(default_factory=lambda: list(DEFAULT_RETRY_STATUSES))

    def validate(self) -> None:
        """Validate execution parameters."""
        _validate_fields(self, types_only=True)
        if self.timeout_sec <= 0:
            raise ValueError(f"timeout_sec must be positive, got {self.timeout_sec}")
        if self.max_workers <= 0:
            raise ValueError(f"max_workers must be positive, got {self.max_workers}")
        if self.retries < 0:
            raise ValueError(f"retries must be non-negative, got {self.retries}")
        if self.acqf_num_restarts <= 0:
            raise ValueError(f"acqf_num_restarts must be positive, got {self.acqf_num_restarts}")
        if self.acqf_raw_samples <= 0:
            raise ValueError(f"acqf_raw_samples must be positive, got {self.acqf_raw_samples}")
        _validate_fields(self)


@dataclass
class GpModelConfig:
    """Configuration for GP surrogate modeling and noise treatment."""

    covar_type: str = "matern52"
    noise_mode: str = "deterministic_fixed"  # "deterministic_fixed", "fixed", "inferred", or "measured_fixed"
    fixed_noise_variance: Optional[float] = None
    relative_noise_ratio: float = 1.0e-6
    min_noise_variance: float = 1.0e-24
    objective_noise_variances: Optional[List[float]] = None

    def validate(self) -> None:
        """Validate GP model config fields."""
        _validate_fields(self, types_only=True)
        if self.covar_type not in ("matern52", "rbf"):
            raise ValueError(f"Invalid covar_type '{self.covar_type}'. Must be 'matern52' or 'rbf'.")
        if self.noise_mode not in ("deterministic_fixed", "fixed", "inferred", "measured_fixed"):
            raise ValueError(
                f"Invalid noise_mode '{self.noise_mode}'. Must be 'deterministic_fixed', 'fixed', 'inferred', or 'measured_fixed'."
            )
        if self.fixed_noise_variance is not None and self.fixed_noise_variance <= 0:
            raise ValueError("fixed_noise_variance must be positive if provided.")
        if self.relative_noise_ratio <= 0:
            raise ValueError("relative_noise_ratio must be positive.")
        if self.min_noise_variance <= 0:
            raise ValueError("min_noise_variance must be positive.")
        if self.noise_mode == "inferred" and (self.fixed_noise_variance is not None or self.objective_noise_variances is not None):
            raise ValueError("inferred noise cannot accept explicit fixed noise.")
        _validate_fields(self)


@dataclass
class BenchmarkConfig:
    """Configuration for paired multi-seed benchmark campaigns."""

    algorithms: List[str] = field(default_factory=lambda: list(SUPPORTED_BENCHMARK_ALGORITHMS))
    seeds: List[int] = field(default_factory=lambda: list(range(42, 52)))
    total_eval_budget: int = 40
    n_sobol_init: int = 10
    batch_size: int = 4
    # Normalized physical reference per configured objective; None means 1.5 for each objective.
    reporting_ref_point: Optional[List[float]] = None
    constraint_profile: str = "nominal"
    output_dir: str = "results/publication_benchmark"

    def resolved_reporting_ref_point(self, objective_count: int) -> List[float]:
        """Normalized physical reference matching the configured objective count."""
        reference = [1.5] * objective_count if self.reporting_ref_point is None else list(self.reporting_ref_point)
        if len(reference) != objective_count:
            raise ValueError("Benchmark reporting reference must match configured objectives.")
        return reference

    def validate(self) -> None:
        """Validates benchmark configuration fields."""
        _validate_fields(self, types_only=True)
        if not self.algorithms or len(set(self.algorithms)) != len(self.algorithms):
            raise ValueError("Benchmark algorithms must be non-empty and unique.")
        for algo in self.algorithms:
            get_benchmark_algorithm(algo)
        if self.n_sobol_init < 1:
            raise ValueError("n_sobol_init must be >= 1.")
        if self.total_eval_budget <= self.n_sobol_init:
            raise ValueError("total_eval_budget must be greater than n_sobol_init.")
        if self.batch_size < 1:
            raise ValueError("batch_size must be >= 1.")
        if not self.seeds or len(set(self.seeds)) != len(self.seeds):
            raise ValueError("Benchmark seeds must be non-empty and unique.")
        if self.reporting_ref_point is not None and (not self.reporting_ref_point or not all(
            isinstance(v, (int, float)) and math.isfinite(v) and v > 0
            for v in self.reporting_ref_point
        )):
            raise ValueError("reporting_ref_point must contain finite positive normalized physical values.")
        _validate_fields(self)


@dataclass
class CampaignSettings:
    """Default campaign plan used by every entry point when an option is not given.

    Worker count comes from ``execution.max_workers``.
    """

    num_initial_samples: int = 16
    num_batches: int = 20
    batch_size: int = 8
    seed: int = 42
    acquisition: str = "qLogNEHVI"

    def validate(self) -> None:
        _validate_fields(self)


@dataclass
class ScalarizedCaseConfig:
    """One weighted-sum scalarization case of the Phase 1 suite."""

    label: str
    weights: List[float]
    seed_offset: int
    description: str = ""
    symbol: Optional[str] = None

    def validate(self) -> None:
        _validate_fields(self)


@dataclass
class MoboConfig:
    """Master configuration container for linac optimization."""

    version: str
    description: str
    design_variables: List[DesignVariableConfig]
    objectives: List[ObjectiveConfig]
    constraints: ConstraintsConfig
    name: Optional[str] = "mobo_200MeV"
    sensitivity_profiles: Dict[str, ConstraintsConfig] = field(default_factory=dict)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    model: GpModelConfig = field(default_factory=GpModelConfig)
    campaign: CampaignSettings = field(default_factory=CampaignSettings)
    # Named scalarization cases (weights in configured objective order); the suite seed of a
    # case is the base seed plus its stable seed_offset, independent of the cases selected.
    scalarized_cases: Dict[str, ScalarizedCaseConfig] = field(default_factory=dict)

    def validate(self) -> None:
        """Validate entire configuration system."""
        _validate_fields(self, types_only=True)
        if not self.design_variables:
            raise ValueError("No design_variables defined in MoboConfig.")
        if not self.objectives:
            raise ValueError("No objectives defined in MoboConfig.")

        var_names = set()
        astra_keys = set()
        for dv in self.design_variables:
            dv.validate()
            if dv.name in var_names:
                raise ValueError(f"Duplicate design variable name: '{dv.name}'")
            if dv.astra_key in astra_keys:
                raise ValueError(f"Duplicate ASTRA key: '{dv.astra_key}'")
            var_names.add(dv.name)
            astra_keys.add(dv.astra_key)

        obj_names = set()
        for obj in self.objectives:
            obj.validate()
            if obj.name in obj_names:
                raise ValueError(f"Duplicate objective name: '{obj.name}'")
            obj_names.add(obj.name)

        from mobo_linac.result_schema import ResultSchema
        ResultSchema.from_config(self)
        self.constraints.validate()
        for name, profile in self.sensitivity_profiles.items():
            profile.validate()

        self.execution.validate()
        self.model.validate()
        self.campaign.validate()
        if self.model.objective_noise_variances is not None and len(self.model.objective_noise_variances) != len(self.objectives):
            raise ValueError("objective_noise_variances must match the configured objective count.")
        offsets = set()
        for case_id, case in self.scalarized_cases.items():
            if not re.fullmatch(_IDENTIFIER, case_id):
                raise ValueError(f"Scalarized case id '{case_id}' must be an identifier.")
            case.validate()  # weight count is checked against objectives when a case is used
            if case.seed_offset in offsets:
                raise ValueError(f"Scalarized case '{case_id}' reuses a seed_offset.")
            offsets.add(case.seed_offset)
        _validate_fields(self)

    def get_constraint_profile(self, profile_name: str = "nominal") -> ConstraintsConfig:
        """Return a declared profile; nominal defaults to the main constraints."""
        if profile_name in self.sensitivity_profiles:
            return self.sensitivity_profiles[profile_name]
        if profile_name == "nominal":
            return self.constraints
        raise ValueError(f"Unknown constraint profile: {profile_name}")

    def get_parameter_bounds_tensor(self) -> torch.Tensor:
        """
        Returns design variable bounds as a (2, D) PyTorch double tensor.
        First row: lower bounds.
        Second row: upper bounds.
        """
        self.validate()
        lower = [dv.lower_bound for dv in self.design_variables]
        upper = [dv.upper_bound for dv in self.design_variables]
        bounds = torch.tensor([lower, upper], dtype=torch.double)
        return bounds

    def get_nominal_parameters(self) -> List[float]:
        """Returns nominal parameter values."""
        return [dv.nominal_value for dv in self.design_variables]

    def save_json(self, output_path: Union[str, Path]) -> Path:
        """Save configuration to JSON file."""
        self.validate()
        from mobo_linac.io.durable import atomic_json
        return atomic_json(output_path, asdict(self))

    def save_yaml(self, output_path: Union[str, Path]) -> Path:
        """Save configuration to YAML file."""
        self.validate()
        from mobo_linac.io.durable import atomic_write_text
        return atomic_write_text(output_path, yaml.dump(asdict(self), default_flow_style=False))


# The dataclass annotations/defaults and these constraints define both runtime
# field validation and exported schema/docs. Relational checks remain in validate().
_IDENTIFIER = r"^[A-Za-z_][A-Za-z0-9_]*$"
FIELD_RULES = {
    "DesignVariableConfig": {
        "name": {"minLength": 1}, "astra_key": {"minLength": 1},
        "ratio": {"minimum": 0}, "coupled_targets": {"items": {"type": "string", "minLength": 1}, "uniqueItems": True},
    },
    "ObjectiveConfig": {
        "name": {"pattern": _IDENTIFIER}, "explicit_name": {"pattern": _IDENTIFIER},
        "aliases": {"items": {"type": "string", "pattern": _IDENTIFIER}, "uniqueItems": True},
        "physical_direction": {"enum": ["minimize", "maximize"]}, "model_sign": {"enum": [-1, 1]},
        "reporting_scale": {"exclusiveMinimum": 0},
    },
    "ConstraintsConfig": {
        **{name: {"exclusiveMinimum": 0} for name in get_type_hints(ConstraintsConfig)},
        "min_transmission": {"exclusiveMinimum": 0, "maximum": 1},
    },
    "ExecutionConfig": {
        **{name: {"minimum": 1} for name in ("timeout_sec", "max_workers", "acqf_num_restarts", "acqf_raw_samples", "acqf_maxiter", "acqf_batch_limit")},
        "retries": {"minimum": 0}, "z_stop_m": {"exclusiveMinimum": 0},
        "z_loss_tolerance_m": {"minimum": 0},
        "reporting_reference_offset": {"minimum": 0}, "acquisition_reference_offset": {"minimum": 0},
        "acquisition_reference_basis": {"enum": ["all_valid", "feasible"]},
        "retry_statuses": {"uniqueItems": True, "items": {"type": "string", "enum": [
            status.value for status in SimulationStatus if status is not SimulationStatus.SUCCESS]}},
    },
    "GpModelConfig": {
        "covar_type": {"enum": ["matern52", "rbf"]},
        "noise_mode": {"enum": ["deterministic_fixed", "fixed", "inferred", "measured_fixed"]},
        **{name: {"exclusiveMinimum": 0} for name in ("fixed_noise_variance", "relative_noise_ratio", "min_noise_variance")},
        "objective_noise_variances": {"minItems": 1, "items": {"type": "number", "exclusiveMinimum": 0}},
    },
    "BenchmarkConfig": {
        "algorithms": {"minItems": 1, "uniqueItems": True, "items": {"type": "string", "enum": list(SUPPORTED_BENCHMARK_ALGORITHMS)}},
        "seeds": {"minItems": 1, "uniqueItems": True, "items": {"type": "integer", "minimum": 0, "maximum": 2**32 - 1}},
        **{name: {"minimum": 1} for name in ("total_eval_budget", "n_sobol_init", "batch_size")},
        "reporting_ref_point": {"minItems": 1, "items": {"type": "number", "exclusiveMinimum": 0}},
        "constraint_profile": {"minLength": 1}, "output_dir": {"minLength": 1},
    },
    "CampaignSettings": {
        **{name: {"minimum": 1} for name in ("num_initial_samples", "batch_size")},
        "num_batches": {"minimum": 0}, "seed": {"minimum": 0, "maximum": 2**32 - 1},
        "acquisition": {"enum": ["qLogNEHVI", "qLogEHVI", "qEHVI", "qNEHVI"]},
    },
    "ScalarizedCaseConfig": {
        "label": {"minLength": 1}, "seed_offset": {"minimum": 0},
        "weights": {"minItems": 1, "items": {"type": "number", "minimum": 0}},
    },
    "MoboConfig": {"version": {"minLength": 1}, "design_variables": {"minItems": 1}, "objectives": {"minItems": 1}},
}


def _type_schema(annotation):
    origin, args = get_origin(annotation), get_args(annotation)
    if origin is Union:
        base = _type_schema(next(arg for arg in args if arg is not type(None)))
        base["type"] = [base["type"], "null"]
        return base
    if origin is list:
        return {"type": "array", "items": _type_schema(args[0])}
    if origin is dict:
        return {"type": "object", "additionalProperties": _type_schema(args[1])}
    if is_dataclass(annotation):
        return _dataclass_schema(annotation)
    return {"type": {str: "string", float: "number", int: "integer", bool: "boolean"}[annotation]}


def _dataclass_schema(cls):
    hints = get_type_hints(cls)
    properties, required = {}, []
    for item in fields(cls):
        definition = _type_schema(hints[item.name])
        definition.update(deepcopy(FIELD_RULES.get(cls.__name__, {}).get(item.name, {})))
        if item.default is not MISSING:
            definition["default"] = item.default
        elif item.default_factory is not MISSING:
            default = item.default_factory()
            definition["default"] = asdict(default) if is_dataclass(default) else default
        else:
            required.append(item.name)
        properties[item.name] = definition
    return {"type": "object", "properties": properties, "required": required, "additionalProperties": False}


def _validate_value(value, definition, path):
    types = definition["type"]
    types = types if isinstance(types, list) else [types]
    if value is None and "null" in types:
        return
    matches = {
        "string": isinstance(value, str), "boolean": isinstance(value, bool),
        "integer": type(value) is int,
        "number": isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value),
        "array": isinstance(value, list), "object": isinstance(value, dict), "null": value is None,
    }
    if not any(matches[t] for t in types):
        raise ValueError(f"{path} must have type {types} with finite numeric values.")
    if "enum" in definition and value not in definition["enum"]:
        raise ValueError(f"{path} must be one of {definition['enum']}.")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        for key, invalid in (("minimum", lambda limit: value < limit), ("maximum", lambda limit: value > limit),
                             ("exclusiveMinimum", lambda limit: value <= limit)):
            if key in definition and invalid(definition[key]):
                raise ValueError(f"{path} violates {key}={definition[key]}.")
    if isinstance(value, str):
        if len(value) < definition.get("minLength", 0) or ("pattern" in definition and not re.fullmatch(definition["pattern"], value)):
            raise ValueError(f"{path} is an invalid identifier/string.")
    if isinstance(value, list):
        if len(value) < definition.get("minItems", 0) or len(value) > definition.get("maxItems", math.inf):
            raise ValueError(f"{path} has invalid array length.")
        if definition.get("uniqueItems") and any(value[i] in value[:i] for i in range(len(value))):
            raise ValueError(f"{path} must contain unique values.")
        for index, item in enumerate(value):
            _validate_value(item, definition["items"], f"{path}[{index}]")
    if isinstance(value, dict):
        properties = definition.get("properties", {})
        missing = set(definition.get("required", ())) - value.keys()
        if missing:
            raise ValueError(f"{path} missing required fields: {sorted(missing)}.")
        for name, item in value.items():
            rule = properties.get(name, definition.get("additionalProperties", False))
            if rule is False:
                raise ValueError(f"Unknown configuration field: {path}.{name}.")
            _validate_value(item, rule, f"{path}.{name}")


def _validate_fields(config, types_only=False):
    definition = _dataclass_schema(type(config))
    def types(definition):
        result = {key: value for key, value in definition.items() if key in ("type", "required", "additionalProperties")}
        if "properties" in definition:
            result["properties"] = {name: types(item) for name, item in definition["properties"].items()}
        if "items" in definition:
            result["items"] = types(definition["items"])
        if isinstance(result.get("additionalProperties"), dict):
            result["additionalProperties"] = types(result["additionalProperties"])
        return result
    _validate_value(asdict(config), types(definition) if types_only else definition, type(config).__name__)


def export_config_schema(output_path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    """Export draft-07 field schema; relational checks are described explicitly."""
    schema = {"$schema": "http://json-schema.org/draft-07/schema#", "title": "MoboConfig",
              "description": "Finite values; validate() also checks ordered nondegenerate bounds, objective signs/aliases, and noise-vector dimensions.",
              **_dataclass_schema(MoboConfig), "definitions": {"BenchmarkConfig": _dataclass_schema(BenchmarkConfig)}}
    if output_path is not None:
        from mobo_linac.io.durable import atomic_json
        atomic_json(output_path, schema)
    return schema


def generate_config_markdown_docs(config: MoboConfig) -> str:
    """
    Generates comprehensive GitHub-flavored Markdown documentation from a MoboConfig instance.
    """
    config.validate()
    lines: List[str] = []
    lines.append(f"# Linac MOBO Configuration: `{config.name}` (v{config.version})\n")
    if config.description:
        lines.append(f"> {config.description}\n")

    lines.append("## 1. Design Variables (Decision Space)\n")
    lines.append("| Variable Name | ASTRA Input Key | Nominal Value | Search Ratio | Bounds [Min, Max] | Unit | Coupled? |")
    lines.append("| :--- | :--- | :---: | :---: | :---: | :---: | :---: |")
    for dv in config.design_variables:
        coupled_str = f"Yes ({', '.join(dv.coupled_targets)})" if dv.is_coupled and dv.coupled_targets else "No"
        lines.append(
            f"| `{dv.name}` | `{dv.astra_key}` | {dv.nominal_value} | {dv.ratio} | [{dv.lower_bound}, {dv.upper_bound}] | {dv.unit} | {coupled_str} |"
        )
    lines.append("")

    lines.append("## 2. Optimization Objectives\n")
    lines.append("| Objective | Explicit Name | Unit | Physical Goal | BoTorch Model Sign |")
    lines.append("| :--- | :--- | :---: | :---: | :---: |")
    for obj in config.objectives:
        lines.append(
            f"| `{obj.name}` | {obj.explicit_name} | {obj.unit} | {obj.physical_direction.capitalize()} | `{obj.model_sign}` |"
        )
    lines.append("")

    lines.append("## 3. Physical Beam & Diagnostic Constraints\n")
    lines.append("| Diagnostic Parameter | Threshold Condition | Target Unit |")
    lines.append("| :--- | :---: | :---: |")
    c = config.constraints
    lines.append(f"| Horizontal Beam Size ($\sigma_x$) | $\le {c.max_sigma_x_m*1e3:.2f}$ | mm |")
    lines.append(f"| Vertical Beam Size ($\sigma_y$) | $\le {c.max_sigma_y_m*1e3:.2f}$ | mm |")
    lines.append(f"| Horizontal Angular Spread ($\sigma_{{x'}}$) | $\le {c.max_sigma_xp_rad*1e3:.2f}$ | mrad |")
    lines.append(f"| Vertical Angular Spread ($\sigma_{{y'}}$) | $\le {c.max_sigma_yp_rad*1e3:.2f}$ | mrad |")
    lines.append(f"| Longitudinal Bunch Length ($\sigma_z$) | $\le {c.max_sigma_z_m*1e3:.2f}$ | mm |")
    lines.append(f"| Mean Kinetic Energy ($E_k$) | $[{c.min_mean_kinetic_energy_eV*1e-6:.1f}, {c.max_mean_kinetic_energy_eV*1e-6:.1f}]$ | MeV |")
    lines.append(f"| Beam Transmission Fraction ($T$) | $\ge {c.min_transmission*100.0:.1f}\\%$ | % |")
    lines.append("")

    lines.append("## 4. Execution & Surrogate Model Runtime\n")
    lines.append(f"- **ASTRA Timeout**: `{config.execution.timeout_sec} s`")
    lines.append(f"- **Parallel Workers**: `{config.execution.max_workers}`")
    lines.append(f"- **GP Covariance Kernel**: `{config.model.covar_type}`")
    lines.append(f"- **GP Noise Mode**: `{config.model.noise_mode}`")
    lines.append(f"- **Acquisition Optimization Restarts / Raw Samples**: `{config.execution.acqf_num_restarts}` / `{config.execution.acqf_raw_samples}`")
    lines.append("")

    lines.append("## 5. Supported Configuration Fields\n")
    lines.append("Bounds must be finite and strictly increasing. Fixed machine settings belong in the ASTRA template, outside the optimization vector.\n")
    lines.append("| Field | Type | Required | Default | Field constraints |")
    lines.append("| :--- | :--- | :--- | :--- | :--- |")
    def document(definition, prefix=""):
        for name, item in definition.get("properties", {}).items():
            path = prefix + name
            constraints = {key: item[key] for key in ("minimum", "exclusiveMinimum", "maximum", "enum", "pattern", "minLength", "minItems", "maxItems", "uniqueItems") if key in item}
            if "items" in item and "properties" not in item["items"]:
                constraints["items"] = item["items"]
            default = json.dumps(item["default"]) if "default" in item else "—"
            lines.append(f"| `{path}` | `{item['type']}` | {name in definition.get('required', [])} | `{default}` | `{json.dumps(constraints)}` |")
            nested = item.get("items", item)
            document(nested, path + ("[]." if "items" in item else "."))
            if isinstance(item.get("additionalProperties"), dict):
                document(item["additionalProperties"], path + ".<profile>.")
    document(export_config_schema())
    document(_dataclass_schema(BenchmarkConfig), "benchmark.")
    return "\n".join(lines)


DEFAULT_CONFIG_NAMES = ("publication_200MeV.yaml", "publication.yaml", "mobo_200MeV.yaml")


def resolve_config_path(config_path: Optional[Union[str, Path]] = None, *, default_names=DEFAULT_CONFIG_NAMES) -> Path:
    """Explicit paths never fall back. Omitted defaults search cwd then repository."""
    if config_path is not None:
        path = Path(config_path).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Requested configuration file not found: {path}")
        return path
    roots = (Path.cwd() / "configs", Path(__file__).resolve().parents[2] / "configs")
    for root in dict.fromkeys(roots):
        for name in default_names:
            path = root / name
            if path.is_file():
                return path.resolve()
    raise FileNotFoundError("No default configuration found; supply an explicit --config path.")


class _ConfigYamlLoader(yaml.SafeLoader):
    pass


_ConfigYamlLoader.add_implicit_resolver(
    "tag:yaml.org,2002:float",
    re.compile(r"^[-+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)[eE][-+]?[0-9]+$"),
    list("-+0123456789."),
)


def load_config(config_path: Optional[Union[str, Path]] = None) -> MoboConfig:
    """Load YAML/JSON through one resolver and record the actual source separately."""
    path = resolve_config_path(config_path)
    with path.open(encoding="utf-8") as stream:
        data = yaml.load(stream, Loader=_ConfigYamlLoader)
    if not isinstance(data, dict):
        raise ValueError(f"Configuration at {path} must contain a top-level dictionary.")
    config = config_from_dict(data, default_name=path.stem)
    config.resolved_path = path  # provenance, deliberately outside serialized scientific fields
    return config


def config_from_dict(data: Dict[str, Any], default_name: str = "mobo_200MeV") -> MoboConfig:
    """Reconstruct saved YAML/JSON/checkpoint configuration through the same validators."""
    if not isinstance(data, dict):
        raise ValueError("Saved configuration must be a dictionary.")
    _validate_value(data, _dataclass_schema(MoboConfig), "MoboConfig")
    design_vars = [DesignVariableConfig(**dv) for dv in data.get("design_variables", [])]
    objs = [ObjectiveConfig(**obj) for obj in data.get("objectives", [])]
    constraints = ConstraintsConfig(**data.get("constraints", {}))

    sens_profiles = {}
    if "sensitivity_profiles" in data and isinstance(data["sensitivity_profiles"], dict):
        for pname, pdata in data["sensitivity_profiles"].items():
            sens_profiles[pname] = ConstraintsConfig(**pdata)

    campaign = CampaignSettings(**(data.get("campaign") or {}))
    cases = {case_id: ScalarizedCaseConfig(**case) for case_id, case in (data.get("scalarized_cases") or {}).items()}
    execution = ExecutionConfig(**data.get("execution", {}))
    model_cfg = GpModelConfig(**data.get("model", {}))

    config = MoboConfig(
        name=data.get("name", default_name),
        version=data["version"],
        description=data["description"],
        design_variables=design_vars,
        objectives=objs,
        constraints=constraints,
        sensitivity_profiles=sens_profiles,
        execution=execution,
        model=model_cfg,
        scalarized_cases=cases,
        campaign=campaign,
    )
    config.validate()
    return config


def normalize_scalar_weights(weights, objective_count):
    """Validate dimensions/finite weights and normalize without sum overflow."""
    if type(objective_count) is not int or objective_count < 1:
        raise ValueError("Scalar weights require at least one objective.")
    if weights is None:
        return torch.full((objective_count,), 1.0 / objective_count, dtype=torch.double)
    if any(isinstance(value, bool) for value in weights):
        raise ValueError("Scalar weights must be numeric, not boolean.")
    values = torch.as_tensor(weights, dtype=torch.double)
    if (values.shape != (objective_count,) or not torch.isfinite(values).all()
            or (values < 0).any() or not (values > 0).any()):
        raise ValueError("Scalar weights must match objectives and be finite, nonnegative, with positive sum.")
    scaled = values / values.max()
    return scaled / scaled.sum()


def resolve_campaign_options(config: "MoboConfig", **requested):
    """Fill omitted (None) campaign options from the configuration, the single default source."""
    defaults = asdict(config.campaign)
    resolved = {name: requested.get(name) if requested.get(name) is not None else value
                for name, value in defaults.items()}
    workers = requested.get("num_workers")
    resolved["num_workers"] = workers if workers is not None else config.execution.max_workers
    return resolved


def validate_campaign_options(*, num_initial_samples, num_batches, batch_size, num_workers=None,
                              seed=42, acq_type="qLogNEHVI", optimization_mode="unconstrained_mobo",
                              total_eval_budget=None):
    """Validate orchestration options before any campaign side effects."""
    for name, value, minimum in (("num_initial_samples", num_initial_samples, 1),
                                 ("num_batches", num_batches, 0), ("batch_size", batch_size, 1),
                                 ("seed", seed, 0)):
        if type(value) is not int or value < minimum:
            raise ValueError(f"{name} must be an integer >= {minimum}.")
    if seed >= 2**32:
        raise ValueError("seed must be less than 2**32.")
    if num_workers is not None and (type(num_workers) is not int or num_workers < 1):
        raise ValueError("num_workers must be a positive integer.")
    if total_eval_budget is not None and (type(total_eval_budget) is not int or total_eval_budget <= num_initial_samples):
        raise ValueError("total_eval_budget must exceed positive initial samples.")
    if optimization_mode not in ("scalarized_bo", "constrained_mobo", "unconstrained_mobo"):
        raise ValueError(f"Unsupported optimization_mode: {optimization_mode}")
    if acq_type not in ("qLogNEHVI", "qLogEHVI", "qEHVI", "qNEHVI", "qLogNEI"):
        raise ValueError(f"Unsupported acquisition: {acq_type}")
    if optimization_mode == "scalarized_bo" and acq_type not in ("qLogNEI", "qLogNEHVI"):
        raise ValueError("scalarized_bo uses qLogNEI; other MOBO acquisitions are unsupported.")
    if acq_type == "qLogNEI" and optimization_mode != "scalarized_bo":
        raise ValueError("qLogNEI requires scalarized_bo optimization mode.")


def validate_evaluation_settings(parameters, config, namelist_overrides=None, source_settings=None):
    """Validate finite machine/source requests before reserving simulation attempts."""
    if isinstance(config, MoboConfig):
        count = len(config.design_variables)
    elif isinstance(config, dict) and "design_variables" in config:
        count = len(config["design_variables"])
    else:
        raise TypeError("A configuration defining design_variables is required.")
    if len(parameters) != count:
        raise ValueError("Parameter vector length must match configured design variables.")
    if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) for value in parameters):
        raise ValueError("Design parameters must be finite numbers.")
    source_settings = {} if source_settings is None else source_settings
    known_sources = {"bunch_charge_scale", "laser_spot_scale", "laser_pulse_duration_scale"}
    if not isinstance(source_settings, dict) or set(source_settings) - known_sources:
        raise ValueError("Unknown source settings; use the supported charge/laser scale names.")
    for key, value in source_settings.items():
        _validate_value(value, {"type": "number", "exclusiveMinimum": 0}, f"source_settings.{key}")
    if namelist_overrides is not None:
        if not isinstance(namelist_overrides, dict):
            raise ValueError("namelist_overrides must be a dictionary.")
        for key, value in namelist_overrides.items():
            if not isinstance(key, str) or not re.fullmatch(r"[A-Za-z_]\w*:[A-Za-z_]\w*(?:\([0-9, ]+\))?", key):
                raise ValueError(f"Invalid namelist override key: {key}")
            values = value if isinstance(value, (list, tuple)) else [value]
            if not values or any(not isinstance(item, (str, bool, int, float)) or
                                 (isinstance(item, (int, float)) and not math.isfinite(item)) for item in values):
                raise ValueError(f"Namelist override {key} must contain finite numeric, boolean, or string values.")
