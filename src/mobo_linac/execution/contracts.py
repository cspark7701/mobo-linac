"""Simulator-independent evaluator protocol and the one validated evaluation entry point.

Every backend (process pool, mock, function adapter, future MPI/Ray/Dask executors)
implements ``evaluate(requests, run_id, on_complete)``. A backend should call
``on_complete`` as each candidate finishes; completions it only returns are published
when ``evaluate`` returns. Campaigns, robustness and verification all go through
:func:`evaluate_requests`.
"""
from dataclasses import dataclass, replace
from typing import Any, Callable, Dict, List, Optional, Protocol, Sequence, Union

from mobo_linac.astra.workdir import format_eval_id
from mobo_linac.evaluation import EvaluationResult, create_evaluation_result
from mobo_linac.execution.requests import EvaluationRequest
from mobo_linac.io.journal import same_evaluation

RawResult = Union[Dict[str, Any], EvaluationResult]


class Evaluator(Protocol):
    def evaluate(self, requests: Sequence[EvaluationRequest], run_id: str,
                 on_complete: Optional[Callable[[RawResult], None]] = None) -> Sequence[RawResult]: ...


@dataclass
class EvaluationCompletion:
    request: EvaluationRequest
    result: EvaluationResult
    details: Dict[str, Any]


def evaluation_identity(value) -> str:
    return format_eval_id(value)


def _decode_completion(raw: RawResult, identities, by_id, run_id: str, config, fallback_index=None):
    """Typed result and raw details of one backend completion, bound to its submitted request."""
    if isinstance(raw, EvaluationResult):
        return replace(raw, evaluation_id=evaluation_identity(raw.evaluation_id)), {}
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
    details["eval_id"] = identity
    details.setdefault("run_id", manifest.get("run_id", run_id))
    details.setdefault("parameters", manifest.get("parameters", by_id[identity].parameters))
    return create_evaluation_result(details, config), details


def evaluate_requests(evaluator: Evaluator, requests: Sequence[EvaluationRequest], *, run_id: str,
                      config, on_complete=None) -> List[EvaluationCompletion]:
    """Validate identities, stream each completion once, and return completions in request order.

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
    completed: Dict[str, EvaluationCompletion] = {}
    errors: List[Exception] = []

    def complete(raw, fallback_index=None):
        try:
            result, details = _decode_completion(raw, identities, by_id, run_id, config, fallback_index)
            if result.evaluation_id not in by_id:
                raise ValueError("Evaluator returned an unexpected candidate identity")
            request = by_id[result.evaluation_id]
            if result.run_id != run_id or result.x_physical != request.parameters:
                raise ValueError("Evaluator completion disagrees with submitted candidate")
            previous = completed.get(result.evaluation_id)
            if previous is not None:
                if not same_evaluation(previous.result, result):
                    raise ValueError("Evaluator returned conflicting candidate completions")
                return
            completion = EvaluationCompletion(request, result, details)
            if on_complete is not None:
                on_complete(completion)
            completed[result.evaluation_id] = completion
        except Exception as error:
            errors.append(error)
            raise

    raw_results = evaluator.evaluate(requests, run_id=run_id, on_complete=complete)
    if errors:
        raise errors[0]
    for index, raw in enumerate(raw_results):
        complete(raw, index)
    if set(completed) != set(identities):
        raise ValueError("Backend returned an incomplete candidate batch")
    return [completed[identity] for identity in identities]
