#!/usr/bin/env python3
"""Paired multi-seed benchmark campaign; equivalent to ``mobo-linac run-benchmark``.

Options and defaults are those of ``mobo-linac run-benchmark`` (see ``--help``).
"""

import sys

from mobo_linac.cli import main as cli_main

COMMAND = "run-benchmark"


def main(argv=None):
    return cli_main([COMMAND, *(sys.argv[1:] if argv is None else argv)])


if __name__ == "__main__":
    sys.exit(main())
