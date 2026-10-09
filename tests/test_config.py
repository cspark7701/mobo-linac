"""
Unit tests for Centralized Configuration System & Strict Schema Validation (Task 17).
"""

import json
from pathlib import Path
import pytest
import sys
import torch

from mobo_linac.config import (
    ConstraintsConfig,
    DesignVariableConfig,
    ExecutionConfig,
    GpModelConfig,
    MoboConfig,
    ObjectiveConfig,
    export_config_schema,
    generate_config_markdown_docs,
    load_config,
)
from mobo_linac.cli import main


def test_load_default_yaml_config():
    """Verify loading default YAML configuration file."""
    config = load_config("configs/mobo_200MeV.yaml")
    assert config.version == "1.0"
    assert len(config.design_variables) == 6
    assert len(config.objectives) == 3
    assert config.constraints.max_sigma_x_m == 1.0e-3
    assert config.constraints.min_mean_kinetic_energy_eV == 195.0e6


def test_bounds_ordering_negative_parameters():
    """Verify that bounds for negative parameters are ordered lower_bound <= upper_bound."""
    config = load_config("configs/mobo_200MeV.yaml")
    bounds_tensor = config.get_parameter_bounds_tensor()

    assert bounds_tensor.shape == (2, 6)
    lower = bounds_tensor[0]
    upper = bounds_tensor[1]

    # Every lower bound must be <= upper bound
    for i, (l, u) in enumerate(zip(lower, upper)):
        assert l <= u, f"Variable {config.design_variables[i].name} has invalid bounds ordering: {l} > {u}"

    # Specifically check quad 2 (negative value)
    quad2 = config.design_variables[2]
    assert quad2.nominal_value < 0
    assert quad2.lower_bound < quad2.nominal_value < quad2.upper_bound


def test_coupled_phase_mapping():
    """Verify that coupled cavity phases are explicitly declared."""
    config = load_config("configs/mobo_200MeV.yaml")

    acc1_2 = config.design_variables[4]
    assert acc1_2.is_coupled is True
    assert acc1_2.coupled_targets == ["cavity:phi(2)", "cavity:phi(3)"]

    acc3_4 = config.design_variables[5]
    assert acc3_4.is_coupled is True
    assert acc3_4.coupled_targets == ["cavity:phi(4)", "cavity:phi(5)"]


def test_invalid_bounds_rejected():
    """Verify that validation rejects lower_bound > upper_bound."""
    invalid_var = DesignVariableConfig(
        name="bad_var",
        astra_key="dummy",
        unit="T",
        nominal_value=1.0,
        ratio=0.5,
        lower_bound=5.0,
        upper_bound=1.0,
    )
    with pytest.raises(ValueError, match="lower_bound"):
        invalid_var.validate()


def test_invalid_coupled_variable_rejected():
    """Verify that coupled variables without targets are rejected."""
    bad_coupled = DesignVariableConfig(
        name="bad_coupled",
        astra_key="dummy",
        unit="deg",
        nominal_value=0.0,
        ratio=0.1,
        lower_bound=-10.0,
        upper_bound=10.0,
        is_coupled=True,
        coupled_targets=None,
    )
    with pytest.raises(ValueError, match="coupled_targets"):
        bad_coupled.validate()


def test_invalid_objective_direction_and_sign():
    """Verify objective validation fails for invalid direction or sign mismatch."""
    with pytest.raises(ValueError, match="physical_direction"):
        ObjectiveConfig(
            name="obj1",
            explicit_name="objective_1",
            unit="m",
            physical_direction="sideways",
            model_sign=-1,
        ).validate()

    with pytest.raises(ValueError, match="model_sign"):
        ObjectiveConfig(
            name="obj2",
            explicit_name="objective_2",
            unit="m",
            physical_direction="minimize",
            model_sign=1,  # Minimization must be -1
        ).validate()


