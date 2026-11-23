# REASON

## Problem
Existing guidance is long, tool-centric, and contains a false JavaScript build command, so future agents cannot quickly operate the Python trading system.

## Constraints
Required prefix; concise; commands and architecture must be verified; preserve project-specific editing rules; avoid generic advice and exhaustive trees; do not read foreign-agent configs.

## Alternatives
1. Append commands and architecture to the 175-line Ruflo file. Lowest deletion, but keeps stale commands and always-loaded swarm boilerplate.
2. Replace it with a concise repository guide. Removes incorrect guidance, stays under the always-loaded context budget, and directly serves `/init`.
3. Keep Ruflo content plus create another guide. Rejected because Claude Code expects root `CLAUDE.md` and duplicate guidance would conflict.

## Decision record
Evidence: `CLAUDE.md:144-151` specifies npm while CI is Python at `.github/workflows/ci.yml:30-77`.
Reasoning: incorrect always-loaded instructions are higher risk than deleting generic orchestration boilerplate.
Decision: replace `CLAUDE.md` with verified commands, architecture, safety invariants, and repository conventions.
Expected: future sessions can install, run, test, and trace the system without rediscovery.
Verification: inspect diff; run single test, compile, independent review, and final judge.
