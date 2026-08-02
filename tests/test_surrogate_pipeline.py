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
    # Constraints: values <= 0 mean feasible, > 0 mean infeasible
    train_constraints = torch.tensor([[-0.5], [0.1], [-0.2]], dtype=torch.double)

    pipeline = SurrogatePipeline(bounds=bounds)
    pipeline.fit(train_X, train_Y, train_constraints=train_constraints)

    assert pipeline.constraint_model is not None

    test_X = torch.tensor([[0.2, 0.3]], dtype=torch.double)
    prob_feas = pipeline.predict_probability_of_feasibility(test_X)
    assert prob_feas.shape == (1,)
    assert 0.0 <= prob_feas.item() <= 1.0