def test_invalid_constraints_rejected():
    """Verify constraint validation fails on non-physical thresholds."""
    with pytest.raises(ValueError, match="mean kinetic energy constraints"):
        ConstraintsConfig(
            min_mean_kinetic_energy_eV=220.0e6,
            max_mean_kinetic_energy_eV=200.0e6,
        ).validate()

    with pytest.raises(ValueError, match="min_transmission"):
        ConstraintsConfig(min_transmission=1.5).validate()

    with pytest.raises(ValueError, match="max_sigma_x_m violates exclusiveMinimum"):
        ConstraintsConfig(max_sigma_x_m=-1.0).validate()


def test_duplicate_design_variable_rejected():
    """Verify MoboConfig rejects duplicate design variable names."""
    dv1 = DesignVariableConfig("var1", "key1", "T", 1.0, 0.1, 0.5, 1.5)
    dv2 = DesignVariableConfig("var1", "key2", "T", 1.0, 0.1, 0.5, 1.5)
    obj = ObjectiveConfig("obj1", "explicit_obj", "m", "minimize", -1)

    cfg = MoboConfig(
        version="1.0",
        description="Test",
        design_variables=[dv1, dv2],
        objectives=[obj],
        constraints=ConstraintsConfig(),
    )
    with pytest.raises(ValueError, match="Duplicate design variable"):
        cfg.validate()


