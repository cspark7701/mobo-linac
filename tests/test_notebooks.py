"""The analysis notebooks are thin, configuration-driven clients that execute against mock runs."""

import json
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS = sorted((ROOT / "notebooks").glob("*.ipynb"))


def _code(path):
    return "\n".join("".join(cell["source"]) for cell in json.loads(path.read_text())["cells"]
                     if cell["cell_type"] == "code")


@pytest.mark.parametrize("path", NOTEBOOKS, ids=lambda p: p.stem)
def test_notebooks_hold_no_objective_names_weights_scales_or_outputs(path):
    notebook = json.loads(path.read_text())
    assert all(not cell.get("outputs") and cell.get("execution_count") is None
               for cell in notebook["cells"] if cell["cell_type"] == "code")
    code = _code(path)
    for literal in ("norm_emit", "sigma_energy", "emit_x", "1e-6", "1e6", "1e-3", "weights=[", "/home/", "astra_bin"):
        assert literal not in code, (path.name, literal)


@pytest.fixture(scope="module")
def mock_production(tmp_path_factory):
    from mobo_linac.cli import main
    root = tmp_path_factory.mktemp("production")
    common = ["--num-initial-samples", "3", "--n-iterations", "1", "-q", "1", "--mock-evaluator", "--quiet",
              "--config", str(ROOT / "configs" / "publication_200MeV.yaml")]
    main(["run-scalarized-suite", *common, "--cases", "balanced", "--output-dir", str(root / "phase1_scalarized")])
    main(["run-unconstrained", *common, "--output-dir", str(root / "phase2_unconstrained")])
    main(["run-constrained", *common, "--output-dir", str(root / "phase3_constrained")])
    main(["compare", "--phase1-dir", str(root / "phase1_scalarized" / "balanced"),
          "--phase2-dir", str(root / "phase2_unconstrained"), "--phase3-dir", str(root / "phase3_constrained"),
          "--output-dir", str(root / "analysis"), "--mock-evaluator", "--quiet"])
    return root


@pytest.mark.parametrize("name", [p.stem for p in NOTEBOOKS])
def test_notebooks_execute_against_mock_runs(name, mock_production, tmp_path, monkeypatch):
    nbclient = pytest.importorskip("nbclient")
    nbformat = pytest.importorskip("nbformat")
    root = mock_production
    environment = {
        "MOBO_NOTEBOOK_HEADLESS": "1", "MOBO_PROJECT_ROOT": str(ROOT), "MOBO_FIGURES_DIR": str(tmp_path / "figures"),
        "MOBO_PHASE1_DIR": str(root / "phase1_scalarized"), "MOBO_PHASE2_DIR": str(root / "phase2_unconstrained"),
        "MOBO_PHASE3_DIR": str(root / "phase3_constrained"), "MOBO_ANALYSIS_DIR": str(root / "analysis"),
        "MOBO_PHASE_DIRS": os.pathsep.join(str(root / name) for name in
                                           ("phase1_scalarized/balanced", "phase2_unconstrained", "phase3_constrained")),
        "MOBO_PRODUCTION_DIR": str(root),
        "PYTHONPATH": str(ROOT / "src") + os.pathsep + os.environ.get("PYTHONPATH", ""),
    }
    for key, value in environment.items():
        monkeypatch.setenv(key, value)
    notebook = nbformat.read(ROOT / "notebooks" / f"{name}.ipynb", as_version=4)
    nbclient.NotebookClient(notebook, timeout=600, kernel_name="python3",
                            resources={"metadata": {"path": str(ROOT / "notebooks")}}).execute()
