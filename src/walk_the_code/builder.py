"""Build command: bundle units, diagrams, groups into a single JSON file."""

import json
import sys
from pathlib import Path

from .config import _line_hash, detect_language, unit_files, primary_file, load_config


def build():
    """CLI entry point: walk-the-code build [config_path]"""
    config_path = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else "config.json"
    config = load_config(config_path)
    config_dir = Path(config["_config_dir"])
    code_dir = Path(config["_code_dir"])
    default_lang = config.get("language", "python")

    units = []
    for unit in config.get("units", []):
        code_path = code_dir / unit["id"] / unit["file"]
        stem = Path(unit["file"]).stem
        exp_path = config_dir / "comments" / unit["id"] / f"{stem}.json"
        explanations = json.loads(exp_path.read_text()) if exp_path.exists() else {}

        # Build files array for multi-file support
        lf = unit_files(unit, default_lang)
        pf = next((f for f in lf if f["role"] == "primary"), lf[0])
        files_data = []
        for fe in lf:
            fp = code_dir / unit["id"] / fe["path"]
            fstem = Path(fe["path"]).stem
            fexp_path = config_dir / "comments" / unit["id"] / f"{fstem}.json"
            fexp = json.loads(fexp_path.read_text()) if fexp_path.exists() else {}
            files_data.append({
                "path": fe["path"], "language": fe["language"], "role": fe["role"],
                "code": fp.read_text() if fp.exists() else "",
                "explanations": fexp, "annotated_lines": len(fexp),
            })

        units.append({
            "id": unit["id"], "title": unit["title"], "tagline": unit.get("tagline", ""),
            "description": unit.get("description", ""),
            "learning_objectives": unit.get("learning_objectives", []),
            "exercises": unit.get("exercises", []),
            "file": unit["file"],
            "language": unit.get("language", detect_language(unit["file"], default_lang)),
            "code": code_path.read_text() if code_path.exists() else "",
            "explanations": explanations,
            "annotated_lines": len(explanations),
            "files": files_data,
        })

    diagrams_dir = config_dir / "diagrams"
    diagrams = {}
    if diagrams_dir.exists():
        for mmd in diagrams_dir.glob("*.mmd"):
            diagrams[mmd.stem] = mmd.read_text()

    groups = config.get("groups", [])

    # --- Validation ---
    warnings = []
    errors = []
    referenced_diagrams = set()

    for unit_entry in units:
        lid = unit_entry["id"]
        # Validate all files (multi-file support)
        for file_entry in unit_entry.get("files", []):
            code_lines = file_entry["code"].split("\n") if file_entry["code"] else []
            total_lines = len(code_lines)
            explanations = file_entry.get("explanations", {})
            fpath = file_entry["path"]

            for line_str, entry in explanations.items():
                line_num = int(line_str)
                if line_num < 1 or line_num > total_lines:
                    errors.append(f"{lid}/{fpath}: annotation for line {line_num} but code has only {total_lines} lines")
                text = entry.get("text", "") if isinstance(entry, dict) else entry
                if not text or not text.strip():
                    warnings.append(f"{lid}/{fpath}: empty annotation text at line {line_num}")
                if isinstance(entry, dict) and entry.get("diagram"):
                    diag_id = entry["diagram"]
                    referenced_diagrams.add(diag_id)
                    if diag_id not in diagrams:
                        errors.append(f"{lid}/{fpath}: line {line_num} references diagram '{diag_id}' but no {diag_id}.mmd found")
                if isinstance(entry, dict) and entry.get("highlight") and not entry.get("diagram"):
                    warnings.append(f"{lid}/{fpath}: line {line_num} has highlight but no diagram reference")
                if isinstance(entry, dict) and entry.get("hash") and 1 <= line_num <= total_lines:
                    expected = _line_hash(code_lines[line_num - 1])
                    if entry["hash"] != expected:
                        warnings.append(f"{lid}/{fpath}: line {line_num} hash mismatch (annotation may be outdated)")

    # Group unit and diagram references (recursive)
    all_unit_ids = {l["id"] for l in units}
    def _validate_groups(chs):
        for ch in chs:
            for unit_id in ch.get("units", []):
                if unit_id not in all_unit_ids:
                    errors.append(f"Group '{ch['id']}': references unit '{unit_id}' which is not in the units list")
            comp_diag = ch.get("comparison_diagram")
            if comp_diag:
                referenced_diagrams.add(comp_diag)
                if comp_diag not in diagrams:
                    errors.append(f"Group '{ch['id']}': comparison_diagram '{comp_diag}' not found in diagrams/")
            _validate_groups(ch.get("groups", []))
    _validate_groups(groups)

    # Orphaned diagram files
    orphaned = set(diagrams.keys()) - referenced_diagrams
    # Exclude diagrams referenced in group inline definitions
    def _collect_inline_diagrams(chs):
        for ch in chs:
            ch_diag = ch.get("diagram", "")
            for d in orphaned.copy():
                if d in ch_diag:
                    orphaned.discard(d)
            _collect_inline_diagrams(ch.get("groups", []))
    _collect_inline_diagrams(groups)
    if orphaned:
        warnings.append(f"Orphaned diagram files not referenced by any annotation: {', '.join(sorted(orphaned))}")

    stale = [w for w in warnings if "hash mismatch" in w]
    other_warnings = [w for w in warnings if "hash mismatch" not in w]
    if stale:
        print(f"\n  Stale annotations ({len(stale)}) — run wtc-hash to fix:")
        for w in stale:
            print(f"    ~ {w}")
    if other_warnings:
        print(f"\n  Warnings ({len(other_warnings)}):")
        for w in other_warnings:
            print(f"    - {w}")
    if errors:
        print(f"\n  Errors ({len(errors)}):")
        for e in errors:
            print(f"    ! {e}")

    output_dir = config_dir / "data"
    output_dir.mkdir(exist_ok=True)
    bundle = {
        "config": {
            "title": config.get("title", ""),
            "tagline": config.get("tagline", ""),
            "repo_url": config.get("repo_url", ""),
            "terminology": config.get("terminology"),
            "show_credits": config.get("show_credits", True),
        },
        "units": units, "diagrams": diagrams, "groups": groups,
    }
    # Inject analytics snippet if configured
    af = config.get("analytics_file")
    if af:
        af_path = config_dir / af
        if af_path.exists():
            bundle["config"]["analytics_snippet"] = af_path.read_text()
    output_path = output_dir / "units.json"
    output_path.write_text(json.dumps(bundle))
    print(f"\nBuilt {output_path} ({len(units)} units, {len(groups)} groups, {len(diagrams)} diagrams, {output_path.stat().st_size / 1024:.0f} KB)")
    if errors:
        print(f"\nBuild completed with {len(errors)} error(s). Fix them to ensure the tutorial works correctly.")
        sys.exit(1)
