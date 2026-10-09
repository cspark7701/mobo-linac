"""Display metadata of configured objectives, shared by figures and report tables.

Shown value = physical value / ``scale`` in ``unit``; ``label`` is the configured LaTeX label
(or the explicit column name) and ``sign`` is -1 for minimized, +1 for maximized objectives.
"""

from dataclasses import dataclass
from typing import List

from mobo_linac.result_schema import ResultSchema


@dataclass(frozen=True)
class ObjectiveDisplay:
    column: str
    label: str
    unit: str
    scale: float
    sign: int
    target: float = float("nan")


def objective_displays(config) -> List[ObjectiveDisplay]:
    schema = ResultSchema.from_config(config)
    displays = []
    for objective, scale, sign in zip(config.objectives, schema.scales, schema.signs):
        unit = objective.display_unit or (objective.unit if scale == 1.0 else f"{scale:g} {objective.unit}")
        target = objective.target if objective.target is not None else float("nan")
        displays.append(ObjectiveDisplay(objective.explicit_name, objective.label or objective.explicit_name,
                                         unit, scale, sign, target))
    return displays
