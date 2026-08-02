#!/usr/bin/env python3
"""
Release validation script for Polymarket Trading Bot.
Runs all tests and checks dependencies to ensure production readiness.
"""

import sys
import subprocess
import os

def run_command(command, description):
    print(f"\n--- Running {description} ---")
    print(f"Command: {command}")
    process = subprocess.Popen(command, shell=True)
    process.wait()
    return process.returncode

def main():
    print("="*60)
    print("POLYMARKET BOT RELEASE VALIDATION")
    print("="*60)

    # 1. Dependency Check
    ret_pip = run_command("python -m pip check", "Dependency Conflict Check")
    if ret_pip != 0:
        print("\n❌ FAILED: Dependency conflicts detected!")
        # We don't exit here yet, let's see test results too
    else:
        print("\n✅ PASSED: No dependency conflicts.")

    # 2. Run All Tests
    print("\n--- Running All Tests (this may take a minute) ---")
    # Run tests from both directories
    ret_tests = run_command("python -m pytest tests/ src/tests/ -v --tb=short", "Comprehensive Test Suite")
    
    if ret_tests == 0:
        print("\n✅ PASSED: All tests passed.")
    else:
        print("\n❌ FAILED: Some tests failed!")

    # Final Verdict
    print("\n" + "="*60)
    if ret_pip == 0 and ret_tests == 0:
        print("VERDICT: RELEASE APPROVED 🚀")
        print("="*60)
        sys.exit(0)
    else:
        print("VERDICT: RELEASE REJECTED ❌")
        print("Please fix the issues above before releasing.")
        print("="*60)
        sys.exit(1)

if __name__ == "__main__":
    main()
