"""Versioned fitted surrogates, separate from campaign observation checkpoints."""

from dataclasses import asdict
from pathlib import Path

import torch
from botorch.models import ModelListGP, SingleTaskGP

from mobo_linac.io.results import _atomic_torch_save
from mobo_linac.models.gp import FitOutcome, build_scalarized_gp_model

ARTIFACT_VERSION = 1


def model_payload(model):
    channels = [model] if isinstance(model, SingleTaskGP) else model.models
    return {
        "kind": "single" if isinstance(model, SingleTaskGP) else "list",
        "channels": [{
            "metadata": channel.artifact_metadata,
            "state": {key: value.detach().cpu().clone() for key, value in channel.state_dict().items()},
            "standardized_noise": channel.likelihood.noise.detach().cpu().clone(),
            "fit_outcomes": [asdict(outcome) for outcome in getattr(channel, "fit_outcomes", ())],
        } for channel in channels],
    }


def restore_model(payload, device="cpu"):
    channels = []
    for record in payload["channels"]:
        model = build_scalarized_gp_model(**record["metadata"], device=device)
        model.load_state_dict(record["state"])
        # FixedNoise noise tensors are not state_dict buffers in GPyTorch.
        if record["metadata"]["train_Yvar"] is not None:
            model.likelihood.noise_covar.noise = record["standardized_noise"].to(next(model.parameters()))
        model.fit_outcomes = tuple(FitOutcome(**outcome) for outcome in record["fit_outcomes"])
        model.eval()
        channels.append(model)
    result = channels[0] if payload["kind"] == "single" else ModelListGP(*channels)
    result.fit_outcomes = tuple(outcome for model in channels for outcome in model.fit_outcomes)
    result.eval()
    return result


def save_model_artifact(model, path, *, training_ids=(), metadata=None):
    """Save tensor/state data atomically; no simulator or optimizer is serialized."""
    ids = list(training_ids)
    channels = [model] if isinstance(model, SingleTaskGP) else model.models
    if ids and len(ids) != channels[0].artifact_metadata["train_X"].shape[0]:
        raise ValueError("training_ids must align with observation rows.")
    _atomic_torch_save({
        "version": ARTIFACT_VERSION, "kind": "gp", "model": model_payload(model),
        "training_ids": ids, "metadata": metadata or {},
    }, Path(path))


def read_artifact(path):
    artifact = torch.load(path, map_location="cpu", weights_only=True)
    if artifact.get("version") != ARTIFACT_VERSION:
        raise ValueError("Unsupported surrogate artifact version.")
    return artifact


def load_model_artifact(path, device="cpu"):
    artifact = read_artifact(path)
    if artifact["kind"] != "gp":
        raise ValueError("Expected a GP model artifact.")
    model = restore_model(artifact["model"], device=device)
    model.training_ids = artifact["training_ids"]
    model.campaign_metadata = artifact["metadata"]
    return model
