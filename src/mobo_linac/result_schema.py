"""Immutable configuration-derived contract for ordered evaluation data."""
from dataclasses import dataclass
from collections.abc import Mapping
import torch
from mobo_linac.diagnostics import finite_measurement

# Archived-run compatibility for the historical 200 MeV objective names:
# legacy alias, legacy model column, default reporting scale, empty-data reference.
_LEGACY = {"norm_emit_x": ("emit_x", "model_emit_x_neg", 1e-6, -1e-4),
           "norm_emit_y": ("emit_y", "model_emit_y_neg", 1e-6, -1e-4),
           "sigma_energy": (None, "model_sigma_energy_neg", 1e6, -1e7)}

RESERVED_COLUMNS = frozenset({
    "evaluation_id", "run_id", "simulation_valid", "physically_feasible", "failure_category",
    "failure_reason", "runtime_s", "work_dir", "batch_idx", "candidate_idx", "attempt_id",
    "manifest_path", "attempt_history"})


@dataclass(frozen=True)
class ResultSchema:
    design_columns: tuple
    physical_columns: tuple
    model_columns: tuple
    objective_aliases: tuple
    signs: tuple
    scales: tuple
    empty_reference: tuple = ()

    @classmethod
    def from_config(cls, config):
        """Derive the schema from a configuration; a schema is returned unchanged.

        There is no implicit default layout. Readers of archived pre-schema
        artifacts must request :func:`legacy_200MeV_schema` explicitly.
        """
        if isinstance(config, cls):
            return config
        if config is None or not hasattr(config, "objectives") or not hasattr(config, "design_variables"):
            raise TypeError("A MoboConfig or ResultSchema is required; implicit default layouts are not supported.")
        aliases, models, scales, references = [], [], [], []
        for obj in config.objectives:
            legacy = _LEGACY.get(obj.name)
            names = tuple(dict.fromkeys((obj.name, obj.explicit_name, *obj.aliases,
                                         *((legacy[0],) if legacy and legacy[0] else ()))))
            aliases.append(names)
            models.append(legacy[1] if legacy and obj.model_sign == -1 else
                          f"model_{obj.name}_{'neg' if obj.model_sign == -1 else 'pos'}")
            scale = obj.reporting_scale if obj.reporting_scale is not None else legacy[2] if legacy else 1.0
            scales.append(scale)
            references.append(legacy[3] if legacy and obj.model_sign == -1 else -10.0 * scale)
        flattened = [name for group in aliases for name in group]
        if len(flattened) != len(set(flattened)):
            raise ValueError("Objective names and aliases must identify exactly one objective.")
        if any(name in RESERVED_COLUMNS for name in flattened):
            raise ValueError("Objective names cannot use result metadata columns.")
        design = tuple(dv.name for dv in config.design_variables)
        physical = tuple(obj.explicit_name for obj in config.objectives)
        columns = design + physical + tuple(models)
        if set(columns) & RESERVED_COLUMNS or len(columns) != len(set(columns)):
            raise ValueError("Result column names must be unique.")
        return cls(design, physical, tuple(models), tuple(aliases),
                   tuple(obj.model_sign for obj in config.objectives), tuple(scales), tuple(references))

    def extract(self, values):
        """Missing observations remain absent; invalid/conflicting aliases remain invalid."""
        if isinstance(values, Mapping):
            ordered = []
            for names in self.objective_aliases:
                supplied = [values[name] for name in names if name in values]
                if not supplied:
                    return None
                if not all(finite_measurement(v) for v in supplied) or any(v != supplied[0] for v in supplied):
                    ordered.append(float("nan"))
                else:
                    ordered.append(float(supplied[0]))
            return ordered
        if isinstance(values, (list, tuple)) and len(values) == len(self.signs):
            return [float(v) if finite_measurement(v) else float("nan") for v in values]
        return None

    def transform(self, values):
        tensor = values if isinstance(values, torch.Tensor) else torch.as_tensor(values, dtype=torch.double)
        if not tensor.is_floating_point():
            tensor = tensor.to(dtype=torch.double)
        if tensor.ndim == 0 or tensor.shape[-1] != len(self.signs):
            raise ValueError("Objective width does not match result schema.")
        return tensor * tensor.new_tensor(self.signs)


def legacy_200MeV_schema() -> ResultSchema:
    """Explicit compatibility schema for archived 200 MeV artifacts written before
    configuration-derived schemas. Never used as an implicit default."""
    return ResultSchema(
        ("solenoid_field_T", "quad_1_gradient_T_m", "quad_2_gradient_T_m", "gun_phase_deg",
         "acc1_acc2_phase_deg", "acc3_acc4_phase_deg"),
        ("norm_emit_x_m_rad", "norm_emit_y_m_rad", "sigma_energy_eV"),
        ("model_emit_x_neg", "model_emit_y_neg", "model_sigma_energy_neg"),
        (("norm_emit_x", "norm_emit_x_m_rad", "emit_x"), ("norm_emit_y", "norm_emit_y_m_rad", "emit_y"),
         ("sigma_energy", "sigma_energy_eV")),
        (-1, -1, -1), (1e-6, 1e-6, 1e6), (-1e-4, -1e-4, -1e7),
    )
