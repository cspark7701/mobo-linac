#!/usr/bin/env python3
"""Validation campaign entry point; equivalent to ``mobo-linac run-validation``."""

import sys

from mobo_linac.cli import main

if __name__ == "__main__":
    main(["run-validation", *sys.argv[1:]])
