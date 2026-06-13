# Skill: Pencil Interface Builder

Use this skill for UI layout/design tasks with Pencil MCP.

## Goal
Produce clean interface screens quickly with reusable structure.

## Workflow
1. Read editor state and selected node.
2. Build layout frames first (header/sidebar/content).
3. Add typography and spacing system.
4. Add cards/forms/tables.
5. Run one screenshot pass for visual QA.

## Rules
- Prefer `batch_get` + `batch_design` in grouped operations.
- Keep hierarchy shallow and names clear.
- Use placeholders and reusable frames where possible.
- Avoid random styling; define consistent spacing and type scale.

## Output
- Updated `.pen` layout
- Short summary of sections changed
