"""
I/O management module for mobo_linac.
Handles serialization, DataFrame conversions, CSV/JSON history saving,
checkpoint saving/restoration, and intra-batch streaming persistence.
"""

from mobo_linac.io.results import (
    CheckpointState,
    TrainingObservations,
    get_training_observations,
    get_constraint_tensors,
    append_streaming_evaluation,
    get_train_tensors,
    load_evaluation_results,
    load_run_checkpoint,
    load_streaming_evaluations,
    results_to_dataframe,
    save_evaluation_results,
    save_run_checkpoint,
)
from mobo_linac.io.journal import JournalRecord, load_streaming_records

__all__ = [
    "CheckpointState",
    "TrainingObservations",
    "get_training_observations",
    "get_constraint_tensors",
    "results_to_dataframe",
    "save_evaluation_results",
    "load_evaluation_results",
    "save_run_checkpoint",
    "load_run_checkpoint",
    "get_train_tensors",
    "append_streaming_evaluation",
    "load_streaming_evaluations",
    "JournalRecord",
    "load_streaming_records",
]
