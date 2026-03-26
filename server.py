#!/usr/bin/env python3
"""walk-the-code server — thin wrapper for standalone use.

When run directly (not installed as a package), this script works as before.
When installed via uv/pip, use the `wtc-serve` command instead.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

sys.argv.insert(0, "wtc-serve")  # make arg parsing work
from walk_the_code.cli import serve
serve()
