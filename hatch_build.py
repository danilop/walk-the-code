"""Derive the package version from the commit being built.

The version is the UTC commit date of HEAD as YYYYMMDDHHmmSS, so a given
commit always builds to the same version. Using the build clock instead
would give two installs of identical code different versions, which is
exactly the confusion this replaces: `uv tool list` could no longer tell
you whether a refresh actually moved you to newer code.

Fallbacks, in order: git metadata, the Version already recorded in
PKG-INFO (building a wheel from an sdist, where there is no .git), then
"0" so a build never hard-fails on version discovery alone.
"""

import os
import subprocess
from pathlib import Path

from hatchling.metadata.plugin.interface import MetadataHookInterface

FALLBACK = "0"


def _from_git(root):
    if not (Path(root) / ".git").exists():
        return None
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%cd", "--date=format-local:%Y%m%d%H%M%S"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=10,
            env={**os.environ, "TZ": "UTC"},
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    stamp = out.stdout.strip()
    return stamp if stamp.isdigit() and len(stamp) == 14 else None


def _from_pkg_info(root):
    pkg_info = Path(root) / "PKG-INFO"
    if not pkg_info.exists():
        return None
    for line in pkg_info.read_text().splitlines():
        if line.startswith("Version:"):
            return line.split(":", 1)[1].strip() or None
        if not line.strip():
            break
    return None


class CustomMetadataHook(MetadataHookInterface):
    def update(self, metadata):
        metadata["version"] = _from_git(self.root) or _from_pkg_info(self.root) or FALLBACK
