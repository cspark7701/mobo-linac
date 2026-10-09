#!/usr/bin/env python3
"""Validation campaign; equivalent to ``mobo-linac run-validation``.

Options and defaults are those of ``mobo-linac run-validation`` (see ``--help``).
"""

import sys

from mobo_linac.cli import main as cli_main

COMMAND = "run-validation"


def main(argv=None):
    return cli_main([COMMAND, *(sys.argv[1:] if argv is None else argv)])


if __name__ == "__main__":
    sys.exit(main())
