"""Validate a walk-the-code project configuration and content."""

import json
import sys
from pathlib import Path

from .config import _line_hash, load_config


def validate():
    """CLI entry point: wtc-validate [config_path] — check project for errors."""
    args = sys.argv[1:]
    config_path = "config.json"
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
    if not config.get("labs"):
        errors.append("Missing required top-level field: labs (or labs array is empty)")

    # --- Validate each lab ---
    labs_validated = 0
    all_lab_ids = set()
    coverage_data = []  # list of (lab_id, annotated_lines, total_lines)

    for i, lab in enumerate(config.get("labs", [])):
        prefix = f"labs[{i}]"

        # Required lab fields
        for field in ("id", "file", "title"):
            if not lab.get(field):
                errors.append(f"{prefix}: missing required field '{field}'")

        lab_id = lab.get("id", f"<index {i}>")
        prefix = f"lab '{lab_id}'"
        all_lab_ids.add(lab_id)

        # Code file exists
        code_path = code_dir / lab_id / lab.get("file", "")
        if lab.get("file"):
            if not code_path.exists():
                errors.append(f"{prefix}: code file not found: {code_path}")

        # Learning objectives
        if not lab.get("learning_objectives"):
            warnings.append(f"{prefix}: no learning_objectives defined")

        # Exercises
        exercises = lab.get("exercises", [])
        if not exercises:
            warnings.append(f"{prefix}: no exercises defined")
        for j, ex in enumerate(exercises):
            if not isinstance(ex, dict):
                errors.append(f"{prefix}: exercises[{j}] is not an object")
            elif not ex.get("prompt"):
                warnings.append(f"{prefix}: exercises[{j}] has no 'prompt' field")

        # Comment file validation
        stem = Path(lab.get("file", "x")).stem
        comment_path = config_dir / "comments" / lab_id / f"{stem}.json"
        explanations = {}
        if comment_path.exists():
            try:
                explanations = json.loads(comment_path.read_text())
                if not isinstance(explanations, dict):
                    errors.append(f"{prefix}: comment file {comment_path.name} is not a JSON object")
                    explanations = {}
            except json.JSONDecodeError as exc:
                errors.append(f"{prefix}: invalid JSON in {comment_path.name}: {exc}")
        # Note: missing comment file is not an error — lab may not have annotations yet

        # Line number range and hash checks (only if code exists)
        if code_path.exists() and explanations:
            code_text = code_path.read_text()
            code_lines = code_text.split("\n")
            total_lines = len(code_lines)

            for line_str, entry in explanations.items():
                try:
                    line_num = int(line_str)
                except ValueError:
                    errors.append(f"{prefix}: non-integer key '{line_str}' in comments")
                    continue

                if line_num < 1 or line_num > total_lines:
                    errors.append(
                        f"{prefix}: annotation for line {line_num} but code has only {total_lines} lines"
                    )

                if (
                    isinstance(entry, dict)
                    and entry.get("text")
                    and 1 <= line_num <= total_lines
                    and not code_lines[line_num - 1].strip()
                ):
                    warnings.append(
                        f"{prefix}: line {line_num} annotation is attached to a blank line"
                    )

                # Diagram references
                if isinstance(entry, dict) and entry.get("diagram"):
                    diag_id = entry["diagram"]
                    diag_path = config_dir / "diagrams" / f"{diag_id}.mmd"
                    if not diag_path.exists():
                        errors.append(
                            f"{prefix}: line {line_num} references diagram '{diag_id}' "
                            f"but {diag_path.name} not found"
                        )

                # Hash freshness
                if isinstance(entry, dict) and entry.get("hash") and 1 <= line_num <= total_lines:
                    expected = _line_hash(code_lines[line_num - 1])
                    if entry["hash"] != expected:
                        warnings.append(
                            f"{prefix}: line {line_num} hash mismatch (annotation may be stale)"
                        )

        # Track coverage data
        if code_path.exists():
            cov_text = code_text if (code_path.exists() and explanations) else code_path.read_text()
            total_for_cov = len(cov_text.split("\n"))
            annotated_for_cov = sum(1 for key in explanations if str(key).isdigit())
            coverage_data.append((lab_id, annotated_for_cov, total_for_cov))

        labs_validated += 1

    # --- Chapter references ---
    for ch in config.get("chapters", []):
        ch_id = ch.get("id", "?")
        for lab_id in ch.get("labs", []):
            if lab_id not in all_lab_ids:
                errors.append(
                    f"chapter '{ch_id}': references lab '{lab_id}' which is not defined"
                )
        comp_diag = ch.get("comparison_diagram")
        if comp_diag:
            diag_path = config_dir / "diagrams" / f"{comp_diag}.mmd"
            if not diag_path.exists():
                errors.append(
                    f"chapter '{ch_id}': comparison_diagram '{comp_diag}' not found in diagrams/"
                )

    # --- Knowledge checks ---
    for ch in config.get("chapters", []):
        ch_id = ch.get("id", "?")
        for qi, check in enumerate(ch.get("knowledge_checks", [])):
            prefix = f"chapter '{ch_id}' knowledge_checks[{qi}]"
            if not isinstance(check, dict):
                errors.append(f"{prefix}: must be an object")
                continue
            if not check.get("question"):
                errors.append(f"{prefix}: missing 'question'")
            opts = check.get("options", [])
            if not isinstance(opts, list) or len(opts) < 2:
                errors.append(f"{prefix}: 'options' must be an array with at least 2 items")
            correct = check.get("correct")
            if not isinstance(correct, int) or correct < 0 or correct >= len(opts):
                errors.append(f"{prefix}: 'correct' must be an integer index into options")
            if not check.get("explanation"):
                errors.append(f"{prefix}: missing 'explanation'")

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
        max_id_len = max(len(lab_id) for lab_id, _, _ in coverage_data)
        for lab_id, annotated, total in coverage_data:
            pct = int(annotated / total * 100) if total else 0
            print(f"    {lab_id + ':':<{max_id_len + 1}}  {annotated}/{total} lines ({pct}%)")
            total_annotated += annotated
            total_code_lines += total
        overall_pct = int(total_annotated / total_code_lines * 100) if total_code_lines else 0
        print(f"    {'Overall:':<{max_id_len + 1}}  {total_annotated}/{total_code_lines} lines ({overall_pct}%)")
        if overall_pct < 50:
            warnings.append(f"Overall annotation coverage is {overall_pct}% (below 50%)")
            print(f"    ~ Warning: overall annotation coverage is below 50%")
        print()

    status = "PASS" if not errors else "FAIL"
    print(f"  Result: {status} — {len(errors)} error(s), {len(warnings)} warning(s), "
          f"{labs_validated} lab(s) validated")

    sys.exit(1 if errors else 0)
