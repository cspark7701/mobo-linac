"""
Process-isolated ASTRA evaluation backend.

``ProcessPoolEvaluator`` keeps one ``ProcessPoolExecutor`` for its lifetime and runs every
candidate in a worker process (also with a single worker), so crashes and environment side
effects behave the same regardless of the worker count. ``in_process=True`` is an explicit
opt-in for debugging. Results are returned aligned with the submitted requests.

Workers start with the ``spawn`` method on every platform. Forking the parent, which holds
PyTorch and BLAS threads, can deadlock a child (Python 3.12 warns about it). Spawned workers
import the package afresh and receive everything they need in the serialized ``WorkerTask``.
"""

from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass
import multiprocessing
import os
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Union
import uuid
import weakref

from mobo_linac.requests import EvaluationRequest
from mobo_linac.status import DEFAULT_RETRY_STATUSES, SimulationStatus, decode_status
from mobo_linac.astra.runner import resolve_template_dir
from mobo_linac.astra.runner import run_astra_eval as execute
from mobo_linac.config import MoboConfig
from mobo_linac.config import config_from_dict


def run_astra_eval(**kwargs):
    """Lazy backend dispatch; also preserves the public worker injection seam."""
    return execute(**kwargs)


@dataclass
class WorkerTask:
    """Serializable description of one candidate evaluation sent to a worker process."""

    candidate_idx: int
    request: Dict[str, Any]  # EvaluationRequest.to_dict()
    run_id: str
    base_results_dir: str
    template_dir: str
    timeout: int = 30
    retries: int = 0
    clean_on_success: bool = False
    use_symlinks: bool = False
    config: Optional[Dict[str, Any]] = None  # asdict(MoboConfig)

    @property
    def parameters(self) -> List[float]:
        return [float(value) for value in self.request["parameters"]]

    @property
    def eval_id(self):
        return self.request["eval_id"]

    def retry_statuses(self) -> set:
        execution = (self.config or {}).get("execution") or {}
        return set(execution.get("retry_statuses") or DEFAULT_RETRY_STATUSES)


def failure_result(task: WorkerTask, status: SimulationStatus, error: str, *, attempt_id=None,
                   attempt_history=None, retries_attempted: int = 0) -> Dict[str, Any]:
    """The one failure record layout (worker exception or crashed/broken pool), with the full request."""
    return {
        "candidate_idx": task.candidate_idx, "run_id": task.run_id, "eval_id": task.eval_id,
        "parameters": task.parameters, "request": task.request, "status": status.value,
        "objectives": None, "diagnostics": None, "eval_dir": None, "manifest_path": None,
        "error": error, "retries_attempted": retries_attempted, "attempt_id": attempt_id,
        "attempt_history": list(attempt_history or []),
    }


def run_worker_task(task: WorkerTask) -> Dict[str, Any]:
    """Evaluate one candidate with category-aware retries (only infrastructure outcomes retry)."""
    config = config_from_dict(task.config)  # the serialized configuration is converted once per task
    retry_statuses = task.retry_statuses()
    max_attempts = task.retries + 1
    history: List[Dict[str, Any]] = []
    last: Dict[str, Any] = {}
    for attempt in range(1, max_attempts + 1):
        attempt_id = "attempt_" + uuid.uuid4().hex
        try:
            res = run_astra_eval(
                parameters=task.parameters, run_id=task.run_id, eval_id=task.eval_id,
                base_results_dir=task.base_results_dir, template_dir=task.template_dir,
                timeout=task.timeout, clean_on_success=task.clean_on_success,
                use_symlinks=task.use_symlinks, config=config, attempt_id=attempt_id, retry_index=attempt - 1,
                namelist_overrides=task.request.get("namelist_overrides"),
                source_settings=task.request.get("source_settings") or {},
                request_metadata=task.request.get("metadata") or {},
            )
        except Exception as error:
            message = f"{type(error).__name__}: {error}"
            retry = attempt < max_attempts and SimulationStatus.UNHANDLED_EXCEPTION.value in retry_statuses
            history.append({"attempt_id": attempt_id, "manifest_path": None,
                            "status": SimulationStatus.UNHANDLED_EXCEPTION.value, "error": message, "retried": retry})
            last = failure_result(task, SimulationStatus.UNHANDLED_EXCEPTION, message, attempt_id=attempt_id,
                                  attempt_history=history, retries_attempted=attempt - 1)
            if not retry:
                return last
            continue
        for key, value in (("run_id", task.run_id), ("eval_id", task.eval_id), ("parameters", task.parameters),
                           ("request", task.request), ("attempt_id", attempt_id)):
            res.setdefault(key, value)
        res["candidate_idx"] = task.candidate_idx
        res["retries_attempted"] = attempt - 1
        status = decode_status(res["status"])
        history.append({"attempt_id": res["attempt_id"], "manifest_path": res.get("manifest_path"),
                        "status": status.value, "retried": False})
        res["attempt_history"] = list(history)
        if status is SimulationStatus.SUCCESS or status.value not in retry_statuses:
            return res
        history[-1]["retried"] = attempt < max_attempts
        last = res
    return last


