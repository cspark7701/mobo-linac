import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_revision_reference_settings.py"


def load():
    spec = importlib.util.spec_from_file_location("reference_settings", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_tdr_config_changes_only_constraints():
    from mobo_linac.config import load_config
    production = load_config(ROOT / "configs/publication_200MeV.yaml")
    tdr = load_config(ROOT / "configs/revision_tdr_200MeV.yaml")
    assert tdr.design_variables == production.design_variables
    assert tdr.objectives == production.objectives
    assert tdr.execution == production.execution and tdr.model == production.model
    assert (tdr.constraints.max_sigma_x_m, tdr.constraints.max_sigma_xp_rad) == (0.30e-3, 0.2663e-3)
    assert tdr.constraints.min_mean_kinetic_energy_eV == 200e6
    # 9,998 of 9,999 counted particles must fail, matching the TDR's strict T > 0.9999.
    assert 9998 / 9999 < tdr.constraints.min_transmission <= 1.0


def test_moga_parameters_are_the_configured_nominal():
    from mobo_linac.config import load_config
    module = load()
    config = load_config(module.PRODUCTION_CONFIG)
    assert module.moga_parameters(config) == [v.nominal_value for v in config.design_variables]


@pytest.mark.skipif(not (ROOT / "results/paper_production/04_primary").exists(),
                    reason="archived primary campaigns are not distributed")
def test_mock_rehearsal_writes_all_outputs(tmp_path):
    module = load()
    assert module.main(["--output-dir", str(tmp_path / "refs"), "--workers", "2", "--mock-evaluator"]) == 0
    plan = json.loads((tmp_path / "refs/plan.json").read_text())
    assert plan["mock"] is True and plan["jitter_trials"] == 50
    tdr = json.loads((tmp_path / "refs/tdr_candidate_jitter/jitter_summary.json").read_text())
    assert [s["candidate_label"] for s in tdr] == ["tdr_candidate_a", "tdr_candidate_b"]
    moga = json.loads((tmp_path / "refs/moga_nominal/moga_reference.json").read_text())
    assert moga["role"] == "moga_derived_nominal"
    with pytest.raises(SystemExit):
        module.main(["--output-dir", str(tmp_path / "refs"), "--mock-evaluator"])
