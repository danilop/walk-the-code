"""Configuration loading, language detection, and shared constants."""

import hashlib
import json
from pathlib import Path


EXT_TO_LANG = {
    ".py": "python", ".js": "javascript", ".ts": "typescript", ".tsx": "typescript",
    ".c": "c", ".h": "c", ".cpp": "cpp", ".cc": "cpp", ".cxx": "cpp", ".hpp": "cpp",
    ".rs": "rust", ".go": "go", ".java": "java",
    ".rb": "ruby", ".php": "php", ".swift": "swift", ".kt": "kotlin", ".kts": "kotlin",
    ".scala": "scala", ".cs": "csharp", ".lua": "lua", ".r": "r",
    ".sh": "bash", ".bash": "bash", ".zsh": "bash",
    ".yaml": "yaml", ".yml": "yaml", ".toml": "ini", ".ini": "ini",
    ".json": "json", ".xml": "xml", ".html": "xml", ".css": "css", ".scss": "scss",
    ".sql": "sql", ".md": "markdown", ".dockerfile": "dockerfile",
    ".tf": "hcl", ".hcl": "hcl", ".proto": "protobuf",
    ".zig": "zig", ".dart": "dart", ".ex": "elixir", ".exs": "elixir",
    ".hs": "haskell", ".ml": "ocaml", ".clj": "clojure",
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


def lab_files(lab, default_lang):
    """Return list of {path, language, role} dicts for a lab."""
    if lab.get("files"):
        return [
            {"path": f["path"], "language": detect_language(f["path"], default_lang),
             "role": f.get("role", "supporting")}
            for f in lab["files"]
        ]
    f = lab.get("file")
    if not f:
        return []
    return [{"path": f, "language": detect_language(f, default_lang), "role": "primary"}]


def primary_file(lab, default_lang):
    """Return the primary file entry for a lab."""
    files = lab_files(lab, default_lang)
    return next((f for f in files if f["role"] == "primary"), files[0])
