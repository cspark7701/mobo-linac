"""
CLI commands package for mobo_linac.
"""

from mobo_linac.cli.commands.audit import (
    analyze_run,
    register_audit_commands,
    run_robustness,
    run_verification,
    validate_config,
)
from mobo_linac.cli.commands.benchmark import (
    analyze_benchmark,
    register_benchmark_commands,
    run_benchmark,
)
from mobo_linac.cli.commands.resume import (
    register_resume_command,
    resume_optimization,
)
from mobo_linac.cli.commands.run import (
    register_run_commands,
    run_constrained,
    run_scalarized,
    run_unconstrained,
    run_validation,
)

__all__ = [
    "run_unconstrained",
    "run_constrained",
    "run_scalarized",
    "run_validation",
    "resume_optimization",
    "run_benchmark",
    "analyze_benchmark",
    "run_robustness",
    "run_verification",
    "validate_config",
    "analyze_run",
    "register_run_commands",
    "register_resume_command",
    "register_benchmark_commands",
    "register_audit_commands",
]
