"""
Gaussian Process Surrogate Models Module for mobo_linac.
"""

from mobo_linac.models.gp import (
    FitOutcome,
    build_gp_models,
    build_scalarized_gp_model,
    fit_gp_models,
)
from mobo_linac.models.artifacts import load_model_artifact, save_model_artifact
from mobo_linac.models.pipeline import SurrogatePipeline
from mobo_linac.models.tuning import (
    AcquisitionTuningSummary,
    HyperparameterTuningSummary,
    PipelineTuningSummary,
    compare_acquisition_functions,
    tune_acquisition_hyperparameters,
    tune_full_optimization_pipeline,
    tune_gp_hyperparameters,
)

__all__ = [
    "FitOutcome",
    "save_model_artifact",
    "load_model_artifact",
    "build_gp_models",
    "build_scalarized_gp_model",
    "fit_gp_models",
    "SurrogatePipeline",
    "tune_gp_hyperparameters",
    "HyperparameterTuningSummary",
    "compare_acquisition_functions",
    "tune_acquisition_hyperparameters",
    "AcquisitionTuningSummary",
    "tune_full_optimization_pipeline",
    "PipelineTuningSummary",
]
