"""
Centralized Configuration Module for mobo_linac.

Defines dataclasses and loader for physical parameters, design variable bounds,
objective definitions, and constraint thresholds.
"""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import yaml
import torch


@dataclass
class DesignVariableConfig:
    """Configuration for a single design variable."""

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
        """Validate bounds ordering and coupled properties."""
        if self.lower_bound > self.upper_bound:
            raise ValueError(
                f"Invalid bounds for design variable '{self.name}': "
                f"lower_bound ({self.lower_bound}) > upper_bound ({self.upper_bound})"
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

    def validate(self) -> None:
        """Validate objective direction and sign."""
        if self.physical_direction not in ("minimize", "maximize"):
            raise ValueError(f"Invalid physical_direction '{self.physical_direction}' for objective '{self.name}'")
        if self.model_sign not in (-1, 1):
            raise ValueError(f"Invalid model_sign '{self.model_sign}' for objective '{self.name}'. Must be -1 or 1.")
        if self.physical_direction == "minimize" and self.model_sign != -1:
            raise ValueError(f"Minimization objective '{self.name}' must have model_sign = -1.")


@dataclass
class ConstraintsConfig:
    """Configuration for diagnostic constraints and thresholds."""

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
        """Validate constraint bounds."""
        if self.min_mean_kinetic_energy_eV > self.max_mean_kinetic_energy_eV:
            raise ValueError(
                f"Invalid kinetic energy constraints: min ({self.min_mean_kinetic_energy_eV}) > max ({self.max_mean_kinetic_energy_eV})"
            )
        if self.max_sigma_x_m <= 0 or self.max_sigma_y_m <= 0 or self.max_sigma_z_m <= 0:
            raise ValueError("Beam size constraints (sigma_x, sigma_y, sigma_z) must be positive.")


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
    """
    Configuration for paired multi-seed benchmark campaigns.

    Defines algorithms, seeds, evaluation budgets, Sobol initial design size,
    batch size, fixed reporting reference point, and constraint profile.
    """

    algorithms: List[str] = field(default_factory=lambda: [
        "constrained_qlognehvi",
        "unconstrained_qlognehvi",
        "scalarized_bo",
        "nsga2",
        "sobol",
    ])
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
            "constrained_qlognehvi", "unconstrained_qlognehvi", "qlogehvi",
            "scalarized_bo", "nsga2", "sobol",
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

        for dv in self.design_variables:
            dv.validate()

        for obj in self.objectives:
            obj.validate()

        self.constraints.validate()
        for name, profile in self.sensitivity_profiles.items():
            profile.validate()

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

    design_vars = [DesignVariableConfig(**dv) for dv in data["design_variables"]]
    objs = [ObjectiveConfig(**obj) for obj in data["objectives"]]
    constraints = ConstraintsConfig(**data["constraints"])

    sens_profiles = {}
    if "sensitivity_profiles" in data:
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

