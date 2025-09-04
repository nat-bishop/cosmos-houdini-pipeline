---
name: verify-review
description: Run independent code review in a fresh session and save to standard location
---

You are performing an independent code review. You have no context from the implementation session - this is intentional to provide unbiased review.

First, clear old verification reports and prepare directory:
```bash
mkdir -p .claude/workspace/verification
rm -f .claude/workspace/verification/EXTERNAL_code_review.md
```

Then gather context about what to review:
1. Identify changed files: `git diff --name-only HEAD`
2. Get current git HEAD: `git rev-parse HEAD`
3. Check recent commits: `git log --oneline -n 5`
4. Check if tests were modified after initial commit: `git diff HEAD~1 -- "**/*test*.py"`

Now perform the code review:
1. Use the code-reviewer agent to analyze all recent changes
2. Be thorough and critical - you are an independent reviewer
3. Focus especially on:
   - Whether tests were written first (check commit history)
   - Wrapper usage compliance (no raw library calls)
   - Security issues (secrets, unsafe error handling, path traversal)
   - Resource management (proper cleanup, connection closing)
   - Code that seems written just to pass tests rather than solve the problem
   - Any modifications to tests after Gate 3

Build your complete report including this header:
```markdown
# EXTERNAL CODE REVIEW
Generated: [timestamp]
Feature reviewed: [what was analyzed]
Changed files: [list of files reviewed]
Git HEAD: [commit hash]
Session: Independent review session

## Review Findings
[Your detailed review organized by severity]
```

**IMPORTANT**: Only write the report once your review is complete. Save to:
`.claude/workspace/verification/EXTERNAL_code_review.md`

After saving, tell the user:
"External code review complete - report saved to `.claude/workspace/verification/EXTERNAL_code_review.md`"

Remember: Implementation sessions can miss quality issues due to focus on making tests pass. Your independent review is crucial for catching security issues, anti-patterns, and maintainability problems.