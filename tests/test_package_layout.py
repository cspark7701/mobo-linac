"""
Unit tests for Python Package Layout and CLI Entry Points.
"""

import subprocess
import sys

import mobo_linac
import mobo_linac.acquisition
import mobo_linac.astra
import mobo_linac.config
import mobo_linac.constraints
import mobo_linac.evaluation
import mobo_linac.execution
import mobo_linac.io
import mobo_linac.metrics
import mobo_linac.models
import mobo_linac.objectives
import mobo_linac.plotting


def test_package_version():
    """Verify package version metadata."""
    assert hasattr(mobo_linac, "__version__")
    assert mobo_linac.__version__ == "1.0.0"

    try:
        import importlib.metadata
        installed_ver = importlib.metadata.version("mobo-linac")
        assert installed_ver == "1.0.0"
    except importlib.metadata.PackageNotFoundError:
        pass


def test_subpackage_imports():
    """Verify clean importability of all subpackages."""
    assert mobo_linac.astra.AstraWorkDirManager is not None
    assert mobo_linac.execution.ProcessPoolEvaluator is not None
    assert mobo_linac.models.build_gp_models is not None
    assert mobo_linac.acquisition.build_acquisition_function is not None
    assert mobo_linac.metrics.HypervolumeTracker is not None
    assert mobo_linac.metrics.save_evaluation_results is not None
    assert mobo_linac.plotting.plot_pareto_front is not None


