"""Crash-safe file writes shared by every persisted artifact.

Replacing writes go to a hidden temporary file in the target directory, are flushed and
fsynced, atomically renamed over the target, and the directory entry is fsynced. A reader
therefore sees either the previous complete file or the new complete file. Write-once
records use exclusive creation; journals append durably.
"""

import io
import json
import os
from pathlib import Path
from typing import Any, Union
import uuid

import numpy as np
import torch

PathLike = Union[str, Path]

# Checkpoints hold tensors, primitives and NumPy RNG state arrays. Loading allows only the
# array reconstruction globals NumPy needs; arbitrary pickled objects are rejected.
_NUMPY_ARRAY_GLOBALS = [np.ndarray, np.dtype, type(np.dtype("uint32"))]
try:  # NumPy >= 2
    _NUMPY_ARRAY_GLOBALS.append(np._core.multiarray._reconstruct)
except AttributeError:  # pragma: no cover - NumPy 1.x
    _NUMPY_ARRAY_GLOBALS.append(np.core.multiarray._reconstruct)


def fsync_dir(path: PathLike) -> None:
    """Persist directory entries (creations, renames, removals) of ``path``."""
    descriptor = os.open(Path(path), os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _temporary(path: Path) -> Path:
    return path.with_name(f".{path.name}.tmp.{uuid.uuid4().hex}")


def atomic_write_bytes(path: PathLike, data: bytes) -> Path:
    """Atomically replace ``path`` with ``data``."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = _temporary(path)
    try:
        with temporary.open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        fsync_dir(path.parent)
    finally:
        if temporary.exists():
            temporary.unlink()
    return path


def atomic_write_text(path: PathLike, text: str) -> Path:
    return atomic_write_bytes(path, text.encode("utf-8"))


def atomic_json(path: PathLike, data: Any, *, allow_nan: bool = False, indent: int = 2) -> Path:
    """Atomically write JSON; NaN is rejected unless the payload explicitly records unknowns."""
    return atomic_write_text(path, json.dumps(data, indent=indent, allow_nan=allow_nan))


def atomic_csv(path: PathLike, frame, **kwargs) -> Path:
    """Atomically write a pandas DataFrame as CSV (``index=False`` unless given)."""
    kwargs.setdefault("index", False)
    buffer = io.StringIO()
    frame.to_csv(buffer, **kwargs)
    return atomic_write_text(path, buffer.getvalue())


def atomic_torch_save(data: Any, path: PathLike) -> Path:
    """Atomically write a ``torch.save`` payload."""
    buffer = io.BytesIO()
    torch.save(data, buffer)
    return atomic_write_bytes(path, buffer.getvalue())


def safe_torch_load(path: PathLike, *, map_location="cpu", allow_unsafe_pickle: bool = False) -> Any:
    """Load a torch payload with ``weights_only=True`` and the NumPy array allow-list.

    ``allow_unsafe_pickle`` is an explicit opt-in for trusted archived files that store
    arbitrary Python objects; it executes pickled code and must not be used for
    untrusted results directories.
    """
    if allow_unsafe_pickle:
        return torch.load(path, map_location=map_location, weights_only=False)
    with torch.serialization.safe_globals(_NUMPY_ARRAY_GLOBALS):
        return torch.load(path, map_location=map_location, weights_only=True)


def write_once_json(path: PathLike, data: Any) -> Path:
    """Exclusive, durable write: an existing record is never replaced."""
    path = Path(path)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    fsync_dir(path.parent)
    return path


def append_line_durable(path: PathLike, line: str) -> None:
    """Append one newline-terminated line and persist it before returning."""
    path = Path(path)
    created = not path.exists()
    with path.open("a", encoding="utf-8") as stream:
        stream.write(line if line.endswith("\n") else line + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    if created:
        fsync_dir(path.parent)


def unlink_durable(path: PathLike) -> None:
    """Remove a file (if present) and persist the directory entry removal."""
    path = Path(path)
    if path.exists():
        path.unlink()
        fsync_dir(path.parent)


def fsync_file(path: PathLike) -> None:
    with Path(path).open("rb") as stream:
        os.fsync(stream.fileno())


def truncate_durable(path: PathLike, size: int) -> None:
    """Truncate a file to ``size`` bytes and persist the change."""
    with Path(path).open("r+b") as stream:
        stream.truncate(size)
        stream.flush()
        os.fsync(stream.fileno())


def ensure_trailing_newline(path: PathLike) -> None:
    """Durably terminate a non-empty file with a newline if its last byte is not one."""
    path = Path(path)
    if not path.exists() or not path.stat().st_size:
        return
    with path.open("r+b") as stream:
        stream.seek(-1, os.SEEK_END)
        if stream.read(1) != b"\n":
            stream.seek(0, os.SEEK_END)
            stream.write(b"\n")
            stream.flush()
            os.fsync(stream.fileno())


def snapshot_file(source: PathLike, destination: PathLike) -> None:
    """Copy bytes to a new destination file and persist them."""
    import shutil
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    fsync_file(destination)
