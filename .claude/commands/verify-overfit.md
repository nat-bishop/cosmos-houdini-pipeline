---
name: verify-overfit
description: Run independent overfit verification in a fresh session and save to standard location
---

You are performing an independent overfit verification. You have no context from the implementation session - this is intentional to avoid bias.

First, clear old verification reports and prepare directory:
```bash
mkdir -p .claude/workspace/verification
rm -f .claude/workspace/verification/overfit_*.md
```

Then perform verification:
1. Identify what feature is being worked on from git changes
2. Check what test files have changed: `git diff --name-only HEAD -- "**/*test*.py"`
3. Use the overfit-verifier agent to analyze the implementation
4. Be EXTREMELY critical - look for:
   - Tests modified to pass rather than fixing implementation
   - Implementation that only handles specific test cases
   - Missing validation, error handling, or security checks
   - Resource management issues
   - Any code written just to make tests green

Save your detailed report to: `.claude/workspace/verification/overfit_report.md`

Your fresh perspective catches what implementation sessions miss. Be harsh but fair.