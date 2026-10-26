"""Corrupt checkpoint fields must never be accepted as a reproducible continuation."""

from copy import deepcopy

import pytest
import torch

from mobo_linac.campaigns.runner import MoboCampaignRunner
from mobo_linac.campaigns import state as recovery_state
from mobo_linac.campaigns.state import CampaignOverrides
from mobo_linac.execution.mock import MockEvaluator
from mobo_linac.config import load_config
from mobo_linac.io.checkpoint import load_run_checkpoint


@pytest.fixture(scope="module")
def original_checkpoint(tmp_path_factory):
    root = tmp_path_factory.mktemp("resume_edges")
    config = load_config("configs/publication_200MeV.yaml")
    MoboCampaignRunner(
        config=config,
        output_dir=root,
        num_initial_samples=2,
        num_batches=0,
        evaluator=MockEvaluator(root),
        export_plots=False,
        export_env_info=False,
        device="cpu",
    ).run()
    return load_run_checkpoint(root), config


@pytest.fixture
def snapshot(original_checkpoint):
    state, config = original_checkpoint
    return deepcopy(state), deepcopy(config)


def set_field(obj, path, value):
    parts = path.split(".")
    for part in parts[:-1]:
        obj = getattr(obj, part)
    setattr(obj, parts[-1], value)


@pytest.mark.parametrize(
    "path,value,match",
    [
        ("campaign.run_id", None, "missing"),
        ("iteration", 0.5, "integer"),
        ("campaign.planned_num_batches", -1, "planned"),
        ("campaign.num_workers", 0, "worker"),
        ("campaign.num_initial_samples", 0, "sample"),
        ("campaign.optimization_mode", "bad", "mode"),
        ("campaign.constrained", True, "constrained"),
        ("campaign.acquisition_mode", "bad", "acquisition"),
        ("campaign.acquisition_mode", "qLogNEI", "scalarized"),
        ("progress.elapsed_wall_time_s", -1, "elapsed"),
        ("progress.evaluation_elapsed_s", [-1], "wall times"),
    ],
)
def test_checkpoint_structure_rejects_invalid_fields(snapshot, path, value, match):
    state, _ = snapshot
    set_field(state, path, value)
    with pytest.raises(ValueError, match=match):
        recovery_state.validate_structure(state)


@pytest.mark.parametrize(
    "path,value,match",
    [
        ("campaign.scalar_weights", [1], "weights"),
        ("metrics.reporting_ref_point", [1], "reference"),
        ("progress.initial_design", [[1]], "initial design"),
        ("progress.sobol_state", {}, "Sobol"),
        ("metrics.metric_history", [], "history length"),
        ("metrics.hypervolumes", [123], "hypervolumes"),
        ("campaign.total_eval_budget", 1, "total budget"),
        ("proposals.proposal_history", {}, "proposal history"),
        ("proposals.proposal_history", [{"batch_idx": 99, "metadata": {}}], "proposal history"),
    ],
)
def test_checkpoint_scientific_consistency(snapshot, path, value, match):
    state, config = snapshot
    set_field(state, path, value)
    with pytest.raises(ValueError, match=match):
        recovery_state.validate_consistency(state, config)


@pytest.mark.parametrize("fault", ["run_id", "duplicate", "initial_history", "negative_hv"])
def test_checkpoint_history_must_agree(snapshot, fault):
    state, config = snapshot
    if fault == "run_id":
        state.results[0].run_id = "other"
    if fault == "duplicate":
        state.results[1].evaluation_id = state.results[0].evaluation_id
    if fault == "initial_history":
        state.progress.initial_design[0][0] += 0.001
    if fault == "negative_hv":
        state.metrics.metric_history[0]["feasible_hypervolume"] = -1
    with pytest.raises(ValueError):
        recovery_state.validate_consistency(state, config)


@pytest.mark.parametrize(
    "overrides,match",
    [
        ({"seed": 100}, "seed"),
        ({"constrained": True}, "constrained"),
        ({"acquisition": "qLogEHVI"}, "acquisition"),
        ({"scalar_weights": (1.0, 0.0, 0.0)}, "weights"),
        ({"batch_size": 0}, "batch size"),
        ({"num_workers": 0}, "worker"),
        ({"num_batches": 0.5}, "integer"),
        ({"num_batches": -1}, "earlier"),
    ],
)
def test_resume_override_validation(snapshot, overrides, match):
    state, config = snapshot
    with pytest.raises(ValueError, match=match):
        recovery_state.merge_with_checkpoint(state, CampaignOverrides(**overrides), config)


def test_resume_requires_configuration_and_plan(snapshot):
    state, config = snapshot
    state.config = None
    with pytest.raises(ValueError, match="saved configuration"):
        recovery_state.check_configuration_compatibility(state, config)
    state.campaign.planned_num_batches = None
    with pytest.raises(ValueError, match="planned iteration"):
        recovery_state.merge_with_checkpoint(state, CampaignOverrides(), config)
    state.campaign.total_eval_budget = 10
    with pytest.raises(ValueError, match="saved total budget"):
        recovery_state.merge_with_checkpoint(state, CampaignOverrides(num_batches=999), config)


@pytest.mark.parametrize(
    "fault,match",
    [
        ("version", "schema"),
        ("batch", "does not follow"),
        ("count", "design/count"),
        ("bounds", "bounds"),
        ("plan", "plan"),
        ("initial", "initial design"),
    ],
)
def test_pending_proposal_validation(snapshot, fault, match):
    state, config = snapshot
    state.campaign.batch_size = 1
    state.campaign.planned_num_batches = 1
    state.proposals.pending_proposal = {
        "version": "1.0",
        "batch_idx": 1,
        "candidates": [config.get_nominal_parameters()],
        "evaluation_ids": ["eval_000003"],
    }
    p = state.proposals.pending_proposal
    if fault == "version":
        p["version"] = "99"
    if fault == "batch":
        p["batch_idx"] = 4
    if fault == "count":
        p["candidates"] = []
    if fault == "bounds":
        p["candidates"][0][0] = 999
    if fault == "plan":
        state.campaign.planned_num_batches = 0
    if fault == "initial":
        state.iteration = -1
        state.results = []
        p.update(
            batch_idx=0, candidates=[config.get_nominal_parameters()] * 2, evaluation_ids=["eval_000001", "eval_000002"]
        )
    with pytest.raises(ValueError, match=match):
        recovery_state.validate_pending_proposal(state, config)


@pytest.mark.parametrize("fault", ["topology", "index", "rng", "valid"])
def test_resume_cuda_state_validation(snapshot, monkeypatch, fault):
    state, _ = snapshot
    state.campaign.device = "cuda:0" if fault != "index" else "cuda:2"
    state.rng.cuda_rng_states = [torch.zeros(1, dtype=torch.uint8)]
    monkeypatch.setattr(recovery_state, "get_device", lambda *a, **k: torch.device(state.campaign.device))
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(torch.cuda, "device_count", lambda: 0 if fault == "topology" else 1)

    class Generator:
        def set_state(self, value):
            if fault == "rng":
                raise RuntimeError("invalid generator state")

    monkeypatch.setattr(torch, "Generator", lambda **kw: Generator())
    if fault == "valid":
        assert recovery_state.resolve_resume_device(state, "auto") == torch.device("cuda:0")
    else:
        with pytest.raises(ValueError):
            recovery_state.resolve_resume_device(state, "auto")
