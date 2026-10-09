#!/usr/bin/env python3
"""Robustness and tolerance analysis of representative Pareto candidates; equivalent to
``mobo-linac run-robustness``.

Options and defaults are those of ``mobo-linac run-robustness`` (see ``--help``).
"""

import sys

from mobo_linac.cli import main as cli_main

COMMAND = "run-robustness"


def main(argv=None):
    return cli_main([COMMAND, *(sys.argv[1:] if argv is None else argv)])


if __name__ == "__main__":
    sys.exit(main())
