#!/usr/bin/env python3
"""Phase comparison report with audited verification; equivalent to ``mobo-linac compare``.

Options and defaults are those of ``mobo-linac compare`` (see ``--help``).
"""

import sys

from mobo_linac.cli import main as cli_main

COMMAND = "compare"


def main(argv=None):
    return cli_main([COMMAND, *(sys.argv[1:] if argv is None else argv)])


if __name__ == "__main__":
    sys.exit(main())
