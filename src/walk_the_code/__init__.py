"""walk-the-code: interactive line-by-line code tutorial viewer."""

from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = PACKAGE_DIR / "assets"

# Dev mode: assets live at repo root, not in a subdirectory
if not ASSETS_DIR.exists():
    ASSETS_DIR = PACKAGE_DIR.parent.parent  # src/walk_the_code -> src -> repo root
