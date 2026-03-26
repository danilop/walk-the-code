#!/usr/bin/env python3
"""Build a static labs.json bundle for GitHub Pages deployment.

Bundles lab metadata, code, comments, and diagrams into a single JSON file.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / (sys.argv[1] if len(sys.argv) > 1 else "config.json")
config = json.loads(CONFIG_PATH.read_text())
CODE_DIR = (ROOT / config.get("code_dir", ".")).resolve()
DEFAULT_LANG = config.get("language", "python")

EXT_TO_LANG = {
    ".py": "python", ".js": "javascript", ".ts": "typescript", ".tsx": "typescript",
    ".c": "c", ".h": "c", ".cpp": "cpp", ".cc": "cpp", ".cxx": "cpp", ".hpp": "cpp",
    ".rs": "rust", ".go": "go", ".java": "java",
}

def detect_language(filename):
    ext = "." + filename.rsplit(".", 1)[-1] if "." in filename else ""
    return EXT_TO_LANG.get(ext, DEFAULT_LANG)
OUTPUT_DIR = ROOT / "data"
OUTPUT_DIR.mkdir(exist_ok=True)

# Bundle labs
labs = []
for lab in config.get("labs", []):
    code_path = CODE_DIR / lab["id"] / lab["file"]
    stem = Path(lab["file"]).stem
    exp_path = ROOT / "comments" / lab["id"] / f"{stem}.json"

    labs.append({
        "id": lab["id"],
        "title": lab["title"],
        "tagline": lab.get("tagline", ""),
        "file": lab["file"],
        "language": lab.get("language", detect_language(lab["file"])),
        "code": code_path.read_text() if code_path.exists() else "",
        "explanations": json.loads(exp_path.read_text()) if exp_path.exists() else {},
    })

# Bundle diagrams
diagrams_dir = ROOT / "diagrams"
diagrams = {}
if diagrams_dir.exists():
    for mmd in diagrams_dir.glob("*.mmd"):
        diagrams[mmd.stem] = mmd.read_text()

bundle = {"config": {"title": config.get("title", ""), "tagline": config.get("tagline", "")},
          "labs": labs, "diagrams": diagrams}

output_path = OUTPUT_DIR / "labs.json"
output_path.write_text(json.dumps(bundle))
size_kb = output_path.stat().st_size / 1024
print(f"Built {output_path} ({len(labs)} labs, {len(diagrams)} diagrams, {size_kb:.0f} KB)")
