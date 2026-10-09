#!/usr/bin/env python3
"""Phase 2 unconstrained MOBO; equivalent to ``mobo-linac run-unconstrained``.

Options and defaults are the CLI's: omitted values come from the configuration's
``campaign`` section (workers from ``execution.max_workers``).
"""

import sys

from mobo_linac.cli import build_parser, main

COMMAND = "run-unconstrained"


def parse_args(argv=None):
    """Parse script arguments exactly as the CLI subcommand does."""
    return build_parser().parse_args([COMMAND, *(sys.argv[1:] if argv is None else argv)])


if __name__ == "__main__":
    main([COMMAND, *sys.argv[1:]])
