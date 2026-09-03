"""
ASTRA Output Parser and Simulation Status Diagnostics.

Extracts physical beam metrics, constraint diagnostics, phase space summaries,
and beam loss telemetry from ASTRA simulation runs and output files.
"""

from dataclasses import dataclass, field
from enum import Enum
import math
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Sequence, Union


class SimulationStatus(str, Enum):
    """Classification status for an ASTRA simulation execution."""

    SUCCESS = "SUCCESS"
    PREMATURE_LOSS = "PREMATURE_LOSS"
    CHARGE_ZERO = "CHARGE_ZERO"
    TIMEOUT = "TIMEOUT"
    NUMERICAL_ERROR = "NUMERICAL_ERROR"
    FILE_CORRUPTED = "FILE_CORRUPTED"
    OUTPUT_MISSING = "OUTPUT_MISSING"
    UNHANDLED_EXCEPTION = "UNHANDLED_EXCEPTION"


@dataclass
class ParsedAstraResult:
    """Structured and typed container for parsed ASTRA outputs."""

    status: SimulationStatus
    simulation_valid: bool = False
    objectives: Optional[Dict[str, float]] = None
    diagnostics: Dict[str, float] = field(default_factory=dict)
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

    def __init__(self, target_z_stop: float = 16.2, z_loss_tolerance: float = 0.1):
        self.target_z_stop = float(target_z_stop)
        self.z_loss_tolerance = float(z_loss_tolerance)

    def parse_astra_simulation(
        self,
        astra_sim: Any,
        eval_dir: Optional[Union[str, Path]] = None,
        error_context: Optional[str] = None,
    ) -> ParsedAstraResult:
        """
        Parses an executed Astra simulation instance or working directory.
        """
        # If execution threw an exception before completion
        if error_context:
            err_lower = error_context.lower()
            if "timeout" in err_lower or "timed out" in err_lower or "time out" in err_lower:
                status = SimulationStatus.TIMEOUT
            elif "nan" in err_lower or "inf" in err_lower or "floating point" in err_lower or "overflow" in err_lower:
                status = SimulationStatus.NUMERICAL_ERROR
            elif "corrupt" in err_lower or "not found" in err_lower or "missing" in err_lower:
                status = SimulationStatus.FILE_CORRUPTED
            else:
                status = SimulationStatus.UNHANDLED_EXCEPTION

            return ParsedAstraResult(
                status=status,
                simulation_valid=False,
                error_message=error_context,
            )

        # Check if output dictionary and stats exist
        if not hasattr(astra_sim, "output") or not isinstance(astra_sim.output, dict):
            return ParsedAstraResult(
                status=SimulationStatus.OUTPUT_MISSING,
                simulation_valid=False,
                error_message="ASTRA simulation produced no output dictionary",
            )

        raw_stats = astra_sim.output.get("stats")
        if not raw_stats or not isinstance(raw_stats, dict) or "norm_emit_x" not in raw_stats:
            # Attempt to parse log file from eval_dir if available
            log_diag = self.parse_log_dir(eval_dir) if eval_dir else {}
            return ParsedAstraResult(
                status=SimulationStatus.OUTPUT_MISSING,
                simulation_valid=False,
                error_message="ASTRA output stats dictionary is missing or empty",
                raw_log_summary=log_diag.get("log_summary"),
            )

        # Extract last-slice metrics
        try:
            norm_emit_x = float(raw_stats["norm_emit_x"][-1])
            norm_emit_y = float(raw_stats["norm_emit_y"][-1])
            sigma_energy = float(raw_stats["sigma_energy"][-1])
            mean_kinetic_energy = float(raw_stats.get("mean_kinetic_energy", [0.0])[-1])

            sigma_x_m = float(raw_stats.get("sigma_x", [0.0])[-1])
            sigma_y_m = float(raw_stats.get("sigma_y", [0.0])[-1])
            sigma_xp_rad = float(raw_stats.get("sigma_xp", [0.0])[-1])
            sigma_yp_rad = float(raw_stats.get("sigma_yp", [0.0])[-1])
            sigma_z_m = float(raw_stats.get("sigma_z", [0.0])[-1])
        except (IndexError, KeyError, TypeError, ValueError) as e:
            return ParsedAstraResult(
                status=SimulationStatus.FILE_CORRUPTED,
                simulation_valid=False,
                error_message=f"Corrupted or incomplete stats arrays: {e}",
            )

        # Check for NaN / Inf values
        scalars = [norm_emit_x, norm_emit_y, sigma_energy, mean_kinetic_energy,
                   sigma_x_m, sigma_y_m, sigma_xp_rad, sigma_yp_rad, sigma_z_m]
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
            except Exception:
                pass

        if n_init is None:
            if "landf_n_particles" in raw_stats and len(raw_stats["landf_n_particles"]) > 0:
                n_init = int(raw_stats["landf_n_particles"][0])
                n_final = int(raw_stats["landf_n_particles"][-1])
            elif "n_stat" in raw_stats and len(raw_stats["n_stat"]) > 0:
                n_init = int(raw_stats["n_stat"][0])
                n_final = int(raw_stats["n_stat"][-1])

        transmission_frac: Optional[float] = None
        if n_init is not None and n_final is not None and n_init > 0:
            transmission_frac = float(n_final) / float(n_init)
        elif "transmission" in raw_stats:
            transmission_frac = float(raw_stats["transmission"][-1])

        # Extract longitudinal exit z
        z_final: Optional[float] = None
        if "z" in raw_stats and len(raw_stats["z"]) > 0:
            z_final = float(raw_stats["z"][-1])

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

        objectives = {
            "norm_emit_x": norm_emit_x,
            "norm_emit_y": norm_emit_y,
            "sigma_energy": sigma_energy,
        }

        diagnostics: Dict[str, float] = {
            "emit_x": norm_emit_x,
            "emit_y": norm_emit_y,
            "sigma_energy": sigma_energy,
            "sigma_energy_eV": sigma_energy,
            "sigma_x": sigma_x_m,
            "sigma_x_m": sigma_x_m,
            "sigma_y": sigma_y_m,
            "sigma_y_m": sigma_y_m,
            "sigma_xp": sigma_xp_rad,
            "sigma_xp_rad": sigma_xp_rad,
            "sigma_yp": sigma_yp_rad,
            "sigma_yp_rad": sigma_yp_rad,
            "sigma_z": sigma_z_m,
            "sigma_z_m": sigma_z_m,
            "mean_kinetic_energy": mean_kinetic_energy,
            "mean_kinetic_energy_eV": mean_kinetic_energy,
        }

        if z_final is not None:
            diagnostics["z_final_m"] = z_final
            diagnostics["z_final"] = z_final
            diagnostics["z_stop_m"] = z_final

        if transmission_frac is not None:
            diagnostics["transmission_fraction"] = transmission_frac
            diagnostics["transmission"] = transmission_frac
        if n_init is not None:
            diagnostics["n_particles_initial"] = float(n_init)
        if n_final is not None:
            diagnostics["n_particles_final"] = float(n_final)

        return ParsedAstraResult(
            status=status,
            simulation_valid=(status == SimulationStatus.SUCCESS),
            objectives=objectives,
            diagnostics=diagnostics,
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
