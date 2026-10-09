"""Reproducible validation campaign: one unconstrained MOBO run with every standard artifact."""

from pathlib import Path
from typing import Any, Dict, Optional, Union

from mobo_linac.config import MoboConfig
from mobo_linac.campaigns.runner import campaign_runner


def run_validation_campaign(
    config: MoboConfig,
    options: Dict[str, Any],
    base_results_dir: Union[str, Path] = "results",
    device: str = "auto",
    evaluator: Optional[Any] = None,
) -> Path:
    """Run a validation campaign in ``<base_results_dir>/validation_<timestamp>``.

    ``options`` are resolved campaign options (see ``config.resolve_campaign_options``).
    The standard campaign figures and artifacts are the validation outputs.
    """

    runner = campaign_runner(config, options, run_name="validation", base_results_dir=base_results_dir,
                             evaluator=evaluator, device=device)
    _, _, run_dir = runner.run()
    return run_dir
