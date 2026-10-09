"""Serializable evaluation requests shared by planners and execution backends."""

from dataclasses import asdict, dataclass, field
import math
import re
from typing import Any, Dict, List, Optional, Union

# Relative photocathode source scales an evaluation request may set (1.0 = nominal).
SOURCE_SETTINGS = ("bunch_charge_scale", "laser_spot_scale", "laser_pulse_duration_scale")


@dataclass
class EvaluationRequest:
    eval_id: Union[int, str]
    parameters: List[float]
    namelist_overrides: Optional[Dict[str, Any]] = None
    source_settings: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def validate(self, config) -> None:
        validate_evaluation_settings(self.parameters, config, self.namelist_overrides, self.source_settings)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def validate_evaluation_settings(parameters, config, namelist_overrides=None, source_settings=None):
    """Validate finite machine/source requests before reserving simulation attempts."""
    if hasattr(config, "design_variables"):
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
    if not isinstance(source_settings, dict) or set(source_settings) - set(SOURCE_SETTINGS):
        raise ValueError(f"Unknown source settings; supported names are {list(SOURCE_SETTINGS)}.")
    for key, value in source_settings.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise ValueError(f"source_settings.{key} must be a finite positive number.")
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
