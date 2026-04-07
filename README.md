# walk-the-code

Interactive line-by-line code tutorial viewer. Click a line, read what it does. Supports multiple programming languages, Mermaid diagrams with per-line node and flow highlighting, chapters for grouping labs, and rich descriptions at every level. The hierarchy labels (chapters/labs) are [configurable](#terminology) — use your own terms like modules/lessons or parts/components.

## Quick start

Try the included example (Monte Carlo Pi in Python and Java):

```bash
git clone https://github.com/danilop/walk-the-code.git
cd walk-the-code
python3 server.py --config example/config.json
# Open http://localhost:8000
```

Requires [uv](https://docs.astral.sh/uv/) (Python package manager). Install with `curl -LsSf https://astral.sh/uv/install.sh | sh`.

## Install as a CLI tool

```bash
uv tool install "walk-the-code @ git+https://github.com/danilop/walk-the-code"
```

This gives you five commands you can run from anywhere:

```bash
wtc-serve --config path/to/config.json        # start the tutorial server
wtc-build path/to/config.json                  # build static site for GitHub Pages
wtc-init                                       # scaffold a new tutorial project
wtc-validate path/to/config.json               # validate config and content
walk-the-code --config path/to/config.json     # alias for wtc-serve
```

## Tests

Run the core test subset without binding sockets:

```bash
python3 -m unittest tests.test_wtc.TestValidator tests.test_wtc.TestBuilder tests.test_wtc.TestInit
```

Run the full suite, including local HTTP server tests, only in environments where localhost port binding is allowed:

```bash
WTC_RUN_SERVER_TESTS=1 python3 -m unittest tests.test_wtc
```

## Use in your own project

1. Clone `walk-the-code/` into your project
2. Create a `config.json` pointing at your code:
   ```json
   {
     "title": "My Tutorial",
     "tagline": "Learn something cool.",
     "repo_url": "https://github.com/your-org/your-project",
     "language": "python",
     "code_dir": "../src",
     "terminology": {
       "group": "Module",
       "group_plural": "Modules",
       "unit": "Lesson",
       "unit_plural": "Lessons"
     },
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
4. Run `wtc-serve --config config.json` (or `python3 server.py --config config.json`)

The `config.json`, `comments/`, and `diagrams/` directories are gitignored in this repo — they're project-specific content tracked by your parent repo.

## How it works

- **config.json** — project metadata, chapter structure, lab definitions, optional run commands, and [custom terminology](#terminology)
- **comments/** — line-by-line explanations in a mirror structure, matched to code via content hashes
- **diagrams/** — shared Mermaid diagrams referenced from comments, with per-line node and flow highlighting
- **wtc-serve / server.py** — local server with code browsing, chapter navigation, and optional code execution via SSE
- **wtc-build** — bundles everything into `data/labs.json` for static deployment (GitHub Pages)

## Config reference

### Top-level fields

| Field | Required | Description |
|---|---|---|
| `title` | no | Project title shown on the index page |
| `tagline` | no | Subtitle shown below the title |
| `repo_url` | no | Repository URL used for the GitHub corner link on tutorial pages |
| `language` | no | Default language for all labs (auto-detected from file extension if omitted) |
| `code_dir` | no | Path to the code directory, relative to config.json (defaults to `.`) |
| `terminology` | no | Custom display names for hierarchy levels (see [Terminology](#terminology)) |
| `chapters` | no | Array of chapter objects that group labs into themed sections |
| `labs` | yes | Array of lab objects |

### Chapter fields

Chapters group labs into themed sections, each with its own page, description, and optional diagram. The JSON key is always `chapters` regardless of [terminology](#terminology) settings.

| Field | Required | Description |
|---|---|---|
| `id` | yes | Unique chapter identifier |
| `title` | yes | Chapter title |
| `description` | no | HTML description shown on the chapter page |
| `diagram` | no | Inline Mermaid source rendered on the chapter page |
| `labs` | yes | Ordered list of lab IDs belonging to this chapter |
| `chapters` | no | Array of sub-chapter objects for hierarchical grouping. |
| `knowledge_checks` | no | Array of multiple-choice quiz objects (see [Knowledge checks](#chapter-fields-additional)) |

### Lab fields

| Field | Required | Description |
|---|---|---|
| `id` | yes | Unique lab identifier (matches a subdirectory in `code_dir`) |
| `file` | yes | Source file to display |
| `files` | no | Array of file objects (`{path, role}`) for multi-file labs. Overrides `file` when present. |
| `title` | yes | Lab title |
| `tagline` | no | One-line summary shown on index and chapter pages |
| `description` | no | HTML overview shown in the explanation panel before any line is selected |
| `language` | no | Override the default language for this lab |
| `run_command` | no | Command to execute the lab (enables the Run button in local server mode) |
| `learning_objectives` | no | Array of strings describing what the learner will be able to do after completing this lab |
| `exercises` | no | Array of exercise objects with `prompt` (required) and `hint` (optional) fields |

### Chapter fields (additional)

| Field | Required | Description |
|---|---|---|
| `comparison_diagram` | no | References a `.mmd` file in `diagrams/` shown as a comparison diagram on the chapter page |

### Exercise format

```json
{
  "exercises": [
    {
      "prompt": "Change the learning rate from 0.01 to 0.1 and observe how training loss changes.",
      "hint": "Look at the optimizer initialization around line 45. Higher learning rates may cause instability."
    }
  ]
}
```

Exercises are displayed in the lab overview panel with completion checkboxes (persisted per-browser in localStorage).

### Terminology

Customize the display names for the two hierarchy levels. The JSON keys (`chapters`, `labs`) never change — only the UI labels do.

```json
{
  "terminology": {
    "group": "Chapter",
    "group_plural": "Chapters",
    "unit": "Lab",
    "unit_plural": "Labs"
  }
}
```

| Field | Default | Description |
|---|---|---|
| `group` | `Group` | Singular name for a chapter-level grouping |
| `group_plural` | `Group` + `s` | Plural form (auto-derived from `group` if omitted) |
| `unit` | `Unit` | Singular name for a lab-level item |
| `unit_plural` | `Unit` + `s` | Plural form (auto-derived from `unit` if omitted) |

Examples: `Module/Modules + Lesson/Lessons`, `Part/Parts + Component/Components`. You only need to set the plural explicitly for irregular forms (e.g. `"unit": "Index", "unit_plural": "Indices"`).

## Validation

Run `wtc-validate` to check your project for errors before serving:

```bash
wtc-validate path/to/config.json
```

Checks: required fields, code file existence, comment JSON validity, diagram references, line number ranges, hash freshness, chapter references, learning objectives and exercises presence.

## How-to guides

### How to create your first lab

**Goal:** Create a working lab with annotated code lines and view it in the browser.

1. Write your code file (e.g. `samples/hello.py`) with the code you want to explain.
2. Create the comment JSON at `comments/hello/hello.json`:
   ```json
   {
     "1": { "text": "Import the math module for arithmetic helpers." },
     "5": { "text": "This is where the main logic starts.", "important": true }
   }
   ```
3. Add the lab to your `config.json`:
   ```json
   { "id": "hello", "file": "hello.py", "title": "Hello World", "tagline": "A first example." }
   ```
4. Generate content hashes: `uv run python add_hashes.py`
5. Start the server: `wtc-serve --config config.json`
6. Open `http://localhost:8000`, select your lab, and click annotated lines to see explanations.

### How to add diagrams to a lab

**Goal:** Display a Mermaid diagram that highlights different nodes or flow links as the reader clicks through code lines.

1. Create a `.mmd` file in `diagrams/` (e.g. `diagrams/data_flow.mmd`):
   ```
   graph LR
     A[Read input] --> B[Process]
     B --> C[Write output]
   ```
2. Reference the diagram from a comment entry by adding `diagram` and `highlight` fields:
   ```json
   {
     "3": { "text": "Read data from stdin.", "diagram": "data_flow", "highlight": ["A"] },
     "7": { "text": "Transform the data.",  "diagram": "data_flow", "highlight": { "nodes": ["B"], "links": [1] } }
   }
   ```
   The array form is shorthand for node highlighting only. Use the object form when you also want to highlight zero-based Mermaid `linkStyle` indices.
3. Run `uv run python add_hashes.py` to update hashes.
4. Start the server and select a line -- the diagram appears in the explanation panel with the specified nodes or links highlighted.

**Tip:** For lines that introduce a key concept but don't have a diagram, add `"important": true` to make them stand out with an orange gutter dot:
```json
{ "5": { "text": "The core algorithm starts here.", "important": true } }
```

### How to deploy to GitHub Pages

**Goal:** Build a static bundle and deploy it via GitHub Actions so readers need no local server.

1. Build the static data bundle:
   ```bash
   wtc-build path/to/config.json    # produces data/labs.json
   ```
2. Add a GitHub Actions workflow (`.github/workflows/deploy.yml`):
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
       cp "$WTC_ASSETS"/style.css "$WTC_ASSETS"/site.js "$WTC_ASSETS"/lab.js "$WTC_ASSETS"/terminal.js "$WTC_ASSETS"/chapter.js _site/
       cp walk-the-code/data/labs.json _site/data/
   ```
3. Push to your repository and verify the Pages deployment. Note: the Run button is hidden in static mode since there is no server to execute code.

### How to create a new content repository

**Goal:** Scaffold a standalone tutorial project that uses walk-the-code as its viewer.

1. Run the interactive scaffolding tool:
   ```bash
   wtc-init
   ```
   This creates `config.json`, `samples/`, `comments/`, and `diagrams/` directories with a minimal starting config.
2. Place your source files in `samples/` and add matching lab entries to `config.json`.
3. Create comment JSON files in `comments/<lab_id>/` for each lab (see [Comment format](#comment-format) for the schema).
4. Generate hashes and validate:
   ```bash
   uv run python add_hashes.py
   wtc-validate config.json
   ```
5. Test locally: `wtc-serve --config config.json` and open `http://localhost:8000`.

### How to create a multi-file lab

**Goal:** Create a lab that displays multiple source files with a tab bar.

1. Use `files` instead of `file` in your lab config:
   ```json
   {
     "id": "my_app",
     "files": [
       {"path": "main.py", "role": "primary"},
       {"path": "utils.py"}
     ],
     "title": "My App"
   }
   ```
2. Create comment files for each source file: `comments/my_app/main.json` and `comments/my_app/utils.json`.
3. The viewer shows a file tab bar. The file with `"role": "primary"` is selected by default.

### Nested chapters example

Chapters can contain sub-chapters for hierarchical grouping:

```json
{
  "chapters": [{
    "id": "part1", "title": "Part 1",
    "chapters": [
      {"id": "ch1", "title": "Chapter 1", "labs": ["lab1", "lab2"]},
      {"id": "ch2", "title": "Chapter 2", "labs": ["lab3"]}
    ]
  }]
}
```

## Guided tour mode

Click "Start Guided Tour" in the lab overview, or add `?tour=true` to the URL. The tour steps through all annotated lines with a persistent control bar. Use `→`/`j` and `←`/`k` to navigate between tour steps.

## Embedding

Embed a lab in any page using an iframe:

```html
<iframe src="https://your-site.github.io/embed.html?lab=my_lab"
  width="100%" height="500"
  sandbox="allow-scripts allow-same-origin"
  loading="lazy"></iframe>
```

URL params: `lab` (required), `file`, `line`, `tour=true`. Supports postMessage API: send `{type:'wtc:selectLine', line:N}`, receive `{type:'wtc:lineSelected', line:N, lab:'id'}`.

## Custom analytics

Set `analytics_file` in config.json to inject a custom HTML snippet into all pages:

```json
{"analytics_file": "analytics.html"}
```

Example `analytics.html` for Umami:

```html
<script defer src="https://cloud.umami.is/script.js" data-website-id="YOUR-ID"></script>
```

Example for GoatCounter:

```html
<script data-goatcounter="https://YOURSITE.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script>
```

## Keyboard shortcuts

| Key | Action |
|---|---|
| `↓` or `j` | Next annotated line |
| `↑` or `k` | Previous annotated line |
| `Escape` | Return to lab overview/description |
| `→` or `j` (in tour) | Next tour step |
| `←` or `k` (in tour) | Previous tour step |
| Click any line | Jump to that line's explanation |

## Supported languages

Python, JavaScript, TypeScript, C, C++, Rust, Go, Java, Ruby, PHP, Swift, Kotlin, Scala, C#, Lua, R, Bash, YAML, JSON, XML, HTML, CSS, SCSS, SQL, Markdown, Dockerfile, HCL/Terraform, Protocol Buffers, Zig, Dart, Elixir, Haskell, OCaml, Clojure.

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
    "important": true,
    "diagram": "attention_flow",
    "highlight": {
      "nodes": ["Q_node", "K_node"],
      "links": [0, 1]
    }
  }
}
```

| Field | Required | Description |
|---|---|---|
| `text` | yes | HTML explanation shown in the side panel |
| `hash` | yes | SHA-256 prefix of the code line (auto-generated by `add_hashes.py`) |
| `important` | no | When `true`, marks this line as a key concept (shown as an orange dot in the gutter) |
| `diagram` | no | References a `.mmd` file in `diagrams/` by name (without extension) |
| `highlight` | no | Mermaid node IDs to highlight, or an object with `nodes` and zero-based `links` to highlight a flow path |

A single file can reference multiple diagrams. A single diagram can be shared across multiple files.

### Gutter indicators

The code gutter shows small dots to help readers orient when first opening a lab:

- **Hollow dot** — line has an explanation
- **Orange dot** — line is marked `"important": true` (key concept)
- **Blue dot** — line has a diagram reference (highest priority)

The legend is shown in the code-coach tooltip. Dots are subtle at rest and brighten on hover.

### Stale annotation detection

Each comment stores a SHA-256 hash of the code line it annotates. When the code changes but the comment isn't updated, the viewer shows a visual warning on affected lines. Run `add_hashes.py` after editing comments to update hashes:

```bash
uv run python add_hashes.py
```

## Diagrams

Place `.mmd` files in `diagrams/`. Reference them from comments by filename (without `.mmd`).

When a line with a `diagram` field is selected, the diagram renders in the explanation panel. If `highlight` is specified, the viewer can emphasize nodes and zero-based Mermaid link indices. Arrow-keying between lines re-renders the diagram with different highlights.

Chapters can also have inline Mermaid diagrams via the `diagram` field (raw Mermaid source, not a file reference).

## Generate a code walkthrough with an AI coding agent

Walk-the-code turns any codebase into an interactive web tutorial — a **code walkthrough** — where readers click lines to see explanations and diagrams. There are two ways to create one:

| Approach | How | Best for |
|---|---|---|
| **AI-assisted** | Ask an AI coding agent to generate everything | Most users — fast, high-quality, handles any repo |
| **Manual** | Run `wtc-init`, then write config and comments by hand | Full control, no AI needed |

The manual path is documented in [How to create a new content repository](#how-to-create-a-new-content-repository). The rest of this section covers the AI-assisted path.

### Skill and prompt files

Two files in the walk-the-code repo (`wtc/`) help AI coding agents generate walkthroughs:

| File | What it is | When to use |
|---|---|---|
| `wtc/agent-skill.md` | Full skill definition with workflow, quality rules, and checklist | Install as a persistent skill/tool in your agent |
| `wtc/prompt.md` | Short prompt that links to the skill and README | Paste into a one-off chat session |

Both reference this README for exact syntax, so they stay in sync as the tool evolves.

### Step-by-step: from repo to deployed walkthrough

**1. Create the walkthrough.** Ask your AI coding agent:

> Read the walk-the-code skill at https://github.com/danilop/walk-the-code/blob/main/wtc/agent-skill.md and create a code walkthrough for this repository. Focus on the core source files, not tests or build configs.

The agent will analyze your codebase and create a `walk-the-code/` directory with everything needed: `config.json`, `comments/`, `diagrams/`, learning objectives, exercises, and content hashes. No scaffolding step required — the agent generates a real config tailored to your code, not a hello-world template.

**2. Preview locally:**

```bash
uv tool install "walk-the-code @ git+https://github.com/danilop/walk-the-code"
wtc-serve --config walk-the-code/config.json
# Open http://localhost:8000
```

**3. Keep it updated after code changes.** Ask your agent:

> Run `wtc-validate --strict walk-the-code/config.json` and fix all stale annotations. Update the explanations to match the current code.

The validator reports which annotations are out of sync. The agent updates only the affected comment files and re-runs `add_hashes.py`.

**4. (Optional) Add CI/CD validation.** Ask your agent:

> Add a GitHub Actions workflow that validates the walk-the-code annotations on every push. Use --strict mode so stale annotations block the build.

The agent creates `.github/workflows/wtc-validate.yml`:

```yaml
name: Walkthrough validation
on: [push, pull_request]
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install "walk-the-code @ git+https://github.com/danilop/walk-the-code"
      - run: wtc-validate --strict walk-the-code/config.json
