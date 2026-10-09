"""Validated perturbation (jitter) specification: lattice and source channels and analysis policy.

Core data: the configuration's ``perturbations`` section and the robustness study use it.
"""

from dataclasses import asdict, dataclass
import math
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

import yaml


SOURCE_MAPPING_REASON = (
    "The ASTRA template reads a fixed particle distribution; no verified source-generation "
    "mapping applies this scale. The source distribution is unchanged."
)
SEED_POLICIES = ("common", "candidate_offset")
KINDS = ("relative", "absolute")
DISTRIBUTIONS = ("normal",)


def _finite_nonnegative(name: str, value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be finite and nonnegative.")
    return float(value)


@dataclass(frozen=True)
class LatticeChannel:
    """Jitter applied to one configured design variable."""

    channel: str
    design_variable: str
    kind: str
    std: float
    unit: str = ""
    distribution: str = "normal"
    basis: str = ""

    def __post_init__(self):
        if not self.channel or not self.design_variable:
            raise ValueError("Lattice channels require channel and design_variable names.")
        if self.kind not in KINDS:
            raise ValueError(f"Lattice channel {self.channel}: kind must be one of {KINDS}.")
        if self.distribution not in DISTRIBUTIONS:
            raise ValueError(f"Lattice channel {self.channel}: unsupported distribution {self.distribution}.")
        _finite_nonnegative(f"{self.channel} std", self.std)

    def apply(self, nominal: float, delta: float) -> float:
        return float(nominal * (1.0 + delta)) if self.kind == "relative" else float(nominal + delta)


@dataclass(frozen=True)
class SourceChannel:
    """Relative jitter of a photocathode/laser source setting (scale = 1 + delta)."""

    channel: str
    setting: str
    std: float
    unit: str = "dimensionless"
    distribution: str = "normal"
    basis: str = ""

    def __post_init__(self):
        if not self.channel or not self.setting:
            raise ValueError("Source channels require channel and setting names.")
        if self.distribution not in DISTRIBUTIONS:
            raise ValueError(f"Source channel {self.channel}: unsupported distribution {self.distribution}.")
        _finite_nonnegative(f"{self.channel} std", self.std)


# Explicit compatibility mapping for version-1 flat perturbation files, which named
# channels only for the archived 200 MeV design layout.
_LEGACY_LATTICE = (
    ("solenoid_field_relative_error", "solenoid_field_T", "relative", "solenoid_field_relative_error", 0.001, "dimensionless"),
    ("quad1_gradient_relative_error", "quad_1_gradient_T_m", "relative", "quad_gradient_relative_error", 0.001, "dimensionless"),
    ("quad2_gradient_relative_error", "quad_2_gradient_T_m", "relative", "quad_gradient_relative_error", 0.001, "dimensionless"),
    ("gun_phase_error_deg", "gun_phase_deg", "absolute", "gun_phase_error_deg", 0.10, "deg"),
    ("cavity_phase_acc12_error_deg", "acc1_acc2_phase_deg", "absolute", "cavity_phase_error_deg", 0.10, "deg"),
    ("cavity_phase_acc34_error_deg", "acc3_acc4_phase_deg", "absolute", "cavity_phase_error_deg", 0.10, "deg"),
)
_LEGACY_SOURCE = (
    ("bunch_charge_relative_jitter", "bunch_charge_scale", 0.010),
    ("laser_spot_size_relative_jitter", "laser_spot_scale", 0.010),
    ("laser_pulse_duration_relative_jitter", "laser_pulse_duration_scale", 0.010),
)
SUPPORTED_SOURCE_SETTINGS = {setting for _, setting, _ in _LEGACY_SOURCE}


@dataclass(frozen=True)
class PerturbationSpecification:
    """Validated jitter model: lattice and source channels in draw order plus analysis policy."""

    lattice: Tuple[LatticeChannel, ...]
    source: Tuple[SourceChannel, ...] = ()
    seed_policy: str = "common"
    fragility_threshold: float = 0.80
    num_perturbations: int = 50
    seed: int = 42

    def __post_init__(self):
        object.__setattr__(self, "lattice", tuple(self.lattice))
        object.__setattr__(self, "source", tuple(self.source))
        names = [c.channel for c in self.lattice] + [c.channel for c in self.source]
        if len(names) != len(set(names)):
            raise ValueError("Perturbation channel names must be unique.")
        if len({c.design_variable for c in self.lattice}) != len(self.lattice):
            raise ValueError("Each design variable may have at most one lattice channel.")
        unknown = {c.setting for c in self.source} - SUPPORTED_SOURCE_SETTINGS
        if unknown:
            raise ValueError(f"Unknown source settings: {sorted(unknown)}")
        if self.seed_policy not in SEED_POLICIES:
            raise ValueError(f"seed_policy must be one of {SEED_POLICIES}.")
        if not 0.0 <= _finite_nonnegative("fragility_threshold", self.fragility_threshold) <= 1.0:
            raise ValueError("fragility_threshold must lie in [0, 1].")
        if type(self.num_perturbations) is not int or self.num_perturbations < 1:
            raise ValueError("num_perturbations must be a positive integer.")
        if type(self.seed) is not int or not 0 <= self.seed < 2**32:
            raise ValueError("seed must be an integer in [0, 2**32).")

    @property
    def channels(self) -> Tuple[str, ...]:
        return tuple(c.channel for c in self.lattice) + tuple(c.channel for c in self.source)

    def to_dict(self) -> Dict[str, Any]:
        """JSON-compatible record of the complete specification."""
        data = asdict(self)
        data["lattice"] = [dict(channel) for channel in data["lattice"]]
        data["source"] = [dict(channel) for channel in data["source"]]
        return data

    def channel_targets(self) -> Dict[str, str]:
        return {c.channel: c.design_variable for c in self.lattice}

    def validate_for(self, config: "MoboConfig") -> None:
        names = {dv.name for dv in config.design_variables}
        missing = [c.design_variable for c in self.lattice if c.design_variable not in names]
        if missing:
            raise ValueError(f"Perturbation channels reference unknown design variables: {missing}")

    def with_stds(self, **stds: float) -> "PerturbationSpecification":
        """Copy with selected channel standard deviations replaced (by channel name)."""
        unknown = set(stds) - set(self.channels)
        if unknown:
            raise ValueError(f"Unknown perturbation channels: {sorted(unknown)}")
        lattice = tuple(LatticeChannel(**{**asdict(c), "std": stds.get(c.channel, c.std)}) for c in self.lattice)
        source = tuple(SourceChannel(**{**asdict(c), "std": stds.get(c.channel, c.std)}) for c in self.source)
        return PerturbationSpecification(lattice, source, self.seed_policy, self.fragility_threshold,
                                         self.num_perturbations, self.seed)

    @classmethod
    def legacy_200MeV(cls, perturbations: Optional[Dict[str, Any]] = None, **policy) -> "PerturbationSpecification":
        """Read a version-1 flat channel mapping for the archived 200 MeV layout."""
        perturbations = perturbations or {}
        allowed = {key for *_, key, _, _ in _LEGACY_LATTICE} | {key for key, _, _ in _LEGACY_SOURCE}
        unknown = set(perturbations) - allowed
        if unknown:
            raise ValueError(f"Unknown legacy perturbation channels: {sorted(unknown)}")

        def std(key, default):
            value = perturbations.get(key, default)
            if isinstance(value, dict):
                if value.get("distribution", "normal") not in DISTRIBUTIONS:
                    raise ValueError(f"{key}: unsupported distribution {value.get('distribution')}.")
                value = value.get("std", default)
            return value

        lattice = [LatticeChannel(name, variable, kind, std(key, default), unit)
                   for name, variable, kind, key, default, unit in _LEGACY_LATTICE]
        source = [SourceChannel(name, setting, std(name, default)) for name, setting, default in _LEGACY_SOURCE]
        return cls(tuple(lattice), tuple(source), **policy)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PerturbationSpecification":
        """Construct from a version-2 specification or a version-1 flat mapping."""
        if not isinstance(data, dict):
            raise ValueError("Perturbation specification must be a mapping.")
        policy_keys = ("seed_policy", "fragility_threshold", "num_perturbations", "seed")
        policy = {key: data[key] for key in policy_keys if key in data}
        allowed = {"version", "description", "lattice", "source", "perturbations", *policy_keys}
        extra = set(data) - allowed
        if extra:
            raise ValueError(f"Unknown perturbation specification fields: {sorted(extra)}")
        if "lattice" in data:
            lattice = tuple(LatticeChannel(**channel) for channel in data["lattice"])
            source = tuple(SourceChannel(**channel) for channel in data.get("source", []))
            return cls(lattice, source, **policy)
        return cls.legacy_200MeV(data.get("perturbations", {}), **policy)

    @classmethod
    def from_yaml(cls, yaml_path: Union[str, Path]) -> "PerturbationSpecification":
        """Loads a specification from a YAML file (callers resolve default locations)."""
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return cls.from_dict(data)