def _positive_int(name: str, value) -> int:
    if type(value) is not int or value < 1:
        raise ValueError(f"{name} must be a positive integer.")
    return value


# Worker start method; "fork" is only safe for test doubles that never use threaded libraries.
DEFAULT_START_METHOD = "spawn"


class ProcessPoolEvaluator:
    """Process-isolated ASTRA backend with a persistent worker pool."""

    def __init__(
        self,
        config,
        base_results_dir: Union[str, Path] = "results",
        template_dir: Optional[Union[str, Path]] = None,
        max_workers: Optional[int] = None,
        timeout: Optional[int] = None,
        retries: Optional[int] = None,
        clean_on_success: Optional[bool] = None,
        use_symlinks: bool = False,
        mp_context: Optional[str] = None,
        in_process: bool = False,
    ):
        if not isinstance(config, MoboConfig):
            raise TypeError("ProcessPoolEvaluator requires the campaign MoboConfig.")
        config.validate()
        execution = config.execution
        self.config = config
        self.base_results_dir = Path(base_results_dir)
        self.template_dir = Path(template_dir).resolve() if template_dir is not None else resolve_template_dir(config)
        self.max_workers = _positive_int("max_workers", max_workers if max_workers is not None
                                         else min(execution.max_workers, os.cpu_count() or 1))
        self.timeout = _positive_int("timeout", execution.timeout_sec if timeout is None else timeout)
        self.retries = execution.retries if retries is None else retries
        if type(self.retries) is not int or self.retries < 0:
            raise ValueError("retries must be a nonnegative integer.")
        self.clean_on_success = execution.clean_on_success if clean_on_success is None else bool(clean_on_success)
        self.use_symlinks = use_symlinks
        mp_context = DEFAULT_START_METHOD if mp_context is None else mp_context
        if mp_context not in multiprocessing.get_all_start_methods():
            raise ValueError(f"mp_context must be one of {multiprocessing.get_all_start_methods()}.")
        self.mp_context = mp_context
        self.in_process = in_process
        self._executor: Optional[ProcessPoolExecutor] = None

    def _pool(self) -> ProcessPoolExecutor:
        if self._executor is None:
            self._executor = ProcessPoolExecutor(max_workers=self.max_workers,
                                                 mp_context=multiprocessing.get_context(self.mp_context))
            weakref.finalize(self, self._executor.shutdown, wait=True)
        return self._executor

    def close(self) -> None:
        if self._executor is not None:
            self._executor.shutdown(wait=True)
            self._executor = None

    def __enter__(self) -> "ProcessPoolEvaluator":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def tasks(self, requests: Sequence[EvaluationRequest], run_id: str) -> List[WorkerTask]:
        config = asdict(self.config)
        return [WorkerTask(candidate_idx=index, request=request.to_dict(), run_id=run_id,
                           base_results_dir=str(self.base_results_dir), template_dir=str(self.template_dir),
                           timeout=self.timeout, retries=self.retries,
                           clean_on_success=self.clean_on_success, use_symlinks=self.use_symlinks, config=config)
                for index, request in enumerate(requests)]

    def evaluate(self, requests: Sequence[EvaluationRequest], run_id: str = "batch_run",
                 on_complete: Optional[Callable[[Dict[str, Any]], None]] = None) -> List[Dict[str, Any]]:
        """Evaluate every request; returns raw results aligned with ``requests``."""
        for request in requests:
            request.validate(self.config)
        tasks = self.tasks(requests, run_id)
        results: List[Optional[Dict[str, Any]]] = [None] * len(tasks)

        def publish(index, result):
            results[index] = result
            if on_complete is not None:
                on_complete(result)

        if self.in_process:
            for index, task in enumerate(tasks):
                publish(index, run_worker_task(task))
        else:
            futures = {}
            for index, task in enumerate(tasks):
                try:
                    futures[self._pool().submit(run_worker_task, task)] = index
                except Exception as error:  # broken pool during submission
                    publish(index, failure_result(task, SimulationStatus.WORKER_CRASH, f"Worker process crashed: {error}"))
            for future in as_completed(futures):
                index = futures[future]
                try:
                    result = future.result()
                except Exception as error:  # crashed worker process
                    result = failure_result(tasks[index], SimulationStatus.WORKER_CRASH, f"Worker process crashed: {error}")
                publish(index, result)
        if any(result is None for result in results):
            raise RuntimeError("Evaluation backend lost a submitted candidate.")
        return results
