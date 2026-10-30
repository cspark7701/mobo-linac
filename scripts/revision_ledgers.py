"""Shared ledger access for the round3 analyses of the archived primary and Sobol-arm runs.

``load_ledgers`` reads the ``evaluations.csv`` ledger of every run of the four arms, and
``feasible`` applies the production profile to the recorded diagnostics, optionally after
scaling the beam sizes and divergences or the bunch length or shifting the mean energy.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ARMS = {"constrained_qlognehvi": ROOT / "results/paper_production/04_primary/benchmark/per_seed",
        "unconstrained_qlognehvi": ROOT / "results/paper_production/04_primary/benchmark/per_seed",
        "scalarized_bo": ROOT / "results/paper_production/04_primary/benchmark/per_seed",
        "sobol": ROOT / "results/revision_round2/sobol"}
SEEDS = range(42, 52)
N_INIT = 16
TRANSVERSE = ("sigma_x_m", "sigma_y_m", "sigma_xp_rad", "sigma_yp_rad")


def feasible(frame: pd.DataFrame, size: float = 1.0, bunch: float = 1.0, energy: float = 0.0) -> pd.Series:
    """Production-profile classification after scaling the recorded diagnostics."""
    ok = (frame[list(TRANSVERSE)] * size <= 1e-3).all(axis=1)
    ok &= frame.sigma_z_m * bunch <= 1e-3
    shifted = frame.mean_kinetic_energy_eV + energy
    ok &= (shifted >= 195e6) & (shifted <= 205e6) & (frame.transmission_fraction >= 0.90)
    return ok


def load_ledgers(arms: dict = ARMS) -> pd.DataFrame:
    frames = []
    for arm, base in arms.items():
        for seed in SEEDS:
            run = f"{arm}_seed_{seed}"
            frame = pd.read_csv(base / run / "evaluations.csv")
            frames.append(frame.assign(arm=arm, seed=seed, run=run,
                                       index_in_run=frame.evaluation_id.str[-6:].astype(int)))
    return pd.concat(frames, ignore_index=True)
