#!/usr/bin/env python3
"""Phase 2 unconstrained MOBO; equivalent to ``mobo-linac run-unconstrained``.

Options and defaults are those of ``mobo-linac run-unconstrained`` (see ``--help``).
"""

import sys

from mobo_linac.cli import main as cli_main

COMMAND = "run-unconstrained"


def parse_args(argv=None):
    """Parse script arguments exactly as the CLI subcommand does."""
    from mobo_linac.cli import build_parser
    return build_parser().parse_args([COMMAND, *(sys.argv[1:] if argv is None else argv)])


def main(argv=None):
    return cli_main([COMMAND, *(sys.argv[1:] if argv is None else argv)])


if __name__ == "__main__":
    sys.exit(main())
