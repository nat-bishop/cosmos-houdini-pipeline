# Test Suite Reorganization Plan

## Current Issues
- All tests in single flat directory (30+ test files)
- Mix of unit, integration, and system tests
- No clear separation of concerns
- Difficult to run specific test categories
- Missing test utilities and shared fixtures

## Proposed Structure

```
tests/
├── __init__.py
├── conftest.py                    # Shared pytest fixtures
├── unit/                          # Fast, isolated unit tests
│   ├── __init__.py
│   ├── config/
│   │   ├── test_config_manager.py
│   │   └── test_directory_manager.py
│   ├── prompts/
│   │   ├── test_schemas.py
│   │   ├── test_schema_validator.py
│   │   ├── test_prompt_spec_manager.py
│   │   ├── test_run_spec_manager.py
│   │   └── test_cosmos_converter.py
│   ├── execution/
│   │   ├── test_command_builder.py
│   │   ├── test_docker_executor.py
│   │   └── test_workflow_utils.py
│   ├── connection/
│   │   ├── test_ssh_manager.py
│   │   └── test_file_transfer.py
│   ├── local_ai/
│   │   ├── test_text_to_name.py
│   │   ├── test_video_metadata.py
│   │   └── test_cosmos_sequence.py
│   └── cli/
│       ├── test_cli_commands.py
│       ├── test_cli_helpers.py
│       └── test_cli_convert_sequence.py
│
├── integration/                   # Tests with mocked external dependencies
│   ├── __init__.py
│   ├── test_prompt_workflow.py   # PromptSpec creation to RunSpec
│   ├── test_file_transfer.py     # SFTP upload/download workflows
│   ├── test_video_pipeline.py    # PNG to video conversion pipeline
│   ├── test_ai_integration.py    # AI description and naming
│   ├── test_upsample_workflow.py # Prompt upsampling pipeline
│   └── test_orchestrator.py      # WorkflowOrchestrator integration
│
├── system/                        # End-to-end tests (may need real resources)
│   ├── __init__.py
│   ├── test_full_pipeline.py     # Complete inference workflow
│   ├── test_batch_processing.py  # Batch job handling
│   ├── test_error_recovery.py    # Failure scenarios and recovery
│   └── test_performance.py       # Load and performance testing
│
├── fixtures/                      # Test data and mock objects
│   ├── __init__.py
│   ├── sample_data/
│   │   ├── test_frames/          # Sample PNG sequences
│   │   ├── test_videos/          # Sample videos
│   │   └── test_specs/           # Sample JSON specs
│   ├── mocks.py                  # Reusable mock objects
│   └── factories.py              # Test data factories
│
└── utils/                         # Test utilities
    ├── __init__.py
    ├── helpers.py                 # Common test helpers
    ├── assertions.py              # Custom assertions
    └── markers.py                 # Pytest markers (slow, gpu, etc.)
```

## Benefits of New Structure

1. **Clear Separation**: Unit vs Integration vs System tests
2. **Faster Testing**: Can run only unit tests during development
3. **Better Organization**: Tests grouped by module/functionality
4. **Shared Resources**: Common fixtures and utilities
5. **Selective Execution**: Easy to run specific test categories

## Pytest Configuration

Create `pytest.ini`:
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

markers =
    unit: Unit tests (fast, isolated)
    integration: Integration tests (mocked external deps)
    system: System tests (may need real resources)
    slow: Tests that take > 1 second
    gpu: Tests that require GPU
    ssh: Tests that require SSH connection
    
addopts = 
    --strict-markers
    -ra
    --cov=cosmos_workflow
    --cov-report=term-missing:skip-covered
```

## Migration Steps

1. Create new directory structure
2. Move existing tests to appropriate categories
3. Create shared fixtures in conftest.py
4. Add test markers for categorization
5. Update CI/CD to run tests by category
6. Create integration test templates

## Test Execution Commands

```bash
# Run all tests
pytest

# Run only unit tests (fast)
pytest tests/unit -m "not slow"

# Run integration tests
pytest tests/integration

# Run system tests (requires resources)
pytest tests/system -m system

# Run tests with coverage
pytest --cov=cosmos_workflow --cov-report=html

# Run specific module tests
pytest tests/unit/prompts
```

## Priority Migration

### Phase 1: Structure Setup
- Create directory structure
- Move obvious unit tests
- Create conftest.py with basic fixtures

### Phase 2: Integration Tests
- Create integration test suite for SFTP
- Create workflow orchestration tests
- Add mocked SSH/Docker tests

### Phase 3: System Tests
- Create end-to-end pipeline test
- Add performance benchmarks
- Create failure recovery tests

### Phase 4: Cleanup
- Remove redundant tests
- Improve test documentation
- Add missing test coverage