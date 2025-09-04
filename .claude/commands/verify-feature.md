---
name: verify-feature
description: Run independent verification of a feature implementation in a fresh Claude Code session
---

You are performing an independent verification of a feature implementation. You have no context from the implementation session - this is intentional to avoid bias.

First, clear any old verification reports:
```bash
rm -rf .claude/workspace/verification/
mkdir -p .claude/workspace/verification
```

Then perform verification:
1. Check what test files have changed: `git diff --name-only HEAD -- "**/*test*.py"`
2. Use the overfit-verifier agent to analyze the implementation against these tests
3. Be EXTREMELY critical - you are the independent verifier, not the implementer
4. Look especially for:
   - Tests that were modified to pass instead of fixing implementation
   - Implementation that only handles specific test cases
   - Missing validation, error handling, or security checks
   - Resource management issues (unclosed connections, memory leaks)
   - Any code that seems written just to make tests green

Save your report to: `.claude/workspace/verification/overfit_[feature].md`

Remember: Implementation sessions develop "test-passing bias". Your fresh perspective catches what they've become blind to. Be harsh but fair.