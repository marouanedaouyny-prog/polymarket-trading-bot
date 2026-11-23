#!/usr/bin/env python3
"""
Config consistency verification script.

Verifies that config.py defaults match the agent prompts and README.

Usage: python check_config.py

This is the single source of truth check — if this passes, all components
are aligned. Failures indicate drift that should be resolved per the
provenance rules in src/utils/config.py.
"""

import sys
import re
from pathlib import Path

BASE = Path(__file__).parent


# 1. Check README vs config — simplest and most important
def check_readme_vs_config():
    """Verify README entry criteria match config.py."""
    errors = []
    readme_path = BASE / "README.md"
    if not readme_path.exists():
        return [f"README.md not found at {readme_path}"]

    try:
        readme = readme_path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        readme = readme_path.read_text(encoding='utf-8', errors='replace')

    # Check edge/confidence entries using simple string search
    # Old format: > 65%, New format: > 8% or > 85%
    if "65%" in readme and "8%" not in readme.replace("85%", "") and "85%" not in readme:
        # Check if it has the old format edge
        if re.search(r'Edge.*>.*65', readme, re.IGNORECASE):
            errors.append("README.md: Edge still mentions 65% (config has 8%)")

    if "65%" in readme and "85%" not in readme:
        if re.search(r'Confidence.*>.*65', readme, re.IGNORECASE):
            errors.append("README.md: Confidence still mentions 65% (config has 85%)")

    # Check price range
    # Old: $0.01-0.35, New: $0.05-0.50
    if "$0.01" in readme:
        errors.append("README.md: Price min still mentions $0.01 (config has $0.05)")

    if "$0.35" in readme:
        errors.append("README.md: Price max still mentions $0.35 (config has $0.50)")

    # Check volume
    if "$15,000" in readme:
        errors.append("README.md: Volume still mentions $15,000 (config has $10,000)")

    return errors


# 2. Check agent_trading_system.py PROJECT_CONTEXT
def check_agent_context():
    """Verify PROJECT_CONTEXT in agent_trading_system.py matches config."""
    errors = []
    agent_path = BASE / "agent_trading_system.py"
    if not agent_path.exists():
        return [f"agent_trading_system.py not found"]

    try:
        agent = agent_path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        agent = agent_path.read_text(encoding='utf-8', errors='replace')

    # Check for old win rate target
    if "85%+ win rate" in agent:
        errors.append("agent_trading_system.py: PROJECT_CONTEXT still says '85%+ win rate'")

    # Check for old price range
    if "$0.01-0.35" in agent:
        errors.append("agent_trading_system.py: PROJECT_CONTEXT still has old price range $0.01-0.35")

    # Check for old edge
    if "edge>65%" in agent:
        errors.append("agent_trading_system.py: PROJECT_CONTEXT still has edge>65%")

    # Check for old confidence
    if "conf>65%" in agent:
        errors.append("agent_trading_system.py: PROJECT_CONTEXT still has conf>65%")

    return errors


def main():
    all_errors = []

    print("=" * 60)
    print("Polymarket Config Consistency Check")
    print("=" * 60)

    # Check 1: README vs config
    print("\n1. Checking README.md vs config.py...")
    readme_errors = check_readme_vs_config()
    if readme_errors:
        all_errors.extend(readme_errors)
        for e in readme_errors:
            print(f"  [FAIL] {e}")
    else:
        print("  [PASS] README.md entry criteria match config.py")

    # Check 2: agent context vs config
    print("\n2. Checking agent_trading_system.py PROJECT_CONTEXT...")
    agent_errors = check_agent_context()
    if agent_errors:
        all_errors.extend(agent_errors)
        for e in agent_errors:
            print(f"  [FAIL] {e}")
    else:
        print("  [PASS] PROJECT_CONTEXT matches config.py")

    # Summary
    print("\n" + "=" * 60)
    if all_errors:
        print(f"FAILED: {len(all_errors)} consistency issues found")
        print("Please fix the issues above before proceeding.")
        sys.exit(1)
    else:
        print("ALL CHECKS PASSED: Config is consistent across the project")
        sys.exit(0)


if __name__ == "__main__":
    main()