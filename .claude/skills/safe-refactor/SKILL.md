# Skill: Safe Refactor

Use this skill for structural cleanup without behavior changes.

## Workflow
1. Identify duplication or complexity hotspot.
2. Refactor in small commits/patches.
3. Keep public interfaces stable.
4. Run impacted tests/checks.
5. Summarize risk and rollback path.

## Rules
- No feature changes during refactor.
- Preserve input/output behavior.
- Prefer incremental edits over large rewrites.