def test_export_config_schema(tmp_path):
    """Verify JSON Schema export."""
    schema_path = tmp_path / "schema.json"
    schema = export_config_schema(schema_path)

    assert schema["$schema"] == "http://json-schema.org/draft-07/schema#"
    assert "design_variables" in schema["properties"]
    assert schema_path.exists()

    with open(schema_path, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded["title"] == "MoboConfig"


def test_generate_config_markdown_docs():
    """Verify Markdown documentation generator."""
    config = load_config("configs/mobo_200MeV.yaml")
    docs = generate_config_markdown_docs(config)

    assert "# Linac MOBO Configuration:" in docs
    assert "## 1. Design Variables (Decision Space)" in docs
    assert "## 2. Optimization Objectives" in docs
    assert "## 3. Physical Beam & Diagnostic Constraints" in docs
    assert "| `solenoid_field_T` |" in docs
    assert "| `norm_emit_x` |" in docs


def test_cli_validate_config(capsys, tmp_path):
    """Verify CLI validate-config subcommand execution and exports."""
    schema_p = tmp_path / "schema.json"
    docs_p = tmp_path / "config_docs.md"

    sys.argv = [
        "mobo-linac",
        "validate-config",
        "--config", "configs/publication_200MeV.yaml",
        "--export-schema", str(schema_p),
        "--export-docs", str(docs_p),
    ]
    main()

    captured = capsys.readouterr()
    assert "is VALID" in captured.out
    assert schema_p.exists()
    assert docs_p.exists()


def test_config_serialization(tmp_path):
    """Verify JSON and YAML serialization and deserialization."""
    config = load_config("configs/mobo_200MeV.yaml")

    json_path = tmp_path / "config.json"
    config.save_json(json_path)
    assert json_path.exists()

    with open(json_path, "r", encoding="utf-8") as f:
        loaded_dict = json.load(f)

    assert loaded_dict["version"] == "1.0"
    assert len(loaded_dict["design_variables"]) == 6

    yaml_path = tmp_path / "config.yaml"
    config.save_yaml(yaml_path)
    assert yaml_path.exists()


def test_explicit_missing_path_never_uses_default(tmp_path):
    from mobo_linac.config import resolve_config_path
    path = tmp_path / "missing.yaml"
    with pytest.raises(FileNotFoundError, match="Requested configuration"):
        load_config(path)
    with pytest.raises(FileNotFoundError):
        resolve_config_path(path)


def test_default_resolution_records_actual_source(tmp_path, monkeypatch):
    from dataclasses import asdict
    from mobo_linac.config import resolve_config_path
    source = Path("configs/mobo_200MeV.yaml").resolve()
    local = tmp_path / "configs"
    local.mkdir()
    target = local / "mobo_200MeV.yaml"
    target.write_text(source.read_text())
    monkeypatch.chdir(tmp_path)
    config = load_config()
    assert config.source_path == target.resolve() == resolve_config_path()
    assert "source_path" not in asdict(config)


@pytest.mark.parametrize("section,field", [
    ("design_variables", "nominal_value"), ("design_variables", "lower_bound"),
    ("design_variables", "upper_bound"), ("design_variables", "ratio"),
    ("constraints", "max_sigma_x_m"), ("constraints", "max_mean_kinetic_energy_eV"),
    ("model", "fixed_noise_variance"), ("model", "relative_noise_ratio"),
    ("model", "min_noise_variance"), ("tracking", "z_stop_m"),
    ("tracking", "z_loss_tolerance_m"),
])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_all_numeric_config_fields_reject_nonfinite(section, field, value):
    config = load_config("configs/mobo_200MeV.yaml")
    target = config.design_variables[0] if section == "design_variables" else getattr(config, section)
    setattr(target, field, value)
    with pytest.raises(ValueError, match="finite"):
        config.validate()


@pytest.mark.parametrize("field,value", [("acqf_maxiter", 0), ("acqf_batch_limit", -1),
    ("timeout_sec", 1.5), ("max_workers", True), ("retries", -1),
    ("clean_on_success", "false")])
def test_execution_limits_share_strict_field_rules(field, value):
    config = ExecutionConfig()
    setattr(config, field, value)
    with pytest.raises(ValueError):
        config.validate()


def test_fixed_design_variables_are_rejected():
    config = load_config("configs/mobo_200MeV.yaml")
    variable = config.design_variables[0]
    variable.lower_bound = variable.upper_bound = variable.nominal_value
    with pytest.raises(ValueError, match="fixed variables"):
        config.validate()


@pytest.mark.parametrize("noise", [[0.01], [0.01, float("nan"), 0.02], [0.01, 0, 0.02]])
def test_noise_vectors_require_positive_finite_matching_outputs(noise):
    config = load_config("configs/mobo_200MeV.yaml")
    config.model.objective_noise_variances = noise
    with pytest.raises(ValueError):
        config.validate()


def test_inferred_noise_rejects_fixed_noise_configuration():
    with pytest.raises(ValueError, match="inferred noise"):
        GpModelConfig(noise_mode="inferred", fixed_noise_variance=0.01).validate()


def test_schema_and_roundtrip_cover_every_dataclass_field(tmp_path):
    from dataclasses import asdict, fields
    from mobo_linac.config import config_from_dict, BenchmarkConfig
    jsonschema = pytest.importorskip("jsonschema")
    schema = export_config_schema()
    jsonschema.Draft7Validator.check_schema(schema)
    config = load_config("configs/publication_200MeV.yaml")
    config.name = None
    config.model.objective_noise_variances = [0.01, 0.02, 0.03]
    config.model.fixed_noise_variance = None
    config.objectives[0].aliases = ["horizontal_emit"]
    config.objectives[0].reporting_scale = 1e-6
    value = asdict(config)
    jsonschema.validate(value, schema)
    assert asdict(config_from_dict(value)) == value
    for suffix, save in (("json", config.save_json), ("yaml", config.save_yaml)):
        path = tmp_path / f"config.{suffix}"
        save(path)
        assert asdict(load_config(path)) == value
    pairs = [(MoboConfig, schema), (DesignVariableConfig, schema["properties"]["design_variables"]["items"]),
             (ObjectiveConfig, schema["properties"]["objectives"]["items"]),
             (ConstraintsConfig, schema["properties"]["constraints"]),
             (ExecutionConfig, schema["properties"]["execution"]),
             (GpModelConfig, schema["properties"]["model"]),
             (BenchmarkConfig, schema["definitions"]["BenchmarkConfig"])]
    for cls, definition in pairs:
        assert set(definition["properties"]) == {field.name for field in fields(cls)}
    docs = generate_config_markdown_docs(config)
    assert "model.objective_noise_variances" in docs
    assert "execution.acqf_maxiter" in docs
    assert "design_variables[].coupled_targets" in docs


@pytest.mark.parametrize("section,field,value", [("execution", "acqf_maxiter", 0),
    ("execution", "clean_on_success", 1), ("model", "objective_noise_variances", [0]),
    ("objectives", "name", "invalid name"), ("model", "surprise", 1)])
def test_schema_and_runtime_reject_same_invalid_fields(section, field, value):
    from dataclasses import asdict
    from mobo_linac.config import config_from_dict
    jsonschema = pytest.importorskip("jsonschema")
    data = asdict(load_config("configs/mobo_200MeV.yaml"))
    target = data[section][0] if section == "objectives" else data[section]
    target[field] = value
    with pytest.raises(ValueError):
        config_from_dict(data)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(data, export_config_schema())


@pytest.mark.parametrize("kwargs", [{"num_initial_samples": 0}, {"num_batches": -1},
    {"batch_size": 0}, {"num_workers": 0}, {"seed": -1}, {"optimization_mode": "typo"},
    {"scalar_weights": [1, 2]}, {"scalar_weights": [float("inf"), 1, 1]},
    {"reporting_ref_point": [1, 2]}])
def test_runner_invalid_options_create_no_directory(tmp_path, kwargs):
    from mobo_linac.campaigns.runner import MoboCampaignRunner
    output = tmp_path / "invalid"
    with pytest.raises(ValueError):
        MoboCampaignRunner(config=load_config("configs/mobo_200MeV.yaml"), output_dir=output, **kwargs)
    assert not output.exists()


def test_large_finite_scalar_weights_normalize_without_overflow():
    from mobo_linac.campaign_options import normalize_scalar_weights
    weights = normalize_scalar_weights([1e308, 1e308, 1e308], 3)
    torch.testing.assert_close(weights, torch.full((3,), 1/3, dtype=torch.double))


@pytest.mark.parametrize("setting", [float("nan"), float("inf"), 0, -1])
def test_invalid_source_scales_fail_before_attempt_creation(tmp_path, setting):
    from mobo_linac.astra.runner import run_astra_eval
    output = tmp_path / "invalid"
    with pytest.raises(ValueError):
        run_astra_eval([0.2, 1, -1, 0, 0, 0], base_results_dir=output,
                       source_settings={"bunch_charge_scale": setting}, config=load_config('configs/mobo_200MeV.yaml'))
    assert not output.exists()


def test_nonfinite_namelist_override_fails_before_attempt_creation(tmp_path):
    from mobo_linac.astra.runner import run_astra_eval
    output = tmp_path / "invalid"
    with pytest.raises(ValueError, match="finite"):
        run_astra_eval([0.2, 1, -1, 0, 0, 0], base_results_dir=output,
                       namelist_overrides={"charge:nrad": float("nan")}, config=load_config('configs/mobo_200MeV.yaml'))
    assert not output.exists()


def test_campaign_records_resolved_default_source(tmp_path):
    from mobo_linac.campaigns.runner import MoboCampaignRunner
    from mobo_linac.execution import MockEvaluator
    runner = MoboCampaignRunner(output_dir=tmp_path, num_initial_samples=2, num_batches=0,
                               evaluator=MockEvaluator(tmp_path), export_plots=False, export_env_info=False)
    runner.run()
    recorded = json.loads((tmp_path / "config_source.json").read_text())
    assert Path(recorded["resolved_path"]) == runner.config_path == runner.config.source_path
    assert recorded["source"] == "file"


def test_perturbation_explicit_missing_path_is_rejected(tmp_path):
    from mobo_linac.robustness.evaluator import load_perturbation_spec
    with pytest.raises(FileNotFoundError):
        load_perturbation_spec(tmp_path / "missing.yaml")


def test_nonfinite_design_request_is_rejected_before_directory(tmp_path):
    from mobo_linac.astra.runner import run_astra_eval
    output = tmp_path / "invalid"
    with pytest.raises(ValueError, match="finite"):
        run_astra_eval([float("nan"), 1, -1, 0, 0, 0], base_results_dir=output, config=load_config('configs/mobo_200MeV.yaml'))
    assert not output.exists()


def test_scalarized_acquisition_combination_is_validated():
    from mobo_linac.campaign_options import validate_campaign_options
    values = dict(num_initial_samples=2, num_batches=1, batch_size=1, acq_type="qLogNEI")
    validate_campaign_options(**values, optimization_mode="scalarized_bo")
    with pytest.raises(ValueError, match="qLogNEI requires"):
        validate_campaign_options(**values, optimization_mode="unconstrained_mobo")


def test_nullable_fields_and_required_defaults_match_schema():
    from dataclasses import asdict
    from mobo_linac.config import config_from_dict
    jsonschema = pytest.importorskip("jsonschema")
    schema = export_config_schema()
    value = asdict(load_config("configs/mobo_200MeV.yaml"))
    for dv in value["design_variables"]:
        if not dv["is_coupled"]:
            dv["coupled_targets"] = None
    value["model"]["objective_noise_variances"] = None
    value["objectives"][0]["reporting_scale"] = None
    jsonschema.validate(value, schema)
    assert asdict(config_from_dict(value)) == value
    del value["version"]
    with pytest.raises(ValueError, match="missing required"):
        config_from_dict(value)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(value, schema)


def test_benchmark_reference_dimension_fails_before_output(tmp_path):
    from mobo_linac.campaigns.benchmark import BenchmarkCampaignRunner
    from mobo_linac.config import BenchmarkConfig
    config = load_config("configs/mobo_200MeV.yaml")
    config.objectives = config.objectives[:2]
    output = tmp_path / "invalid"
    with pytest.raises(ValueError, match="reporting reference"):
        BenchmarkCampaignRunner(config, benchmark_config=BenchmarkConfig(
            output_dir=str(output), reporting_ref_point=[1.5, 1.5, 1.5]))
    assert not output.exists()


def test_benchmark_preserves_resolved_configuration_source(tmp_path):
    from mobo_linac.campaigns.benchmark import BenchmarkCampaignRunner
    config = load_config("configs/mobo_200MeV.yaml")
    benchmark = BenchmarkCampaignRunner(config, output_dir=tmp_path)
    assert benchmark.config.source_path == config.source_path


def test_invalid_batch_parameters_are_not_coerced_before_validation(tmp_path, monkeypatch):
    from mobo_linac.execution import EvaluationRequest, ProcessPoolEvaluator
    def forbid(*args, **kwargs):
        pytest.fail("Invalid request reached a worker")
    monkeypatch.setattr("mobo_linac.execution.parallel.run_worker_task", forbid)
    output = tmp_path / "invalid"
    evaluator = ProcessPoolEvaluator(load_config('configs/mobo_200MeV.yaml'), base_results_dir=output, max_workers=1)
    with pytest.raises(ValueError, match="finite numbers"):
        evaluator.evaluate([EvaluationRequest(1, [True, 1, -1, 0, 0, 0])])
    assert not output.exists()


@pytest.mark.parametrize("field,value", [("z_stop_m", 0), ("z_loss_tolerance_m", -0.1)])
def test_tracking_exit_plane_rules(field, value):
    from mobo_linac.config import TrackingConfig
    config = TrackingConfig()
    setattr(config, field, value)
    with pytest.raises(ValueError):
        config.validate()


def test_config_module_imports_cleanly_with_warnings_as_errors():
    import subprocess
    import sys
    completed = subprocess.run([sys.executable, "-W", "error", "-c", "import mobo_linac.config"],
                               capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr


def test_each_load_validates_fields_and_relations_once(monkeypatch):
    import mobo_linac.config as config_module
    calls = {"fields": 0, "relations": 0}
    original_value, original_relations = config_module._validate_value, config_module.MoboConfig.check_relations
    def count_value(value, definition, path):
        calls["fields"] += path == "MoboConfig"
        return original_value(value, definition, path)
    def count_relations(self):
        calls["relations"] += 1
        return original_relations(self)
    monkeypatch.setattr(config_module, "_validate_value", count_value)
    monkeypatch.setattr(config_module.MoboConfig, "check_relations", count_relations)
    config = load_config("configs/publication_200MeV.yaml")
    assert calls == {"fields": 1, "relations": 1}
    config.get_parameter_bounds_tensor()  # no re-validation on accessors
    assert calls == {"fields": 1, "relations": 1}


def test_archived_layout_migrates_and_serializes_to_current_layout():
    from dataclasses import asdict
    from mobo_linac.config import config_from_dict
    current = asdict(load_config("configs/publication_200MeV.yaml"))
    archived = {key: value for key, value in current.items() if key != "tracking"}
    archived["execution"] = {**current["execution"], "z_stop_m": 16.2, "z_loss_tolerance_m": 0.1}
    archived["sensitivity_profiles"] = {**current["sensitivity_profiles"], "nominal": current["constraints"]}
    migrated = config_from_dict(archived)
    assert migrated.tracking.z_stop_m == 16.2 and "z_stop_m" not in asdict(migrated)["execution"]
    assert "nominal" not in migrated.sensitivity_profiles
    assert migrated.get_constraint_profile("nominal") == migrated.constraints
    divergent = dict(archived, sensitivity_profiles={"nominal": {**current["constraints"], "max_sigma_x_m": 5e-3}})
    with pytest.raises(ValueError, match="nominal"):
        config_from_dict(divergent)


SYNTHETIC_CHANNEL_SCRIPT = r"""
import mobo_linac.diagnostics as diagnostics
channel = diagnostics.DiagnosticChannel(
    "bunch_charge_C", ("charge",), "C", lower_attribute="min_bunch_charge_C", lower_violation="charge",
    physical_minimum=0.0, label="$Q$", display_unit="pC", display_scale=1e-12,
    description="Bunch charge", lower_default=1.0e-10)
diagnostics.DIAGNOSTIC_CHANNELS = diagnostics.DIAGNOSTIC_CHANNELS + (channel,)  # the only code edit
from dataclasses import asdict
from mobo_linac.config import config_from_dict, export_config_schema, generate_config_markdown_docs, load_config
data = asdict(load_config("configs/mobo_200MeV.yaml"))
data["constraints"]["min_bunch_charge_C"] = 2.0e-10  # the YAML edit
config = config_from_dict(data)
assert config.constraints.min_bunch_charge_C == 2.0e-10
rule = export_config_schema()["properties"]["constraints"]["properties"]["min_bunch_charge_C"]
assert rule == {"type": "number", "exclusiveMinimum": 0.0, "default": 1.0e-10}, rule
assert "| Bunch charge ($Q$) | $\\ge 200$ | pC |" in generate_config_markdown_docs(config)
data["constraints"]["min_bunch_charge_C"] = -1.0
try:
    config_from_dict(data)
except ValueError as error:
    assert "min_bunch_charge_C" in str(error)
else:
    raise AssertionError("negative bound accepted")
"""


def test_synthetic_constraint_channel_needs_only_a_registry_entry():
    """A channel added to the registry becomes a validated, documented constraint field."""
    import subprocess
    import sys
    completed = subprocess.run([sys.executable, "-c", SYNTHETIC_CHANNEL_SCRIPT], capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr


def test_display_metadata_does_not_affect_checkpoint_compatibility():
    config = load_config("configs/mobo_200MeV.yaml")
    relabeled = load_config("configs/mobo_200MeV.yaml")
    relabeled.design_variables[0].label = None
    relabeled.objectives[0].display_unit = "nm"
    assert relabeled.scientific_dict() == config.scientific_dict()
    relabeled.design_variables[0].upper_bound += 1.0
    assert relabeled.scientific_dict() != config.scientific_dict()


def test_acquisition_names_and_legacy_alias_decode_once():
    from mobo_linac.campaign_options import Acquisition, MULTIOBJECTIVE_ACQUISITIONS, decode_acquisition
    assert decode_acquisition("scalarized_qLogNEI") is Acquisition.qLogNEI
    assert "qLogNEI" not in MULTIOBJECTIVE_ACQUISITIONS
    with pytest.raises(ValueError, match="Unsupported acquisition"):
        decode_acquisition("qUnknown")


def test_benchmark_section_supplies_runner_defaults(tmp_path):
    from mobo_linac.campaigns.benchmark import BenchmarkCampaignRunner
    config = load_config("configs/publication_200MeV.yaml")
    runner = BenchmarkCampaignRunner(config, output_dir=tmp_path, seeds=[7])
    assert runner.seeds == [7] and runner.total_eval_budget == config.benchmark.total_eval_budget
    assert runner.output_dir == tmp_path
