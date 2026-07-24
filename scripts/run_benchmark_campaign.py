#!/usr/bin/env python3
"""
Benchmark Campaign Script.

Invokes canonical benchmark orchestration package APIs.
"""

import sys
from mobo_linac.cli import main

if __name__ == "__main__":
    if len(sys.argv) == 1:
        sys.argv.append("run-benchmark")
    main()
