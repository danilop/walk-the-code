#!/usr/bin/env python3
"""Generate line-by-line explanations using Claude API.

Reads config.json, generates explanations for each lab, writes to comments/ mirror structure.
Run: ANTHROPIC_API_KEY=... uv run --extra generate python generate_explanations.py
"""

import json
import re
import sys
from pathlib import Path

import anthropic

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / (sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else "config.json")
config = json.loads(CONFIG_PATH.read_text())
CODE_DIR = (ROOT / config.get("code_dir", ".")).resolve()
DEFAULT_LANG = config.get("language", "python")

COMMENT_NAMES = {"python": "#", "javascript": "//", "typescript": "//",
                 "c": "//", "cpp": "//", "rust": "//", "go": "//", "java": "//"}


def generate_for_lab(client, lab):
    code_path = CODE_DIR / lab["id"] / lab["file"]
    code = code_path.read_text()
    lang = lab.get("language", DEFAULT_LANG)
    comment_char = COMMENT_NAMES.get(lang, "#")

    prompt = f"""You are annotating a {lang} source file for an interactive code tutorial.

Lab: {lab['title']} — {lab.get('tagline', '')}

For each CODE line (not blank, not pure comment lines starting with {comment_char}), write a short explanation (1-2 sentences, 15-30 words).
Use <code>name</code> tags for identifiers. Be clear, precise, non-verbose.

Return a JSON object mapping line numbers (strings) to HTML explanation strings.
Only include lines with meaningful code. Return ONLY the JSON, no markdown fencing.

```{lang}
{code}
```"""

    response = client.messages.create(model="claude-sonnet-4-20250514", max_tokens=8192,
                                       messages=[{"role": "user", "content": prompt}])
    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        if text.endswith("```"): text = text[:-3]
        text = text.strip()
    return json.loads(text)


def main():
    client = anthropic.Anthropic()
    force = "--force" in sys.argv
    for lab in config.get("labs", []):
        stem = Path(lab["file"]).stem
        out = ROOT / "comments" / lab["id"] / f"{stem}.json"
        if out.exists() and not force:
            print(f"  {lab['id']}: exists, skipping (use --force)")
            continue
        print(f"  {lab['id']}: generating...")
        explanations = generate_for_lab(client, lab)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(explanations, indent=2))
        print(f"    -> {len(explanations)} explanations saved")


if __name__ == "__main__":
    print("Generating explanations...")
    main()
    print("Done!")
