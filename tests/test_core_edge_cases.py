"""Core contracts reject malformed settings without creating scientific defaults."""

from dataclasses import asdict
import logging
import math

import pytest
import torch

from mobo_linac import config as configuration
from mobo_linac.campaign_options import (
    Acquisition,
    decode_acquisition,
    normalize_scalar_weights,
    validate_campaign_options,
)
from mobo_linac.constraints import ConstraintEvaluator, get_botorch_constraint_functions
from mobo_linac.conventions import reporting_metadata, validate_campaign_compatibility
from mobo_linac.objectives import extract_physical_objectives
from mobo_linac.perturbations import LatticeChannel, SourceChannel, PerturbationSpecification
from mobo_linac.requests import validate_evaluation_settings, requests_for
from mobo_linac.result_schema import ResultSchema
from mobo_linac.status import SimulationStatus, decode_status, classify_exception
from mobo_linac.utils.device import module_device
from mobo_linac.utils.logger import configure_logging


@pytest.mark.parametrize(
    "factory",
    [
        lambda: normalize_scalar_weights([1], 0),
        lambda: normalize_scalar_weights([True], 1),
        lambda: validate_campaign_options(num_initial_samples=2, num_batches=0, batch_size=1, seed=2**32),
        lambda: validate_campaign_options(num_initial_samples=2, num_batches=0, batch_size=1, total_eval_budget=2),
        lambda: ConstraintEvaluator(None),
        lambda: get_botorch_constraint_functions(None),
        lambda: get_botorch_constraint_functions(configuration.ConstraintsConfig()),
        lambda: get_botorch_constraint_functions(configuration.ConstraintsConfig(), num_objectives=0),
        lambda: validate_evaluation_settings([], None),
        lambda: validate_evaluation_settings([], {"design_variables": [1]}),
        lambda: validate_evaluation_settings([1], {"design_variables": [1]}, source_settings={"unknown": 1}),
        lambda: validate_evaluation_settings([1], {"design_variables": [1]}, namelist_overrides=[]),
        lambda: validate_evaluation_settings([1], {"design_variables": [1]}, namelist_overrides={"invalid": 1}),
        lambda: requests_for([[1]], eval_ids=[]),
        lambda: LatticeChannel("", "x", "relative", 0.1),
        lambda: LatticeChannel("x", "x", "invalid", 0.1),
        lambda: SourceChannel("", "x", 0.1),
        lambda: SourceChannel("x", "x", 0.1, distribution="invalid"),
        lambda: PerturbationSpecification((LatticeChannel("x", "x", "relative", 0.1),) * 2),
        lambda: PerturbationSpecification(
            (LatticeChannel("x", "x", "relative", 0.1), LatticeChannel("y", "x", "relative", 0.1))
        ),
        lambda: PerturbationSpecification((), (SourceChannel("x", "invalid", 0.1),)),
        lambda: PerturbationSpecification((), fragility_threshold=2),
        lambda: PerturbationSpecification((), num_perturbations=0),
        lambda: PerturbationSpecification((), seed=-1),
        lambda: PerturbationSpecification(()).with_stds(unknown=0.1),
        lambda: PerturbationSpecification.from_dict([]),
        lambda: PerturbationSpecification.from_dict(
            {"perturbations": {"gun_phase_error_deg": {"distribution": "invalid"}}}
        ),
        lambda: configuration.config_from_dict([]),
        lambda: configuration.config_from_dict({"execution": {"z_stop_m": 1}, "tracking": {"z_stop_m": 2}}),
    ],
)
def test_invalid_core_settings(factory):
    with pytest.raises((ValueError, TypeError)):
        factory()


def test_status_and_parameter_free_device_contracts():
    assert decode_acquisition(Acquisition.qLogNEHVI) is Acquisition.qLogNEHVI
    assert decode_status(SimulationStatus.SUCCESS) is SimulationStatus.SUCCESS
    assert decode_status(object()) is SimulationStatus.UNHANDLED_EXCEPTION
    assert classify_exception(EOFError()) is SimulationStatus.FILE_CORRUPTED
    assert module_device(torch.nn.Identity(), "cpu") == "cpu"
    assert module_device(object(), "cpu") == "cpu"
    configure_logging(level=logging.ERROR)
    assert logging.getLogger("mobo_linac").level == logging.ERROR
    configure_logging()


def test_config_relations_and_migrations(sample_config, tmp_path):
    with pytest.raises(ValueError, match="smaller"):
        configuration.TrackingConfig(z_stop_m=1, z_loss_tolerance_m=1).check_relations()
    configuration.SimulationConfig().validate()
    assert configuration.SimulationConfig().resolved_against(tmp_path).executable is None
    with pytest.raises(ValueError, match="static_files"):
        configuration.SimulationConfig(static_files=["../field"]).check_relations()
    configuration.CampaignSettings().validate()
    configuration.ScalarizedCaseConfig("one", [1, 1, 1], 0).validate()
    assert sample_config.get_nominal_parameters() == [v.nominal_value for v in sample_config.design_variables]
    with pytest.raises(ValueError, match="Unknown constraint profile"):
        sample_config.get_constraint_profile("absent")
    with pytest.raises(FileNotFoundError, match="No default"):
        configuration.resolve_config_path(default_names=("never-present.yaml",))
    path = tmp_path / "invalid.yaml"
    path.write_text("[]")
    with pytest.raises(ValueError, match="top-level"):
        configuration.load_config(path)
    data = asdict(sample_config)
    data["model"]["noise_mode"] = "fixed"
    data["execution"]["template_dir"] = "."
    data["simulation"] = {}
    restored = configuration.config_from_dict(data)
    assert restored.model.noise_mode == "deterministic_fixed"
    assert restored.simulation.template_dir == "."
    sample_config.perturbations = {"version": 2, "lattice": [], "source": []}
    sample_config.validate()


@pytest.mark.parametrize(
    "change,match",
    [
        (lambda c: c.sensitivity_profiles.update(nominal=c.constraints), "nominal"),
        (
            lambda c: c.scalarized_cases.update(
                {"not an identifier": configuration.ScalarizedCaseConfig("x", [1, 1, 1], 999)}
            ),
            "identifier",
        ),
        (lambda c: c.scalarized_cases.update({"another": next(iter(c.scalarized_cases.values()))}), "seed_offset"),
    ],
)
def test_invalid_configuration_relations(sample_config, change, match):
    change(sample_config)
    with pytest.raises(ValueError, match=match):
        sample_config.check_relations()


def test_schema_metadata_and_missing_observations(sample_config):
    schema = ResultSchema.from_config(sample_config)
    assert schema.transform(torch.ones(3, dtype=torch.long)).dtype == torch.double
    stats = {obj.name: object() for obj in sample_config.objectives}
    assert all(math.isnan(v) for v in extract_physical_objectives(stats, sample_config).values())
    with pytest.raises(ValueError):
        reporting_metadata(sample_config, [1])
    metadata = reporting_metadata(sample_config, schema.empty_reference)
    metadata["objective_units"] = []
    with pytest.raises(ValueError, match="dimensions"):
        validate_campaign_compatibility(metadata, metadata)
    sample_config.objectives[0].aliases = ["run_id"]
    with pytest.raises(ValueError, match="metadata"):
        ResultSchema.from_config(sample_config)
    sample_config.objectives[0].aliases = []
    sample_config.design_variables[0].name = sample_config.objectives[0].explicit_name
    with pytest.raises(ValueError, match="unique"):
        ResultSchema.from_config(sample_config)
