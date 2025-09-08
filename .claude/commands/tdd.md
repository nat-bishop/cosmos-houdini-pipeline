<system_context>

You are implementing a new feature using Test-Driven Development (TDD). This is a disciplined, gated workflow that ensures quality through behavioral testing and systematic verification.

Feature to implement: $ARGUMENTS

</system_context>

<critical_notes>

## MISSION CRITICAL RULES

1. **Gates are sequential and mandatory** - Each gate MUST complete successfully before proceeding to the next.

2. **Tests are contracts** - Once written (Gate 1) and committed (Gate 3), tests MUST NOT be modified.

3. **Behavioral testing only** - Test what the system does, not how it does it.

4. **Use wrappers exclusively** - NEVER call raw libraries (paramiko, docker, subprocess, json) directly.

5. **Generalization pressure** - Write enough test cases that only a general solution can pass.

6. **Clean workspace** - All temporary files go in .claude/workspace/ and must be cleaned up.

</critical_notes>

<workflow>

## TDD WORKFLOW

### Phase 1: Understanding
**First, explore and understand** what needs to be built. Analyze:
- How this feature fits the existing architecture
- Which modules and patterns to follow
- Multiple implementation approaches
- The best design for maintainability

### Phase 2: Gated Implementation

**Gate 1 — Write Failing Tests**
- Identify or create appropriate test files
- Write comprehensive behavioral tests covering:
  - Happy path scenarios
  - Edge cases and boundaries
  - Error conditions and exceptions
- Use wrappers for determinism (no raw mocking)
- **Expected**: All new tests fail

**Gate 2 — Verify Tests Fail**
- Run: `pytest <test_files> -xvs`
- Confirm all new tests fail with meaningful errors
- Verify no existing tests were modified
- **Do not** run full test suite coverage

**Gate 3 — Commit Failing Tests**
- Stage: `git add <test_files>`
- Commit: `git commit -m "test: add failing tests for <feature> (TDD Gate 3)"`
- Tests are now the immutable contract

**Gate 4 — Implement Solution**
- Write minimal code to make tests pass
- **Do not** modify any tests
- Run: `pytest <test_files> -xvs`
- Launch: `overfit-verifier` agent to ensure generalization
- **Expected**: All tests pass

**Gate 5 — Update Documentation**
- Launch: `doc-drafter` agent
- Update CHANGELOG.md if applicable
- Update relevant API documentation

**Gate 6 — Final Review**
Run in parallel:
- Launch: `code-reviewer` agent
- Run: `ruff check . && ruff format .`
- Run: `pytest --cov --cov-report=term-missing`
- Verify coverage meets requirements

</workflow>

<patterns>

## IMPLEMENTATION PATTERNS

### Use TodoWrite Tool
Track your progress through gates:
```python
todos = [
    {"content": "Write failing tests for <feature>", "status": "in_progress", "activeForm": "Writing failing tests"},
    {"content": "Verify tests fail", "status": "pending", "activeForm": "Verifying test failures"},
    {"content": "Commit failing tests", "status": "pending", "activeForm": "Committing failing tests"},
    {"content": "Implement solution", "status": "pending", "activeForm": "Implementing solution"},
    {"content": "Update documentation", "status": "pending", "activeForm": "Updating documentation"},
    {"content": "Final review", "status": "pending", "activeForm": "Running final review"}
]
```

### Test Structure Example
```python
def test_feature_behavior():
    """Test the behavior, not the implementation."""
    # Arrange
    system = SystemUnderTest()

    # Act
    result = system.perform_action(input_data)

    # Assert
    assert result.meets_requirement()
```

### Wrapper Usage
```python
# BAD: Direct library usage
import paramiko
client = paramiko.SSHClient()

# GOOD: Use our wrapper
from cosmos_workflow.connection import SSHManager
with SSHManager(config) as ssh:
    ssh.execute_command(cmd)
```

</patterns>

<paved_path>

## ARCHITECTURE (PAVED PATH)

The canonical TDD approach for this codebase:

1. **Always start with exploration** - Understand before implementing
2. **Use CosmosAPI facade** - Never bypass to use DataRepository or GPUExecutor directly
3. **Follow existing patterns** - Check neighboring files for conventions
4. **Behavioral tests only** - Test outcomes, not mechanisms
5. **Wrapper enforcement** - All external interactions through our wrappers
6. **Clean architecture** - Separate concerns, small functions, single responsibility

</paved_path>

<completion>

## COMPLETION CHECKLIST

Before considering the feature complete:
- [ ] All 6 gates passed successfully
- [ ] Tests cover all behavioral requirements
- [ ] Implementation is general, not overfitted
- [ ] Documentation is updated
- [ ] Code passes review, lint, and coverage
- [ ] Workspace cleaned (.claude/workspace/)
- [ ] Implementation committed with appropriate message

</completion>