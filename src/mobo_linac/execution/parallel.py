"""
Process-Safe Parallel Execution Module for ASTRA Candidate Evaluations.

Replaces unsafe shared-thread execution with process-isolated execution using
ProcessPoolExecutor. Guarantees deterministic order, candidate alignment, and
resilience against single-candidate failures.
"""

import multiprocessing
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

from mobo_linac.astra.runner import run_astra_eval


def _worker_eval_task(task_args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Top-level worker task executed by ProcessPoolExecutor.
    Must take serializable arguments dictionary.

    Args:
        task_args: Dictionary containing candidate parameters and configuration.

    Returns:
        Structured evaluation result dictionary.
    """
    candidate_idx = task_args["candidate_idx"]
    parameters = task_args["parameters"]
    run_id = task_args["run_id"]
    eval_id = task_args["eval_id"]
    base_results_dir = task_args.get("base_results_dir", "results")
    template_dir = task_args.get("template_dir", ".")
    template_in = task_args.get("template_in", "astra.in")
    timeout = task_args.get("timeout", 30)
    retries = task_args.get("retries", 0)
    clean_on_success = task_args.get("clean_on_success", False)
    use_symlinks = task_args.get("use_symlinks", False)
    config = task_args.get("config", None)

    attempts = 0
    max_attempts = retries + 1
    last_res: Dict[str, Any] = {}

    while attempts < max_attempts:
        attempts += 1
        try:
            res = run_astra_eval(
                parameters=parameters,
                run_id=run_id,
                eval_id=eval_id,
                base_results_dir=base_results_dir,
                template_dir=template_dir,
                template_in=template_in,
                timeout=timeout,
                clean_on_success=clean_on_success,
                use_symlinks=use_symlinks,
                config=config,
            )
            res["candidate_idx"] = candidate_idx
            res["retries_attempted"] = attempts - 1
            if res["status"] == "success":
                return res
            last_res = res
        except Exception as e:
            last_res = {
                "candidate_idx": candidate_idx,
                "status": "failed",
                "objectives": None,
                "diagnostics": None,
                "eval_dir": None,
                "manifest_path": None,
                "error": str(e),
                "retries_attempted": attempts - 1,
            }

    return last_res


def evaluate_candidates_parallel(
    candidates: Sequence[Sequence[float]],
    run_id: str = "batch_run",
    eval_ids: Optional[Sequence[Union[int, str]]] = None,
    max_workers: Optional[int] = None,
    timeout: int = 30,
    retries: int = 0,
    base_results_dir: Union[str, Path] = "results",
    template_dir: Union[str, Path] = ".",
    template_in: str = "astra.in",
    clean_on_success: bool = False,
    use_symlinks: bool = False,
    mp_context: Optional[str] = None,
    config: Optional[Union[Any, Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """
    Evaluates a batch of candidate parameter vectors in parallel using ProcessPoolExecutor.

    Guarantees that the returned list of results is strictly ordered matching the input candidates.

    Args:
        candidates: Sequence of candidate parameter vectors.
        run_id: Unique identifier for the optimization run.
        eval_ids: Optional list of evaluation IDs matching candidates length.
        max_workers: Maximum number of worker processes.
        timeout: Timeout in seconds for each ASTRA execution.
        retries: Number of retries on transient evaluation failures.
        base_results_dir: Root results output directory.
        template_dir: Source directory for static files and template input.
        template_in: Template ASTRA input file name.
        clean_on_success: If True, remove evaluation working directory after success.
        use_symlinks: Use symlinks for static data files instead of copying.
        mp_context: Multiprocessing start method ('spawn', 'forkserver', 'fork').
        config: Optional MoboConfig or config dictionary for dynamic parameter mapping.

    Returns:
        List of structured result dictionaries aligned with input candidates.
    """
    n_candidates = len(candidates)
    if n_candidates == 0:
        return []

    if eval_ids is None:
        eval_ids_list = [i + 1 for i in range(n_candidates)]
    else:
        if len(eval_ids) != n_candidates:
            raise ValueError(f"eval_ids length ({len(eval_ids)}) must match candidates length ({n_candidates})")
        eval_ids_list = list(eval_ids)

    if max_workers is None or max_workers <= 0:
        cpu_cnt = os.cpu_count() or 1
        max_workers = min(n_candidates, max(1, cpu_cnt))

    # Serialize config if needed for worker processes
    serializable_config = None
    if config is not None:
        if hasattr(config, "__dataclass_fields__"):
            from dataclasses import asdict
            serializable_config = asdict(config)
        elif isinstance(config, dict):
            serializable_config = config

    # Prepare serializable task dictionaries for each worker
    tasks = []
    for idx, (cand, eid) in enumerate(zip(candidates, eval_ids_list)):
        task = {
            "candidate_idx": idx,
            "parameters": [float(p) for p in cand],
            "run_id": run_id,
            "eval_id": eid,
            "base_results_dir": str(base_results_dir),
            "template_dir": str(template_dir),
            "template_in": template_in,
            "timeout": timeout,
            "retries": retries,
            "clean_on_success": clean_on_success,
            "use_symlinks": use_symlinks,
            "config": serializable_config,
        }
        tasks.append(task)

    results: List[Optional[Dict[str, Any]]] = [None] * n_candidates

    # Sequential execution if max_workers == 1 or single candidate
    if max_workers == 1 or n_candidates == 1:
        for idx, task in enumerate(tasks):
            results[idx] = _worker_eval_task(task)
        return [r for r in results if r is not None]

    # ProcessPoolExecutor setup
    ctx = multiprocessing.get_context(mp_context) if mp_context else None
    executor = ProcessPoolExecutor(max_workers=max_workers, mp_context=ctx)

    try:
        future_to_idx = {
            executor.submit(_worker_eval_task, task): idx
            for idx, task in enumerate(tasks)
        }

        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                res = future.result()
                results[idx] = res
            except Exception as e:
                # Catch worker process crash or unhandled exception
                results[idx] = {
                    "candidate_idx": idx,
                    "status": "failed",
                    "objectives": None,
                    "diagnostics": None,
                    "eval_dir": None,
                    "manifest_path": None,
                    "error": f"Worker process crashed: {str(e)}",
                    "retries_attempted": 0,
                }
    finally:
        executor.shutdown(wait=True)

    return [r for r in results if r is not None]


class BatchEvaluator:
    """
    Reusable process-safe batch evaluator for optimization campaigns.
    """

    def __init__(
        self,
        base_results_dir: Union[str, Path] = "results",
        template_dir: Union[str, Path] = ".",
        template_in: str = "astra.in",
        max_workers: Optional[int] = None,
        timeout: int = 30,
        retries: int = 0,
        clean_on_success: bool = False,
        use_symlinks: bool = False,
        mp_context: Optional[str] = None,
        config: Optional[Union[Any, Dict[str, Any]]] = None,
    ):
        self.base_results_dir = base_results_dir
        self.template_dir = template_dir
        self.template_in = template_in
        self.max_workers = max_workers
        self.timeout = timeout
        self.retries = retries
        self.clean_on_success = clean_on_success
        self.use_symlinks = use_symlinks
        self.mp_context = mp_context
        self.config = config

    def evaluate_batch(
        self,
        candidates: Sequence[Sequence[float]],
        run_id: str = "batch_run",
        eval_ids: Optional[Sequence[Union[int, str]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Evaluate candidate batch and return detailed result dictionaries.
        """
        return evaluate_candidates_parallel(
            candidates=candidates,
            run_id=run_id,
            eval_ids=eval_ids,
            max_workers=self.max_workers,
            timeout=self.timeout,
            retries=self.retries,
            base_results_dir=self.base_results_dir,
            template_dir=self.template_dir,
            template_in=self.template_in,
            clean_on_success=self.clean_on_success,
            use_symlinks=self.use_symlinks,
            mp_context=self.mp_context,
            config=self.config,
        )
