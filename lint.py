#!/usr/bin/env python3
"""Quick linting check script for the project."""

import subprocess
import sys


def run_command(cmd: str, description: str) -> bool:
    """Run a command and report results."""
    print(f"\n{'=' * 60}")
    print(f"Running: {description}")
    print(f"Command: {cmd}")
    print("=" * 60)
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print("[PASSED]")
            if result.stdout:
                print(result.stdout[:500])  # First 500 chars
            return True
        else:
            print("[FAILED]")
            if result.stderr:
                print("Errors:", result.stderr[:500])
            if result.stdout:
                print("Output:", result.stdout[:500])
            return False
    except Exception as e:
        print(f"[ERROR]: {e}")
        return False


def main():
    """Run all linting checks."""
    print("Starting code quality checks...")
    
    checks = [
        ("ruff check cosmos_workflow/ --statistics", "Ruff Linting"),
        ("ruff format --check cosmos_workflow/", "Ruff Formatting Check"),
        ("mypy cosmos_workflow/ --ignore-missing-imports", "MyPy Type Checking"),
        ("bandit -r cosmos_workflow/ -f json -q 2>/dev/null | python -m json.tool | head -20", "Bandit Security Check"),
    ]
    
    results = []
    for cmd, desc in checks:
        results.append(run_command(cmd, desc))
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    for (_, desc), passed in zip(checks, results):
        status = "[PASSED]" if passed else "[FAILED]"
        print(f"{desc}: {status}")
    
    if all(results):
        print("\n[SUCCESS] All checks passed!")
        return 0
    else:
        print("\n[WARNING] Some checks failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())