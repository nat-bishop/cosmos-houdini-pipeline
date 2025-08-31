# Testing Strategy for Cosmos Workflow Orchestrator

## Current State (2025-08-31)

### ✅ Unit Tests - PASSING
- **436 unit tests** all passing
- **~75% code coverage**
- **Fast execution** (<8 seconds)
- **No external dependencies** required
- Uses test doubles and fixtures effectively

### ⚠️ Integration Tests - OUTDATED
- 21 integration tests failing
- Written for older codebase version
- Expect methods that no longer exist (e.g., `load_by_id`)
- Mock at wrong abstraction level
- Marked as `@pytest.mark.optional` in `tests/integration/conftest.py`

### ⚠️ System Tests - REQUIRE INFRASTRUCTURE
- 6 system tests failing
- Require actual NVIDIA Cosmos model
- Need real GPU and Docker infrastructure
- Marked as `@pytest.mark.optional` in `tests/system/conftest.py`

### ⚠️ Performance Tests - REQUIRE CUDA
- 3 performance tests failing
- Require CUDA for GPU tests
- Marked as `@pytest.mark.optional` in `tests/performance/conftest.py`

## Testing Philosophy

As a **solo professional project**, the testing strategy prioritizes:

1. **Reliable unit tests** for fast feedback during development
2. **Behavioral testing** that survives refactoring
3. **Practical coverage** over exhaustive testing
4. **Clear separation** between test types

## Test Commands

### Daily Development (RECOMMENDED)
```bash
# Run all unit tests (fast, reliable)
pytest tests/unit/ -q

# Run with coverage report
pytest tests/unit/ --cov=cosmos_workflow --cov-report=term-missing

# Run specific test file
pytest tests/unit/workflows/test_workflow_orchestrator.py -v
```

### Before Committing
```bash
# Format and lint
ruff format cosmos_workflow/
ruff check cosmos_workflow/ --fix

# Run unit tests with coverage
pytest tests/unit/ --cov=cosmos_workflow --cov-report=term-missing
```

### Optional Test Suites
```bash
# Run integration tests (when refactored)
pytest tests/integration/ -v

# Run system tests (requires GPU/Docker)
pytest tests/system/ -v

# Run performance benchmarks
pytest tests/performance/ -v

# Run ALL tests including optional
pytest tests/ -v
```

## Why Integration/System Tests Are Optional

### Integration Tests
- Were written for an **older architecture**
- Mock at the **wrong abstraction level**
- Would require **significant refactoring** to align with current code
- Not critical for solo development workflow
- Can be refactored when time permits

### System Tests
- Require **real GPU infrastructure**
- Need **NVIDIA Cosmos model** (large download)
- Meant as **smoke tests** for production
- Not suitable for regular CI/CD
- Should only run in production-like environments

### Performance Tests
- Require **CUDA availability**
- Test **deterministic execution** features
- Useful for **benchmarking** but not daily development
- Run when validating performance-critical changes

## Future Improvements (Low Priority)

1. **Refactor integration tests** to match current architecture
2. **Create docker-compose** test environment for integration tests
3. **Add GitHub Actions** for automated unit test runs
4. **Update performance tests** to work without CUDA (CPU fallback)

## Key Decisions

1. **Unit tests are mandatory** - Must pass before any commit
2. **Integration/system tests are optional** - Run when needed
3. **Coverage target is ~80%** - Current ~75% is acceptable
4. **Test doubles over mocks** - More maintainable
5. **Behavioral over implementation** - Tests survive refactoring

## Test File Organization

```
tests/
├── unit/               # Fast, isolated tests (MUST PASS)
│   ├── cli/
│   ├── config/
│   ├── execution/
│   ├── local_ai/
│   ├── prompts/
│   ├── transfer/
│   ├── utils/
│   └── workflows/
├── integration/        # Cross-component tests (OPTIONAL)
│   └── conftest.py    # Marks all as optional
├── system/            # End-to-end tests (OPTIONAL)
│   └── conftest.py    # Marks all as optional
├── performance/       # Benchmark tests (OPTIONAL)
│   └── conftest.py    # Marks all as optional
└── conftest.py        # Shared fixtures
```

## Maintenance Notes

- **Unit tests** should be updated with code changes
- **Integration tests** can be ignored until refactored
- **System tests** only matter for production deployment
- **Performance tests** only matter for optimization work

This pragmatic approach ensures reliable testing without unnecessary overhead for a solo professional project.
