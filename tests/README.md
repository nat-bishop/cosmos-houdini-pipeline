# Cosmos Workflow Test Suite

## Overview

This test suite ensures the reliability and safety of the Cosmos Workflow system, with particular emphasis on data safety and GPU resource management.

## Test Structure

```
tests/
├── unit/                 # Unit tests for individual components
├── integration/          # Integration tests for component interactions
├── safety/              # CRITICAL: Safety tests for data protection
├── fixtures/            # Shared test fixtures and fakes
└── conftest.py         # Pytest configuration and fixtures
```

## Quick Start

```bash
# Run all tests
pytest

# Run all tests with coverage
pytest --cov=cosmos_workflow --cov-report=html

# Run specific test categories
pytest tests/unit           # Fast unit tests
pytest tests/integration    # Component interaction tests
pytest tests/safety         # Critical safety tests - must always pass

# Run specific test file with verbose output
pytest tests/safety/test_deletion_safety_critical.py -xvs

# Run last failed tests first
pytest --lf

# Stop on first failure
pytest -x
```

## Critical Testing Principles for This Repository

### 1. **Data Safety is Paramount**
- ALL destructive operations MUST require explicit confirmation (`force_overwrite=True`)
- Preview functions must accurately show what will be deleted
- Tests in `tests/safety/` are CRITICAL and must never be weakened
- If a safety test fails, fix the code, not the test

### 2. **Use Real Database Operations**
- Tests use SQLite in-memory databases for speed and isolation
- Never mock database operations when testing data integrity
- Each test gets a fresh database to prevent cross-contamination
- Real bugs hide behind database mocks

### 3. **Run Types and Blocking Behavior**
All runs are "blocking runs" that prevent prompt overwriting without `force_overwrite=True`:

| Run Type | Description | Uses GPU | Blocks Overwrite |
|----------|-------------|----------|------------------|
| transfer | Main inference/generation | Yes | Yes |
| enhance | Prompt enhancement | Yes | Yes |
| upscale | Video upscaling | Yes | Yes |
| reason | Reasoning tasks | Yes | Yes |
| predict | Prediction tasks | Yes | Yes |

**Important:** ALL runs block overwriting because they all represent GPU work that shouldn't be casually deleted.

### 4. **Test Organization Best Practices**

#### Feature Tests Stay With Features
```python
# tests/integration/test_prompt_enhancement_database.py
def test_enhancement_creates_run():
    """Test that enhancement creates proper database run."""
    # Feature-specific test stays with feature tests
```

#### Safety Tests Get Special Treatment
```python
# tests/safety/test_deletion_safety_critical.py
class TestCriticalDeletionSafety:
    """CRITICAL: Core safety invariants that must never be violated.

    DO NOT modify without careful review.
    """
```

### 5. **Valid Status Values**
Run statuses are strictly defined in the database:
- `pending` - Queued for execution
- `running` - Currently executing (ACTIVE - requires extra care when deleting)
- `completed` - Successfully finished
- `failed` - Execution failed

Never use invalid statuses like "uploading", "queued", etc.

### 6. **Enhancement Tracking**
Enhanced prompts store metadata in their `inputs` JSON field:
```python
{
    "enhanced": true,
    "parent_prompt_id": "ps_original_id",
    "enhancement_model": "pixtral",
    "enhanced_at": "2024-01-01T12:00:00Z"
}
```

## Writing New Tests

### Fixture Best Practices

#### Use Temporary Directories for File Operations
```python
@pytest.fixture
def repository(temp_db):
    with tempfile.TemporaryDirectory() as temp_dir:
        # Ensures cleanup after test
        config = MagicMock()
        config.get_local_config.return_value = MagicMock(outputs_dir=Path(temp_dir))
        yield DataRepository(temp_db, config)
```

#### Mock External Services, Not Internal Components
```python
# GOOD: Mock external GPU executor
with patch("cosmos_workflow.api.cosmos_api.GPUExecutor"):
    api = CosmosAPI()
    api.service = repository  # Use real repository

# BAD: Don't mock internal data operations
# with patch("cosmos_workflow.services.DataRepository"):  # Hides bugs!
```

### Error Testing Patterns

