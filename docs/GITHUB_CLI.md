# GitHub CLI Integration

## Installation Check
```bash
gh --version || echo "Install from: https://cli.github.com"
```

## TDD Workflow with GitHub

### After TDD Cycle Completion
```bash
# Create PR with TDD context
gh pr create \
  --title "feat: implement X using TDD" \
  --body "## Summary
- Tests written first and committed separately
- Implementation passes all tests
- Code reviewed by subagents
- No overfitting detected

## Test Coverage
- Unit tests: tests/test_feature.py
- Coverage: 95%

## Checks Passed
- test-runner: ✅
- code-reviewer: ✅
- overfit-verifier: ✅
- doc-drafter: ✅"

# Check CI status
gh run list --workflow=test.yml --limit=5

# Watch specific run
gh run watch

# View PR checks
gh pr checks
```

### Review Workflow
```bash
# List PRs needing review
gh pr list --reviewer @me

# Review PR with inline comments
gh pr review 123 --comment -b "LGTM, tests are comprehensive"

# Approve PR
gh pr review 123 --approve
```

### Issue Integration
```bash
# Create issue for test failures
gh issue create \
  --title "Test failure: test_feature_edge_case" \
  --body "$(cat .claude/reports/test-run.json | jq -r '.failures[0].message')" \
  --label bug,test-failure

# Link PR to issue
gh pr edit --add-label "fixes #123"
```

### Automation Examples
```bash
# Auto-merge when checks pass
gh pr merge --auto --squash

# Create draft PR during TDD
gh pr create --draft --title "WIP: TDD for feature X"

# Convert to ready when implementation complete
gh pr ready
```

## Useful Aliases
Add to your shell config:
```bash
alias ghpr='gh pr create'
alias ghci='gh run list --workflow=test.yml --limit=1'
alias ghwatch='gh run watch'
alias ghchecks='gh pr checks'
```
