"""
Shared plotting schema, figure lifecycle and saving helpers.

Every figure takes its labels, display units and scales from the configuration through
:class:`PlotSchema`; constraint limit lines come from the active constraint profile.
"""

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Generator, List, Optional, Tuple, Union

import matplotlib.pyplot as plt
import numpy as np

from mobo_linac.diagnostics import DIAGNOSTIC_CHANNELS
from mobo_linac.result_schema import ResultSchema
from mobo_linac.display import objective_displays
from mobo_linac.metrics.front import pareto_mask


@dataclass(frozen=True)
class AxisSpec:
    """One plotted quantity: column, axis label and divisor to display units."""

    column: str
    label: str
    scale: float = 1.0
    sign: int = -1  # -1: smaller is better (minimize); +1: larger is better


@dataclass(frozen=True)
class ConstraintSpec:
    column: str
    label: str
    scale: float
    lower: Optional[float]
    upper: Optional[float]


def _axis_label(label: str, unit: str) -> str:
    return f"{label} [{unit}]" if unit else label


@dataclass(frozen=True)
class PlotSchema:
    design: Tuple[AxisSpec, ...]
    objectives: Tuple[AxisSpec, ...]
    constraints: Tuple[ConstraintSpec, ...]
    result_schema: ResultSchema

    @classmethod
    def from_config(cls, config) -> "PlotSchema":
        if config is None or not hasattr(config, "constraints"):
            raise TypeError("Figures require the campaign MoboConfig (labels, scales and constraint limits).")
        schema = ResultSchema.from_config(config)
        design = tuple(AxisSpec(dv.name, _axis_label(dv.label or dv.name, dv.unit))
                       for dv in config.design_variables)
        objectives = [AxisSpec(d.column, _axis_label(d.label, d.unit), d.scale, d.sign)
                      for d in objective_displays(config)]
        constraints = []
        for channel in DIAGNOSTIC_CHANNELS:
            lower, upper = channel.bounds(config.constraints)
            constraints.append(ConstraintSpec(channel.name, _axis_label(channel.label or channel.name, channel.display_unit),
                                              channel.display_scale, lower, upper))
        return cls(design, tuple(objectives), tuple(constraints), schema)

    def objective(self, column: str) -> AxisSpec:
        return next(spec for spec in self.objectives if spec.column == column)


def grid_shape(count: int, columns: int = 3) -> Tuple[int, int]:
    columns = max(1, min(columns, count))
    return int(np.ceil(count / columns)), columns


@contextmanager
def figure_scope(auto_close: bool = True) -> Generator[None, None, None]:
    """Close every Matplotlib figure created within the scope on exit."""
    initial_fignums = set(plt.get_fignums())
    try:
        yield
    finally:
        if auto_close:
            for fignum in set(plt.get_fignums()) - initial_fignums:
                plt.close(fignum)


def save_fig(
    fig: plt.Figure,
    output_path: Optional[Union[str, Path]],
    dpi: int = 300,
    close: bool = False,
) -> None:
    """Save a figure (creating parent directories) and optionally close it."""
    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=dpi, bbox_inches="tight")
    if close:
        plt.close(fig)


def scaled(frame, column: str, scale: float):
    """Column in display units; missing values stay NaN (drawn as gaps)."""
    return frame[column].astype(float) / scale


def best_so_far(values, sign: int):
    """Running best in the objective's preferred direction."""
    return values.cummin() if sign == -1 else values.cummax()


def nondominated_mask(frame, schema: PlotSchema) -> np.ndarray:
    """Non-dominated rows of finite objective values in the frame (direction aware)."""
    values = frame[[spec.column for spec in schema.objectives]].to_numpy(dtype=float)
    finite = np.isfinite(values).all(axis=1)
    mask = np.zeros(len(frame), dtype=bool)
    if finite.any():
        model = values[finite] * np.asarray([spec.sign for spec in schema.objectives], dtype=float)
        mask[np.flatnonzero(finite)] = pareto_mask(model).numpy()
    return mask


__all__: List[str] = ["AxisSpec", "ConstraintSpec", "PlotSchema", "best_so_far",
                      "figure_scope", "grid_shape", "nondominated_mask", "save_fig", "scaled"]
