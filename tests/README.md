# Test Suite

## Quick Start

```bash
# Run all tests with coverage
pytest tests/ --cov=cosmos_workflow

# Run unit tests only (fast)
pytest tests/ -m unit

# Run specific test file
pytest tests/unit/test_ssh_manager.py
```

## Test Organization

```
tests/
├── unit/           # Unit tests for individual components
├── integration/    # Integration tests for component interactions
├── system/         # End-to-end system tests
├── contracts/      # Contract tests for fakes
└── fixtures/       # Test utilities and fake implementations
```

## Coverage Requirements
- Minimum 80% code coverage
- All new features must have tests
- Edge cases must be covered

## Writing Tests
- Test behavior, not implementation
- Use fakes instead of mocks
- Name tests clearly: `test_<component>_<action>_<expected_outcome>`

## Available Fakes
See `tests/fixtures/fakes.py` for test doubles:
- `FakeSSHManager` - SSH connection simulation
- `FakeDockerExecutor` - Docker operation simulation
- `FakeFileTransferService` - File transfer simulation
- `FakeWorkflowOrchestrator` - Workflow simulation

## Running Specific Tests
```bash
# Last failed tests first
pytest --lf

# Tests matching pattern
pytest -k "workflow"

# Stop on first failure
pytest -x
```
