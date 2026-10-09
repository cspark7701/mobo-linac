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
    get_train_tensors,
    load_evaluation_results,
    load_run_checkpoint,
    results_to_dataframe,
    save_evaluation_results,
    save_run_checkpoint,
)
from mobo_linac.io.artifacts import RunArtifactWriter, validate_run_completion
from mobo_linac.io.journal import (
    EvaluationJournal,
    JournalRecord,
    append_streaming_evaluation,
    load_streaming_evaluations,
    load_streaming_records,
)

__all__ = [
    "RunArtifactWriter",
    "validate_run_completion",
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
    "EvaluationJournal",
    "JournalRecord",
    "load_streaming_records",
]
