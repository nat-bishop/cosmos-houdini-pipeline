# Workflow Orchestrator Test Plan & Code Cleanup

## Current State Analysis

### Coverage Status ✅ ACHIEVED
- **Initial Coverage**: 13.66% (109 uncovered lines)
- **Target Coverage**: 80%+
- **Achieved Coverage**: **93.79%** ✅
- **File**: `cosmos_workflow/workflows/workflow_orchestrator.py`
- **Tests Added**: 25 comprehensive tests
- **Date Completed**: 2025-08-31

### Convenience Methods Investigation

#### Specialized Workflow Methods Found
The following methods provide convenient APIs for common workflows:
1. `run_full_cycle()` - Lines 147-170 - Full pipeline with all steps
2. `run_inference_only()` - Lines 172-192 - Quick generation without upscaling
3. `run_upscaling_only()` - Lines 194-214 - Upscale existing outputs

#### Usage Analysis
These convenience methods are actively used by the CLI:
- `run_full_cycle` - Called by CLI 'run' command (line 58)
- `run_inference_only` - Called by CLI 'run' with --no-upscale flag (line 84)
- `run_upscaling_only` - Called by CLI 'upscale' command (line 108)

**Purpose**: These methods provide cleaner, more intuitive APIs for common workflows. They delegate to the flexible `run()` method with appropriate presets, making the CLI simpler and more user-friendly.

### Potentially Removable Code
After analysis, there's no dead code to remove. All methods are either:
- Used by the CLI
- Core functionality
- Helper methods used internally

## Test Implementation Plan

### Phase 1: Basic Tests & Quick Wins (Target: +20% coverage)

#### 1.1 Initialization Tests
```python
def test_init_with_default_config()
def test_init_with_custom_config_file()
def test_initialize_services_creates_all_services()
def test_initialize_services_reuses_existing()
```

#### 1.2 Helper Method Tests
```python
def test_get_workflow_type_full_cycle()
def test_get_workflow_type_inference_only()
def test_get_workflow_type_upscaling_only()
def test_get_workflow_type_custom()
def test_get_video_directories_with_override()
def test_get_video_directories_from_run_spec()
def test_get_video_directories_default()
```

#### 1.3 Status Check Tests
```python
def test_check_remote_status_success()
def test_check_remote_status_connection_failure()
```

### Phase 2: Core Workflow Tests (Target: +30% coverage)

#### 2.1 Main run() Method Tests
```python
def test_run_full_workflow_success()
def test_run_inference_only_workflow()
def test_run_upscale_only_workflow()
def test_run_custom_workflow_upload_download_only()
def test_run_with_exception_handling()
def test_run_with_missing_prompt_file()
```

#### 2.2 Legacy Method Tests
```python
def test_run_full_cycle_delegates_correctly()
def test_run_inference_only_delegates_correctly()
def test_run_upscaling_only_delegates_correctly()
```

### Phase 3: Logging & Edge Cases (Target: +15% coverage)

#### 3.1 Logging Tests
```python
def test_log_workflow_completion_creates_file()
def test_log_workflow_completion_appends_to_existing()
def test_log_workflow_failure_creates_file()
def test_log_workflow_failure_with_exception()
```

#### 3.2 Edge Cases
```python
def test_run_with_ssh_connection_failure()
def test_run_with_docker_executor_failure()
def test_run_with_file_transfer_failure()
def test_video_directories_with_invalid_run_spec()
```

## Mock Strategy

### Core Mocks Required
```python
@pytest.fixture
def mock_config_manager():
    """Mock ConfigManager with test configurations."""
    manager = MagicMock(spec=ConfigManager)
    manager.get_remote_config.return_value = MagicMock(
        remote_dir="/remote/cosmos",
        host="192.168.1.100",
        docker_image="cosmos:latest"
    )
    manager.get_local_config.return_value = MagicMock(
        notes_dir=Path("test_notes")
    )
    manager.get_ssh_options.return_value = {}
    return manager

@pytest.fixture
def mock_ssh_manager():
    """Mock SSHManager with context manager support."""
    ssh = MagicMock(spec=SSHManager)
    ssh.__enter__ = MagicMock(return_value=ssh)
    ssh.__exit__ = MagicMock(return_value=None)
    return ssh

@pytest.fixture
def mock_file_transfer():
    """Mock FileTransferService."""
    transfer = MagicMock(spec=FileTransferService)
    transfer.upload_prompt_and_videos = MagicMock()
    transfer.download_results = MagicMock()
    transfer.file_exists_remote = MagicMock(return_value=True)
    return transfer

@pytest.fixture
def mock_docker_executor():
    """Mock DockerExecutor."""
    docker = MagicMock(spec=DockerExecutor)
    docker.run_inference = MagicMock()
    docker.run_upscaling = MagicMock()
    docker.get_docker_status = MagicMock(return_value="running")
    return docker

@pytest.fixture
def workflow_orchestrator(mock_config_manager):
    """Create WorkflowOrchestrator with mocked config."""
    with patch('cosmos_workflow.workflows.workflow_orchestrator.ConfigManager',
               return_value=mock_config_manager):
        return WorkflowOrchestrator()
```

## Implementation Strategy

### File Structure
```
tests/unit/workflows/
├── __init__.py
├── test_workflow_orchestrator.py
└── test_upsample_integration.py  # Future
```

### Test Organization
```python
class TestWorkflowOrchestratorInit:
    """Test initialization and service creation."""

class TestWorkflowOrchestratorRun:
    """Test main run() method and workflows."""

class TestWorkflowOrchestratorLegacy:
    """Test legacy methods for backward compatibility."""

class TestWorkflowOrchestratorHelpers:
    """Test helper methods."""

class TestWorkflowOrchestratorLogging:
    """Test logging functionality."""
```

## Expected Outcomes

### Coverage Improvements
| Phase | Current | Target | Lines to Cover |
|-------|---------|--------|----------------|
| Phase 1 | 14% | 35% | ~23 lines |
| Phase 2 | 35% | 65% | ~33 lines |
| Phase 3 | 65% | 80% | ~16 lines |

### Risk Areas
1. **SSH Context Manager** - Ensure proper mocking of `with self.ssh_manager:`
2. **File I/O** - Mock file operations for logging
3. **Path Operations** - Mock Path.exists(), Path.mkdir()
4. **Exception Handling** - Test both success and failure paths

## Success Criteria
1. ✅ All tests pass
2. ✅ Coverage increases to 80%+
3. ✅ No test takes longer than 0.1 seconds
4. ✅ Tests are maintainable and clear
5. ✅ Legacy methods remain functional for CLI

## Next Steps
1. Create test file structure
2. Implement Phase 1 tests
3. Run and verify coverage improvement
4. Continue with Phase 2
5. Complete with Phase 3 and edge cases

## Time Estimate
- Phase 1: 30 minutes
- Phase 2: 45 minutes
- Phase 3: 30 minutes
- **Total: ~2 hours**

Ready to begin implementation!