```

Without `--strict`, stale hashes are warnings (exit code 0). With `--strict`, they become errors (exit code 1), blocking the build until annotations are updated.

**5. (Optional) Deploy to GitHub Pages.** Ask your agent:

> Add a GitHub Actions workflow that builds and deploys the walk-the-code walkthrough to GitHub Pages on every push to main.

The agent creates `.github/workflows/wtc-deploy.yml`:

```yaml
name: Deploy walkthrough
on:
  push:
    branches: [main]
permissions:
  contents: read
  pages: write
  id-token: write
jobs:
  deploy:
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
      - name: Build walkthrough
        run: |
          uv tool install "walk-the-code @ git+https://github.com/danilop/walk-the-code"
          wtc-build walk-the-code/config.json
          WTC_PYTHON="$(uv tool dir)/walk-the-code/bin/python"
          WTC_ASSETS=$("$WTC_PYTHON" -c "from walk_the_code import ASSETS_DIR; print(ASSETS_DIR)")
          mkdir -p _site/data
          for f in index.html lab.html chapter.html embed.html favicon.svg style.css site.js \
                   lab.js lab-state.js lab-data.js lab-render.js lab-edit.js lab-search.js \
                   lab-tour.js terminal.js chapter.js embed.js; do
            [ -f "$WTC_ASSETS/$f" ] && cp "$WTC_ASSETS/$f" _site/
          done
          cp walk-the-code/data/labs.json _site/data/
      - uses: actions/upload-pages-artifact@v3
        with:
          path: _site
      - uses: actions/deploy-pages@v4
        id: deployment
```

Enable GitHub Pages (Settings → Pages → Source: GitHub Actions) and the walkthrough is live at `https://<user>.github.io/<repo>/`.

## Troubleshooting

- **"Port already in use"** — Try a different port: `wtc-serve 8001 --config config.json`.
- **"Lab not found" in the browser** — Check that the lab `id` in config.json matches a subdirectory in `code_dir`.
- **Stale annotation warnings** — Run `uv run python add_hashes.py` to update hashes after editing code.
- **Diagrams not rendering** — Verify the `.mmd` file exists in `diagrams/` and the `diagram` field in comments matches the filename (without `.mmd`).
- **Run button not showing** — The Run button only appears in server mode. Add `run_command` to the lab's config entry.
- **"Clone repo to run" hint** — Install walk-the-code as a CLI tool (`uv tool install ...`) or run directly with `python3 server.py`.

## Example

The `example/` folder contains a complete working tutorial with two files computing Pi via Monte Carlo simulation — one in Python, one in Java — sharing a single Mermaid diagram with per-line highlighting.

```bash
python3 server.py --config example/config.json
```
