"""Versioned fitted surrogates, separate from campaign observation checkpoints."""

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Union

from botorch.models import ModelListGP, SingleTaskGP

from mobo_linac.utils.durable import atomic_torch_save, safe_torch_load
from mobo_linac.models.gp import FitOutcome, SurrogateSettings, build_output_gp, channel_record, output_models

ARTIFACT_VERSION = 1


def model_payload(model):
    """Per-output training data, settings, state and fit outcome (format unchanged since v1)."""
    channels = []
    for channel in output_models(model):
        record = channel_record(channel)
        channels.append({
            "metadata": record.artifact_metadata(),
            "state": {key: value.detach().cpu().clone() for key, value in channel.state_dict().items()},
            "standardized_noise": channel.likelihood.noise.detach().cpu().clone(),
            "fit_outcomes": [asdict(record.fit_outcome)] if record.fit_outcome is not None else [],
        })
    return {"kind": "single" if isinstance(model, SingleTaskGP) else "list", "channels": channels}


def restore_model(payload, device="cpu"):
    channels = []
    for record in payload["channels"]:
        metadata = record["metadata"]
        mode = "deterministic_fixed" if metadata["noise_mode"] == "fixed" else metadata["noise_mode"]  # archived alias
        model = build_output_gp(metadata["train_X"], metadata["train_Y"], metadata["bounds"],
                                SurrogateSettings(covar_type=metadata["covar_type"], noise_mode=mode),
                                train_Yvar=metadata["train_Yvar"], device=device)
        model.load_state_dict(record["state"])
        # FixedNoise noise tensors are not state_dict buffers in GPyTorch.
        if metadata["train_Yvar"] is not None:
            model.likelihood.noise_covar.noise = record["standardized_noise"].to(next(model.parameters()))
        outcomes = [FitOutcome(**{**outcome, "errors": tuple(outcome.get("errors", ()))})
                    for outcome in record["fit_outcomes"]]
        channel_record(model).fit_outcome = outcomes[0] if outcomes else None
        model.eval()
        channels.append(model)
    result = channels[0] if payload["kind"] == "single" else ModelListGP(*channels)
    result.eval()
    return result


@dataclass
class LoadedSurrogate:
    """A restored surrogate with the evaluation identities and campaign metadata it was saved with."""

    model: Union[SingleTaskGP, ModelListGP]
    training_ids: List[Any] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


def save_model_artifact(model, path, *, training_ids=(), metadata=None):
    """Save tensor/state data atomically; no simulator or optimizer is serialized."""
    ids = list(training_ids)
    first = output_models(model)[0]
    if ids and len(ids) != channel_record(first).train_X.shape[0]:
        raise ValueError("training_ids must align with observation rows.")
    atomic_torch_save({
        "version": ARTIFACT_VERSION, "kind": "gp", "model": model_payload(model),
        "training_ids": ids, "metadata": metadata or {},
    }, Path(path))


def read_artifact(path):
    artifact = safe_torch_load(path)
    if artifact.get("version") != ARTIFACT_VERSION:
        raise ValueError("Unsupported surrogate artifact version.")
    return artifact


def load_model_artifact(path, device="cpu") -> LoadedSurrogate:
    artifact = read_artifact(path)
    if artifact["kind"] != "gp":
        raise ValueError("Expected a GP model artifact.")
    return LoadedSurrogate(restore_model(artifact["model"], device=device), artifact["training_ids"], artifact["metadata"])