#### Test Error Messages Are Actionable
```python
def test_error_message_actionable(self, api, repository):
    """Error messages must tell user exactly what to do."""
    with pytest.raises(ValueError) as exc:
        api.enhance_prompt(prompt_id, force_overwrite=False)

    error = str(exc.value)
    # Must include:
    assert prompt_id in error                    # Which prompt
    assert "preview_prompt_deletion" in error    # How to check
    assert "force_overwrite=True" in error      # How to proceed
    assert "1 run(s)" in error                  # What will be deleted
```

#### Test Partial Failure Handling
```python
def test_partial_failure_doesnt_corrupt_data():
    """If deletion fails midway, data must remain consistent."""
    # Make second deletion fail
    def mock_delete(run_id, keep_outputs=True):
        if call_count == 2:
            raise RuntimeError("Database locked")
        return original_delete(run_id, keep_outputs)

    # Verify first run deleted, second run remains
    # Verify prompt unchanged (transaction rolled back)
```

### Naming Conventions
```python
# Safety-critical tests
def test_never_delete_without_confirmation():
    """Things that must NEVER happen."""

def test_always_require_force_for_active_runs():
    """Things that must ALWAYS happen."""

# Feature tests
def test_enhancement_creates_proper_run():
    """Standard feature behavior."""

# Edge case tests
def test_empty_prompt_allows_overwrite():
    """Boundary condition testing."""
```

## Available Test Fakes

Located in `tests/fixtures/fakes.py`:

- `FakeSSHManager` - SSH connection simulation
- `FakeDockerExecutor` - Docker operation simulation
- `FakeFileTransferService` - File transfer simulation
- `FakeRemoteExecutor` - Remote command execution

Usage:
```python
fake_ssh = FakeSSHManager()
fake_ssh.is_connected = True  # Set state
fake_file_transfer = FakeFileTransferService(fake_ssh)
```

## Common Pitfalls to Avoid

### 1. Don't Mock Database Operations
```python
# BAD - hides real bugs
with patch("cosmos_workflow.services.DataRepository.create_prompt"):
    pass

# GOOD - use real database
db = DatabaseConnection(":memory:")
repository = DataRepository(db, config)
```

### 2. Don't Weaken Safety Tests
```python
# If this test fails, DON'T change the test
def test_active_runs_require_force():
    """SAFETY: Active runs must always require force_overwrite."""
    # Fix the code instead!
```

### 3. Don't Use Magic Strings
```python
# BAD
run["model_type"] = "uploading"  # Invalid!

# GOOD
from cosmos_workflow.config.run_types import RunType
run["model_type"] = RunType.TRANSFER
```

### 4. Don't Ignore Test Warnings
- Warnings often indicate real issues
- Fix the root cause, don't suppress
- Use `pytest -W error` to treat warnings as errors

## Continuous Integration Checklist

Before committing:
```bash
# 1. Format and lint
ruff format .
ruff check . --fix

# 2. Run all tests
pytest

# 3. Run safety tests specifically (MUST PASS)
pytest tests/safety/ -xvs

# 4. Check test coverage
pytest --cov=cosmos_workflow --cov-report=term-missing
```

## Test Coverage Goals

- **Overall:** > 80%
- **Safety-critical paths:** 100% (no exceptions)
- **Data operations:** > 90%
- **API endpoints:** > 85%
- **Error handling:** > 95%

## Debugging Failing Tests

If a test is consistently failing:

1. **Is it a safety test?** Never disable these - fix the code
2. **Check database state:** Ensure clean setup/teardown
3. **Look for race conditions:** Especially in async code
4. **Verify fixture scope:** Session vs function scope matters
5. **Check for test pollution:** Tests should be independent

```bash
# Run single test in isolation
pytest path/to/test.py::TestClass::test_method -xvs

# Run with full traceback
pytest --tb=long

# Run with pdb on failure
pytest --pdb
```

## Performance Considerations

- Unit tests: < 0.1s each
- Integration tests: < 1s each
- Safety tests: < 0.5s each
- Total suite: < 30s

If tests are slow:
1. Use in-memory SQLite instead of disk
2. Mock external API calls
3. Use smaller test datasets
4. Parallelize with `pytest-xdist`

## Remember

> **Tests protect against regressions. A failing test is a gift that prevents a bug from reaching production.**

Safety tests are your last line of defense against data loss. Treat them with respect.