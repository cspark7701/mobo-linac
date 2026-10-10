"""
Centralized Configuration Module for mobo_linac.

Defines declarative schemas, strict physical validation, JSON Schema exporter,
and Markdown documentation generator for accelerator Bayesian optimization.
"""

from dataclasses import MISSING, asdict, dataclass, field, fields, is_dataclass, make_dataclass, replace
from functools import lru_cache
import json
import math
import re
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional, Union, get_args, get_origin, get_type_hints
import torch
import yaml

from mobo_linac.campaign_options import MULTIOBJECTIVE_ACQUISITIONS
from mobo_linac.diagnostics import DIAGNOSTIC_CHANNELS
from mobo_linac.perturbations import PerturbationSpecification
from mobo_linac.result_schema import ResultSchema
from mobo_linac.utils.durable import atomic_json, atomic_write_text
from mobo_linac.status import DEFAULT_RETRY_STATUSES, SimulationStatus
from mobo_linac.benchmark_algorithms import (
    SUPPORTED_BENCHMARK_ALGORITHMS,
    get_benchmark_algorithm,
)

# Field metadata marking display-only settings (labels, units shown in figures/tables).
DISPLAY = {"display": True}


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
    # Display label (LaTeX allowed) for figures and tables; not a scientific setting.
    label: Optional[str] = field(default=None, metadata=DISPLAY)

    def validate(self) -> None:
        _validate_fields(self)
        self.check_relations()

    def check_relations(self) -> None:
        """Bounds ordering and coupling rules (field types and ranges come from FIELD_RULES)."""
        if self.lower_bound >= self.upper_bound:
            raise ValueError(
                f"Invalid bounds for design variable '{self.name}': "
                f"lower_bound ({self.lower_bound}) >= upper_bound ({self.upper_bound}); fixed variables must be removed from the optimization vector"
            )
        if self.is_coupled and not self.coupled_targets:
            raise ValueError(
                f"Design variable '{self.name}' is marked coupled but has no coupled_targets."
            )


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
    label: Optional[str] = field(default=None, metadata=DISPLAY)
    display_unit: Optional[str] = field(default=None, metadata=DISPLAY)
    # Design goal in physical units for reports (knee target distance); not an optimization setting.
    target: Optional[float] = field(default=None, metadata=DISPLAY)

    def validate(self) -> None:
        _validate_fields(self)
        self.check_relations()

    def check_relations(self) -> None:
        """Direction/sign agreement (names, enums and scale ranges come from FIELD_RULES)."""
        expected = -1 if self.physical_direction == "minimize" else 1
        if self.model_sign != expected:
            raise ValueError(f"{self.physical_direction.capitalize()} objective '{self.name}' must have "
                             f"model_sign = {expected}.")


def _constraints_check_relations(self) -> None:
    """Every two-sided channel needs lower <= upper (ranges come from the channel rules)."""
    for channel in DIAGNOSTIC_CHANNELS:
        lower, upper = channel.bounds(self)
        if lower is not None and upper is not None and lower > upper:
            raise ValueError(f"Invalid {channel.description.lower() or channel.name} constraints: "
                             f"{channel.lower_attribute} ({lower}) > {channel.upper_attribute} ({upper}).")


def _constraints_validate(self) -> None:
    _validate_fields(self)
    self.check_relations()


# One field per configurable channel bound, generated from the diagnostic channel registry:
# a new constraint channel needs only a registry entry (and, optionally, YAML values).
ConstraintsConfig = make_dataclass(
    "ConstraintsConfig",
    [(attribute, float, field(default=default)) for channel in DIAGNOSTIC_CHANNELS
     for attribute, default, _ in channel.bound_fields()],
    namespace={"__doc__": "Constraint bounds of the diagnostic channels (generated from the channel registry).",
               "validate": _constraints_validate, "check_relations": _constraints_check_relations},
)
ConstraintsConfig.__module__ = __name__


@dataclass
class TrackingConfig:
    """Lattice exit plane: tracking must reach z_stop_m - z_loss_tolerance_m to count as transported."""

    z_stop_m: float = 16.2
    z_loss_tolerance_m: float = 0.1

    def validate(self) -> None:
        _validate_fields(self)

    def check_relations(self) -> None:
        if self.z_loss_tolerance_m >= self.z_stop_m:
            raise ValueError("tracking.z_loss_tolerance_m must be smaller than tracking.z_stop_m.")


