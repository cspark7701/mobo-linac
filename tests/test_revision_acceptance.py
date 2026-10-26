"""Acceptance-profile boundary checks for the post-hoc manuscript audit."""
import importlib.util
from pathlib import Path
import pandas as pd

spec=importlib.util.spec_from_file_location('revision_acceptance',Path(__file__).parents[1]/'scripts/analyze_revision_acceptance.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def row(**changes):
    values=dict(simulation_valid=True,sigma_x_m=.0001,sigma_y_m=.0001,
                sigma_xp_rad=.0001,sigma_yp_rad=.0001,sigma_z_m=.0005,
                mean_kinetic_energy_eV=200e6,transmission_fraction=1.,sigma_energy_eV=.3e6)
    values.update(changes)
    return values


def test_published_strict_boundaries_and_invalid_rows():
    df=pd.DataFrame([row(),row(sigma_x_m=.0003),row(transmission_fraction=.9999),row(simulation_valid=False),row(sigma_z_m=float('nan'))])
    masks=module.profile_masks(df)
    assert masks['production'].tolist()==[True,True,True,False,False]
    assert masks['napac2025'].tolist()==[True,False,False,False,False]


def test_energy_objective_and_constraint_are_distinct():
    df=pd.DataFrame([row(sigma_energy_eV=.6e6),row(mean_kinetic_energy_eV=195e6),row(mean_kinetic_energy_eV=205e6),row(mean_kinetic_energy_eV=205e6+1)])
    masks=module.profile_masks(df)
    assert masks['production'].tolist()==[True,True,True,False]
    assert masks['jkps2025_necessary_subset'].tolist()==[False,False,True,True]
    assert masks['jinst2024_necessary_subset'].tolist()==[False,False,True,True]
