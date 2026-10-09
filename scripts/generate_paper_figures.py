#!/usr/bin/env python3
"""Manuscript figures and LaTeX tables from recorded runs; equivalent to ``mobo-linac paper-figures``.

Options and defaults are those of ``mobo-linac paper-figures`` (see ``--help``).
"""

import sys

from mobo_linac.cli import main as cli_main

COMMAND = "paper-figures"


def main(argv=None):
    return cli_main([COMMAND, *(sys.argv[1:] if argv is None else argv)])


if __name__ == "__main__":
    sys.exit(main())