def test_cli_help_execution():
    """Verify mobo-linac CLI command line interface execution."""
    res = subprocess.run(
        [sys.executable, "-m", "mobo_linac.cli", "--help"],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0
    assert "Multi-Objective Bayesian Optimization" in res.stdout
    assert "run" in res.stdout
    assert "resume" in res.stdout
    assert "analyze" in res.stdout


def test_mock_campaign_and_analysis_do_not_initialize_astra(tmp_path):
    """Block external simulator imports and check environment after real mock work."""
    code = r'''
import importlib.abc
import os
import sys
from pathlib import Path
class BlockSimulator(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in ('astra', 'distgen'):
            raise AssertionError('Unexpected simulator initialization: ' + fullname)
sys.meta_path.insert(0, BlockSimulator())
before = dict(os.environ)
from mobo_linac.campaigns.runner import MoboCampaignRunner
from mobo_linac.execution.mock import MockEvaluator
from mobo_linac.execution.candidate_evaluator import CandidateEvaluatorBase
from mobo_linac.io.run_data import read_run_data
from mobo_linac.metrics.publication import campaign_summary
from mobo_linac.astra.runner import resolve_executable_path
assert dict(os.environ) == before
for mode, constrained in [('scalarized_bo', False), ('unconstrained_mobo', False), ('constrained_mobo', True)]:
    root = Path(sys.argv[1]) / mode
    results, tracker, run_dir = MoboCampaignRunner(config='configs/publication_200MeV.yaml',
        output_dir=root, num_initial_samples=2, num_batches=0, seed=42,
        optimization_mode=mode, constrained=constrained, evaluator=MockEvaluator(root),
        export_plots=False, export_env_info=False).run()
    assert len(results) == 2
    assert campaign_summary(read_run_data(run_dir))
from mobo_linac.config import load_config
from mobo_linac.robustness.workflow import run_robustness_workflow
from mobo_linac.verification.verifier import run_verification_pipeline
config = load_config('configs/publication_200MeV.yaml')
run_robustness_workflow(results, config, Path(sys.argv[1]) / 'robustness',
                       num_perturbations=1, evaluator=MockEvaluator(root))
run_verification_pipeline(results, config=config, output_dir=Path(sys.argv[1]) / 'verification',
                          evaluator=MockEvaluator(root))
assert os.environ.get('ASTRA_BIN') == before.get('ASTRA_BIN')
assert os.environ.get('GENERATOR_BIN') == before.get('GENERATOR_BIN')
assert 'astra' not in sys.modules and 'distgen' not in sys.modules
resolve_executable_path('ASTRA_BIN', 'astra')
assert os.environ.get('ASTRA_BIN') == before.get('ASTRA_BIN')
'''
    res = subprocess.run([sys.executable, '-c', code, str(tmp_path)], capture_output=True, text=True)
    assert res.returncode == 0, res.stderr


def test_campaign_runner_construction_leaves_global_state_untouched(tmp_path):
    import random
    import numpy as np
    import torch
    from mobo_linac.campaigns.runner import MoboCampaignRunner
    from mobo_linac.config import load_config
    torch.set_default_dtype(torch.float32)
    try:
        before = (torch.get_rng_state().clone(), np.random.get_state()[1].copy(), random.getstate())
        MoboCampaignRunner(config=load_config("configs/mobo_200MeV.yaml"), output_dir=tmp_path / "run",
                           num_initial_samples=2, num_batches=0, seed=123, device="cpu")
        after = (torch.get_rng_state(), np.random.get_state()[1], random.getstate())
        assert torch.equal(before[0], after[0]) and (before[1] == after[1]).all() and before[2] == after[2]
        assert torch.get_default_dtype() == torch.float32
    finally:
        torch.set_default_dtype(torch.double)


def test_campaign_run_restores_default_dtype(tmp_path):
    import torch
    from mobo_linac.campaigns.runner import MoboCampaignRunner
    from mobo_linac.config import load_config
    from mobo_linac.execution import MockEvaluator
    torch.set_default_dtype(torch.float32)
    try:
        MoboCampaignRunner(config=load_config("configs/mobo_200MeV.yaml"), output_dir=tmp_path / "run",
                           num_initial_samples=2, num_batches=0, device="cpu", export_plots=False,
                           export_env_info=False, evaluator=MockEvaluator(tmp_path)).run()
        assert torch.get_default_dtype() == torch.float32
    finally:
        torch.set_default_dtype(torch.double)


def test_campaign_loop_has_no_closures_over_mutable_state_and_short_steps():
    import ast
    from pathlib import Path
    source = Path(__file__).resolve().parents[1] / "src" / "mobo_linac" / "campaigns" / "runner.py"
    tree = ast.parse(source.read_text())
    assert not any(isinstance(node, ast.Nonlocal) for node in ast.walk(tree))
    long = {node.name: node.end_lineno - node.lineno + 1 for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.end_lineno - node.lineno + 1 > 60}
    assert long == {}


def test_astra_template_directory_is_independent_of_working_directory(tmp_path, monkeypatch):
    from mobo_linac.astra.runner import resolve_template_dir
    from mobo_linac.campaigns.runner import MoboCampaignRunner
    from mobo_linac.config import load_config
    config = load_config("configs/mobo_200MeV.yaml")
    expected = resolve_template_dir(config)
    assert expected.is_absolute() and (expected / "astra.in").is_file()
    monkeypatch.chdir(tmp_path)
    assert resolve_template_dir(config) == expected
    runner = MoboCampaignRunner(config=config, output_dir=tmp_path / "run", num_initial_samples=2,
                                num_batches=0, device="cpu")
    assert runner.build_evaluator().template_dir == expected
    config.simulation.template_dir = ".."  # relative to the configuration file's directory
    assert resolve_template_dir(config) == expected


# Package layers, lowest first. A module may import only from its own or lower layers.
LAYERS = {
    "status": 0, "diagnostics": 0, "result_schema": 0, "display": 0, "campaign_options": 0, "config": 0,
    "benchmark_algorithms": 0, "utils": 0, "evaluation": 0, "objectives": 0, "constraints": 0,
    "perturbations": 0, "conventions": 0, "requests": 0,
    "io": 1, "models": 2, "acquisition": 2, "metrics": 2,
    "astra": 3, "execution": 3, "plotting": 3,
    "campaigns": 4, "robustness": 4, "verification": 4, "reporting": 4, "cli": 5,
}
# Documented function-level imports: CLI subcommands load their workflow on demand, and
# Matplotlib-backed plotting is imported only where figures are exported.
LAZY_ALLOWED = ("mobo_linac.cli", "->mobo_linac.plotting", "mobo_linac.astra.runner->astra")


def _package_imports():
    import ast
    from pathlib import Path
    root = Path(__file__).resolve().parents[1] / "src" / "mobo_linac"
    for path in root.rglob("*.py"):
        parts = path.relative_to(root).with_suffix("").parts
        module = ".".join(("mobo_linac",) + tuple(p for p in parts if p != "__init__"))
        tree = ast.parse(path.read_text())
        top = {id(node) for node in tree.body}
        # ``if TYPE_CHECKING:`` imports are annotation-only and count as module level.
        for block in tree.body:
            if isinstance(block, ast.If) and getattr(block.test, "id", None) == "TYPE_CHECKING":
                top |= {id(node) for node in block.body}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("mobo_linac"):
                yield module, node.module, id(node) in top


def test_package_layers_are_respected():
    def layer(name):
        parts = name.split(".")
        return LAYERS[parts[1]] if len(parts) > 1 else None
    violations = sorted({f"{source} -> {target}" for source, target, _ in _package_imports()
                         if layer(source) is not None and layer(target) is not None and layer(target) > layer(source)})
    assert violations == []


def test_function_level_package_imports_are_documented_exceptions():
    lazy = sorted({f"{source}->{target}" for source, target, top in _package_imports() if not top})
    undocumented = [item for item in lazy if not any(
        item.startswith(allowed) or allowed in item for allowed in LAZY_ALLOWED)]
    assert undocumented == []


def test_campaign_engine_imports_without_matplotlib():
    import subprocess
    import sys
    code = ("import sys, mobo_linac.campaigns, mobo_linac.robustness, mobo_linac.verification; "
            "assert 'matplotlib' not in sys.modules, sorted(m for m in sys.modules if 'matplotlib' in m)[:3]")
    completed = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr
