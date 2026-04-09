# Walk the Code — Code Walkthrough Prompt

Create or update an interactive code walkthrough using walk-the-code (https://github.com/danilop/walk-the-code). The output is a web-based explanation of a codebase where readers click code lines to see annotations and diagrams.

The hierarchy levels (chapters/labs) can be renamed to fit your domain — for example "Modules/Lessons" or "Parts/Steps" — via the `terminology` field in config.json.

## Instructions

1. Read the walk-the-code README at https://github.com/danilop/walk-the-code/blob/main/README.md for the full config schema, comment format, and CLI commands.

2. Read the detailed skill guide at https://github.com/danilop/walk-the-code/blob/main/walk-the-code-skill/SKILL.md for the complete workflow, quality principles, and content checklist.

3. Follow the 8-step workflow in the skill guide:
   - Assess the codebase (identify core files, entry points, data flow)
   - Design the walkthrough structure (grouping, ordering, diagrams)
   - Create or update config.json, comments/, diagrams/, and a start.sh launcher
   - Write annotations that explain WHY, not WHAT
   - Create reusable Mermaid diagrams with per-line node highlighting
   - Add learning objectives and exercises
   - Run add_hashes.py and wtc-validate
   - Preview with ./walk-the-code/start.sh

## Key quality rules

- Explain intent and design decisions, not what the code literally does
- Mark only 10-15% of annotated lines as `important` (architectural boundaries)
- Target 30-60% annotation coverage (not every line needs a comment)
- Design 2-4 diagrams that are reused across many lines with different highlights
- Order content for learning, not for the file system
