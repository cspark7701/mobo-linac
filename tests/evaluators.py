"""Evaluator test doubles built on the single evaluator protocol."""

from mobo_linac.evaluation import EvaluationResult
from mobo_linac.execution import FunctionEvaluator, MockEvaluator


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


class ScriptedEvaluator(MockEvaluator):
    """The one scripted mock used for interruption, recording and timing tests.

    ``submissions`` records ``(evaluation ids, parameters, run_id)`` per evaluate call.
    The batch at index ``interrupt_batch`` (or the batch starting at ``interrupt_at_id``) first
    publishes the candidate at ``completion_position`` (if given) and then raises ``message``.
    ``swallow_callback_errors`` publishes completions after evaluation and ignores ``OSError``
    from the callback (a backend that hides persistence failures); ``before_batch`` is called at the
    start of every batch, and ``duration_sec`` overrides the reported per-candidate runtime.
    """

    def __init__(self, run_dir=None, *, interrupt_batch=None, interrupt_at_id=None, completion_position=None,
                 message="Injected parent interruption", swallow_callback_errors=False, before_batch=None,
                 duration_sec=None, **kwargs):
        super().__init__(run_dir, **kwargs)
        self.interrupt_batch, self.interrupt_at_id = interrupt_batch, interrupt_at_id
        self.completion_position, self.message = completion_position, message
        self.swallow_callback_errors, self.before_batch = swallow_callback_errors, before_batch
        self.duration_sec = duration_sec
        self.submissions = []

    def respond(self, *args, **kwargs):
        record = super().respond(*args, **kwargs)
        if self.duration_sec is not None:
            record["timestamps"]["duration_sec"] = self.duration_sec
        return record

    def evaluate(self, requests, run_id="mock", on_complete=None):
        index = len(self.submissions)
        self.submissions.append(([r.eval_id for r in requests], [r.parameters for r in requests], run_id))
        if self.before_batch is not None:
            self.before_batch()
        if index == self.interrupt_batch or (self.interrupt_at_id is not None and requests[0].eval_id == self.interrupt_at_id):
            if self.completion_position is not None:
                request = requests[self.completion_position]
                on_complete(self.respond(request.parameters, run_id, request.eval_id))
            raise RuntimeError(self.message)
        if not self.swallow_callback_errors:
            return super().evaluate(requests, run_id, on_complete)
        results = super().evaluate(requests, run_id)
        for result in results:
            try:
                on_complete(result)
            except OSError:
                pass
        return results
