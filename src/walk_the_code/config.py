"""Configuration loading, language detection, and shared constants."""

import hashlib
import json
from pathlib import Path


EXT_TO_LANG = {
    ".py": "python", ".js": "javascript", ".ts": "typescript", ".tsx": "typescript",
    ".c": "c", ".h": "c", ".cpp": "cpp", ".cc": "cpp", ".cxx": "cpp", ".hpp": "cpp",
    ".rs": "rust", ".go": "go", ".java": "java",
}

CONTENT_TYPES = {
    ".html": "text/html", ".css": "text/css", ".js": "application/javascript",
    ".json": "application/json", ".mjs": "application/javascript",
}


def _line_hash(text):
    return hashlib.sha256(text.strip().encode()).hexdigest()[:8]


def detect_language(filename, fallback="python"):
    ext = "." + filename.rsplit(".", 1)[-1] if "." in filename else ""
    return EXT_TO_LANG.get(ext, fallback)


def load_config(config_path):
    config_path = Path(config_path).resolve()
    config = json.loads(config_path.read_text())
    config_dir = config_path.parent
    config["_config_dir"] = str(config_dir)
    config["_code_dir"] = str((config_dir / config.get("code_dir", ".")).resolve())
    return config
