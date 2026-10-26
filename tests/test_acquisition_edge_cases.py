from types import SimpleNamespace

"""Acquisition validation checks placement and budgets before touching an optimizer."""

import pytest
import torch

from mobo_linac.acquisition import mobo
from mobo_linac.campaigns.analysis import compute_bootstrap_ci, compute_aggregate_benchmark_metrics


@pytest.mark.parametrize(
    "options",
    [
        {"batch_size": 0},
        {"bounds": torch.zeros(2, 1)},
        {"sobol_engine": torch.quasirandom.SobolEngine(2)},
        {"fallback_seed": -1},
        {"options": {"maxiter": 0}},
    ],
)
def test_invalid_proposal_inputs(options):
    arguments = dict(acq_func=torch.nn.Identity(), bounds=torch.tensor([[0.0], [1.0]], dtype=torch.double))
    arguments.update(options)
    with pytest.raises(ValueError):
        mobo.generate_next_candidates(**arguments)


def test_acquisition_output_count_and_type():
    with pytest.raises(ValueError):
        mobo.SliceObjective(0)
    x = torch.tensor([[0.1], [0.8]], dtype=torch.double)
    y = torch.cat((x, x), dim=1)
    with pytest.raises(ValueError, match="Unsupported acquisition"):
        mobo.build_acquisition_function(None, x, y, torch.tensor([-1.0, -1.0]), acq_type="bad")


def test_device_placement_errors_and_feasibility_migration(monkeypatch):
    bounds = torch.tensor([[0.0], [1.0]], dtype=torch.double)
    mixed = torch.nn.Module()
    mixed.register_buffer("cpu_buffer", torch.ones(1))
    mixed.register_buffer("meta", torch.ones(1, device="meta"))
    with pytest.raises(ValueError, match="one device"):
        mobo.generate_next_candidates(mixed, bounds)
    cpu = torch.nn.Linear(1, 1).double()
    monkeypatch.setattr(mobo, "get_device", lambda device: torch.device("cuda:0"))
    with pytest.raises(ValueError, match="placement"):
        mobo.generate_next_candidates(cpu, bounds, device="cuda:0")
    moved = []

    class Mask:
        device = torch.device("meta")

        def to(self, device):
            moved.append(device)
            return torch.zeros(2, dtype=torch.bool)

    monkeypatch.setattr(
        mobo,
        "_MULTIOBJECTIVE_FACTORY",
        {mobo.Acquisition.qLogEHVI: (lambda **kwargs: SimpleNamespace(to=lambda **placement: kwargs), False)},
    )
    x = torch.tensor([[0.1], [0.8]], dtype=torch.double)
    y = torch.cat((x, x), dim=1)
    result = mobo.build_acquisition_function(
        None, x, y, torch.tensor([-1.0, -1.0]), train_feas_mask=Mask(), acq_type="qLogEHVI"
    )
    assert moved == [torch.device("cpu")] and "partitioning" in result


def test_bootstrap_and_empty_algorithm_inputs():
    import numpy as np

    with pytest.raises(ValueError, match="2D"):
        compute_bootstrap_ci(np.ones(3))
    aggregate, summary = compute_aggregate_benchmark_metrics({"empty": {}})
    assert aggregate.empty and summary.empty
