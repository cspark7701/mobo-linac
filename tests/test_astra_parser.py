"""
Unit tests for AstraOutputParser and SimulationStatus diagnostics in mobo_linac.astra.parser.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
import pytest

from mobo_linac.astra.parser import (
    AstraOutputParser,
    ParsedAstraResult,
    SimulationStatus,
)
from mobo_linac.diagnostics import DIAGNOSTIC_CHANNELS

from mobo_linac.config import load_config as _load_test_config
TEST_CONFIG = _load_test_config("configs/mobo_200MeV.yaml")


def nominal_stats():
    return {"norm_emit_x": [1e-6], "norm_emit_y": [1e-6], "sigma_energy": [0.5e6],
            "sigma_x": [0.5e-3], "sigma_y": [0.5e-3], "sigma_xp": [0.5e-3],
            "sigma_yp": [0.5e-3], "sigma_z": [0.5e-3], "mean_kinetic_energy": [200e6],
            "transmission": [1.0], "z": [16.2]}


@pytest.mark.parametrize("channel", DIAGNOSTIC_CHANNELS, ids=lambda c: c.name)
def test_parser_missing_channels_are_not_observed_zeroes(channel):
    stats = nominal_stats()
    del stats[channel.aliases[0]]
    result = AstraOutputParser(config=TEST_CONFIG).parse_astra_simulation(MockAstraSim(stats))
    assert result.status == SimulationStatus.OUTPUT_MISSING
    assert not result.simulation_valid
    assert channel.name not in result.diagnostics
    assert channel.name in result.error_message


@pytest.mark.parametrize("alias", ["sigma_x", "sigma_y", "sigma_xp", "sigma_yp", "sigma_z", "mean_kinetic_energy", "transmission"])
def test_parser_empty_measurement_arrays_remain_unobserved(alias):
    stats = nominal_stats()
    stats[alias] = []
    result = AstraOutputParser(config=TEST_CONFIG).parse_astra_simulation(MockAstraSim(stats))
    assert not result.simulation_valid
    assert result.status == SimulationStatus.OUTPUT_MISSING


@pytest.mark.parametrize("value", [float("nan"), float("inf")])
def test_parser_nonfinite_transmission_is_numerically_invalid(value):
    stats = nominal_stats()
    stats["transmission"] = [value]
    result = AstraOutputParser(config=TEST_CONFIG).parse_astra_simulation(MockAstraSim(stats))
    assert not result.simulation_valid
    assert result.status == SimulationStatus.NUMERICAL_ERROR


def test_parser_canonical_units_and_conflicting_aliases():
    stats = nominal_stats()
    for channel in DIAGNOSTIC_CHANNELS:
        stats[channel.name] = stats.pop(channel.aliases[0])
    parser = AstraOutputParser(config=TEST_CONFIG)
    result = parser.parse_astra_simulation(MockAstraSim(stats))
    assert result.simulation_valid
    assert result.diagnostics["mean_kinetic_energy_eV"] == 200e6
    stats["sigma_x"] = [0.7e-3]
    conflicted = parser.parse_astra_simulation(MockAstraSim(stats))
    assert conflicted.status == SimulationStatus.NUMERICAL_ERROR
    assert not conflicted.simulation_valid


def test_parser_invalid_particle_counts_are_classified_without_crashing():
    stats = nominal_stats()
    stats["landf_n_particles"] = [float("nan"), 100]
    result = AstraOutputParser(config=TEST_CONFIG).parse_astra_simulation(MockAstraSim(stats))
    assert result.status == SimulationStatus.NUMERICAL_ERROR
    assert not result.simulation_valid


@dataclass
class MockParticle:
    n_particle: int


class MockAstraSim:
    """Mock Astra simulation instance for unit testing output parser."""

    def __init__(
        self,
        stats: Optional[Dict[str, Any]] = None,
        particles: Optional[List[MockParticle]] = None,
    ):
        self.output = {"stats": stats} if stats is not None else {}
        self.particles = particles or []


def test_parser_healthy_simulation():
    """Tests parsing a standard, successful ASTRA run."""
    parser = AstraOutputParser(config=TEST_CONFIG)
    stats = {
        "norm_emit_x": [4.0e-6, 3.5e-6],
        "norm_emit_y": [4.1e-6, 3.6e-6],
        "sigma_energy": [1.0e6, 0.85e6],
        "mean_kinetic_energy": [50e6, 201.5e6],
        "sigma_x": [1.0e-3, 0.45e-3],
        "sigma_y": [1.0e-3, 0.48e-3],
        "sigma_xp": [0.8e-3, 0.35e-3],
        "sigma_yp": [0.8e-3, 0.38e-3],
        "sigma_z": [1.2e-3, 0.65e-3],
        "z": [0.0, 16.2],
        "landf_n_particles": [1000, 1000],
    }
    sim = MockAstraSim(stats=stats, particles=[MockParticle(1000), MockParticle(1000)])

    res: ParsedAstraResult = parser.parse_astra_simulation(sim)

    assert res.status == SimulationStatus.SUCCESS
    assert res.simulation_valid is True
    assert res.objectives["norm_emit_x"] == 3.5e-6
    assert res.objectives["norm_emit_y"] == 3.6e-6
    assert res.objectives["sigma_energy"] == 0.85e6
    assert res.telemetry["z_final_m"] == 16.2
    assert set(res.diagnostics) <= {channel.name for channel in DIAGNOSTIC_CHANNELS}
    assert res.transmission_fraction == 1.0


def test_parser_premature_beam_loss():
    """Tests premature tracking termination detection (e.g., lost at collimator)."""
    parser = AstraOutputParser(config=TEST_CONFIG)
    stats = {
        "norm_emit_x": [4.0e-6, 3.5e-6],
        "norm_emit_y": [4.1e-6, 3.6e-6],
        "sigma_energy": [1.0e6, 0.85e6],
        "mean_kinetic_energy": [50e6, 120e6],
        "z": [0.0, 8.4],  # stopped early at z=8.4m
        "landf_n_particles": [1000, 0],
    }
    sim = MockAstraSim(stats=stats, particles=[MockParticle(1000), MockParticle(0)])

    res: ParsedAstraResult = parser.parse_astra_simulation(sim)

    assert res.status in (SimulationStatus.PREMATURE_LOSS, SimulationStatus.CHARGE_ZERO)
    assert res.simulation_valid is False
    assert res.z_final_m == 8.4


def test_parser_charge_zero():
    """Tests beam loss with zero transmission at exit."""
    parser = AstraOutputParser(config=TEST_CONFIG)
    stats = {
        "norm_emit_x": [4.0e-6, 3.5e-6],
        "norm_emit_y": [4.1e-6, 3.6e-6],
        "sigma_energy": [1.0e6, 0.85e6],
        "mean_kinetic_energy": [50e6, 200e6],
        "z": [0.0, 16.2],
        "landf_n_particles": [1000, 0],
    }
    sim = MockAstraSim(stats=stats, particles=[MockParticle(1000), MockParticle(0)])

    res: ParsedAstraResult = parser.parse_astra_simulation(sim)

    assert res.status == SimulationStatus.CHARGE_ZERO
    assert res.simulation_valid is False
    assert res.transmission_fraction == 0.0


def test_parser_timeout_and_exceptions():
    """Tests timeout error handling."""
    parser = AstraOutputParser(config=TEST_CONFIG)
    import subprocess
    res_timeout = parser.parse_astra_simulation(None, error=subprocess.TimeoutExpired("astra", 30))
    assert res_timeout.status == SimulationStatus.TIMEOUT
    assert res_timeout.simulation_valid is False

    res_num = parser.parse_astra_simulation(None, error=FloatingPointError("overflow"))
    assert res_num.status == SimulationStatus.NUMERICAL_ERROR
    assert res_num.simulation_valid is False


@pytest.mark.parametrize("message", ["information unavailable", "infeasible request", "config not found"])
def test_exception_messages_never_choose_the_category(message):
    """Classification uses exception types and run state, not message substrings."""
    parser = AstraOutputParser(config=TEST_CONFIG)
    assert parser.parse_astra_simulation(None, error=RuntimeError(message)).status == SimulationStatus.UNHANDLED_EXCEPTION


def test_runtime_timeout_record_and_unfinished_run_are_classified():
    class Sim:
        def __init__(self, run_info):
            self.output = {"run_info": run_info}
    parser = AstraOutputParser(config=TEST_CONFIG)
    timed_out = Sim({"start_time": 0.0, "why_error": "timeout"})
    unfinished = Sim({"start_time": 0.0, "why_error": ""})
    error = ValueError("Couldn't find finished simulation")
    assert parser.parse_astra_simulation(timed_out, error=error).status == SimulationStatus.TIMEOUT
    assert parser.parse_astra_simulation(unfinished, error=error).status == SimulationStatus.RUN_FAILED


def test_parser_missing_and_corrupted_output(tmp_path):
    """Tests handling when output stats dictionary is missing or has NaNs."""
    parser = AstraOutputParser(config=TEST_CONFIG)
    sim_empty = MockAstraSim(stats=None)
    res_empty = parser.parse_astra_simulation(sim_empty, eval_dir=tmp_path)
    assert res_empty.status == SimulationStatus.OUTPUT_MISSING
    assert res_empty.simulation_valid is False

    # NaN in stats
    stats_nan = {
        "norm_emit_x": [float("nan")],
        "norm_emit_y": [3.5e-6],
        "sigma_energy": [1e6],
    }
    sim_nan = MockAstraSim(stats=stats_nan)
    res_nan = parser.parse_astra_simulation(sim_nan)
    assert res_nan.status == SimulationStatus.NUMERICAL_ERROR
    assert res_nan.simulation_valid is False


def test_configured_parser_extracts_observed_aliases_and_missing_custom_objective():
    from mobo_linac.config import load_config, ObjectiveConfig
    config = load_config("configs/mobo_200MeV.yaml")
    config.objectives = [config.objectives[2], ObjectiveConfig("brightness", "brightness_value", "1", "maximize", 1, aliases=["observed_brightness"])]
    stats = nominal_stats()
    stats["observed_brightness"] = [2.0, 4.0]
    result = AstraOutputParser(config=config).parse_astra_simulation(MockAstraSim(stats))
    assert result.simulation_valid
    assert result.objectives["brightness"] == 4.0
    stats["brightness"] = [5.0]
    conflict = AstraOutputParser(config=config).parse_astra_simulation(MockAstraSim(stats))
    assert not conflict.simulation_valid and conflict.status == SimulationStatus.NUMERICAL_ERROR
    del stats["brightness"]
    del stats["observed_brightness"]
    missing = AstraOutputParser(config=config).parse_astra_simulation(MockAstraSim(stats))
    assert missing.objectives is None
    assert missing.status == SimulationStatus.OUTPUT_MISSING
