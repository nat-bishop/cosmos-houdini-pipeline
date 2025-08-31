# Test Suite Documentation

## Overview

The Cosmos workflow test suite is organized into three main categories:

1. **Unit Tests** - Fast, isolated tests of individual components
2. **Integration Tests** - Tests of component interactions with mocked external dependencies
3. **System Tests** - End-to-end tests that may require actual resources

## Test Structure

```
tests/
├── unit/                  # Fast, isolated unit tests
│   ├── config/           # Configuration management tests
│   ├── prompts/          # Schema and prompt management tests
│   ├── execution/        # Command building and execution tests
│   ├── connection/       # SSH and file transfer tests
│   ├── local_ai/         # AI and video processing tests
│   └── cli/              # CLI command tests
│
├── integration/           # Integration tests with mocked dependencies
│   ├── test_sftp_workflow.py
│   ├── test_workflow_orchestration.py
│   └── test_video_pipeline.py
│
├── system/               # End-to-end system tests
│   ├── test_end_to_end_pipeline.py
│   └── test_performance.py
│
├── fixtures/             # Test data and mock objects
│   ├── sample_data/     # Sample JSON specs and test data
│   └── mocks.py         # Reusable mock objects
│
└── utils/               # Test utilities
    └── helpers.py       # Common test helper functions
```

## Running Tests

### Quick Start

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=cosmos_workflow --cov-report=html

# Run specific test categories
pytest tests/unit -m unit           # Unit tests only
pytest tests/integration -m integration  # Integration tests
pytest tests/system -m system       # System tests
```

### Test Categories

#### Unit Tests (Fast)
```bash
# Run all unit tests
pytest tests/unit -v

# Run specific module tests
pytest tests/unit/prompts -v
pytest tests/unit/execution -v

# Run with timeout (30 seconds per test)
pytest tests/unit --timeout=30
```

#### Integration Tests (Medium)
```bash
# Run all integration tests
pytest tests/integration -v

# Run specific integration test
pytest tests/integration/test_sftp_workflow.py -v

# Run with markers
pytest -m "integration and not slow"
```

#### System Tests (Slow)
```bash
# Run system tests (may require resources)
pytest tests/system -v

# Run performance benchmarks
pytest tests/system/test_performance.py -v

# Skip slow tests
pytest -m "system and not slow"
```

## Test Markers

Tests can be marked with various attributes:

- `@pytest.mark.unit` - Unit test
- `@pytest.mark.integration` - Integration test
- `@pytest.mark.system` - System test
- `@pytest.mark.slow` - Test takes > 1 second
- `@pytest.mark.gpu` - Requires GPU
- `@pytest.mark.ssh` - Requires SSH connection
- `@pytest.mark.docker` - Requires Docker

### Using Markers

```python
@pytest.mark.integration
@pytest.mark.slow
def test_large_file_transfer():
    # Test implementation
    pass
```

### Running Tests by Marker

```bash
# Run only slow tests
pytest -m slow

# Run fast unit tests
pytest -m "unit and not slow"

# Run GPU tests
pytest -m gpu
```

## Writing Tests

### Unit Test Example

```python
# tests/unit/prompts/test_example.py
import pytest
from cosmos_workflow.prompts.schemas import PromptSpec

class TestPromptSpec:
    def test_creation(self):
        spec = PromptSpec(
            id="test_001",
            name="test",
            prompt="Test prompt"
        )
        assert spec.id == "test_001"
```

### Integration Test Example

```python
# tests/integration/test_example.py
import pytest
from unittest.mock import Mock

@pytest.mark.integration
class TestWorkflow:
    def test_workflow(self, mock_ssh_manager, mock_file_transfer):
        # Test with mocked external dependencies
        result = workflow.execute()
        assert result is True
```

### System Test Example

```python
# tests/system/test_example.py
import pytest

@pytest.mark.system
@pytest.mark.slow
class TestEndToEnd:
    def test_complete_pipeline(self):
        # Test complete workflow
        # May require actual resources
        pass
