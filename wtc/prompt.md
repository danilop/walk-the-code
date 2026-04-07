# Walk the Code — Tutorial Generation Prompt

You are creating an interactive code walkthrough using walk-the-code (https://github.com/danilop/walk-the-code). The output is a web tutorial where readers click code lines to see explanations and diagrams.

## Instructions

1. Read the walk-the-code README at https://github.com/danilop/walk-the-code/blob/main/README.md for the full config schema, comment format, and CLI commands.

2. Read the detailed skill guide at https://github.com/danilop/walk-the-code/blob/main/wtc/agent-skill.md for the complete workflow, quality principles, and content checklist.

3. Follow the 8-step workflow in the skill guide:
   - Assess the codebase (identify core files, entry points, data flow)
   - Design the tutorial structure (chapters, ordering, diagrams)
   - Create config.json, comments/, and diagrams/
   - Write annotations that explain WHY, not WHAT
   - Create reusable Mermaid diagrams with per-line node highlighting
   - Add learning objectives and exercises
   - Run add_hashes.py and wtc-validate
   - Preview with wtc-serve

## Key quality rules

- Explain intent and design decisions, not what the code literally does
- Mark only 10-15% of annotated lines as `important` (architectural boundaries)
- Target 30-60% annotation coverage (not every line needs a comment)
- Design 2-4 diagrams that are reused across many lines with different highlights
- Order labs for learning, not for the file system
