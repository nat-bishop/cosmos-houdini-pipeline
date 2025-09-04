---
name: verify-overfit
description: Run independent overfit verification in a fresh session and save to standard location
---

You are performing an independent overfit verification. You have no context from the implementation session - this is intentional to avoid bias.

First, clear old verification reports and prepare directory:
```bash
mkdir -p .claude/workspace/verification
rm -f .claude/workspace/verification/EXTERNAL_*.md
```

Then gather context about what to verify:
1. Identify current feature from: `git status` and `git diff --name-only HEAD`
2. Check what test files have changed: `git diff --name-only HEAD -- "**/*test*.py"`
3. Get current git HEAD: `git rev-parse HEAD`

Now perform the verification:
1. Use the overfit-verifier agent to analyze the implementation against the tests
2. Be EXTREMELY critical - you are the independent verifier, not the implementer
3. Compare implementation files to their test files - does the implementation truly solve the general problem?
4. Look especially for:
   - Tests that were modified to pass instead of fixing implementation
   - Implementation that only handles specific test cases
   - Missing validation, error handling, or security checks
   - Resource management issues (unclosed connections, memory leaks)
   - Any code written just to make tests green

Build your complete report including this header:
```markdown
# EXTERNAL OVERFIT VERIFICATION
Generated: [timestamp]
Feature: [what was analyzed]
Changed files: [list of files analyzed]
Git HEAD: [commit hash]
Session: Independent verification session

## Findings
[Your detailed analysis]
```

**IMPORTANT**: Only write the report once your analysis is complete. Save to:
`.claude/workspace/verification/EXTERNAL_overfit_check.md`

After saving, tell the user:
"External overfit verification complete - report saved to `.claude/workspace/verification/EXTERNAL_overfit_check.md`"

Remember: Implementation sessions develop "test-passing bias" and miss critical issues. Your fresh perspective is valuable. Be harsh but fair.