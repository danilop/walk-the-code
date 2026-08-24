"""walk-the-code: interactive line-by-line code tutorial viewer."""

from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = PACKAGE_DIR / "assets"

# Dev mode: assets live at repo root, not in a subdirectory
if not ASSETS_DIR.exists():
    ASSETS_DIR = PACKAGE_DIR.parent.parent  # src/walk_the_code -> src -> repo root

try:  # installed distribution
    from importlib.metadata import PackageNotFoundError, version as _dist_version

    __version__ = _dist_version("walk-the-code")
except (ImportError, PackageNotFoundError):  # running from a source checkout
    __version__ = "0+unknown"


def build_commit():
    """Return the git commit this distribution was built from, if recorded.

    uv and pip write direct_url.json when installing from a VCS URL, which is
    how walk-the-code is normally installed. Returns None for a plain source
    checkout or a release without VCS metadata.
    """
    import json
    from importlib.metadata import distribution

    try:
        raw = distribution("walk-the-code").read_text("direct_url.json")
    except Exception:
        return None
    if not raw:
        return None
    try:
        return (json.loads(raw).get("vcs_info") or {}).get("commit_id")
    except ValueError:
        return None


def version_string():
    """Human-readable version line: the timestamp, plus the commit when known."""
    commit = build_commit()
    return f"walk-the-code {__version__}" + (f" (commit {commit[:12]})" if commit else "")
