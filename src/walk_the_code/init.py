"""Scaffold a new walk-the-code project."""

import json
import sys
from pathlib import Path

from .config import _line_hash

_VALID_TEMPLATES = ("basic", "multilang", "group")

# ---------------------------------------------------------------------------
# Example unit content — basic (Python hello)
# ---------------------------------------------------------------------------

_EXAMPLE_CODE = """\
# A simple greeting generator
import random

GREETINGS = ["Hello", "Hi", "Hey", "Greetings"]
TARGETS = ["World", "Developer", "Learner"]

def greet():
    greeting = random.choice(GREETINGS)
    target = random.choice(TARGETS)
    return f"{greeting}, {target}!"

if __name__ == "__main__":
    for i in range(5):
        print(greet())
"""

_EXAMPLE_COMMENTS = {
    "1": "<p>A comment line explaining the purpose of this file.</p>",
    "2": "<p>Python's <code>random</code> module provides pseudo-random number generation.</p>",
    "4": "<p>A list of greeting words to randomly choose from.</p>",
    "5": "<p>A list of targets for the greeting.</p>",
    "7": {"text": "<p>A function that combines a random greeting with a random target.</p>", "important": True},
    "8": "<p><code>random.choice()</code> picks a random element from a list.</p>",
    "10": "<p>An f-string combines the greeting and target with a comma and exclamation mark.</p>",
    "12": {"text": '<p>The <code>if __name__ == "__main__"</code> guard runs this block only when executed directly.</p>', "important": True},
    "13": "<p>Generate 5 random greetings to demonstrate the function.</p>",
}

_EXAMPLE_LAB = {
    "id": "hello",
    "file": "hello.py",
    "title": "Hello World",
    "tagline": "A simple greeting generator to get you started.",
    "description": "<p>This example unit shows how walk-the-code works. Click any line to see its explanation.</p>",
    "learning_objectives": [
        "Navigate the walk-the-code interface",
        "Understand how line-by-line annotations work",
        "Run a unit from the browser",
    ],
    "exercises": [
        {
            "prompt": "Add a new greeting word to the GREETINGS list and run the unit.",
            "hint": "Edit line 4 and add another string to the list.",
        },
        {
            "prompt": "Modify greet() to also include a random emoji.",
            "hint": "Import a list of emoji strings and use random.choice() to pick one.",
        },
    ],
    "run_command": ["python3", "hello.py"],
}

# ---------------------------------------------------------------------------
# Example unit content — Java hello (used by multilang & group templates)
# ---------------------------------------------------------------------------

_JAVA_CODE = """\
import java.util.Random;

public class Hello {
    static final String[] GREETINGS = {"Hello", "Hi", "Hey", "Greetings"};
    static final String[] TARGETS = {"World", "Developer", "Learner"};

    public static String greet() {
        Random rng = new Random();
        String greeting = GREETINGS[rng.nextInt(GREETINGS.length)];
        String target = TARGETS[rng.nextInt(TARGETS.length)];
        return greeting + ", " + target + "!";
    }

    public static void main(String[] args) {
        for (int i = 0; i < 5; i++) {
            System.out.println(greet());
        }
    }
}
"""

_JAVA_COMMENTS = {
    "1": "<p>Import Java's <code>Random</code> class for generating random numbers.</p>",
    "3": "<p>The public class name must match the file name.</p>",
    "4": "<p>An array of greeting words, similar to the Python version.</p>",
    "5": "<p>An array of targets for the greeting.</p>",
    "7": "<p>A static method that builds a random greeting string.</p>",
    "8": "<p>Create a new <code>Random</code> instance to pick random indices.</p>",
    "9": "<p><code>nextInt(n)</code> returns a random integer from 0 to n-1.</p>",
    "11": "<p>Concatenate the greeting and target with punctuation.</p>",
    "14": "<p>The <code>main</code> method is the entry point for a Java program.</p>",
    "15": "<p>Loop 5 times to demonstrate the greeting function.</p>",
}

