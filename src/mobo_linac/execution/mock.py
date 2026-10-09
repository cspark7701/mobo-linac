"""
Deterministic evaluators for tests, dry runs and offline CI, plus a function adapter.

``MockEvaluator`` answers any configured objective and diagnostic layout without the
ASTRA binary; ``FunctionEvaluator`` adapts a per-request callable to the evaluator
protocol with the submitted identities preserved.
"""

from dataclasses import replace
from pathlib import Path
import time
from typing import Any, Callable, Dict, List, Optional, Sequence, Union

from mobo_linac.astra.workdir import format_eval_id
from mobo_linac.diagnostics import DIAGNOSTIC_CHANNELS
from mobo_linac.evaluation import EvaluationResult
from mobo_linac.requests import EvaluationRequest

LEGACY_OBJECTIVES = ("norm_emit_x", "norm_emit_y", "sigma_energy")
# Synthetic in-limit beam diagnostics of the canonical 200 MeV channels.
_CANONICAL_DIAGNOSTICS = {
    "sigma_x_m": 0.5e-3, "sigma_y_m": 0.5e-3, "sigma_xp_rad": 0.4e-3, "sigma_yp_rad": 0.4e-3,
    "sigma_z_m": 0.5e-3, "mean_kinetic_energy_eV": 200.0e6, "transmission_fraction": 1.0,
}


def _in_limit_value(channel) -> float:
    """A value inside the channel's default bounds (for channels without a canonical mock value)."""
    lower, upper = channel.lower_default, channel.upper_default
    if lower is not None and upper is not None:
        return 0.5 * (lower + upper)
    if upper is not None:
        return 0.5 * upper
    if lower is not None:
        return min(1.0, 2.0 * lower) if channel.physical_maximum is not None else 2.0 * lower
    return 1.0


class MockEvaluator:
    """Deterministic synthetic responses with failure injection and streaming completions."""

    def __init__(
        self,
        run_dir: Optional[Union[str, Path]] = None,
        failure_rate: float = 0.0,
        fail_eval_ids: Optional[Sequence[Union[int, str]]] = None,
        delay_sec: float = 0.0,
        noise_std: float = 0.0,
        config: Optional[Any] = None,
    ):
        """``config`` selects the synthetic objective names; omitted, the evaluator reports the
        archived 200 MeV statistic names, which configured campaigns resolve through aliases.
        ``run_dir`` only labels the reported evaluation directories (nothing is written)."""
        self.run_dir = Path(run_dir) if run_dir is not None else None
        self.failure_rate = float(failure_rate)
        self.fail_eval_ids = {format_eval_id(eid) for eid in fail_eval_ids or ()}
        self.delay_sec = float(delay_sec)
        self.noise_std = float(noise_std)
        self.objective_names = ([obj.name for obj in config.objectives] if config is not None
                                else list(LEGACY_OBJECTIVES))

    def respond(self, parameters: Sequence[float], run_id: str = "mock_run",
                eval_id: Union[int, str] = 1) -> Dict[str, Any]:
        """The raw result dictionary (ASTRA result layout) for one candidate."""
        eval_id = format_eval_id(eval_id)
        values = [float(x) for x in parameters]
        work_dir = str(self.run_dir / eval_id) if self.run_dir is not None else None
        base = {"eval_id": eval_id, "run_id": run_id, "parameters": values, "eval_dir": work_dir,
                "execution_kind": "mock"}
        if eval_id in self.fail_eval_ids or (self.failure_rate > 0 and sum(values) % 1.0 < self.failure_rate):
            return dict(base, status="RUN_FAILED", objectives=None, diagnostics=None, manifest_path=None,
                        error="Simulated evaluation failure in mock environment", timestamps={"duration_sec": 0.01})
        total = sum(values)
        # Historical statistic names keep their values; other objectives get bounded synthetic values.
        legacy = {"norm_emit_x": float(0.1e-6 + 0.01e-6 * (total % 5)),
                  "norm_emit_y": float(0.1e-6 + 0.01e-6 * (total % 7)),
                  "sigma_energy": float(0.5e6 + 0.05e6 * (total % 3))}
        objectives = {name: legacy.get(name, float(1.0 + 0.1 * (total % (index + 3))))
                      for index, name in enumerate(self.objective_names)}
        diagnostics = {channel.name: _CANONICAL_DIAGNOSTICS.get(channel.name, _in_limit_value(channel))
                       for channel in DIAGNOSTIC_CHANNELS}
        return dict(base, status="SUCCESS", objectives=objectives, diagnostics=diagnostics, error=None,
                    timestamps={"duration_sec": max(0.01, self.delay_sec)},
                    manifest_path=None)  # no attempt manifest is written for synthetic responses

    def evaluate(self, requests: Sequence[EvaluationRequest], run_id: str = "mock_batch",
                 on_complete: Optional[Callable[[Dict[str, Any]], None]] = None) -> List[Dict[str, Any]]:
        """Answer each request in order, publishing every completion as it is produced."""
        results = []
        for request in requests:
            if self.delay_sec > 0:
                time.sleep(self.delay_sec)
            result = dict(self.respond(request.parameters, run_id, request.eval_id), request=request.to_dict())
            results.append(result)
            if on_complete is not None:
                on_complete(result)
        return results


class FunctionEvaluator:
    """Adapt ``function(request, run_id) -> raw result`` to the evaluator protocol.

    The submitted request identity, run identity and parameters are always reported, so a
    callable cannot relabel a completion.
    """

    def __init__(self, function: Callable[[EvaluationRequest, str], Union[Dict[str, Any], EvaluationResult]]):
        self.function = function

    def evaluate(self, requests: Sequence[EvaluationRequest], run_id: str,
                 on_complete: Optional[Callable[[Any], None]] = None) -> List[Any]:
        results = []
        for request in requests:
            raw = self.function(request, run_id)
            if isinstance(raw, EvaluationResult):
                raw = replace(raw, evaluation_id=format_eval_id(request.eval_id), run_id=run_id,
                              x_physical=list(request.parameters))
            else:
                raw = dict(raw, eval_id=request.eval_id, run_id=run_id, parameters=list(request.parameters))
            results.append(raw)
            if on_complete is not None:
                on_complete(raw)
        return results
