"""Fault injection for the shared durable-write module."""

import json
import os

import numpy as np
import pandas as pd
import pytest
import torch

from mobo_linac.io import durable


class Untrusted:
    """Arbitrary object a checkpoint must not unpickle by default."""


@pytest.mark.parametrize("write", [
    lambda path: durable.atomic_write_text(path, "new"),
    lambda path: durable.atomic_json(path, {"new": 1}),
    lambda path: durable.atomic_csv(path, pd.DataFrame({"new": [1]})),
    lambda path: durable.atomic_torch_save({"new": torch.ones(1)}, path),
])
def test_interrupted_replace_keeps_previous_file_and_no_temporary(tmp_path, monkeypatch, write):
    target = tmp_path / "artifact"
    target.write_bytes(b"old complete content")

    def fail(*args, **kwargs):
        raise OSError("injected crash before rename")

    monkeypatch.setattr(os, "replace", fail)
    with pytest.raises(OSError, match="injected"):
        write(target)
    assert target.read_bytes() == b"old complete content"
    assert [p.name for p in tmp_path.iterdir()] == ["artifact"]


def test_write_once_and_append_semantics(tmp_path):
    record = durable.write_once_json(tmp_path / "once.json", {"a": 1})
    with pytest.raises(FileExistsError):
        durable.write_once_json(record, {"a": 2})
    assert json.loads(record.read_text()) == {"a": 1}
    journal = tmp_path / "journal.jsonl"
    journal.write_bytes(b'{"partial"')
    durable.ensure_trailing_newline(journal)
    durable.append_line_durable(journal, '{"b": 2}')
    assert journal.read_text().splitlines() == ['{"partial"', '{"b": 2}']
    durable.truncate_durable(journal, 3)
    assert journal.read_bytes() == b'{"p'


def test_checkpoints_load_without_unpickling_arbitrary_objects(tmp_path):
    from mobo_linac.config import load_config
    from mobo_linac.io.results import load_run_checkpoint, save_run_checkpoint
    path = save_run_checkpoint(0, [], [], tmp_path / "checkpoint.pt", config=load_config("configs/mobo_200MeV.yaml"))
    state = load_run_checkpoint(path)  # weights_only with the NumPy RNG allow-list
    assert state.numpy_rng_state[0] == "MT19937"
    np.random.RandomState().set_state(state.numpy_rng_state)

    torch.save({"iteration": 0, "payload": Untrusted()}, tmp_path / "unsafe.pt")
    with pytest.raises(ValueError, match="unsafe"):
        load_run_checkpoint(tmp_path / "unsafe.pt")
    assert load_run_checkpoint(tmp_path / "unsafe.pt", allow_unsafe_pickle=True).iteration == 0


def test_only_the_durable_module_performs_low_level_durable_operations():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1] / "src" / "mobo_linac"
    offenders = [str(path.relative_to(root)) for path in root.rglob("*.py")
                 if path.name != "durable.py"
                 and any(token in path.read_text() for token in ("os.replace(", "os.fsync(", "NamedTemporaryFile"))]
    assert offenders == []
