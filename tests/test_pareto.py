"""
Unit tests for Feasible Pareto Extraction and Representative Candidate Selection (Task 08).
"""

import pytest
import numpy as np
import torch

from mobo_linac.evaluation import EvaluationResult, FailureCategory
from mobo_linac.metrics.pareto import (
    compute_crowding_distances,
    detect_and_report_candidate_duplicates,
    extract_pareto_sets,
    select_representative_pareto_candidates,
)

from mobo_linac.config import load_config as _load_test_config
TEST_CONFIG = _load_test_config("configs/mobo_200MeV.yaml")


@pytest.fixture
def synthetic_results_with_dominated():
    """
    Creates a synthetic set of EvaluationResults containing:
    - 3 Non-dominated feasible Pareto points
    - 2 Dominated feasible points (worse in all objectives)
    - 1 Infeasible point
    """
    # Candidate 1: Extreme emit_x (0.5 um, 1.5 um, 1.0 MeV) - Feasible Pareto
    c1 = EvaluationResult(
        evaluation_id="eval_p1", run_id="r", x_physical=[0.1]*6,
        objectives_physical=[0.5e-6, 1.5e-6, 1.0e6], objectives_model=[-0.5e-6, -1.5e-6, -1.0e6],
        simulation_valid=True, physically_feasible=True, failure_category=FailureCategory.SUCCESS.value, runtime_s=1.0
    )
    # Candidate 2: Extreme emit_y (1.5 um, 0.5 um, 1.0 MeV) - Feasible Pareto
    c2 = EvaluationResult(
        evaluation_id="eval_p2", run_id="r", x_physical=[0.2]*6,
        objectives_physical=[1.5e-6, 0.5e-6, 1.0e6], objectives_model=[-1.5e-6, -0.5e-6, -1.0e6],
        simulation_valid=True, physically_feasible=True, failure_category=FailureCategory.SUCCESS.value, runtime_s=1.0
    )
    # Candidate 3: Extreme energy spread (1.2 um, 1.2 um, 0.3 MeV) - Feasible Pareto
    c3 = EvaluationResult(
        evaluation_id="eval_p3", run_id="r", x_physical=[0.3]*6,
        objectives_physical=[1.2e-6, 1.2e-6, 0.3e6], objectives_model=[-1.2e-6, -1.2e-6, -0.3e6],
        simulation_valid=True, physically_feasible=True, failure_category=FailureCategory.SUCCESS.value, runtime_s=1.0
    )
    # Candidate 4: Dominated Feasible point (2.0 um, 2.0 um, 2.0 MeV) - DOMINATED BY C1, C2, C3
    c4 = EvaluationResult(
        evaluation_id="eval_dom1", run_id="r", x_physical=[0.4]*6,
        objectives_physical=[2.0e-6, 2.0e-6, 2.0e6], objectives_model=[-2.0e-6, -2.0e-6, -2.0e6],
        simulation_valid=True, physically_feasible=True, failure_category=FailureCategory.SUCCESS.value, runtime_s=1.0
    )
    # Candidate 5: Dominated Feasible point (3.0 um, 3.0 um, 3.0 MeV) - DOMINATED BY ALL
    c5 = EvaluationResult(
        evaluation_id="eval_dom2", run_id="r", x_physical=[0.5]*6,
        objectives_physical=[3.0e-6, 3.0e-6, 3.0e6], objectives_model=[-3.0e-6, -3.0e-6, -3.0e6],
        simulation_valid=True, physically_feasible=True, failure_category=FailureCategory.SUCCESS.value, runtime_s=1.0
    )
    # Candidate 6: Infeasible point
    c6 = EvaluationResult(
        evaluation_id="eval_inf", run_id="r", x_physical=[0.6]*6,
        objectives_physical=[0.1e-6, 0.1e-6, 0.1e6], objectives_model=[-0.1e-6, -0.1e-6, -0.1e6],
        simulation_valid=True, physically_feasible=False, failure_category=FailureCategory.SUCCESS.value, runtime_s=1.0
    )

    return [c1, c2, c3, c4, c5, c6]


def test_extract_pareto_sets(synthetic_results_with_dominated):
    """Verify extract_pareto_sets correctly separates feasible Pareto from dominated points."""
    pareto_sets = extract_pareto_sets(synthetic_results_with_dominated, TEST_CONFIG)

    feas_pareto_ids = [r.evaluation_id for r in pareto_sets["feasible_pareto"]]
    feas_dom_ids = [r.evaluation_id for r in pareto_sets["feasible_dominated"]]

    assert "eval_p1" in feas_pareto_ids
    assert "eval_p2" in feas_pareto_ids
    assert "eval_p3" in feas_pareto_ids

    assert "eval_dom1" in feas_dom_ids
    assert "eval_dom2" in feas_dom_ids

    # Infeasible candidate should not be in feasible_pareto or feasible_dominated
    assert "eval_inf" not in feas_pareto_ids
    assert "eval_inf" not in feas_dom_ids


def test_select_representative_pareto_candidates_excludes_dominated(synthetic_results_with_dominated):
    """Verify representative candidate selection chooses ONLY from feasible Pareto set."""
    selected_cands = select_representative_pareto_candidates(synthetic_results_with_dominated, TEST_CONFIG)

    selected_ids = [r.evaluation_id for r in selected_cands.values()]

    # Dominated points must NEVER be selected as representative candidates
    assert "eval_dom1" not in selected_ids
    assert "eval_dom2" not in selected_ids

    # Check objective extremes
    assert selected_cands["min_emit_x"].evaluation_id == "eval_p1"
    assert selected_cands["min_emit_y"].evaluation_id == "eval_p2"
    assert selected_cands["min_sigma_energy"].evaluation_id == "eval_p3"


