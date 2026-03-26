# walk-the-code

Interactive line-by-line code tutorial viewer. Click a line, read what it does. Supports multiple programming languages, Mermaid diagrams with per-line node highlighting, chapters for grouping labs, and rich descriptions at every level.

## Quick start

Try the included example (Monte Carlo Pi in Python and Java):

```bash
git clone https://github.com/danilop/walk-the-code.git
cd walk-the-code
uv run python server.py --config example/config.json
# Open http://localhost:8000
```

Requires [uv](https://docs.astral.sh/uv/) (Python package manager). Install with `curl -LsSf https://astral.sh/uv/install.sh | sh`.

## Install as a CLI tool

```bash
uv tool install "walk-the-code @ git+https://github.com/danilop/walk-the-code"
```

This gives you three commands you can run from anywhere:

```bash
wtc-serve --config path/to/config.json        # start the tutorial server
wtc-build path/to/config.json                  # build static site for GitHub Pages
walk-the-code --config path/to/config.json     # alias for wtc-serve
```

## Use in your own project

1. Clone `walk-the-code/` into your project
2. Create a `config.json` pointing at your code:
   ```json
   {
     "title": "My Tutorial",
     "tagline": "Learn something cool.",
     "language": "python",
     "code_dir": "../src",
     "chapters": [
       {
         "id": "basics",
         "title": "The Basics",
         "description": "<p>Start here.</p>",
         "diagram": "graph LR\n  A[Input] --> B[Output]",
         "labs": ["step1", "step2"]
       }
     ],
     "labs": [
       {
         "id": "step1",
         "file": "main.py",
         "title": "Step 1",
         "tagline": "The basics.",
         "description": "<p>This lab introduces the core concepts.</p>"
       },
       {
         "id": "step2",
         "file": "utils.py",
         "title": "Step 2",
         "tagline": "Helper functions.",
         "description": "<p>Utility code used by the main module.</p>",
         "run_command": ["python3", "utils.py"]
       }
     ]
   }
   ```
3. Add explanations in `comments/step1/main.json` (see [Comment format](#comment-format))
4. Run `wtc-serve --config config.json` (or `uv run python server.py --config config.json`)

The `config.json`, `comments/`, and `diagrams/` directories are gitignored in this repo — they're project-specific content tracked by your parent repo.

## How it works

- **config.json** — project metadata, chapter structure, lab definitions, and optional run commands
- **comments/** — line-by-line explanations in a mirror structure, matched to code via content hashes
- **diagrams/** — shared Mermaid diagrams referenced from comments, with per-line node highlighting
- **wtc-serve / server.py** — local server with code browsing, chapter navigation, and optional code execution via SSE
- **wtc-build / build_static.py** — bundles everything into `data/labs.json` for static deployment (GitHub Pages)

## Config reference

### Top-level fields

| Field | Required | Description |
|---|---|---|
| `title` | no | Project title shown on the index page |
| `tagline` | no | Subtitle shown below the title |
| `language` | no | Default language for all labs (auto-detected from file extension if omitted) |
| `code_dir` | no | Path to the code directory, relative to config.json (defaults to `.`) |
| `chapters` | no | Array of chapter objects that group labs into themed sections |
| `labs` | yes | Array of lab objects |

### Chapter fields

Chapters group labs into themed sections, each with its own page, description, and optional diagram.

| Field | Required | Description |
|---|---|---|
| `id` | yes | Unique chapter identifier |
| `title` | yes | Chapter title |
| `description` | no | HTML description shown on the chapter page |
| `diagram` | no | Inline Mermaid source rendered on the chapter page |
| `labs` | yes | Ordered list of lab IDs belonging to this chapter |

### Lab fields

| Field | Required | Description |
|---|---|---|
| `id` | yes | Unique lab identifier (matches a subdirectory in `code_dir`) |
| `file` | yes | Source file to display |
| `title` | yes | Lab title |
| `tagline` | no | One-line summary shown on index and chapter pages |
| `description` | no | HTML overview shown in the explanation panel before any line is selected |
| `language` | no | Override the default language for this lab |
| `run_command` | no | Command to execute the lab (enables the Run button in local server mode) |

## Keyboard shortcuts

| Key | Action |
|---|---|
| `↓` or `j` | Next annotated line |
| `↑` or `k` | Previous annotated line |
| `Escape` | Return to lab overview/description |
| Click any line | Jump to that line's explanation |

## Supported languages

Python, JavaScript, TypeScript, C, C++, Rust, Go, Java.

Language is **auto-detected from the file extension** (`.py` → Python, `.java` → Java, `.rs` → Rust, etc.). You can set a default for all labs with the top-level `language` field, or override per-lab in config:

```json
{"id": "my_lab", "file": "main.rs", "title": "Rust Example", "language": "rust"}
```

## Running code

Add a `run_command` to any lab in config.json. The Run button appears in the browser when using the local server.

```json
{"id": "my_lab", "file": "pi.py", "run_command": ["python3", "pi.py"]}
{"id": "my_lab", "file": "Pi.java", "run_command": ["sh", "-c", "javac Pi.java && java Pi"]}
{"id": "my_lab", "file": "main.go", "run_command": ["go", "run", "main.go"]}
```

Use `sh -c "..."` for compile-then-run languages. If `run_command` is omitted, the Run button is hidden for that lab. Code execution only works with the local server — static deployments are read-only.

## Comment format

Comments live in `comments/<lab_id>/<filename_without_ext>.json`:

```json
{
  "42": {
    "text": "Scaled dot-product attention: Q·K^T / sqrt(d)",
    "hash": "a1b2c3d4",
    "diagram": "attention_flow",
    "highlight": ["Q_node", "K_node"]
  }
}
```

| Field | Required | Description |
|---|---|---|
| `text` | yes | HTML explanation shown in the side panel |
| `hash` | yes | SHA-256 prefix of the code line (auto-generated by `add_hashes.py`) |
| `diagram` | no | References a `.mmd` file in `diagrams/` by name (without extension) |
| `highlight` | no | Mermaid node IDs to highlight when this line is selected |

A single file can reference multiple diagrams. A single diagram can be shared across multiple files.

### Stale annotation detection

Each comment stores a SHA-256 hash of the code line it annotates. When the code changes but the comment isn't updated, the viewer shows a visual warning on affected lines. Run `add_hashes.py` after editing comments to update hashes:

```bash
uv run python add_hashes.py
```

## Diagrams

Place `.mmd` files in `diagrams/`. Reference them from comments by filename (without `.mmd`).

When a line with a `diagram` field is selected, the diagram renders in the explanation panel. If `highlight` nodes are specified, those nodes get a colored highlight. Arrow-keying between lines re-renders the diagram with different highlights.

Chapters can also have inline Mermaid diagrams via the `diagram` field (raw Mermaid source, not a file reference).

## Static deployment (GitHub Pages)

```bash
wtc-build path/to/config.json
# Produces data/labs.json — serve the asset files + data/ as a static site
```

In static mode, the Run button is hidden (no server to execute code). A sample GitHub Actions workflow:

```yaml
- name: Install walk-the-code
  run: uv tool install "walk-the-code @ git+https://github.com/danilop/walk-the-code"

- name: Build static bundle
  run: wtc-build walk-the-code/config.json

- name: Prepare site
  run: |
    WTC_PYTHON="$(uv tool dir)/walk-the-code/bin/python"
    WTC_ASSETS=$("$WTC_PYTHON" -c "from walk_the_code import ASSETS_DIR; print(ASSETS_DIR)")
    mkdir -p _site/data
    cp "$WTC_ASSETS"/index.html "$WTC_ASSETS"/lab.html "$WTC_ASSETS"/chapter.html _site/
    cp "$WTC_ASSETS"/style.css "$WTC_ASSETS"/lab.js "$WTC_ASSETS"/terminal.js "$WTC_ASSETS"/chapter.js _site/
    cp walk-the-code/data/labs.json _site/data/
```

## Generate explanations with AI

You can use any AI coding agent (such as [Kiro CLI](https://kiro.dev/docs/kiro-cli/)) to generate line-by-line explanations for your code. The agent can read your source files and produce the comment JSON files in the expected format (see [Comment format](#comment-format)). After generating or editing comments, update content hashes:

```bash
uv run python add_hashes.py
```

## Example

The `example/` folder contains a complete working tutorial with two files computing Pi via Monte Carlo simulation — one in Python, one in Java — sharing a single Mermaid diagram with per-line highlighting.

```bash
uv run python server.py --config example/config.json
```