_JAVA_LAB = {
    "id": "hello_java",
    "file": "Hello.java",
    "title": "Hello World (Java)",
    "tagline": "The same greeting generator, written in Java.",
    "description": "<p>A Java version of the hello unit, demonstrating multi-language support.</p>",
    "learning_objectives": [
        "Compare Python and Java implementations side by side",
        "See how walk-the-code handles different languages",
    ],
    "run_command": ["sh", "-c", "javac Hello.java && java Hello"],
}

_PYTHON_MULTILANG_LAB = {
    "id": "hello_python",
    "file": "hello.py",
    "title": "Hello World (Python)",
    "tagline": "A simple greeting generator in Python.",
    "description": "<p>This example unit shows how walk-the-code works. Click any line to see its explanation.</p>",
    "learning_objectives": [
        "Navigate the walk-the-code interface",
        "Understand how line-by-line annotations work",
        "Run a unit from the browser",
    ],
    "exercises": [
        {
            "prompt": "Add a new greeting word to the GREETINGS list and run the unit.",
            "hint": "Edit line 4 and add another string to the list.",
        },
    ],
    "run_command": ["python3", "hello.py"],
}


def init(template="basic"):
    """CLI entry point: wtc-init — create a minimal WTC project structure."""
    # Parse --template from sys.argv if not passed directly
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--template" and i + 1 < len(args):
            template = args[i + 1]
            i += 2
        else:
            i += 1

    if template not in _VALID_TEMPLATES:
        print(f"Error: unknown template '{template}'. Choose from: {', '.join(_VALID_TEMPLATES)}")
        sys.exit(1)

    print("walk-the-code project scaffolding\n")
    print(f"  Template: {template}\n")

    title = _prompt("Project title", "My Tutorial")
    tagline = _prompt("Tagline", "An interactive code walkthrough")
    repo_url = _prompt("Repository URL", "https://github.com/user/repo")

    cwd = Path.cwd()

    config_path = cwd / "config.json"
    if config_path.exists():
        print(f"\nError: {config_path} already exists. Aborting.")
        sys.exit(1)

    # Create directories
    dirs = ["samples", "comments", "diagrams"]
    for d in dirs:
        (cwd / d).mkdir(parents=True, exist_ok=True)

    # Dispatch to the appropriate template
    if template == "basic":
        _scaffold_basic(cwd, config_path, title, tagline, repo_url, dirs)
    elif template == "multilang":
        _scaffold_multilang(cwd, config_path, title, tagline, repo_url, dirs)
    elif template == "group":
        _scaffold_group(cwd, config_path, title, tagline, repo_url, dirs)

    print("\nRun `wtc-serve` to preview it in your browser.\n")
    print("Next steps:")
    print("  1. Explore the example unit(s) to understand the project structure")
    print("  2. Add your own source files under samples/<unit_id>/")
    print("  3. Add annotations under comments/<unit_id>/<filename>.json")
    print("  4. Add Mermaid diagrams under diagrams/<name>.mmd")
    print('  5. Register new units in config.json under "units"')
    print("  6. Run `wtc-serve` to preview or `wtc-build` to bundle")


# ---------------------------------------------------------------------------
# Template scaffolders
# ---------------------------------------------------------------------------

def _scaffold_basic(cwd, config_path, title, tagline, repo_url, dirs):
    """Create the basic (default) template — a single Python hello unit."""
    _create_unit(cwd, "hello", "hello.py", _EXAMPLE_CODE, _EXAMPLE_COMMENTS)

    config = {
        "$schema": "config.schema.json",
        "title": title,
        "tagline": tagline,
        "repo_url": repo_url,
        "code_dir": "samples",
        "terminology": {
            "group": "Group",
            "group_plural": "Groups",
            "unit": "Unit",
            "unit_plural": "Units",
        },
        "groups": [],
        "units": [_EXAMPLE_LAB],
    }
    config_path.write_text(json.dumps(config, indent=2) + "\n")

    print(f"\nCreated project in {cwd}/")
    print("  config.json")
    for d in dirs:
        print(f"  {d}/")
    print("  samples/hello/hello.py")
    print("  comments/hello/hello.json")
    print("\nAn example unit (hello) has been included to help you get started.")


