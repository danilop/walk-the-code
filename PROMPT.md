# Walk the Code — Code Walkthrough Prompt

Create or update an interactive code walkthrough using walk-the-code (https://github.com/danilop/walk-the-code). The output is a web-based explanation of a codebase where readers click code lines to see annotations and diagrams.

The hierarchy levels (chapters/labs) can be renamed to fit your domain — for example "Modules/Lessons" or "Parts/Steps" — via the `terminology` field in config.json.

## Instructions

1. Read the walk-the-code README at https://github.com/danilop/walk-the-code/blob/main/README.md for the full config schema, comment format, and CLI commands.

2. Read the detailed skill guide at https://github.com/danilop/walk-the-code/blob/main/walk-the-code-skill/SKILL.md for the complete workflow, quality principles, and content checklist.

3. Follow the workflow in the skill guide:
   - Determine the walkthrough type (educational labs vs. repository documentation)
   - Assess the codebase (core files, entry points, data flow, dependency graph, layers)
   - Design the walkthrough structure (group by functional cohesion, filter out noise, order for learning)
   - Create or update config.json, comments/, diagrams/, and a start.sh launcher
   - Write annotations that explain WHY, not WHAT — and capture tribal knowledge for repo documentation
   - Create reusable Mermaid diagrams with per-line node highlighting (prioritize system architecture maps for repos)
   - Add learning objectives and exercises
   - Run add_hashes.py and wtc-validate
   - Preview with ./walk-the-code/start.sh

## Key quality rules

- Explain intent and design decisions, not what the code literally does
- Mark only 10-15% of annotated lines as `important` (architectural boundaries)
- Target 30-60% annotation coverage (not every line needs a comment)
- Design 2-4 diagrams that are reused across many lines with different highlights
- Do not add custom colors or styles to diagrams (no `style`, `classDef`, `:::`, or `fill:`/`color:`) — the tool applies its own theme
- Order content for learning, not for the file system

**Additionally for repository documentation:**

- Group files by functional cohesion (shared responsibility, call graph proximity), not just directory structure
- Skip generated files, boilerplate, and infrastructure noise — document files where understanding requires more than reading the code
- Capture tribal knowledge: infer trade-offs, invariants, and what would break from the code's structure and constraints
- Prioritize a system architecture diagram reused across all labs with per-file highlights
