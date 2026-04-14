"""Add content hashes to comment JSON files for sync detection."""

import json
import sys
from pathlib import Path

from .config import _line_hash, _unit_code_path, load_config


def hash():
    """CLI entry point: wtc-hash [config_path] — compute and write content hashes."""
    config_path = "config.json"
    for arg in sys.argv[1:]:
        if not arg.startswith("-"):
            config_path = arg
            break

    try:
        config = load_config(config_path)
    except FileNotFoundError:
        print(f"Error: config file not found: {config_path}")
        sys.exit(1)
    except json.JSONDecodeError as exc:
        print(f"Error: invalid JSON in {config_path}: {exc}")
        sys.exit(1)

    config_dir = Path(config["_config_dir"])
    code_dir = Path(config["_code_dir"])
    comments_dir = config_dir / "comments"

    total = 0
    for unit in config.get("units", []):
        uid = unit["id"]
        files = [f["path"] for f in unit["files"]] if unit.get("files") else [unit["file"]]

        for code_file in files:
            code_path = _unit_code_path(code_dir, unit, code_file)
            stem = Path(code_file).stem
            exp_path = comments_dir / uid / f"{stem}.json"

            if not code_path.exists():
                print(f"  {uid}/{code_file}: code file not found, skipping")
                continue

            code_lines = code_path.read_text().split("\n")
            exp_path.parent.mkdir(parents=True, exist_ok=True)

            if exp_path.exists():
                explanations = json.loads(exp_path.read_text())
            else:
                explanations = {}
                print(f"  {uid}/{code_file}: no comment file, creating empty")

            sample = next(iter(explanations.values()), None) if explanations else None
            already_hashed = isinstance(sample, dict)

            new_exp = {}
            for line_str, entry in explanations.items():
                idx = int(line_str) - 1
                h = _line_hash(code_lines[idx]) if 0 <= idx < len(code_lines) else ""
                if already_hashed:
                    entry["hash"] = h
                    new_exp[line_str] = entry
                else:
                    new_exp[line_str] = {"text": entry, "hash": h}

            exp_path.write_text(json.dumps(new_exp, indent=2))
            count = len(new_exp)
            total += count
            print(f"  {uid}/{code_file}: {count} entries updated")

    print(f"Done! {total} total entries hashed.")