def test_detect_and_report_candidate_duplicates(synthetic_results_with_dominated):
    """Verify duplicate detection across selected candidate roles."""
    selected_cands = select_representative_pareto_candidates(synthetic_results_with_dominated, TEST_CONFIG)
    report = detect_and_report_candidate_duplicates(selected_cands)

    assert "unique_candidates" in report
    assert "duplicates_map" in report
    assert "summary_message" in report
    assert isinstance(report["summary_message"], str)


def test_compute_crowding_distances_standard_and_edge_cases():
    """Verify NSGA-II crowding distances across standard, small N, and degenerate sets."""
    # 1. Standard 2D 3-point Pareto front
    objs_2d = np.array([
        [0.0, 1.0],
        [0.5, 0.5],
        [1.0, 0.0],
    ])
    dists = compute_crowding_distances(objs_2d)
    assert len(dists) == 3
    assert np.isinf(dists[0])
    assert np.isinf(dists[2])
    assert dists[1] > 0.0

    # 2. Edge case: N = 0
    empty_dists = compute_crowding_distances(np.zeros((0, 3)))
    assert len(empty_dists) == 0

    # 3. Edge case: N = 1 and N = 2
    dists_1 = compute_crowding_distances([[1.0, 2.0, 3.0]])
    assert len(dists_1) == 1
    assert np.isinf(dists_1[0])

    dists_2 = compute_crowding_distances([[1.0, 2.0], [2.0, 1.0]])
    assert len(dists_2) == 2
    assert np.isinf(dists_2[0]) and np.isinf(dists_2[1])

    # 4. Zero range (identical objectives along one dimension)
    identical_dim_objs = np.array([
        [1.0, 5.0],
        [2.0, 5.0],
        [3.0, 5.0],
    ])
    dists_ident = compute_crowding_distances(identical_dim_objs)
    assert len(dists_ident) == 3
    assert np.isinf(dists_ident[0])
    assert np.isinf(dists_ident[2])
    assert not np.isnan(dists_ident[1])

    # 5. 1D input array handling
    dists_1d = compute_crowding_distances([1.0, 2.0, 3.0, 4.0])
    assert len(dists_1d) == 4
    assert np.isinf(dists_1d[0]) and np.isinf(dists_1d[-1])
    assert dists_1d[1] > 0.0



def _record(identity, objectives, feasible=True):
    return EvaluationResult(
        evaluation_id=identity, run_id="selection", x_physical=[0.2, 1.0, -2.0, 35.0, -39.0, 310.0],
        objectives_physical=list(objectives), objectives_model=[-v for v in objectives],
        simulation_valid=True, physically_feasible=feasible, failure_category="SUCCESS")


def test_selection_never_substitutes_infeasible_points_or_mutates_inputs():
    from copy import deepcopy
    from mobo_linac.metrics.selection import select_representatives
    infeasible = [_record("eval_a", [1e-6, 1e-6, 1e5], feasible=False)]
    infeasible[0].objectives_model = None
    before = deepcopy(infeasible)
    with pytest.raises(ValueError, match="feasible"):
        select_representatives(infeasible, TEST_CONFIG)
    assert extract_pareto_sets(infeasible, TEST_CONFIG)["feasible_pareto"] == []
    assert infeasible == before


def test_robustness_verification_and_reports_share_one_knee(tmp_path):
    from mobo_linac.metrics.selection import select_representatives, read_representatives
    from mobo_linac.verification.verifier import select_verification_candidates
    records = [_record(f"eval_{i}", [i * 1e-6, (6 - i) * 1e-6, (1 + (i - 3) ** 2) * 1e5]) for i in range(1, 6)]
    selection = select_representatives(records, TEST_CONFIG)
    assert select_representative_pareto_candidates(records, TEST_CONFIG) == selection.roles
    assert select_verification_candidates(records, TEST_CONFIG) == selection.roles
    # Ideal-distance knee in min-max normalized costs: the middle compromise.
    assert selection.roles["knee_point"].evaluation_id == "eval_3"
    written = read_representatives(selection.write(tmp_path / "representatives.json"))
    assert written["policy"] == "ideal_distance"
    assert written["roles"]["knee_point"] == {"run_id": "selection", "evaluation_id": "eval_3"}


def test_mixed_direction_and_custom_objective_extremes():
    from dataclasses import asdict
    from mobo_linac.config import config_from_dict
    from mobo_linac.metrics.selection import select_representatives
    data = asdict(TEST_CONFIG)
    data["objectives"].append({"name": "peak_current", "explicit_name": "peak_current_A", "unit": "A",
                               "physical_direction": "maximize", "model_sign": 1})
    config = config_from_dict(data)
    records = []
    for i, current in enumerate([10.0, 30.0, 20.0], start=1):
        record = _record(f"eval_{i}", [i * 1e-6, (4 - i) * 1e-6, 2e5, current])
        record.objectives_model = [-i * 1e-6, -(4 - i) * 1e-6, -2e5, current]
        records.append(record)
    roles = select_representatives(records, config).roles
    assert roles["max_peak_current"].evaluation_id == "eval_2"
    assert roles["min_emit_x"].evaluation_id == "eval_1"
