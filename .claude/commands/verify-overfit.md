---
name: verify-overfit
description: Run overfitting verification from a fresh context
---

You are performing overfitting verification without implementation context.

Required Setup:
```bash
mkdir -p .claude/workspace/verification
rm -f .claude/workspace/verification/EXTERNAL_*.md
```

Gather information:
1. Identify changed files: `git diff --name-only HEAD`
2. Get current git HEAD: `git rev-parse HEAD`
3. Identify the feature being verified from the changed files

Perform verification:
1. **Static analysis only - do NOT generate test scripts**
2. Use the overfit-verifier agent to check the implementation
3. Focus question: Would this code work with inputs other than the test cases?
4. Document any code that appears tailored to specific test values

Build and save report:
```markdown
# EXTERNAL OVERFIT VERIFICATION
Generated: [timestamp]
Feature: [what was analyzed]
Changed files: [list of files analyzed]
Git HEAD: [commit hash]

## Verdict
[PASS/FAIL]

## Findings
[Specific overfitting patterns found with line numbers, or "No overfitting detected"]
```

Save to: `.claude/workspace/verification/EXTERNAL_overfit_check.md` Do not save until finished with your analysis.

Note: You have no context from the implementation session. This allows objective evaluation of whether the code is general or test-specific.