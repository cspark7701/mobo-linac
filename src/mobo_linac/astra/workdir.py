"""
Isolated Working Directory Manager for ASTRA Simulations.

Ensures every ASTRA evaluation executes in an isolated filesystem directory
to prevent file collisions during concurrent evaluations.
"""

import hashlib
import json
import shutil
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

from mobo_linac.io.durable import fsync_dir, snapshot_file, write_once_json  # noqa: F401  (re-exported)


DEFAULT_TEMPLATE_IN = "astra.in"


def format_eval_id(eval_id: Union[int, str]) -> str:
    """
    Format evaluation identifier as a standardized string (e.g. 'eval_000001').

    Args:
        eval_id: Integer or string evaluation ID.

    Returns:
        Formatted evaluation directory name string.
    """
    if isinstance(eval_id, int):
        return f"eval_{eval_id:06d}"
    eval_str = str(eval_id).strip()
    validate_component(eval_str)
    if not eval_str.startswith("eval_"):
        try:
            val = int(eval_str)
            return f"eval_{val:06d}"
        except ValueError:
            return f"eval_{eval_str}"
    return eval_str


def validate_component(value: str) -> None:
    if not value or value in (".", "..") or Path(value).name != value or "/" in value or "\\" in value:
        raise ValueError("Run and attempt identities must be single directory names.")


def file_sha256(path: Union[str, Path]) -> str:
    hasher = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def read_evaluation_manifest(path: Union[str, Path]) -> Dict[str, Any]:
    """Read an exact new or legacy manifest path without choosing between attempts."""
    path = Path(path)
    if path.is_dir():
        path = path / "manifest.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version", 0) not in (0, 1):
        raise ValueError("Unsupported evaluation manifest schema.")
    return data


