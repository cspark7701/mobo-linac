"""
Unit tests for Parameter-to-ASTRA Key Mapping and Feasibility Mask Shape (Task 08).
"""

import pytest
import torch

from mobo_linac.config import load_config
from mobo_linac.evaluation import EvaluationResult, create_evaluation_result
from mobo_linac.io.results import get_train_tensors


def test_parameter_key_mapping_and_coupled_phases(sample_config):
    """
    Verify 6D candidate parameter mapping to 8 ASTRA input variables
    and coupled cavity phase expansion.
    """
    params = [0.22, 1.25, -2.5, 35.0, -40.0, 310.0]

    # Mapping checks in config design variables
    dvs = sample_config.design_variables
    assert len(dvs) == 6

    assert dvs[0].astra_key == "solenoid:maxb(1)"
    assert dvs[1].astra_key == "quadrupole:q_grad(1)"
    assert dvs[2].astra_key == "quadrupole:q_grad(2)"
    assert dvs[3].astra_key == "cavity:phi(1)"

    # Coupled cavity phase 2 & 3
    assert dvs[4].is_coupled is True
    assert dvs[4].coupled_targets == ["cavity:phi(2)", "cavity:phi(3)"]

    # Coupled cavity phase 4 & 5
    assert dvs[5].is_coupled is True
    assert dvs[5].coupled_targets == ["cavity:phi(4)", "cavity:phi(5)"]


def test_feasibility_mask_shape(sample_config):
    """
    Verify that feasibility mask shape is strictly 1D tensor of length N.
    """
    results = [
        EvaluationResult(
            evaluation_id=f"eval_{i:06d}",
            run_id="shape_test",
            x_physical=[0.2, 1.0, -1.0, 0.0, 0.0, 0.0],
            objectives_physical=[1.0e-6, 1.0e-6, 5.0e4],
            objectives_model=[-1.0e-6, -1.0e-6, -5.0e4],
            diagnostics={"sigma_x": 0.8e-3, "mean_kinetic_energy": 200.0e6},
            simulation_valid=True,
            physically_feasible=(i % 2 == 0),
            failure_category="SUCCESS" if (i % 2 == 0) else "INFEASIBLE_BEAM",
        )
        for i in range(10)
    ]

    train_X, train_Y, train_feas_mask = get_train_tensors(results, exclude_invalid=True)

    assert train_X.shape == (10, 6)
    assert train_Y.shape == (10, 3)
    assert train_feas_mask.shape == (10,)  # 1D tensor shape [N]
    assert train_feas_mask.dtype == torch.bool
