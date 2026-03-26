#!/usr/bin/env python3
"""walk-the-code static builder — thin wrapper for standalone use."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from walk_the_code.cli import build
build()
