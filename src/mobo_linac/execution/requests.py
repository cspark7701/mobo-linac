"""Serializable evaluation requests shared by planners and execution backends."""

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Union


@dataclass
class EvaluationRequest:
    eval_id: Union[int, str]
    parameters: List[float]
    namelist_overrides: Optional[Dict[str, Any]] = None
    source_settings: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def validate(self, config) -> None:
        from mobo_linac.config import validate_evaluation_settings
        validate_evaluation_settings(self.parameters, config, self.namelist_overrides, self.source_settings)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
