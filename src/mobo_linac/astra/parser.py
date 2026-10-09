"""
ASTRA Output Parser and Simulation Status Diagnostics.

Extracts physical beam metrics, constraint diagnostics, phase space summaries,
and beam loss telemetry from ASTRA simulation runs and output files.
"""

from dataclasses import dataclass, field
import math
from pathlib import Path
from typing import Any, Dict, Optional, Union

from mobo_linac.diagnostics import (
    DIAGNOSTIC_CHANNELS, DIAGNOSTIC_NAMES, invalid_diagnostic_channels, normalize_diagnostics,
)
from mobo_linac.status import SimulationStatus, classify_exception


@dataclass
class ParsedAstraResult:
    """Structured and typed container for parsed ASTRA outputs.

    ``diagnostics`` holds only canonical constraint channels; ``telemetry`` holds
    auxiliary observations such as the final longitudinal position and particle counts.
    """

    status: SimulationStatus
    simulation_valid: bool = False
    objectives: Optional[Dict[str, float]] = None
    diagnostics: Dict[str, float] = field(default_factory=dict)
    telemetry: Dict[str, float] = field(default_factory=dict)
    raw_stats: Optional[Dict[str, Any]] = None
    z_final_m: Optional[float] = None
    transmission_fraction: Optional[float] = None
    n_particles_initial: Optional[int] = None
    n_particles_final: Optional[int] = None
    error_message: Optional[str] = None
    raw_log_summary: Optional[str] = None


