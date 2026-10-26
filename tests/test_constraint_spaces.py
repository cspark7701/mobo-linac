"""Constraint shading must match recorded thresholds and joint feasibility."""

import importlib.util
from pathlib import Path
import sys
from dataclasses import replace

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from mobo_linac.plotting.common import PlotSchema


def tool():
    spec = importlib.util.spec_from_file_location('constraint_spaces', Path(__file__).resolve().parents[1]/'scripts/compare_constraint_spaces.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def observations(schema):
    values = {}
    for s in schema.constraints:
        values[s.column] = ((s.lower+s.upper)/2 if s.lower is not None and s.upper is not None
                            else s.upper/2 if s.upper is not None else (s.lower+1)/2)
    frame = pd.DataFrame([values, values, values, {s.column: np.nan for s in schema.constraints}])
    frame['simulation_valid'] = [True, True, True, False]
    frame['physically_feasible'] = [True, False, False, False]
    specs = {s.column: s for s in schema.constraints}
    frame.loc[1, 'sigma_z_m'] = 1.1*specs['sigma_z_m'].upper
    frame.loc[2, 'mean_kinetic_energy_eV'] = 1.01*specs['mean_kinetic_energy_eV'].upper
    return frame


def test_projection_acceptance_does_not_imply_joint_feasibility(sample_config):
    module = tool()
    schema = PlotSchema.from_config(sample_config)
    frame, masks = module.measured_constraints(observations(schema), schema)
    assert len(frame) == 3  # The invalid attempt never receives coordinates.
    assert masks['sigma_x_m'].all() and masks['sigma_y_m'].all()
    assert list(frame.physically_feasible) == [True, False, False]
    assert set(sum(([x, y] for x, y, _ in module.PAIRS), [])) == {s.column for s in schema.constraints}
    fig = module.constraint_figure([module.Campaign(module.ALGORITHMS[0], frame)], schema)
    for ax in fig.axes:
        assert sum(len(c.get_offsets()) for c in ax.collections) == 3
        assert len(ax.patches) == 1
    energy = next(s for s in schema.constraints if s.column == 'mean_kinetic_energy_eV')
    patch = fig.axes[3].patches[0]
    assert patch.get_x() == pytest.approx(energy.lower/energy.scale)
    assert patch.get_width() == pytest.approx((energy.upper-energy.lower)/energy.scale)
    plt.close(fig)


def test_changed_thresholds_control_shading_and_recorded_flags(sample_config):
    module = tool()
    schema = PlotSchema.from_config(sample_config)
    frame = observations(schema)
    x = next(s for s in schema.constraints if s.column == 'sigma_x_m')
    schema = replace(schema, constraints=tuple(replace(s, upper=x.upper*.4) if s.column==x.column else s for s in schema.constraints))
    with pytest.raises(ValueError, match='Recorded feasibility'):
        module.measured_constraints(frame, schema)
    frame.physically_feasible = False
    measured, _ = module.measured_constraints(frame, schema)
    fig = module.constraint_figure([module.Campaign(module.ALGORITHMS[0], measured)], schema)
    patch = fig.axes[0].patches[0]
    assert patch.get_x()+patch.get_width() == pytest.approx(x.upper*.4/x.scale)
    plt.close(fig)


def test_nonfinite_valid_diagnostics_are_not_imputed(sample_config):
    module = tool()
    schema = PlotSchema.from_config(sample_config)
    frame = observations(schema)
    frame.loc[0, 'sigma_z_m'] = np.nan
    with pytest.raises(ValueError, match='Missing/nonfinite'):
        module.measured_constraints(frame, schema)
