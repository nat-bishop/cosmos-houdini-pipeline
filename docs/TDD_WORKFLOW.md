# Test-Driven Development Workflow

## Overview
This project follows strict TDD practices with specialized subagents for each phase.

## TDD Cycle

### 1. Write Tests First
Write comprehensive tests that will initially fail:
```python
# tests/test_new_feature.py
def test_feature_basic():
    assert my_function(2, 3) == 5

def test_feature_edge_cases():
    assert my_function(0, 0) == 0
    assert my_function(-1, 1) == 0
```

### 2. Verify Tests Fail
Run tests using the test-runner subagent:
```
@subagent test-runner
Run: pytest tests/test_new_feature.py -xvs
```
Confirm all new tests fail before proceeding.

### 3. Commit Tests
After verifying tests are correct and failing:
```bash
git add tests/test_new_feature.py
git commit -m "test: add tests for new feature"
```

### 4. Implement Code
Write minimal code to make tests pass:
- Focus on passing tests, not perfection
- Iterate: implement → test → adjust
- Keep implementation in main thread for context

### 5. Verify Tests Pass
```
@subagent test-runner
Run: pytest tests/test_new_feature.py -xvs
```

### 6. Check for Overfitting (Parallel)
While tests are passing, verify implementation is general:
```
@subagent overfit-verifier
Check: tests/test_new_feature.py against cosmos_workflow/feature.py
```

### 7. Review Code Quality (Parallel)
Run code review for security and critical issues:
```
@subagent code-reviewer
Review current git diff
```

### 8. Fix Issues
Address any critical issues from code-reviewer or overfitting from verifier.

### 9. Update Documentation (Parallel)
Keep docs in sync with code:
```
@subagent doc-drafter
Update documentation for recent changes
```

### 10. Commit Implementation
Once all checks pass:
```bash
git add -A
git commit -m "feat: implement new feature"
```

## Parallel Execution
These can run simultaneously after tests pass:
- `overfit-verifier`
- `code-reviewer`
- `doc-drafter`

## Subagent Reports
All subagents write to `.claude/reports/`:
- `test-run.json` - Test results
- `code-review.json` - Review findings
- `overfit-check.json` - Overfitting analysis
- `doc-updates.json` - Documentation changes

## GitHub Integration
After completing TDD cycle:
```bash
# Create PR
gh pr create --title "feat: new feature" --body "Implements X with full test coverage"

# Check CI status
gh run list --workflow=test.yml

# View PR checks
gh pr checks
```

## Key Principles
1. **Never skip writing tests first**
2. **Tests must fail before implementation**
3. **Implementation stays in main thread**
4. **Subagents provide independent verification**
5. **Documentation updates are automatic**
6. **Commit tests and implementation separately**
