"""Validate a walk-the-code project configuration and content."""

import json
import sys
from pathlib import Path

from .config import _line_hash, detect_language, unit_files, load_config


def validate():
    """CLI entry point: wtc-validate [--strict] [config_path] — check project for errors."""
    args = sys.argv[1:]
    config_path = "config.json"
    strict = "--strict" in args
    for arg in args:
        if not arg.startswith("-"):
            config_path = arg
            break

    errors = []
    warnings = []

    # --- Load config ---
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

    # --- Required top-level fields ---
    if not config.get("title"):
        warnings.append("No top-level 'title' field — will default to 'walk-the-code'")
    if not config.get("units"):
        errors.append("Missing required top-level field: units (or units array is empty)")

    # --- Validate each unit ---
    units_validated = 0
    all_unit_ids = set()
    coverage_data = []  # list of (unit_id, annotated_lines, total_lines)
    important_data = []  # list of (unit_id, important_count, annotated_count)

    for i, unit in enumerate(config.get("units", [])):
        prefix = f"units[{i}]"

        # Required unit fields
        for field in ("id", "file", "title"):
            if not unit.get(field):
                errors.append(f"{prefix}: missing required field '{field}'")

        unit_id = unit.get("id", f"<index {i}>")
        prefix = f"unit '{unit_id}'"
        all_unit_ids.add(unit_id)

        # Code file exists
        code_path = code_dir / unit_id / unit.get("file", "")
        if unit.get("file"):
            if not code_path.exists():
                errors.append(f"{prefix}: code file not found: {code_path}")

        # Learning objectives
        if not unit.get("learning_objectives"):
            warnings.append(f"{prefix}: no learning_objectives defined")

        # Exercises
        exercises = unit.get("exercises", [])
        if not exercises:
            warnings.append(f"{prefix}: no exercises defined")
        for j, ex in enumerate(exercises):
            if not isinstance(ex, dict):
                errors.append(f"{prefix}: exercises[{j}] is not an object")
            elif not ex.get("prompt"):
                warnings.append(f"{prefix}: exercises[{j}] has no 'prompt' field")

        # Comment file validation (primary file - backward compat)
        stem = Path(unit.get("file", "x")).stem
        comment_path = config_dir / "comments" / unit_id / f"{stem}.json"
        explanations = {}
        if comment_path.exists():
            try:
                explanations = json.loads(comment_path.read_text())
                if not isinstance(explanations, dict):
                    errors.append(f"{prefix}: comment file {comment_path.name} is not a JSON object")
                    explanations = {}
            except json.JSONDecodeError as exc:
                errors.append(f"{prefix}: invalid JSON in {comment_path.name}: {exc}")
        # Note: missing comment file is not an error — unit may not have annotations yet

        # Multi-file validation
        default_lang = config.get("language", "python")
        lf = unit_files(unit, default_lang)
        all_file_explanations = {}  # path -> explanations dict
        for fe in lf:
            fpath = code_dir / unit_id / fe["path"]
            if not fpath.exists():
                errors.append(f"{prefix}: file '{fe['path']}' not found: {fpath}")
            fstem = Path(fe["path"]).stem
            fcomment = config_dir / "comments" / unit_id / f"{fstem}.json"
            fexp = {}
            if fcomment.exists():
                try:
                    fexp = json.loads(fcomment.read_text())
                    if not isinstance(fexp, dict):
                        errors.append(f"{prefix}: comment file {fcomment.name} is not a JSON object")
                        fexp = {}
                except json.JSONDecodeError as exc:
                    errors.append(f"{prefix}: invalid JSON in {fcomment.name}: {exc}")
            all_file_explanations[fe["path"]] = (fpath, fexp)

        # Line number range and hash checks for all files
        for fpath_str, (fpath, fexp) in all_file_explanations.items():
            if fpath.exists() and fexp:
                code_text = fpath.read_text()
                code_lines = code_text.split("\n")
                total_lines = len(code_lines)

                for line_str, entry in fexp.items():
                    try:
                        line_num = int(line_str)
                    except ValueError:
                        errors.append(f"{prefix} ({fpath_str}): non-integer key '{line_str}' in comments")
                        continue

                    if line_num < 1 or line_num > total_lines:
                        errors.append(
                            f"{prefix} ({fpath_str}): annotation for line {line_num} but code has only {total_lines} lines"
                        )

                    if (
                        isinstance(entry, dict)
                        and entry.get("text")
                        and 1 <= line_num <= total_lines
                        and not code_lines[line_num - 1].strip()
                    ):
                        warnings.append(
                            f"{prefix} ({fpath_str}): line {line_num} annotation is attached to a blank line"
                        )

                    if isinstance(entry, dict) and entry.get("diagram"):
                        diag_id = entry["diagram"]
                        diag_path = config_dir / "diagrams" / f"{diag_id}.mmd"
                        if not diag_path.exists():
                            errors.append(
                                f"{prefix} ({fpath_str}): line {line_num} references diagram '{diag_id}' "
                                f"but {diag_path.name} not found"
                            )

                    if isinstance(entry, dict) and entry.get("hash") and 1 <= line_num <= total_lines:
                        expected = _line_hash(code_lines[line_num - 1])
                        if entry["hash"] != expected:
                            warnings.append(
                                f"{prefix} ({fpath_str}): line {line_num} hash mismatch (annotation may be stale)"
                            )

        # Track coverage and important data per file
        for fpath_str, (fpath, fexp) in all_file_explanations.items():
            if fpath.exists():
                cov_text = fpath.read_text()
                total_for_cov = len(cov_text.split("\n"))
                annotated_for_cov = sum(1 for key in fexp if str(key).isdigit())
                imp_count = sum(
                    1 for v in fexp.values()
                    if isinstance(v, dict) and v.get("important")
                )
                label = f"{unit_id}/{fpath_str}" if len(all_file_explanations) > 1 else unit_id
                coverage_data.append((label, annotated_for_cov, total_for_cov))
                if annotated_for_cov > 0:
                    important_data.append((label, imp_count, annotated_for_cov))

        units_validated += 1

    # --- Validate analytics_file ---
    af = config.get("analytics_file")
    if af:
        af_path = config_dir / af
        if not af_path.exists():
            errors.append(f"analytics_file '{af}' not found: {af_path}")
        else:
            af_content = af_path.read_text()
            import re as _re
            for m in _re.finditer(r'<script[^>]*\bsrc=["\']?(http://[^"\'>\s]+)', af_content):
                warnings.append(f"analytics_file: script references non-HTTPS URL: {m.group(1)}")

    # --- Group references (recursive) ---
    all_group_ids = set()
    def _validate_groups(chs):
        for ch in chs:
            ch_id = ch.get("id", "?")
            if ch_id in all_group_ids:
                errors.append(f"Duplicate group ID: '{ch_id}'")
            all_group_ids.add(ch_id)
            for unit_id in ch.get("units", []):
                if unit_id not in all_unit_ids:
                    errors.append(
                        f"group '{ch_id}': references unit '{unit_id}' which is not defined"
                    )
            comp_diag = ch.get("comparison_diagram")
            if comp_diag:
                diag_path = config_dir / "diagrams" / f"{comp_diag}.mmd"
                if not diag_path.exists():
                    errors.append(
                        f"group '{ch_id}': comparison_diagram '{comp_diag}' not found in diagrams/"
                    )
            # Knowledge checks
            for qi, check in enumerate(ch.get("knowledge_checks", [])):
                kprefix = f"group '{ch_id}' knowledge_checks[{qi}]"
                if not isinstance(check, dict):
                    errors.append(f"{kprefix}: must be an object")
                    continue
                if not check.get("question"):
                    errors.append(f"{kprefix}: missing 'question'")
                opts = check.get("options", [])
                if not isinstance(opts, list) or len(opts) < 2:
                    errors.append(f"{kprefix}: 'options' must be an array with at least 2 items")
                correct = check.get("correct")
                if not isinstance(correct, int) or correct < 0 or correct >= len(opts):
                    errors.append(f"{kprefix}: 'correct' must be an integer index into options")
                if not check.get("explanation"):
                    errors.append(f"{kprefix}: missing 'explanation'")
            _validate_groups(ch.get("groups", []))
    _validate_groups(config.get("groups", []))

    # --- Summary ---
    print(f"\nwalk-the-code validate: {config_path}\n")

    if warnings:
        print(f"  Warnings ({len(warnings)}):")
        for w in warnings:
            print(f"    ~ {w}")
        print()

    if errors:
        print(f"  Errors ({len(errors)}):")
        for e in errors:
            print(f"    ! {e}")
        print()

    # --- Annotation coverage ---
    if coverage_data:
        print("  Annotation coverage:")
        total_annotated = 0
        total_code_lines = 0
        max_id_len = max(len(unit_id) for unit_id, _, _ in coverage_data)
        for unit_id, annotated, total in coverage_data:
            pct = int(annotated / total * 100) if total else 0
            print(f"    {unit_id + ':':<{max_id_len + 1}}  {annotated}/{total} lines ({pct}%)")
            total_annotated += annotated
            total_code_lines += total
        overall_pct = int(total_annotated / total_code_lines * 100) if total_code_lines else 0
        print(f"    {'Overall:':<{max_id_len + 1}}  {total_annotated}/{total_code_lines} lines ({overall_pct}%)")
        if overall_pct < 50:
            warnings.append(f"Overall annotation coverage is {overall_pct}% (below 50%)")
            print(f"    ~ Warning: overall annotation coverage is below 50%")
        print()

    # --- Important ratio ---
    if important_data:
        print("  Important ratio:")
        total_imp = sum(ic for _, ic, _ in important_data)
        total_ann = sum(ac for _, _, ac in important_data)
        max_id_len2 = max(len(uid) for uid, _, _ in important_data)
        for uid, ic, ac in important_data:
            pct = int(ic / ac * 100) if ac else 0
            print(f"    {uid + ':':<{max_id_len2 + 1}}  {ic}/{ac} ({pct}%)")
        overall_imp_pct = int(total_imp / total_ann * 100) if total_ann else 0
        print(f"    {'Overall:':<{max_id_len2 + 1}}  {total_imp}/{total_ann} ({overall_imp_pct}%)")
        if overall_imp_pct > 20:
            warnings.append(f"Important ratio is {overall_imp_pct}% (above 20% — consider demoting some lines)")
            print(f"    ~ Warning: important ratio is above 20%")
        print()

    # --- Strict mode: promote stale hashes to errors ---
    if strict:
        stale = [w for w in warnings if "hash mismatch" in w]
        if stale:
            for w in stale:
                warnings.remove(w)
                errors.append(w.replace("(annotation may be stale)", "(stale — fails in --strict mode)"))

    status = "PASS" if not errors else "FAIL"
    print(f"  Result: {status} — {len(errors)} error(s), {len(warnings)} warning(s), "
          f"{units_validated} unit(s) validated")

    sys.exit(1 if errors else 0)
