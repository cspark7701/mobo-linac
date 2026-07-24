#!/usr/bin/env python3
"""
Robustness and Sensitivity Analysis Production Script (Task 07).

Executes perturbation sensitivity studies over representative Pareto candidates.
"""

import sys
from mobo_linac.cli import main

if __name__ == "__main__":
    if len(sys.argv) == 1:
        sys.argv.append("run-robustness")
    main()
