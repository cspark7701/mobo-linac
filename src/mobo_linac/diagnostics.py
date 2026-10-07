"""Canonical measured beam diagnostic layout and configured constraint bounds."""

from dataclasses import dataclass
import math
from numbers import Real
from typing import Any, Dict, Mapping, Optional, Tuple


@dataclass(frozen=True)
class DiagnosticChannel:
    name: str
    aliases: Tuple[str, ...]
    unit: str
    lower_attribute: Optional[str] = None
    upper_attribute: Optional[str] = None
    lower_violation: Optional[str] = None
    upper_violation: Optional[str] = None
    physical_minimum: Optional[float] = None
    physical_maximum: Optional[float] = None

    def bounds(self, config):
        return (getattr(config, self.lower_attribute) if self.lower_attribute else None,
                getattr(config, self.upper_attribute) if self.upper_attribute else None)


DIAGNOSTIC_CHANNELS = (
    DiagnosticChannel("sigma_x_m", ("sigma_x",), "m", upper_attribute="max_sigma_x_m", upper_violation="sigma_x_m", physical_minimum=0.0),
    DiagnosticChannel("sigma_y_m", ("sigma_y",), "m", upper_attribute="max_sigma_y_m", upper_violation="sigma_y_m", physical_minimum=0.0),
    DiagnosticChannel("sigma_xp_rad", ("sigma_xp",), "rad", upper_attribute="max_sigma_xp_rad", upper_violation="sigma_xp_rad", physical_minimum=0.0),
    DiagnosticChannel("sigma_yp_rad", ("sigma_yp",), "rad", upper_attribute="max_sigma_yp_rad", upper_violation="sigma_yp_rad", physical_minimum=0.0),
    DiagnosticChannel("sigma_z_m", ("sigma_z",), "m", upper_attribute="max_sigma_z_m", upper_violation="sigma_z_m", physical_minimum=0.0),
    DiagnosticChannel("mean_kinetic_energy_eV", ("mean_kinetic_energy",), "eV", "min_mean_kinetic_energy_eV", "max_mean_kinetic_energy_eV", "energy_lower_eV", "energy_upper_eV"),
    DiagnosticChannel("transmission_fraction", ("transmission",), "1", lower_attribute="min_transmission", lower_violation="transmission", physical_minimum=0.0, physical_maximum=1.0),
)
DIAGNOSTIC_NAMES = tuple(channel.name for channel in DIAGNOSTIC_CHANNELS)


def finite_measurement(value: Any) -> bool:
    return isinstance(value, Real) and not isinstance(value, bool) and math.isfinite(float(value))


def normalize_diagnostics(diagnostics: Mapping[str, Any]) -> Dict[str, Any]:
    """Resolve measured aliases without imputation; conflicting aliases become invalid.

    Canonical keys are absent when no observation was supplied, and NaN when
    supplied values are nonnumeric, nonfinite, or disagree with their aliases.
    Extra telemetry is preserved. No physical thresholds are applied here.
    """
    diagnostics = diagnostics or {}
    normalized = dict(diagnostics)
    for channel in DIAGNOSTIC_CHANNELS:
        keys = (channel.name,) + channel.aliases
        values = [diagnostics[key] for key in keys if key in diagnostics]
        for alias in channel.aliases:
            normalized.pop(alias, None)
        if not values:
            continue
        if not all(finite_measurement(value) for value in values) or any(
            float(value) != float(values[0]) for value in values[1:]
        ):
            normalized[channel.name] = float("nan")
        else:
            normalized[channel.name] = float(values[0])
    return normalized


def invalid_diagnostic_channels(diagnostics: Mapping[str, Any]) -> Tuple[str, ...]:
    """Return missing, nonfinite, or unphysical canonical observation names."""
    return tuple(channel.name for channel in DIAGNOSTIC_CHANNELS
                 if not valid_channel_measurement(channel, diagnostics.get(channel.name)))


def valid_channel_measurement(channel: DiagnosticChannel, value: Any) -> bool:
    return (finite_measurement(value)
            and (channel.physical_minimum is None or value >= channel.physical_minimum)
            and (channel.physical_maximum is None or value <= channel.physical_maximum))


def diagnostic_observations(diagnostics: Mapping[str, Any]) -> Optional[Tuple[float, ...]]:
    normalized = normalize_diagnostics(diagnostics)
    if invalid_diagnostic_channels(normalized):
        return None
    return tuple(normalized[name] for name in DIAGNOSTIC_NAMES)


def constraint_sides(config):
    """Yield channel index, side, threshold, and legacy violation name in order."""
    for index, channel in enumerate(DIAGNOSTIC_CHANNELS):
        lower, upper = channel.bounds(config)
        if lower is not None:
            yield index, "lower", lower, channel.lower_violation
        if upper is not None:
            yield index, "upper", upper, channel.upper_violation
