#!/usr/bin/env python3
"""
Pareto Verification Production Script (Task 08).

Executes independent reruns of Pareto candidates in fresh isolated workdirs,
computes checksums and relative differences, and generates verification tables.
"""

import sys
from mobo_linac.cli import main

if __name__ == "__main__":
    if len(sys.argv) == 1 or sys.argv[1] != "run-verification":
        sys.argv.insert(1, "run-verification")
    main()