class AstraOutputParser:
    """
    Parser for extracting scalar beam metrics, trajectories, and failure classifications
    from ASTRA simulation objects and working directories.
    """

    def __init__(self, *, config):
        """Exit-plane target and tolerance come only from the configured lattice settings."""
        from mobo_linac.result_schema import ResultSchema
        self.schema = ResultSchema.from_config(config)
        self.config = config
        self.target_z_stop = float(config.execution.z_stop_m)
        self.z_loss_tolerance = float(config.execution.z_loss_tolerance_m)

    def parse_astra_simulation(
        self,
        astra_sim: Any,
        eval_dir: Optional[Union[str, Path]] = None,
        error: Optional[BaseException] = None,
    ) -> ParsedAstraResult:
        """
        Parses an executed Astra simulation instance or working directory.

        ``error`` is the exception raised during execution; it is classified by type
        and recorded run information, never by message text.
        """
        if error is not None:
            return ParsedAstraResult(
                status=classify_exception(error, astra_sim),
                simulation_valid=False,
                error_message=f"{type(error).__name__}: {error}",
            )

        # Check if output dictionary and stats exist
        if not hasattr(astra_sim, "output") or not isinstance(astra_sim.output, dict):
            return ParsedAstraResult(
                status=SimulationStatus.OUTPUT_MISSING,
                simulation_valid=False,
                error_message="ASTRA simulation produced no output dictionary",
            )

        raw_stats = astra_sim.output.get("stats")
        objective_keys = {name for names in self.schema.objective_aliases for name in names}
        if not raw_stats or not isinstance(raw_stats, dict) or not objective_keys & set(raw_stats):
            # Attempt to parse log file from eval_dir if available
            log_diag = self.parse_log_dir(eval_dir) if eval_dir else {}
            return ParsedAstraResult(
                status=SimulationStatus.OUTPUT_MISSING,
                simulation_valid=False,
                error_message="ASTRA output stats dictionary is missing or empty",
                raw_log_summary=log_diag.get("log_summary"),
            )

        # Extract last-slice configured objective statistics.
        try:
            for key in objective_keys & set(raw_stats):
                float(raw_stats[key][-1])
        except (IndexError, KeyError, TypeError, ValueError) as e:
            return ParsedAstraResult(
                status=SimulationStatus.FILE_CORRUPTED,
                simulation_valid=False,
                error_message=f"Corrupted or incomplete stats arrays: {e}",
            )
        objective_values = {key: float(raw_stats[key][-1]) for key in objective_keys & set(raw_stats)}

        # Check for NaN / Inf values
        def last_measurement(key):
            try:
                value = raw_stats[key][-1]
            except (IndexError, KeyError, TypeError):
                return None
            try:
                return float(value)
            except (TypeError, ValueError, OverflowError):
                return float("nan")

        measured = {}
        for channel in DIAGNOSTIC_CHANNELS:
            if channel.name == "transmission_fraction":
                continue  # Counts/transmission are extracted separately below.
            for key in (channel.name,) + channel.aliases:
                if key in raw_stats:
                    value = last_measurement(key)
                    if value is not None:
                        measured[key] = value
        diagnostics = normalize_diagnostics(measured)
        scalars = list(objective_values.values()) + list(diagnostics.values())
        if any(math.isnan(s) or math.isinf(s) for s in scalars):
            return ParsedAstraResult(
                status=SimulationStatus.NUMERICAL_ERROR,
                simulation_valid=False,
                error_message="Non-finite NaN/Inf values detected in beam statistics",
            )

        # Extract particle counts & transmission
        n_init: Optional[int] = None
        n_final: Optional[int] = None

        if hasattr(astra_sim, "particles") and astra_sim.particles and len(astra_sim.particles) >= 1:
            try:
                n_init = int(astra_sim.particles[0].n_particle)
                n_final = int(astra_sim.particles[-1].n_particle)
            except (AttributeError, TypeError, ValueError, OverflowError):
                n_init = n_final = None

        if n_init is None:
            for count_name in ("landf_n_particles", "n_stat"):
                counts = raw_stats.get(count_name)
                if counts is None:
                    continue
                try:
                    if len(counts) == 0:
                        continue
                    n_init, n_final = int(counts[0]), int(counts[-1])
                except (TypeError, ValueError, OverflowError):
                    return ParsedAstraResult(status=SimulationStatus.NUMERICAL_ERROR,
                                             simulation_valid=False, raw_stats=raw_stats,
                                             error_message="Invalid particle-count observations")
                break

        transmission_frac: Optional[float] = None
        if n_init is not None and n_final is not None and n_init > 0:
            transmission_frac = float(n_final) / float(n_init)
        else:
            transmission_channel = DIAGNOSTIC_CHANNELS[-1]
            measured_transmission = {}
            for key in (transmission_channel.name,) + transmission_channel.aliases:
                value = last_measurement(key)
                if value is not None:
                    measured_transmission[key] = value
            transmission_frac = normalize_diagnostics(measured_transmission).get(transmission_channel.name)

        # Longitudinal exit telemetry retains its existing loss-detection role.
        z_final = last_measurement("z")
        if z_final is not None and not math.isfinite(z_final):
            return ParsedAstraResult(status=SimulationStatus.NUMERICAL_ERROR,
                                     simulation_valid=False, raw_stats=raw_stats,
                                     error_message="Non-finite longitudinal exit observation")

        # Classification checks
        status = SimulationStatus.SUCCESS
        error_message: Optional[str] = None

        if transmission_frac is not None and transmission_frac <= 0.0:
            status = SimulationStatus.CHARGE_ZERO
            error_message = "Transmitted charge/particles is zero (complete beam loss)"
        elif z_final is not None and z_final < (self.target_z_stop - self.z_loss_tolerance):
            status = SimulationStatus.PREMATURE_LOSS
            error_message = (
                f"Premature tracking termination at z = {z_final:.3f} m "
                f"(expected >= {self.target_z_stop - self.z_loss_tolerance:.3f} m)"
            )

        from mobo_linac.objectives import extract_physical_objectives
        try:
            objectives = extract_physical_objectives(raw_stats, self.schema)
            if status == SimulationStatus.SUCCESS and not all(math.isfinite(value) for value in objectives.values()):
                status = SimulationStatus.NUMERICAL_ERROR
                error_message = "Configured objectives contain invalid or conflicting observations"
        except KeyError:
            objectives = None
            status = SimulationStatus.OUTPUT_MISSING
            error_message = "Configured objective statistics missing"

        if transmission_frac is not None:
            diagnostics["transmission_fraction"] = transmission_frac
        diagnostics = {name: diagnostics[name] for name in DIAGNOSTIC_NAMES if name in diagnostics}
        telemetry: Dict[str, float] = {}
        if z_final is not None:
            telemetry["z_final_m"] = z_final
        if n_init is not None:
            telemetry["n_particles_initial"] = float(n_init)
        if n_final is not None:
            telemetry["n_particles_final"] = float(n_final)

        invalid_channels = invalid_diagnostic_channels(diagnostics)
        if status == SimulationStatus.SUCCESS and invalid_channels:
            invalid_present = any(name in diagnostics for name in invalid_channels)
            status = SimulationStatus.NUMERICAL_ERROR if invalid_present else SimulationStatus.OUTPUT_MISSING
            error_message = "Missing or invalid diagnostic observations: " + ", ".join(invalid_channels)

        return ParsedAstraResult(
            status=status,
            simulation_valid=(status == SimulationStatus.SUCCESS),
            objectives=objectives,
            diagnostics=diagnostics,
            telemetry=telemetry,
            raw_stats=raw_stats,
            z_final_m=z_final,
            transmission_fraction=transmission_frac,
            n_particles_initial=n_init,
            n_particles_final=n_final,
            error_message=error_message,
        )

    @staticmethod
    def parse_log_dir(eval_dir: Optional[Union[str, Path]]) -> Dict[str, Any]:
        """Parses ASTRA execution log or stdout file if available."""
        if not eval_dir:
            return {}
        p = Path(eval_dir)
        log_files = list(p.glob("*.log")) + list(p.glob("run.log"))
        if not log_files or not log_files[0].exists():
            return {}
        try:
            content = log_files[0].read_text()
            last_lines = "\n".join(content.strip().splitlines()[-10:])
            return {"log_summary": last_lines}
        except Exception:
            return {}
