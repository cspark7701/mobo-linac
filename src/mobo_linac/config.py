"""
Centralized Configuration Module for mobo_linac.

Defines declarative schemas, strict physical validation, JSON Schema exporter,
and Markdown documentation generator for accelerator Bayesian optimization.
"""

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import torch
import yaml


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

    def __post_init__(self) -> None:
        self.nominal_value = float(self.nominal_value)
        self.ratio = float(self.ratio)
        self.lower_bound = float(self.lower_bound)
        self.upper_bound = float(self.upper_bound)

    def validate(self) -> None:
        """Validate bounds ordering, nominal value validity, and coupling rules."""
        if not self.name or not isinstance(self.name, str):
            raise ValueError("Design variable must have a non-empty name string.")
        if not self.astra_key or not isinstance(self.astra_key, str):
            raise ValueError(f"Design variable '{self.name}' must have a non-empty astra_key string.")
        if self.lower_bound > self.upper_bound:
            raise ValueError(
                f"Invalid bounds for design variable '{self.name}': "
                f"lower_bound ({self.lower_bound}) > upper_bound ({self.upper_bound})"
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


@dataclass
class ObjectiveConfig:
    """Configuration for an optimization objective."""

    name: str
    explicit_name: str
    unit: str
    physical_direction: str  # "minimize" or "maximize"
    model_sign: int  # -1 for minimization (maximization in BoTorch), 1 for maximization

    def validate(self) -> None:
        """Validate objective direction, name, and BoTorch model sign."""
        if not self.name or not isinstance(self.name, str):
            raise ValueError("Objective must have a non-empty name string.")
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

    def __post_init__(self) -> None:
        self.max_sigma_x_m = float(self.max_sigma_x_m)
        self.max_sigma_y_m = float(self.max_sigma_y_m)
        self.max_sigma_xp_rad = float(self.max_sigma_xp_rad)
        self.max_sigma_yp_rad = float(self.max_sigma_yp_rad)
        self.max_sigma_z_m = float(self.max_sigma_z_m)
        self.min_mean_kinetic_energy_eV = float(self.min_mean_kinetic_energy_eV)
        self.max_mean_kinetic_energy_eV = float(self.max_mean_kinetic_energy_eV)
        self.min_transmission = float(self.min_transmission)

    def validate(self) -> None:
        """Validate beam diagnostic thresholds and transmission ranges."""
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

    def validate(self) -> None:
        """Validate execution parameters."""
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


@dataclass
class BenchmarkConfig:
    """Configuration for paired multi-seed benchmark campaigns."""

    algorithms: List[str] = field(
        default_factory=lambda: [
            "constrained_qlognehvi",
            "unconstrained_qlognehvi",
            "scalarized_bo",
            "nsga2",
            "sobol",
        ]
    )
    seeds: List[int] = field(default_factory=lambda: list(range(42, 52)))
    total_eval_budget: int = 40
    n_sobol_init: int = 10
    batch_size: int = 4
    reporting_ref_point: List[float] = field(default_factory=lambda: [1.5, 1.5, 1.5])
    constraint_profile: str = "nominal"
    output_dir: str = "results/publication_benchmark"

    def validate(self) -> None:
        """Validates benchmark configuration fields."""
        supported = [
            "constrained_qlognehvi",
            "unconstrained_qlognehvi",
            "qlogehvi",
            "scalarized_bo",
            "nsga2",
            "sobol",
        ]
        for algo in self.algorithms:
            if algo not in supported:
                raise ValueError(f"Unsupported algorithm '{algo}'. Supported: {supported}")
        if self.total_eval_budget <= self.n_sobol_init:
            raise ValueError("total_eval_budget must be greater than n_sobol_init.")
        if self.batch_size < 1:
            raise ValueError("batch_size must be >= 1.")
        if len(self.seeds) == 0:
            raise ValueError("At least one seed must be specified.")


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

    def validate(self) -> None:
        """Validate entire configuration system."""
        if not self.name:
            self.name = "mobo_200MeV"
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

        self.constraints.validate()
        for name, profile in self.sensitivity_profiles.items():
            profile.validate()

        self.execution.validate()
        self.model.validate()

    def get_constraint_profile(self, profile_name: str = "nominal") -> ConstraintsConfig:
        """Returns the specified constraint sensitivity profile, falling back to main constraints."""
        if profile_name in self.sensitivity_profiles:
            return self.sensitivity_profiles[profile_name]
        return self.constraints

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
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2)
        return path

    def save_yaml(self, output_path: Union[str, Path]) -> Path:
        """Save configuration to YAML file."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(asdict(self), f, default_flow_style=False)
        return path


def export_config_schema(output_path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    """
    Exports a standard JSON Schema (draft-07 compatible) describing MoboConfig.
    """
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "MoboConfig",
        "description": "Declarative configuration schema for Linac Multi-Objective Bayesian Optimization",
        "type": "object",
        "required": ["version", "description", "design_variables", "objectives", "constraints"],
        "properties": {
            "name": {"type": "string", "default": "mobo_200MeV"},
            "version": {"type": "string"},
            "description": {"type": "string"},
            "design_variables": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": [
                        "name",
                        "astra_key",
                        "unit",
                        "nominal_value",
                        "ratio",
                        "lower_bound",
                        "upper_bound",
                    ],
                    "properties": {
                        "name": {"type": "string"},
                        "astra_key": {"type": "string"},
                        "unit": {"type": "string"},
                        "nominal_value": {"type": "number"},
                        "ratio": {"type": "number", "minimum": 0.0},
                        "lower_bound": {"type": "number"},
                        "upper_bound": {"type": "number"},
                        "is_coupled": {"type": "boolean", "default": False},
                        "coupled_targets": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                },
            },
            "objectives": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["name", "explicit_name", "unit", "physical_direction", "model_sign"],
                    "properties": {
                        "name": {"type": "string"},
                        "explicit_name": {"type": "string"},
                        "unit": {"type": "string"},
                        "physical_direction": {"type": "string", "enum": ["minimize", "maximize"]},
                        "model_sign": {"type": "integer", "enum": [-1, 1]},
                    },
                },
            },
            "constraints": {
                "type": "object",
                "properties": {
                    "max_sigma_x_m": {"type": "number", "exclusiveMinimum": 0.0},
                    "max_sigma_y_m": {"type": "number", "exclusiveMinimum": 0.0},
                    "max_sigma_xp_rad": {"type": "number", "exclusiveMinimum": 0.0},
                    "max_sigma_yp_rad": {"type": "number", "exclusiveMinimum": 0.0},
                    "max_sigma_z_m": {"type": "number", "exclusiveMinimum": 0.0},
                    "min_mean_kinetic_energy_eV": {"type": "number", "exclusiveMinimum": 0.0},
                    "max_mean_kinetic_energy_eV": {"type": "number", "exclusiveMinimum": 0.0},
                    "min_transmission": {"type": "number", "exclusiveMinimum": 0.0, "maximum": 1.0},
                },
            },
            "sensitivity_profiles": {
                "type": "object",
                "additionalProperties": {"$ref": "#/properties/constraints"},
            },
            "execution": {
                "type": "object",
                "properties": {
                    "timeout_sec": {"type": "integer", "minimum": 1},
                    "max_workers": {"type": "integer", "minimum": 1},
                    "retries": {"type": "integer", "minimum": 0},
                    "clean_on_success": {"type": "boolean"},
                    "acqf_num_restarts": {"type": "integer", "minimum": 1},
                    "acqf_raw_samples": {"type": "integer", "minimum": 1},
                    "acqf_maxiter": {"type": "integer", "minimum": 1},
                    "acqf_batch_limit": {"type": "integer", "minimum": 1},
                    "z_stop_m": {"type": "number"},
                    "z_loss_tolerance_m": {"type": "number"},
                },
            },
            "model": {
                "type": "object",
                "properties": {
                    "covar_type": {"type": "string", "enum": ["matern52", "rbf"]},
                    "noise_mode": {
                        "type": "string",
                        "enum": ["deterministic_fixed", "fixed", "inferred", "measured_fixed"],
                    },
                    "fixed_noise_variance": {"type": ["number", "null"]},
                    "relative_noise_ratio": {"type": "number", "exclusiveMinimum": 0.0},
                    "min_noise_variance": {"type": "number", "exclusiveMinimum": 0.0},
                },
            },
        },
    }

    if output_path is not None:
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(schema, f, indent=2)

    return schema


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

    return "\n".join(lines)


def load_config(config_path: Union[str, Path] = "configs/publication_200MeV.yaml") -> MoboConfig:
    """
    Load configuration from YAML file.
    """
    path = Path(config_path).resolve()
    if not path.exists():
        fallback_path = Path("configs/publication.yaml").resolve()
        if fallback_path.exists():
            path = fallback_path
        else:
            path = Path("configs/mobo_200MeV.yaml").resolve()

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError(f"YAML configuration at {path} must contain a top-level dictionary.")

    design_vars = [DesignVariableConfig(**dv) for dv in data.get("design_variables", [])]
    objs = [ObjectiveConfig(**obj) for obj in data.get("objectives", [])]
    constraints = ConstraintsConfig(**data.get("constraints", {}))

    sens_profiles = {}
    if "sensitivity_profiles" in data and isinstance(data["sensitivity_profiles"], dict):
        for pname, pdata in data["sensitivity_profiles"].items():
            sens_profiles[pname] = ConstraintsConfig(**pdata)

    execution = ExecutionConfig(**data.get("execution", {}))
    model_cfg = GpModelConfig(**data.get("model", {}))

    config = MoboConfig(
        name=str(data.get("name", path.stem)),
        version=str(data.get("version", "1.0")),
        description=str(data.get("description", "")),
        design_variables=design_vars,
        objectives=objs,
        constraints=constraints,
        sensitivity_profiles=sens_profiles,
        execution=execution,
        model=model_cfg,
    )
    config.validate()
    return config