@dataclass
class SimulationConfig:
    """Beam-dynamics code inputs: template directory, input template, static files, executable.

    ``load_config`` resolves relative ``template_dir``/``executable`` against the configuration
    file's directory and stores them absolute; the executable is otherwise found through
    ``$ASTRA_BIN`` and then ``PATH``.
    """

    template_dir: Optional[str] = None
    input_template: str = "astra.in"
    static_files: List[str] = field(default_factory=list)
    executable: Optional[str] = None

    def validate(self) -> None:
        _validate_fields(self)

    def check_relations(self) -> None:
        if any(Path(name).is_absolute() or ".." in Path(name).parts for name in self.static_files):
            raise ValueError("simulation.static_files must be names inside simulation.template_dir.")

    def resolved_against(self, base: Path) -> "SimulationConfig":
        def absolute(value):
            if value is None:
                return None
            path = Path(value).expanduser()
            return str((path if path.is_absolute() else base / path).resolve())
        return replace(self, template_dir=absolute(self.template_dir), executable=absolute(self.executable))


@dataclass
class ExecutionConfig:
    """Execution runtime configuration."""

    timeout_sec: int = 2000  # seconds per ASTRA attempt; one run takes about 280 s on the reference host
    max_workers: int = 4
    retries: int = 0
    clean_on_success: bool = False
    acqf_num_restarts: int = 10
    acqf_raw_samples: int = 1024
    acqf_maxiter: int = 200
    acqf_batch_limit: int = 5
    # Reduced-budget fallback tiers of the acquisition optimizer and the CUDA batch limit
    # (recorded in proposal metadata).
    acqf_retry_maxiter: int = 100
    acqf_retry_restart_divisor: int = 2
    acqf_retry_min_restarts: int = 2
    acqf_retry_raw_samples_divisor: int = 4
    acqf_retry_min_raw_samples: int = 32
    acqf_cuda_batch_limit: int = 1
    # Reference policy: the reporting reference is fixed once from the initial design with
    # this fractional range offset (unless supplied explicitly); the acquisition reference
    # is recomputed each iteration from the selected observations with its own offset.
    reporting_reference_offset: float = 0.10
    acquisition_reference_offset: float = 0.05
    acquisition_reference_basis: str = "all_valid"
    # Simulation statuses that start a fresh attempt (bounded by ``retries``).
    retry_statuses: List[str] = field(default_factory=lambda: list(DEFAULT_RETRY_STATUSES))

    def validate(self) -> None:
        _validate_fields(self)

    def check_relations(self) -> None:
        """All execution limits are field rules."""


