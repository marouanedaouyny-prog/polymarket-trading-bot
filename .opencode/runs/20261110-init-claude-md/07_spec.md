# SPEC

## Requirements
- Start with the exact requested `# CLAUDE.md` heading and guidance sentence.
- Include Python setup, API/paper execution, build/smoke, full test, single test, coverage, lint, type, and format commands.
- Describe only big-picture runtime layers and data flow.
- Explain configuration precedence and live-trading fail-closed gates.
- Preserve relevant local constraints: minimal scope, read before edit, no generated work at root, files under 500 lines, boundary validation.
- Note network-dependent tests and parallel/legacy implementations where this prevents mistakes.

## Acceptance criteria
- No npm build/test guidance.
- Commands match repository CI or executable entrypoints.
- Architecture claims cite actual imported modules in the research ledger.
- File remains concise and avoids generic development advice.
- No application files changed.

## Priority resolution
User requirements > correctness > security/data safety > architecture > convenience. Therefore live-safety invariants and authoritative CI commands supersede stale README/Ruflo text.
