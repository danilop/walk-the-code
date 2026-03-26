#!/usr/bin/env python3
"""walk-the-code server — thin wrapper for standalone use.

When run directly (not installed as a package), this script works as before.
When installed via uv/pip, use the `wtc-serve` command instead.
"""
import sys
sys.argv.insert(0, "wtc-serve")  # make arg parsing work
from walk_the_code.cli import serve
serve()
