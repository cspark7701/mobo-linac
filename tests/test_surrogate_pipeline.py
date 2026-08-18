"""
Unit tests for SurrogatePipeline (Task 31 refactoring).
"""

import pytest
import torch
from mobo_linac.models.pipeline import SurrogatePipeline


def test_surrogate_pipeline_fit_and_prediction():
    """Test fitting objective surrogates and making predictions."""
    bounds = torch.tensor([[0.0, 0.0], [1.0, 1.0]], dtype=torch.double)
    train_X = torch.tensor([[0.2, 0.3], [0.5, 0.6], [0.8, 0.9]], dtype=torch.double)
    train_Y = torch.tensor([[-0.1, -0.2], [-0.4, -0.5], [-0.7, -0.8]], dtype=torch.double)

    pipeline = SurrogatePipeline(bounds=bounds)
    assert pipeline.is_fitted is False

    pipeline.fit(train_X, train_Y)
    assert pipeline.is_fitted is True
    assert pipeline.objective_model is not None
    assert pipeline.constraint_model is None

    test_X = torch.tensor([[0.3, 0.4]], dtype=torch.double)
    mean, var = pipeline.predict_objectives(test_X)
    assert mean.shape == (1, 2)
    assert var.shape == (1, 2)

    # Predict feasibility without constraint models returns 1.0
    prob_feas = pipeline.predict_probability_of_feasibility(test_X)
    assert prob_feas.shape == (1,)
    assert prob_feas.item() == pytest.approx(1.0)


def test_surrogate_pipeline_constraint_surrogates():
    """Test fitting constraint surrogates and predicting probability of feasibility."""
    bounds = torch.tensor([[0.0, 0.0], [1.0, 1.0]], dtype=torch.double)
    train_X = torch.tensor([[0.2, 0.3], [0.5, 0.6], [0.8, 0.9]], dtype=torch.double)
    train_Y = torch.tensor([[-0.1], [-0.4], [-0.7]], dtype=torch.double)
    # Generic constraints: values <= 0 mean feasible, > 0 mean infeasible
    train_constraints = torch.tensor([[-0.5], [0.1], [-0.2]], dtype=torch.double)

    pipeline = SurrogatePipeline(bounds=bounds)
    pipeline.fit(train_X, train_Y, train_constraints=train_constraints)

    assert pipeline.constraint_model is not None

    test_X = torch.tensor([[0.2, 0.3]], dtype=torch.double)
    prob_feas = pipeline.predict_probability_of_feasibility(test_X)
    assert prob_feas.shape == (1,)
    assert 0.0 <= prob_feas.item() <= 1.0


def test_surrogate_pipeline_analytical_physical_feasibility():
    """Verify exact analytical Normal CDF feasibility calculation on 7-channel physical linac diagnostics."""
    from mobo_linac.config import ConstraintsConfig

    bounds = torch.tensor([[0.0] * 6, [1.0] * 6], dtype=torch.double)
    train_X = torch.tensor([
        [0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
        [0.2, 0.3, 0.4, 0.5, 0.6, 0.7],
        [0.3, 0.4, 0.5, 0.6, 0.7, 0.8],
        [0.4, 0.5, 0.6, 0.7, 0.8, 0.9],
    ], dtype=torch.double)
    train_Y = torch.tensor([[-1.0e-6, -1.0e-6, -1.0e6]] * 4, dtype=torch.double)

    # 7 Physical channels: [sigma_x, sigma_y, sigma_xp, sigma_yp, sigma_z, energy, transmission]
    # Well within nominal feasible bounds
    train_c = torch.tensor([
        [0.4e-3, 0.4e-3, 0.4e-3, 0.4e-3, 0.4e-3, 200.0e6, 1.0],
        [0.5e-3, 0.5e-3, 0.5e-3, 0.5e-3, 0.5e-3, 200.1e6, 0.99],
        [0.6e-3, 0.6e-3, 0.6e-3, 0.6e-3, 0.6e-3, 199.9e6, 0.98],
        [0.45e-3, 0.45e-3, 0.45e-3, 0.45e-3, 0.45e-3, 200.0e6, 0.995],
    ], dtype=torch.double)

    c_cfg = ConstraintsConfig(
        max_sigma_x_m=1.0e-3,
        max_sigma_y_m=1.0e-3,
        max_sigma_xp_rad=1.0e-3,
        max_sigma_yp_rad=1.0e-3,
        max_sigma_z_m=1.0e-3,
        min_mean_kinetic_energy_eV=195.0e6,
        max_mean_kinetic_energy_eV=205.0e6,
        min_transmission=0.90,
    )

    pipeline = SurrogatePipeline(bounds=bounds, constraints_config=c_cfg)
    pipeline.fit(train_X, train_Y, train_constraints=train_c)

    test_X = torch.tensor([[0.25, 0.35, 0.45, 0.55, 0.65, 0.75]], dtype=torch.double)
    p_feas = pipeline.predict_probability_of_feasibility(test_X)

    assert p_feas.shape == (1,)
    # Since candidates are well within feasible interior, P_feas should be high (> 0.8)
    assert p_feas.item() > 0.8
    assert p_feas.item() <= 1.0

