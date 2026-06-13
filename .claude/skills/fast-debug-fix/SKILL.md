# Skill: Fast Debug Fix

Use this skill when the user reports an error, failing test, or runtime bug.

## Workflow
1. Reproduce quickly with the smallest command.
2. Locate root cause with targeted search.
3. Patch minimally.
4. Re-run the failing check only.
5. Report cause, fix, and verification.

## Rules
- Do not refactor unrelated code.
- Keep edits local to the failing path.
- Prefer deterministic tests/log checks over guesswork.