@dataclass
class GpModelConfig:
    """Configuration for GP surrogate modeling and noise treatment."""

    covar_type: str = "matern52"
    noise_mode: str = "deterministic_fixed"  # "deterministic_fixed", "inferred", or "measured_fixed"
    fixed_noise_variance: Optional[float] = None
    relative_noise_ratio: float = 1.0e-6
    min_noise_variance: float = 1.0e-24
    objective_noise_variances: Optional[List[float]] = None

    def validate(self) -> None:
        _validate_fields(self)
        self.check_relations()

    def check_relations(self) -> None:
        if self.noise_mode == "inferred" and (self.fixed_noise_variance is not None or self.objective_noise_variances is not None):
            raise ValueError("inferred noise cannot accept explicit fixed noise.")


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
        # Algorithm names first: the registry explains unimplemented/unknown algorithms.
        for algo in self.algorithms if isinstance(self.algorithms, list) else []:
            get_benchmark_algorithm(algo)
        _validate_fields(self)
        self.check_relations()

    def check_relations(self) -> None:
        for algo in self.algorithms:
            get_benchmark_algorithm(algo)
        if self.total_eval_budget <= self.n_sobol_init:
            raise ValueError("total_eval_budget must be greater than n_sobol_init.")


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

    def check_relations(self) -> None:
        """All campaign defaults are field rules."""


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

    def check_relations(self) -> None:
        """Weight count is checked against objectives when a case is used."""


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
    tracking: TrackingConfig = field(default_factory=TrackingConfig)
    simulation: SimulationConfig = field(default_factory=SimulationConfig)
    # Optional campaign-family settings: benchmark defaults and the robustness perturbation
    # specification (validated against the design variables when present).
    benchmark: Optional[BenchmarkConfig] = None
    perturbations: Optional[Dict[str, Any]] = None
    # Provenance, not a scientific field: the file this configuration was loaded from.
    source_path: ClassVar[Optional[Path]] = None

    def validate(self) -> None:
        """Validate every field once (whole tree), then the relational rules."""
        _validate_fields(self)
        self.check_relations()

    def check_relations(self) -> None:
        """Cross-field rules not expressible as field schema rules."""
        for section in [*self.design_variables, *self.objectives, self.constraints,
                        *self.sensitivity_profiles.values(), self.execution, self.model, self.campaign,
                        self.tracking, self.simulation, *self.scalarized_cases.values(),
                        *([self.benchmark] if self.benchmark is not None else [])]:
            section.check_relations()
        for kind, names in (("design variable name", [dv.name for dv in self.design_variables]),
                            ("ASTRA key", [dv.astra_key for dv in self.design_variables]),
                            ("objective name", [obj.name for obj in self.objectives])):
            duplicates = sorted({name for name in names if names.count(name) > 1})
            if duplicates:
                raise ValueError(f"Duplicate {kind}: '{duplicates[0]}'")
        ResultSchema.from_config(self)
        if "nominal" in self.sensitivity_profiles:
            raise ValueError("The nominal constraint profile is the top-level constraints section; "
                             "do not redeclare it in sensitivity_profiles.")
        if self.model.objective_noise_variances is not None and len(self.model.objective_noise_variances) != len(self.objectives):
            raise ValueError("objective_noise_variances must match the configured objective count.")
        offsets = set()
        for case_id, case in self.scalarized_cases.items():
            if not re.fullmatch(_IDENTIFIER, case_id):
                raise ValueError(f"Scalarized case id '{case_id}' must be an identifier.")
            if case.seed_offset in offsets:
                raise ValueError(f"Scalarized case '{case_id}' reuses a seed_offset.")
            offsets.add(case.seed_offset)
        if self.benchmark is not None:
            self.get_constraint_profile(self.benchmark.constraint_profile)
            self.benchmark.resolved_reporting_ref_point(len(self.objectives))
        if self.perturbations is not None:
            PerturbationSpecification.from_dict(self.perturbations).validate_for(self)

    def scientific_dict(self) -> Dict[str, Any]:
        """Serialized configuration without display-only metadata (for compatibility checks)."""
        return _strip_display(self)

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
        return atomic_json(output_path, asdict(self))

    def save_yaml(self, output_path: Union[str, Path]) -> Path:
        """Save configuration to YAML file."""
        self.validate()
        return atomic_write_text(output_path, yaml.dump(asdict(self), default_flow_style=False))


