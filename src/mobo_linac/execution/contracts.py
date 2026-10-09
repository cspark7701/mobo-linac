"""Simulator-independent request protocol and compatibility boundary.

Built-in backends explicitly advertise streaming. Legacy batch backends default
to completion at return; they can opt into streaming with the same capability.
"""
from dataclasses import dataclass, replace
from typing import Any, Callable, Dict, List, Optional, Protocol, Sequence, Union

from mobo_linac.evaluation import EvaluationResult, create_evaluation_result
from mobo_linac.execution.requests import EvaluationRequest
from mobo_linac.io.journal import same_evaluation
from mobo_linac.astra.workdir import format_eval_id

RawResult = Union[Dict[str, Any], EvaluationResult]


class RequestEvaluator(Protocol):
    supports_completion_callback: bool

    def evaluate_requests(self, requests: Sequence[EvaluationRequest], run_id: str,
                          on_evaluation_complete: Optional[Callable[[RawResult], None]] = None
                          ) -> Sequence[RawResult]: ...


@dataclass
class EvaluationCompletion:
    request: EvaluationRequest
    result: EvaluationResult
    details: Dict[str, Any]


def evaluation_identity(value):
    return format_eval_id(value)


def evaluate_requests(evaluator, requests: Sequence[EvaluationRequest], *, run_id: str,
                      config, on_complete=None) -> List[EvaluationCompletion]:
    """Validate identities, stream once, and return completions in request order.

    Legacy evaluate_batch implementations cannot execute source/namelist changes.
    Callback errors remain authoritative even if a backend swallows them.
    """
    identities = [evaluation_identity(request.eval_id) for request in requests]
    if len(set(identities)) != len(identities):
        raise ValueError("Duplicate evaluation request identity")
    for request in requests:
        request.validate(config)
    if not requests:
        return []
    by_id = dict(zip(identities, requests))
    completed = {}
    callback_error = None

    def complete(raw, fallback_index=None):
        nonlocal callback_error
        try:
            if isinstance(raw, EvaluationResult):
                identity = evaluation_identity(raw.evaluation_id)
                result, details = replace(raw, evaluation_id=identity), {}
            else:
                details = dict(raw)
                manifest = details.get("manifest") or {}
                identity = details.get("eval_id", manifest.get("eval_id"))
                if identity is None:
                    index = details.get("candidate_idx", fallback_index)
                    if type(index) is not int or not 0 <= index < len(identities):
                        raise ValueError("Evaluator completion lacks a stable candidate identity")
                    identity = identities[index]
                identity = evaluation_identity(identity)
                if identity not in by_id:
                    raise ValueError("Evaluator returned an unexpected candidate identity")
                request = by_id[identity]
                details["eval_id"] = identity
                details.setdefault("run_id", manifest.get("run_id", run_id))
                details.setdefault("parameters", manifest.get("parameters", request.parameters))
                result = create_evaluation_result(details, config)
            if identity not in by_id:
                raise ValueError("Evaluator returned an unexpected candidate identity")
            request = by_id[identity]
            if result.run_id != run_id or result.x_physical != request.parameters:
                raise ValueError("Evaluator completion disagrees with submitted candidate")
            if identity in completed:
                if not same_evaluation(completed[identity].result, result):
                    raise ValueError("Evaluator returned conflicting candidate completions")
                return
            completion = EvaluationCompletion(request, result, details)
            if on_complete is not None:
                on_complete(completion)
            completed[identity] = completion
        except Exception as error:
            callback_error = error
            raise

    kwargs = {"run_id": run_id}
    if getattr(evaluator, "supports_completion_callback", False):
        kwargs["on_evaluation_complete"] = complete
    if hasattr(evaluator, "evaluate_requests"):
        raw_results = evaluator.evaluate_requests(requests, **kwargs)
    else:
        if any(r.namelist_overrides or r.source_settings or r.metadata for r in requests):
            raise ValueError("Complete evaluation requests require a request evaluator")
        raw_results = evaluator.evaluate_batch([r.parameters for r in requests],
                                               eval_ids=[r.eval_id for r in requests], **kwargs)
    if callback_error is not None:
        raise callback_error
    for index, raw in enumerate(raw_results):
        complete(raw, index)
    if set(completed) != set(identities):
        raise ValueError("Backend returned an incomplete candidate batch")
    return [completed[identity] for identity in identities]
