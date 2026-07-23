"""
Isolated Working Directory Manager for ASTRA Simulations.

Ensures every ASTRA evaluation executes in an isolated filesystem directory
to prevent file collisions during concurrent evaluations.
"""

import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


DEFAULT_STATIC_FILES = [
    "gun.dat",
    "PAL_SOL_A.dat",
    "TWS_Sband.dat",
    "pal_photo2.ini",
]

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
    if not eval_str.startswith("eval_"):
        try:
            val = int(eval_str)
            return f"eval_{val:06d}"
        except ValueError:
            return f"eval_{eval_str}"
    return eval_str


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
        static_files: Optional[List[str]] = None,
        template_in: str = DEFAULT_TEMPLATE_IN,
        use_symlinks: bool = False,
    ) -> Path:
        """
        Create and populate an isolated evaluation working directory.

        Args:
            run_id: Unique identifier for the run.
            eval_id: Identifier for the evaluation.
            static_files: List of static dependency files to copy/symlink.
            template_in: Name or relative path of template ASTRA input file.
            use_symlinks: If True, create symlinks for static files. astra.in is ALWAYS copied.

        Returns:
            Path to the prepared evaluation directory.
        """
        eval_dir = self.get_eval_dir(run_id, eval_id)
        eval_dir.mkdir(parents=True, exist_ok=True)

        files_to_copy = static_files if static_files is not None else DEFAULT_STATIC_FILES

        # Copy static dependencies (field maps, initial distribution, etc.)
        for file_name in files_to_copy:
            src = self.template_dir / file_name
            if not src.exists():
                raise FileNotFoundError(f"Required static file not found: {src}")
            dst = eval_dir / file_name
            if dst.exists() or dst.is_symlink():
                dst.unlink()

            if use_symlinks:
                dst.symlink_to(src.resolve())
            else:
                shutil.copy2(src, dst)

        # Always copy astra.in independently so it can be edited without affecting master
        template_src = self.template_dir / template_in
        if not template_src.exists():
            raise FileNotFoundError(f"Required template input file not found: {template_src}")

        target_in = eval_dir / "astra.in"
        if target_in.exists() or target_in.is_symlink():
            target_in.unlink()
        shutil.copy2(template_src, target_in)

        return eval_dir

    def save_manifest(
        self,
        eval_dir: Union[str, Path],
        manifest_data: Dict[str, Any],
    ) -> Path:
        """
        Save evaluation manifest JSON in the evaluation directory.

        Args:
            eval_dir: Evaluation directory path.
            manifest_data: Dictionary containing parameters, status, timestamps, etc.

        Returns:
            Path to written manifest.json
        """
        eval_path = Path(eval_dir)
        manifest_path = eval_path / "manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)
        return manifest_path

    def cleanup_eval_dir(self, eval_dir: Union[str, Path]) -> None:
        """
        Remove evaluation directory safely.

        Args:
            eval_dir: Path to directory to remove.
        """
        eval_path = Path(eval_dir)
        if eval_path.exists():
            shutil.rmtree(eval_path)