```

## Fixtures

### Common Fixtures (conftest.py)

- `temp_dir` - Temporary directory for test files
- `mock_config_manager` - Mocked configuration manager
- `mock_ssh_manager` - Mocked SSH connection
- `mock_file_transfer` - Mocked file transfer service
- `sample_prompt_spec` - Sample PromptSpec for testing
- `sample_run_spec` - Sample RunSpec for testing

### Using Fixtures

```python
def test_with_fixtures(temp_dir, sample_prompt_spec):
    # temp_dir is automatically created and cleaned up
    test_file = temp_dir / "test.json"
    test_file.write_text(json.dumps(sample_prompt_spec.to_dict()))
```

## Coverage

### Generating Coverage Reports

```bash
# Terminal report
pytest --cov=cosmos_workflow --cov-report=term-missing

# HTML report
pytest --cov=cosmos_workflow --cov-report=html
open htmlcov/index.html

# XML report (for CI/CD)
pytest --cov=cosmos_workflow --cov-report=xml
```

### Coverage Goals

- Unit tests: >90% coverage
- Integration tests: >70% coverage
- Overall: >80% coverage

## CI/CD Integration

### GitHub Actions

Tests run automatically on:
- Push to main/develop branches
- Pull requests
- Manual workflow dispatch

### Workflow Stages

1. **Unit Tests** - Run on multiple Python versions
2. **Integration Tests** - Run after unit tests pass
3. **System Tests** - Run on main branch only
4. **Performance Tests** - Run on push events
5. **Code Quality** - Check formatting and linting

### Pre-commit Hooks

Install pre-commit hooks for local development:

```bash
pip install pre-commit
pre-commit install
```

This will run:
- Code formatting (black)
- Import sorting (isort)
- Linting (flake8)
- Unit tests

## Debugging Tests

### Verbose Output

```bash
# Show all test output
pytest -vv

# Show print statements
pytest -s

# Show local variables on failure
pytest -l
```

### Running Specific Tests

```bash
# Run single test file
pytest tests/unit/prompts/test_schemas.py

# Run single test class
pytest tests/unit/prompts/test_schemas.py::TestPromptSpec

# Run single test method
pytest tests/unit/prompts/test_schemas.py::TestPromptSpec::test_creation
```

### Debugging with pdb

```python
def test_debugging():
    import pdb; pdb.set_trace()  # Debugger breakpoint
    assert True
```

## Performance Testing

### Running Benchmarks

```bash
# Run performance tests
pytest tests/system/test_performance.py -v

# Generate benchmark report
pytest tests/system/test_performance.py --benchmark-only
```

### Interpreting Results

Performance metrics are saved to `performance_metrics.json` including:
- Operation duration
- Throughput metrics
- Memory usage
- Statistical analysis (min, max, mean, median, stdev)

## Best Practices

1. **Keep tests fast** - Unit tests should run in < 1 second
2. **Use appropriate markers** - Help others run relevant tests
3. **Mock external dependencies** - Don't require actual resources for unit/integration tests
4. **Clear test names** - Test names should describe what they test
5. **Use fixtures** - Reduce code duplication
6. **Test edge cases** - Don't just test happy paths
7. **Document complex tests** - Add comments for complex test logic
8. **Clean up resources** - Ensure tests clean up after themselves

## Troubleshooting

### Common Issues

#### ImportError
- Ensure cosmos_workflow is in PYTHONPATH
- Install package in development mode: `pip install -e .`

#### Fixture not found
- Check fixture is defined in conftest.py
- Ensure conftest.py is in test directory or parent

#### Test timeout
- Increase timeout: `pytest --timeout=300`
- Check for infinite loops or blocking operations

#### Coverage gaps
- Run coverage with `--cov-report=term-missing` to see uncovered lines
- Add tests for uncovered code paths

## Contributing

When adding new features:
1. Write unit tests first (TDD)
2. Add integration tests for component interactions
3. Include system tests for end-to-end workflows
4. Ensure >80% coverage for new code
5. Run pre-commit hooks before committing
6. Update this documentation if adding new test patterns
