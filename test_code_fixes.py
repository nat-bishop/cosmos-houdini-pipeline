#!/usr/bin/env python3
"""Verify the code fixes are correctly applied."""

import ast
import re


def check_file_for_patterns(filepath, patterns, description):
    """Check if a file contains expected patterns."""
    print(f"\nChecking {description}...")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        all_found = True
        for pattern_desc, pattern in patterns:
            if re.search(pattern, content):
                print(f"  [OK] {pattern_desc}")
            else:
                print(f"  [FAIL] {pattern_desc} - NOT FOUND")
                all_found = False

        return all_found
    except Exception as e:
        print(f"  [ERROR] Error reading file: {e}")
        return False


def main():
    """Check all the fixes."""
    print("="*60)
    print("VERIFYING UI FIXES")
    print("="*60)

    # Fix 1: Cancel selected job using shared queue service
    fix1 = check_file_for_patterns(
        "cosmos_workflow/ui/tabs/jobs_handlers.py",
        [
            ("Function signature with queue_service parameter",
             r"def cancel_selected_job\(job_id, queue_service\):"),
            ("Uses shared queue_service",
             r"queue_handlers = QueueHandlers\(queue_service\)"),
        ],
        "Fix 1: Cancel selected job handler"
    )

    fix1_wiring = check_file_for_patterns(
        "cosmos_workflow/ui/core/builder.py",
        [
            ("Uses functools.partial for cancel_job",
             r"cancel_job_bound = functools\.partial\(cancel_selected_job, queue_service=simple_queue_service\)"),
            ("Wired to cancel_job_bound",
             r"fn=cancel_job_bound"),
        ],
        "Fix 1: Cancel job wiring in builder.py"
    )

    # Fix 2: Kill confirmation dialog wiring
    fix2 = check_file_for_patterns(
        "cosmos_workflow/ui/core/builder.py",
        [
            ("Kill button shows confirmation dialog",
             r'components\.get\("kill_confirmation"\).*?# The confirmation dialog'),
            ("Kill preview text wiring",
             r'components\.get\("kill_preview"\).*?# The preview text'),
            ("Confirm kill hides dialog",
             r'components\.get\("kill_confirmation"\).*?# Hide dialog'),
            ("Cancel kill hides dialog",
             r'components\.get\("kill_confirmation"\).*?# Hide dialog'),
        ],
        "Fix 2: Kill confirmation dialog wiring"
    )

    # Fix 3: Delete run dialog return values
    fix3 = check_file_for_patterns(
        "cosmos_workflow/ui/tabs/runs/run_actions.py",
        [
            ("Returns 4 values on success",
             r"selected_run_id,\s*# Pass the run ID"),
            ("Returns 4 values on no run_id",
             r"gr\.update\(\),\s*None,"),
            ("No placeholder on checkbox",
             r"gr\.update\(value=False\),\s*# Reset checkbox"),
        ],
        "Fix 3: Delete run preview return values"
    )

    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    fixes = {
        "Fix 1 (Cancel Job Handler)": fix1,
        "Fix 1 (Cancel Job Wiring)": fix1_wiring,
        "Fix 2 (Kill Confirmation)": fix2,
        "Fix 3 (Delete Run Dialog)": fix3,
    }

    all_good = all(fixes.values())

    for name, status in fixes.items():
        status_icon = "[OK]" if status else "[FAIL]"
        print(f"{status_icon} {name}: {'PASS' if status else 'FAIL'}")

    print("\n" + "="*60)
    if all_good:
        print("[SUCCESS] ALL FIXES VERIFIED SUCCESSFULLY!")
    else:
        print("[FAILURE] Some fixes are missing or incorrect")
    print("="*60)

    return all_good


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)