def _scaffold_multilang(cwd, config_path, title, tagline, repo_url, dirs):
    """Create the multilang template — Python + Java units."""
    _create_unit(cwd, "hello_python", "hello.py", _EXAMPLE_CODE, _EXAMPLE_COMMENTS)
    _create_unit(cwd, "hello_java", "Hello.java", _JAVA_CODE, _JAVA_COMMENTS)

    config = {
        "$schema": "config.schema.json",
        "title": title,
        "tagline": tagline,
        "repo_url": repo_url,
        "code_dir": "samples",
        "terminology": {
            "group": "Group",
            "group_plural": "Groups",
            "unit": "Unit",
            "unit_plural": "Units",
        },
        "groups": [],
        "units": [_PYTHON_MULTILANG_LAB, _JAVA_LAB],
    }
    config_path.write_text(json.dumps(config, indent=2) + "\n")

    print(f"\nCreated project in {cwd}/")
    print("  config.json")
    for d in dirs:
        print(f"  {d}/")
    print("  samples/hello_python/hello.py")
    print("  comments/hello_python/hello.json")
    print("  samples/hello_java/Hello.java")
    print("  comments/hello_java/Hello.json")
    print("\nTwo example units (Python and Java) demonstrate multi-language support.")


def _scaffold_group(cwd, config_path, title, tagline, repo_url, dirs):
    """Create the group template — a single unit wrapped in a group with a Mermaid diagram."""
    _create_unit(cwd, "hello", "hello.py", _EXAMPLE_CODE, _EXAMPLE_COMMENTS)

    group_def = {
        "id": "getting-started",
        "title": "Getting Started",
        "description": "<p>Your first group, containing a single introductory unit.</p>",
        "diagram": "graph LR\n  A[Read code] --> B[Click a line]\n  B --> C[Read explanation]",
        "units": ["hello"],
    }

    config = {
        "$schema": "config.schema.json",
        "title": title,
        "tagline": tagline,
        "repo_url": repo_url,
        "code_dir": "samples",
        "terminology": {
            "group": "Group",
            "group_plural": "Groups",
            "unit": "Unit",
            "unit_plural": "Units",
        },
        "groups": [group_def],
        "units": [_EXAMPLE_LAB],
    }
    config_path.write_text(json.dumps(config, indent=2) + "\n")

    print(f"\nCreated project in {cwd}/")
    print("  config.json")
    for d in dirs:
        print(f"  {d}/")
    print("  samples/hello/hello.py")
    print("  comments/hello/hello.json")
    print("\nAn example group with an inline Mermaid diagram wraps the hello unit.")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_unit(cwd, unit_id, filename, code, comments_map):
    """Write sample code and comment annotations for a single unit."""
    # Write sample code
    sample_dir = cwd / "samples" / unit_id
    sample_dir.mkdir(parents=True, exist_ok=True)
    (sample_dir / filename).write_text(code)

    # Build comment annotations with computed hashes
    code_lines = code.splitlines()
    comments = {}
    for line_num, entry in comments_map.items():
        line_content = code_lines[int(line_num) - 1]
        if isinstance(entry, dict):
            comments[line_num] = {**entry, "hash": _line_hash(line_content)}
        else:
            comments[line_num] = {"text": entry, "hash": _line_hash(line_content)}

    # Write comment file
    comment_dir = cwd / "comments" / unit_id
    comment_dir.mkdir(parents=True, exist_ok=True)
    comment_filename = Path(filename).stem + ".json"
    (comment_dir / comment_filename).write_text(json.dumps(comments, indent=2) + "\n")


def _prompt(label, default):
    """Read a line from stdin with a default value."""
    try:
        value = input(f"  {label} [{default}]: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)
    return value if value else default
