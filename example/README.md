# Example: Monte Carlo Pi

A minimal walk-the-code example with two files (Python and Java) computing Pi via Monte Carlo simulation. Demonstrates:

- **Multi-language support** — Python (`#` comments) and Java (`//` comments) auto-detected from file extension
- **Shared diagrams** — both files reference the same `monte_carlo.mmd` diagram
- **Per-line highlighting** — different lines highlight different nodes in the diagram

## Run

```bash
# From the walk-the-code root:
uv run python server.py --config example/config.json
```

Note: the `language` field is not set in config.json — it's auto-detected from `.py` → python and `.java` → java.
