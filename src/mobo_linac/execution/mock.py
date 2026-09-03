"""
Canonical Mock Evaluator Infrastructure for mobo_linac.

Provides lightweight, deterministic, and failure-configurable mock evaluators
for unit tests, dry-runs, and offline CI pipelines without requiring the ASTRA binary.
"""

from pathlib import Path
import time
from typing import Any, Callable, Dict, List, Optional, Sequence, Union


class MockBatchEvaluator:
    """
    Canonical mock batch evaluator providing realistic linac physics responses,
    intermittent failure injection, and streaming completion callbacks.
    """

    def __init__(
        self,
        run_dir: Optional[Union[str, Path]] = None,
        failure_rate: float = 0.0,
        fail_eval_ids: Optional[Sequence[Union[int, str]]] = None,
        delay_sec: float = 0.0,
        noise_std: float = 0.0,
    ):
        self.run_dir = Path(run_dir) if run_dir is not None else Path("results/mock_eval")
        self.failure_rate = float(failure_rate)
        self.fail_eval_ids = set(str(eid) for eid in fail_eval_ids) if fail_eval_ids else set()
        self.delay_sec = float(delay_sec)
        self.noise_std = float(noise_std)

    def _generate_candidate_result(
        self,
        candidate: Sequence[float],
        run_id: str,
        eval_id_str: str,
    ) -> Dict[str, Any]:
        """Generates a structured dictionary matching ASTRA evaluation result schema."""
        cand_list = [float(x) for x in candidate]
        eval_work_dir = self.run_dir / eval_id_str

        # Check explicit failure injection
        if eval_id_str in self.fail_eval_ids or (self.failure_rate > 0 and sum(cand_list) % 1.0 < self.failure_rate):
            return {
                "status": "failed",
                "eval_id": eval_id_str,
                "run_id": run_id,
                "parameters": cand_list,
                "objectives": None,
                "diagnostics": None,
                "eval_dir": str(eval_work_dir),
                "manifest_path": None,
                "error": "Simulated evaluation failure in mock environment",
                "timestamps": {"duration_sec": 0.01},
            }

        # Deterministic physical beam response
        sum_cand = sum(cand_list) if cand_list else 0.0
        ex = float(0.1e-6 + 0.01e-6 * (sum_cand % 5))
        ey = float(0.1e-6 + 0.01e-6 * (sum_cand % 7))
        se = float(0.5e6 + 0.05e6 * (sum_cand % 3))

        return {
            "status": "success",
            "eval_id": eval_id_str,
            "run_id": run_id,
            "parameters": cand_list,
            "objectives": {
                "norm_emit_x": ex,
                "norm_emit_y": ey,
                "sigma_energy": se,
            },
            "diagnostics": {
                "sigma_x_m": 0.5e-3,
                "sigma_y_m": 0.5e-3,
                "sigma_xp_rad": 0.4e-3,
                "sigma_yp_rad": 0.4e-3,
                "sigma_z_m": 0.5e-3,
                "mean_kinetic_energy_eV": 200.0e6,
                "transmission_fraction": 1.0,
            },
            "timestamps": {"duration_sec": max(0.01, self.delay_sec)},
            "eval_dir": str(eval_work_dir),
            "manifest_path": str(eval_work_dir / "manifest.json"),
            "error": None,
        }

    def __call__(
        self,
        parameters: Sequence[float],
        run_id: str = "mock_run",
        eval_id: Union[int, str] = 1,
    ) -> Dict[str, Any]:
        """Direct callable interface for single candidate evaluation."""
        eval_id_str = f"eval_{eval_id:06d}" if isinstance(eval_id, int) else str(eval_id)
        if self.delay_sec > 0:
            time.sleep(self.delay_sec)
        return self._generate_candidate_result(parameters, run_id, eval_id_str)

    def evaluate_batch(
        self,
        candidates: Sequence[Sequence[float]],
        run_id: str = "mock_batch",
        eval_ids: Optional[Sequence[Union[int, str]]] = None,
        on_evaluation_complete: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> List[Dict[str, Any]]:
        """Evaluates batch of candidates matching BatchEvaluator.evaluate_batch()."""
        raw_results: List[Dict[str, Any]] = []
        for idx, cand in enumerate(candidates):
            if eval_ids and idx < len(eval_ids):
                raw_eid = eval_ids[idx]
                eval_id_str = f"eval_{raw_eid:06d}" if isinstance(raw_eid, int) else str(raw_eid)
            else:
                eval_id_str = f"eval_{idx+1:06d}"

            if self.delay_sec > 0:
                time.sleep(self.delay_sec)

            res = self._generate_candidate_result(cand, run_id, eval_id_str)
            raw_results.append(res)

            if on_evaluation_complete is not None:
                try:
                    on_evaluation_complete(res)
                except Exception:
                    pass

        return raw_results


# Alias for backward compatibility
CliMockEvaluator = MockBatchEvaluator