def _strip_display(value):
    if is_dataclass(value):
        return {item.name: _strip_display(getattr(value, item.name)) for item in fields(value)
                if not item.metadata.get("display")}
    if isinstance(value, list):
        return [_strip_display(item) for item in value]
    if isinstance(value, dict):
        return {key: _strip_display(item) for key, item in value.items()}
    return deepcopy(value)


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
        "reporting_scale": {"exclusiveMinimum": 0}, "target": {"exclusiveMinimum": 0},
    },
    "ConstraintsConfig": {attribute: rule for channel in DIAGNOSTIC_CHANNELS
                          for attribute, _, rule in channel.bound_fields()},
    "TrackingConfig": {"z_stop_m": {"exclusiveMinimum": 0}, "z_loss_tolerance_m": {"minimum": 0}},
    "SimulationConfig": {"template_dir": {"minLength": 1}, "input_template": {"minLength": 1},
                         "static_files": {"uniqueItems": True, "items": {"type": "string", "minLength": 1}},
                         "executable": {"minLength": 1}},
    "ExecutionConfig": {
        **{name: {"minimum": 1} for name in ("timeout_sec", "max_workers", "acqf_num_restarts", "acqf_raw_samples",
                                             "acqf_maxiter", "acqf_batch_limit", "acqf_retry_maxiter",
                                             "acqf_retry_restart_divisor", "acqf_retry_min_restarts",
                                             "acqf_retry_raw_samples_divisor", "acqf_retry_min_raw_samples",
                                             "acqf_cuda_batch_limit")},
        "retries": {"minimum": 0},
        "reporting_reference_offset": {"minimum": 0}, "acquisition_reference_offset": {"minimum": 0},
        "acquisition_reference_basis": {"enum": ["all_valid", "feasible"]},

        "retry_statuses": {"uniqueItems": True, "items": {"type": "string", "enum": [
            status.value for status in SimulationStatus if status is not SimulationStatus.SUCCESS]}},
    },
    "GpModelConfig": {
        "covar_type": {"enum": ["matern52", "rbf"]},
        "noise_mode": {"enum": ["deterministic_fixed", "inferred", "measured_fixed"]},
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
        "acquisition": {"enum": list(MULTIOBJECTIVE_ACQUISITIONS)},
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
        if args[1] is Any:  # free-form section validated by its own domain parser
            return {"type": "object"}
        return {"type": "object", "additionalProperties": _type_schema(args[1])}
    if is_dataclass(annotation):
        return deepcopy(_dataclass_schema(annotation))
    return {"type": {str: "string", float: "number", int: "integer", bool: "boolean"}[annotation]}


@lru_cache(maxsize=None)
def _dataclass_schema(cls):
    """Field schema of a configuration dataclass (cached; treat the result as read-only)."""
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
    if isinstance(value, dict) and ("properties" in definition or "additionalProperties" in definition):
        properties = definition.get("properties", {})
        missing = set(definition.get("required", ())) - value.keys()
        if missing:
            raise ValueError(f"{path} missing required fields: {sorted(missing)}.")
        for name, item in value.items():
            rule = properties.get(name, definition.get("additionalProperties", False))
            if rule is False:
                raise ValueError(f"Unknown configuration field: {path}.{name}.")
            _validate_value(item, rule, f"{path}.{name}")


def _validate_fields(config):
    """Check every field of a configuration object (and nested sections) against the schema."""
    _validate_value(asdict(config), _dataclass_schema(type(config)), type(config).__name__)


def export_config_schema(output_path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    """Export draft-07 field schema; relational checks are described explicitly."""
    schema = deepcopy({"$schema": "http://json-schema.org/draft-07/schema#", "title": "MoboConfig",
              "description": "Finite values; validate() also checks ordered nondegenerate bounds, objective signs/aliases, and noise-vector dimensions.",
              **_dataclass_schema(MoboConfig), "definitions": {"BenchmarkConfig": _dataclass_schema(BenchmarkConfig)}})
    if output_path is not None:
        atomic_json(output_path, schema)
    return schema


def _constraint_rows(constraints) -> List[str]:
    rows = []
    for channel in DIAGNOSTIC_CHANNELS:
        lower, upper = (None if bound is None else bound / channel.display_scale for bound in channel.bounds(constraints))
        if lower is not None and upper is not None:
            condition = f"$[{lower:.4g}, {upper:.4g}]$"
        elif upper is not None:
            condition = rf"$\le {upper:.4g}$"
        else:
            condition = rf"$\ge {lower:.4g}$"
        rows.append(f"| {channel.description} ({channel.label}) | {condition} | {channel.display_unit} |")
    return rows


def generate_config_markdown_docs(config: MoboConfig) -> str:
    """
    Generates comprehensive GitHub-flavored Markdown documentation from a MoboConfig instance.
    """
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
    lines.extend(_constraint_rows(config.constraints))
    lines.append("")

    lines.append("## 4. Execution & Surrogate Model Runtime\n")
    lines.append(f"- **ASTRA Timeout**: `{config.execution.timeout_sec} s`")
    lines.append(f"- **Parallel Workers**: `{config.execution.max_workers}`")
    lines.append(f"- **Exit Plane**: `{config.tracking.z_stop_m} m` (loss tolerance `{config.tracking.z_loss_tolerance_m} m`)")
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


DEFAULT_CONFIG_NAMES = ("publication_200MeV.yaml", "mobo_200MeV.yaml")


def resolve_config_path(config_path: Optional[Union[str, Path]] = None, *, default_names=DEFAULT_CONFIG_NAMES) -> Path:
    """Explicit paths never fall back. Omitted defaults search ``./configs``, the configurations
    installed with the package (``<prefix>/share/mobo-linac/configs``), then a source checkout."""
    if config_path is not None:
        path = Path(config_path).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Requested configuration file not found: {path}")
        return path
    roots = (Path.cwd() / "configs", Path(sys.prefix) / "share" / "mobo-linac" / "configs",
             Path(__file__).resolve().parents[2] / "configs")  # src/mobo_linac/config.py -> <checkout>/configs
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
    config.simulation = config.simulation.resolved_against(path.parent)
    config.source_path = path  # provenance: a declared non-field attribute, never serialized
    return config


def migrate_legacy_layout(data: Dict[str, Any]) -> Dict[str, Any]:
    """Map earlier saved layouts onto the current one (input is not modified).

    - ``execution.z_stop_m``/``z_loss_tolerance_m`` moved to the ``tracking`` section.
    - ``execution.template_dir`` moved to ``simulation.template_dir``.
    - ``model.noise_mode: fixed`` is the former alias of ``deterministic_fixed``.
    - A ``sensitivity_profiles.nominal`` entry identical to ``constraints`` is dropped
      (the nominal profile *is* the top-level constraints); a differing one is rejected.
    """
    data = deepcopy(data)
    execution = data.get("execution")
    if isinstance(execution, dict):
        moved = {name: execution.pop(name) for name in ("z_stop_m", "z_loss_tolerance_m") if name in execution}
        if moved:
            tracking = data.setdefault("tracking", {})
            for name, value in moved.items():
                if name in tracking and tracking[name] != value:
                    raise ValueError(f"Conflicting execution.{name} and tracking.{name}.")
                tracking[name] = value
    model = data.get("model")
    if isinstance(model, dict) and model.get("noise_mode") == "fixed":
        data["model"] = dict(model, noise_mode="deterministic_fixed")  # former alias
    if isinstance(execution, dict) and "template_dir" in execution:
        template = execution.pop("template_dir")
        if template is not None:
            data.setdefault("simulation", {}).setdefault("template_dir", template)
    profiles = data.get("sensitivity_profiles")
    if isinstance(profiles, dict) and "nominal" in profiles:
        defaults = {attribute: default for channel in DIAGNOSTIC_CHANNELS for attribute, default, _ in channel.bound_fields()}
        if {**defaults, **profiles["nominal"]} != {**defaults, **(data.get("constraints") or {})}:
            raise ValueError("sensitivity_profiles.nominal differs from constraints; the nominal profile "
                             "is the top-level constraints section.")
        profiles = dict(profiles)
        del profiles["nominal"]
        data["sensitivity_profiles"] = profiles
    return data


def config_from_dict(data: Dict[str, Any], default_name: str = "mobo_200MeV") -> MoboConfig:
    """Reconstruct saved YAML/JSON/checkpoint configuration; fields and relations are validated once."""
    if not isinstance(data, dict):
        raise ValueError("Saved configuration must be a dictionary.")
    data = migrate_legacy_layout(data)
    _validate_value(data, _dataclass_schema(MoboConfig), "MoboConfig")
    optional = lambda key, cls: None if data.get(key) is None else cls(**data[key])
    config = MoboConfig(
        name=data.get("name", default_name),
        version=data["version"],
        description=data["description"],
        design_variables=[DesignVariableConfig(**dv) for dv in data.get("design_variables", [])],
        objectives=[ObjectiveConfig(**obj) for obj in data.get("objectives", [])],
        constraints=ConstraintsConfig(**data.get("constraints", {})),
        sensitivity_profiles={name: ConstraintsConfig(**profile)
                              for name, profile in (data.get("sensitivity_profiles") or {}).items()},
        execution=ExecutionConfig(**data.get("execution", {})),
        model=GpModelConfig(**data.get("model", {})),
        campaign=CampaignSettings(**(data.get("campaign") or {})),
        scalarized_cases={case_id: ScalarizedCaseConfig(**case)
                          for case_id, case in (data.get("scalarized_cases") or {}).items()},
        tracking=TrackingConfig(**(data.get("tracking") or {})),
        simulation=SimulationConfig(**(data.get("simulation") or {})),
        benchmark=optional("benchmark", BenchmarkConfig),
        perturbations=data.get("perturbations"),
    )
    config.check_relations()
    return config
