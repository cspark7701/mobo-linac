"""Process-isolated benchmark jobs and exclusive ownership of shared reports."""

from contextlib import contextmanager
from dataclasses import dataclass
from functools import wraps
import fcntl
import os
from pathlib import Path
import time
from typing import Any

import torch

from mobo_linac.benchmark_algorithms import get_benchmark_algorithm
from mobo_linac.campaigns.runner import campaign_runner
from mobo_linac.config import config_from_dict
from mobo_linac.utils.logger import configure_logging


@contextmanager
def benchmark_lock(output_dir):
    """Reject competing writers; the persistent lock file contains no campaign data."""
    with (Path(output_dir) / ".benchmark.lock").open("a") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError(f"Another benchmark scheduler or analysis owns {output_dir}.") from None
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def exclusive_benchmark(method):
    """Allow nested report calls by the owner while excluding other runner instances."""
    @wraps(method)
    def wrapped(self, *args, **kwargs):
        if getattr(self, "_owns_benchmark", False):
            return method(self, *args, **kwargs)
        with benchmark_lock(self.output_dir):
            self._owns_benchmark = True
            try:
                return method(self, *args, **kwargs)
            finally:
                self._owns_benchmark = False
    return wrapped


@dataclass(frozen=True)
class CampaignJob:
    config: dict
    source_path: str | None
    algorithm: str
    seed: int
    output_dir: str
    initial: int
    batches: int
    batch_size: int
    budget: int
    workers: int
    device: str
    reference: list[float]
    evaluator: Any
    threads: int
    log_level: int


def run_campaign_job(job: CampaignJob, *, isolated: bool = True) -> dict:
    """Only per-run outputs are written here; the parent validates and publishes completion."""
    if isolated:
        torch.set_num_threads(job.threads)
        configure_logging(level=job.log_level)
    config = config_from_dict(job.config)
    config.source_path = Path(job.source_path) if job.source_path is not None else None
    spec = get_benchmark_algorithm(job.algorithm)
    options = {"num_initial_samples": job.initial, "num_batches": job.batches,
               "batch_size": job.batch_size, "num_workers": job.workers,
               "seed": job.seed, "acquisition": spec.acquisition}
    runner = campaign_runner(config, options, optimization_mode=spec.optimization_mode,
                             output_dir=job.output_dir, constrained=spec.constrained,
                             total_eval_budget=job.budget, evaluator=job.evaluator,
                             reporting_ref_point=job.reference, device=job.device)
    start = time.time()
    try:
        results, _, _ = runner.run()
        return {"evaluation_count": len(results), "pid": os.getpid(), "started_at": start,
                "finished_at": time.time(), "workers": job.workers}
    finally:
        if job.evaluator is not None and hasattr(job.evaluator, "close"):
            try:
                job.evaluator.close()
            except Exception:
                pass