class AstraWorkDirManager:
    """
    Manages isolated working directories for parallel ASTRA evaluations.
    """

    def __init__(
        self,
        base_results_dir: Union[str, Path] = "results",
        template_dir: Union[str, Path] = ".",
    ):
        """
        Initialize the working directory manager.

        Args:
            base_results_dir: Root directory for results output.
            template_dir: Source directory containing template astra.in and fieldmap/dist files.
        """
        self.base_results_dir = Path(base_results_dir).resolve()
        self.template_dir = Path(template_dir).resolve()

    def get_work_root(self, run_id: str) -> Path:
        """
        Get the root work directory for a specific optimization run.

        Args:
            run_id: Unique identifier for the run (e.g. '20260723_120000').

        Returns:
            Path to results/<run_id>/work
        """
        validate_component(run_id)
        return self.base_results_dir / run_id / "work"

    def get_eval_dir(self, run_id: str, eval_id: Union[int, str]) -> Path:
        """
        Get the specific evaluation directory path.

        Args:
            run_id: Unique identifier for the run.
            eval_id: Identifier for the evaluation.

        Returns:
            Path to results/<run_id>/work/eval_<eval_id>
        """
        eval_dirname = format_eval_id(eval_id)
        return self.get_work_root(run_id) / eval_dirname

    def prepare_eval_dir(
        self,
        run_id: str,
        eval_id: Union[int, str],
        static_files: Sequence[str] = (),
        template_in: str = DEFAULT_TEMPLATE_IN,
        use_symlinks: bool = False,
        attempt_id: Optional[str] = None,
    ) -> Path:
        """
        Create and populate an isolated evaluation working directory.

        Args:
            run_id: Unique identifier for the run.
            eval_id: Identifier for the evaluation.
            static_files: Static dependency files (``simulation.static_files``) to copy/symlink.
            template_in: Name or relative path of template ASTRA input file.
            use_symlinks: If True, create symlinks for static files. astra.in is ALWAYS copied.
            attempt_id: Optional attempt directory beneath the logical evaluation directory.

        Returns:
            Path to the prepared evaluation directory.
        """
        eval_dir = self.get_eval_dir(run_id, eval_id)
        if attempt_id is not None:
            validate_component(attempt_id)
            eval_dir = eval_dir / attempt_id
        eval_dir.mkdir(parents=True, exist_ok=False)

        files_to_copy = list(static_files)

        # Copy static dependencies (field maps, initial distribution, etc.)
        for file_name in files_to_copy:
            src = self.template_dir / file_name
            if not src.exists():
                raise FileNotFoundError(f"Required static file not found: {src}")
            dst = eval_dir / file_name

            if use_symlinks:
                dst.symlink_to(src.resolve())
            else:
                shutil.copy2(src, dst)

        # Always copy astra.in independently so it can be edited without affecting master
        template_src = self.template_dir / template_in
        if not template_src.exists():
            raise FileNotFoundError(f"Required template input file not found: {template_src}")

        target_in = eval_dir / "astra.in"
        shutil.copy2(template_src, target_in)

        return eval_dir

    def save_manifest(
        self,
        eval_dir: Union[str, Path],
        manifest_data: Dict[str, Any],
    ) -> Path:
        """
        Save evaluation manifest JSON once in the supplied provenance or legacy directory.

        Args:
            eval_dir: Evaluation directory path.
            manifest_data: Dictionary containing parameters, status, timestamps, etc.

        Returns:
            Path to written manifest.json
        """
        return write_once_json(Path(eval_dir) / "manifest.json", manifest_data)

    def reserve_attempt(self, run_id, eval_id, attempt_id=None):
        """Reserve a globally fresh attempt, including concurrent independent reruns."""
        attempt_id = attempt_id or "attempt_" + uuid.uuid4().hex
        validate_component(attempt_id)
        if (self.get_eval_dir(run_id, eval_id) / attempt_id).exists():
            raise FileExistsError("Existing attempt workdir cannot be reused.")
        provenance = self.get_provenance_dir(run_id, eval_id, attempt_id)
        provenance.mkdir(parents=True, exist_ok=False)
        return attempt_id, provenance

    def get_provenance_dir(self, run_id, eval_id, attempt_id):
        validate_component(run_id)
        validate_component(attempt_id)
        return self.base_results_dir / run_id / "provenance" / format_eval_id(eval_id) / attempt_id

    def snapshot_inputs(self, eval_dir, provenance, stage="inputs", names=None):
        """Copy input bytes away from disposable workdirs and mutable symlink targets."""
        source = Path(eval_dir)
        target = Path(provenance) / stage
        target.mkdir(exist_ok=False)
        paths = sorted(path for path in source.rglob("*") if path.is_file()) if names is None else [source / name for name in names]
        hashes = {}
        for path in paths:
            if not path.is_file():
                continue
            name = str(path.relative_to(source))
            destination = target / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            snapshot_file(path, destination)
            hashes[name] = file_sha256(destination)
        for directory in [target] + sorted(p for p in target.rglob("*") if p.is_dir()):
            fsync_dir(directory)
        return hashes

    def cleanup_eval_dir(self, eval_dir):
        """Dispose of one workdir while preserving final manifests and input snapshots."""
        eval_path = Path(eval_dir).resolve()
        relative = eval_path.relative_to(self.base_results_dir)
        if len(relative.parts) not in (3, 4) or relative.parts[1] != "work":
            raise ValueError("Cleanup requires an exact evaluation or attempt workdir.")
        if not eval_path.exists():
            return
        if len(relative.parts) == 3 and any(p.is_dir() for p in eval_path.iterdir()):
            raise ValueError("Cleanup cannot delete a logical evaluation containing attempts.")
        if len(relative.parts) == 3 and (eval_path / "manifest.json").exists():
            run_id, _, eval_id = relative.parts
            provenance = self.get_provenance_dir(run_id, eval_id, "legacy")
            provenance.mkdir(parents=True, exist_ok=False)
            self.snapshot_inputs(eval_path, provenance, stage="legacy_files", names=[p.name for p in eval_path.iterdir() if p.is_file() and p.name != "manifest.json"])
            shutil.copyfile(eval_path / "manifest.json", provenance / "manifest.json")
        if len(relative.parts) == 4:
            run_id, _, eval_id, attempt_id = relative.parts
            if not (self.get_provenance_dir(run_id, eval_id, attempt_id) / "manifest.json").is_file():
                raise ValueError("Final attempt provenance must exist before cleanup.")
        shutil.rmtree(eval_path)
