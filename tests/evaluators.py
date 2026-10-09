"""Evaluator test doubles built on the single evaluator protocol."""

from mobo_linac.evaluation import EvaluationResult
from mobo_linac.execution import FunctionEvaluator


def mock_data_evaluator(data):
    """Answer every request with explicit mock rerun data (``objectives_physical``, ``diagnostics``)."""
    def respond(request, run_id):
        return {"status": "SUCCESS" if data.get("simulation_valid", True) else "RUN_FAILED",
                "objectives": data.get("objectives_physical"), "diagnostics": data.get("diagnostics", {}),
                "execution_kind": "mock"}
    return FunctionEvaluator(respond)


def callable_evaluator(function, mock=True):
    """Adapt ``function(parameters, run_id, eval_id) -> raw dict``; mock results are labelled as such."""
    def respond(request, run_id):
        raw = function(request.parameters, run_id=run_id, eval_id=request.eval_id)
        if isinstance(raw, EvaluationResult):  # stored records stand in for rerun data
            raw = {"status": "SUCCESS" if raw.simulation_valid else "RUN_FAILED",
                   "objectives": raw.objectives_physical, "diagnostics": raw.diagnostics}
        return dict(raw, execution_kind="mock") if mock else raw
    return FunctionEvaluator(respond)
