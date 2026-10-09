#!/usr/bin/env python3
"""Independent audited reruns of representative Pareto candidates; equivalent to
``mobo-linac run-verification``.

Options and defaults are those of ``mobo-linac run-verification`` (see ``--help``).
"""

import sys

from mobo_linac.cli import main as cli_main

COMMAND = "run-verification"


def main(argv=None):
    return cli_main([COMMAND, *(sys.argv[1:] if argv is None else argv)])


if __name__ == "__main__":
    sys.exit(main())
