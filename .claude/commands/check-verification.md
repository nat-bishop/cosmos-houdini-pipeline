---
name: check-verification
description: Check for external verification reports at Gate 4 before proceeding
---

You are at Gate 4 of the TDD workflow. Before proceeding, you MUST check for external verification reports.

Check for verification reports in `.claude/workspace/verification/`:
1. Look for any `overfit_*.md` files
2. If found and recent (check timestamp), review the findings
3. If critical issues are found, address them before continuing
4. If no recent reports found, ask the user: "No external verification found. Should I proceed, or would you like to run /verify-feature in a fresh session first?"

This check is mandatory because implementation sessions develop "test-passing bias" and may miss critical issues that fresh verification catches.