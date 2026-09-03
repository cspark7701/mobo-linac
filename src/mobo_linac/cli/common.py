"""
Shared argument mixins and mock evaluators for the mobo_linac CLI.
"""

import argparse
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union


class CliMockEvaluator:
    """Mock evaluator for CLI testing without requiring ASTRA binary."""

    def __init__(self, run_dir: Path):
        self.run_dir = Path(run_dir)

    def evaluate_batch(
        self,
        candidates: Sequence[Sequence[float]],
        run_id: str,
        eval_ids: Optional[Sequence[Union[int, str]]] = None,
    ) -> List[Dict[str, Any]]:
        raw_results = []
        for idx, cand in enumerate(candidates):
            eval_id_str = (
                f"eval_{eval_ids[idx]:06d}"
                if eval_ids and idx < len(eval_ids)
                else f"eval_{idx+1:06d}"
            )
            raw_results.append({
                "status": "success",
                "eval_id": eval_id_str,
                "run_id": run_id,
                "parameters": cand,
                "objectives": {
                    "norm_emit_x": float(0.1e-6 + 0.01e-6 * (sum(cand) % 5)),
                    "norm_emit_y": float(0.1e-6 + 0.01e-6 * (sum(cand) % 7)),
                    "sigma_energy": float(0.5e6 + 0.05e6 * (sum(cand) % 3)),
                },
                "diagnostics": {
                    "sigma_x_m": 0.5e-3,
                    "sigma_y_m": 0.5e-3,
                    "sigma_xp_rad": 0.5e-3,
                    "sigma_yp_rad": 0.5e-3,
                    "sigma_z_m": 0.5e-3,
                    "mean_kinetic_energy_eV": 200.0e6,
                    "transmission_fraction": 1.0,
                },
                "timestamps": {"duration_sec": 0.1},
                "eval_dir": str(self.run_dir / eval_id_str),
            })
        return raw_results


def add_common_run_args(subparser: argparse.ArgumentParser) -> None:
    """Adds standard Bayesian optimization execution arguments to a subparser."""
    subparser.add_argument(
        "--config",
        type=str,
        default="configs/publication.yaml",
        help="Path to config file",
    )
    subparser.add_argument(
        "--n-iterations",
        type=int,
        default=300,
        help="Total BO iterations",
    )
    subparser.add_argument(
        "-b",
        "-q",
        "--batch-size",
        "--batch_size",
        dest="batch_size",
        type=int,
        default=8,
        help="Batch size for q-MOBO candidate proposals",
    )
    subparser.add_argument(
        "--num-initial-samples",
        type=int,
        default=16,
        help="Initial random Sobol samples",
    )
    subparser.add_argument(
        "--num-workers",
        type=int,
        default=4,
        help="Number of parallel worker processes",
    )
    subparser.add_argument(
        "-a",
        "--acquisition",
        type=str,
        choices=["qLogNEHVI", "qLogEHVI", "qEHVI", "qNEHVI"],
        default="qLogNEHVI",
        help="Acquisition function ('qLogNEHVI', 'qLogEHVI', 'qEHVI', 'qNEHVI')",
    )
    subparser.add_argument(
        "--device",
        type=str,
        default="auto",
        help="Target PyTorch compute device ('auto', 'cuda', 'cuda:0', 'cpu')",
    )
    subparser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed",
    )
    subparser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Custom output directory",
    )
    subparser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned execution details without running ASTRA",
    )
    subparser.add_argument(
        "--mock-evaluator",
        action="store_true",
        help="Use fast mock evaluator for testing without ASTRA binary",
    )
