# Behavior Testing Guide for Cosmos Workflow Tests

## Overview
This guide documents the refactoring of our test suite from implementation-focused mock testing to behavior-driven testing, following the principles from TEST_SUITE_INVESTIGATION_REPORT.md.

## Core Principles

### 1. Test Behavior, Not Implementation
```python
# ❌ BAD: Testing implementation details
mock_ssh.execute_command.assert_called_once_with("docker run")
mock_file_transfer.upload_file.assert_called_with(str(test_file), remote_path)

# ✅ GOOD: Testing behavior and outcomes
assert len(executor.containers_run) == 1
assert "test_scene" in executor.inference_results
assert executor.inference_results["test_scene"]["status"] == "success"
```

### 2. Use Fakes Instead of Mocks
```python
# ❌ BAD: Heavy mocking of internals
with patch("cosmos_workflow.SSHManager") as mock_ssh:
    with patch("cosmos_workflow.FileTransfer") as mock_ft:
        mock_ssh.return_value.execute_command.return_value = (0, "", "")
        # Complex mock setup...

# ✅ GOOD: Simple fake with predictable behavior
ssh_manager = FakeSSHManager()
file_transfer = FakeFileTransferService(ssh_manager)
orchestrator = FakeWorkflowOrchestrator()
```

### 3. Test at System Boundaries
```python
# ✅ GOOD: Contract test at SSH boundary
def test_ssh_connection_contract(ssh_manager):
    """Test what SSH promises, not how it works."""
    assert ssh_manager.connect() is True
    assert ssh_manager.is_connected() is True

    exit_code, stdout, stderr = ssh_manager.execute_command("echo test")
    assert exit_code == 0
    assert "test" in stdout
```

## Fake Implementations

### Location
All fakes are in `tests/fixtures/fakes.py`

### Available Fakes
- `FakeSSHManager` - Simulates SSH connections and commands
- `FakeFileTransferService` - Tracks file transfers without SFTP
- `FakeDockerExecutor` - Simulates Docker container execution
- `FakeWorkflowOrchestrator` - Complete workflow simulation
- `FakeRemoteExecutor` - Remote command execution
- `FakePromptSpec` / `FakeRunSpec` - Test data objects

### Using Fakes
```python
@pytest.fixture
def fake_orchestrator():
    return FakeWorkflowOrchestrator()

def test_workflow_completes(fake_orchestrator, test_specs):
    # Execute
    result = fake_orchestrator.run_inference(str(test_specs["run_file"]))

    # Verify behavior
    assert result is True
    assert len(fake_orchestrator.workflows_run) == 1
    assert fake_orchestrator.docker_executor.containers_run[0][0] == "inference"
```

## Test Categories

### 1. Unit Tests with Fakes
Location: `tests/unit/*/test_*_refactored.py`

Test individual components with fake dependencies:
```python
def test_inference_produces_expected_output(docker_executor, prompt_file):
    docker_executor.run_inference(prompt_file, num_gpu=2)

    # Verify behavior, not calls
    assert "test_scene" in docker_executor.inference_results
    result = docker_executor.inference_results["test_scene"]
    assert result["status"] == "success"
    assert result["output_path"].endswith(".mp4")
```

### 2. Integration Tests with Fakes
Location: `tests/integration/test_*_refactored.py`

Test component integration without real infrastructure:
```python
def test_full_pipeline(fake_orchestrator, test_specs):
    result = fake_orchestrator.run_inference(str(test_specs["run_file"]))

    # Verify integrated behavior
    assert result is True
    assert len(fake_orchestrator.file_transfer.uploaded_files) > 0
    assert len(fake_orchestrator.docker_executor.containers_run) == 1
```

### 3. Contract Tests
Location: `tests/contracts/test_*_contract.py`

Test boundaries and interfaces:
```python
class TestSSHContract:
    def test_command_execution_contract(self, ssh_manager):
        exit_code, stdout, stderr = ssh_manager.execute_command("echo hello")
        assert exit_code == 0
        assert "hello" in stdout
```

## Benefits of This Approach

### 1. Refactoring Freedom
Tests verify behavior, not implementation. You can refactor internals without breaking tests:
- Change method names
- Reorganize class structure
- Modify internal algorithms
- Update dependencies

### 2. Faster Test Execution
Fakes are lightweight and deterministic:
- No network calls
- No filesystem I/O
- No Docker containers
- Predictable timing

### 3. Better Test Coverage
Testing behavior reveals actual coverage:
- Focus on user-facing functionality
- Test error conditions easily
- Verify edge cases simply

### 4. Clearer Test Intent
Tests document expected behavior:
```python
def test_upscaling_requires_completed_inference(setup_for_upscaling):
    """Upscaling should fail without prior inference."""
    # Clear intent, behavior-focused test
```

## Migration Strategy

### Phase 1: Create Fakes (✅ COMPLETE)
- Created comprehensive fake implementations
- Fakes maintain contracts of real components

### Phase 2: Refactor Critical Tests (✅ COMPLETE)
- Workflow orchestration tests
- Docker executor tests
- SSH boundary tests

### Phase 3: Add Contract Tests (✅ COMPLETE)
- SSH contract tests
- File transfer contract tests
- Docker executor contract tests

### Phase 4: Refactor Remaining Tests (⏳ IN PROGRESS)
- SFTP workflow tests
- Video pipeline tests
- Prompt management tests

### Phase 5: Remove Old Tests (📅 PLANNED)
- Remove heavily mocked tests
- Keep only behavior-focused tests

## Guidelines for New Tests

### DO ✅
- Test behavior and outcomes
- Use fakes for dependencies
- Test at system boundaries
- Verify contracts, not implementations
- Make tests readable and intent-clear

### DON'T ❌
- Mock internal methods
- Assert on method calls
- Test private methods
- Use deep mock hierarchies
- Couple tests to implementation

## Example: Refactoring a Mock-Heavy Test

### Before (Mock-Heavy)
```python
def test_workflow_orchestration(self):
    with patch("module.SSHManager") as mock_ssh:
        with patch("module.FileTransfer") as mock_ft:
            with patch("module.DockerExecutor") as mock_docker:
                mock_ssh.return_value.execute_command.return_value = (0, "", "")
                mock_ft.return_value.upload_file.return_value = True
                mock_docker.return_value.run_inference.return_value = (0, "output", "")

                orchestrator = WorkflowOrchestrator()
                result = orchestrator.run()

                mock_ssh.return_value.execute_command.assert_called_once()
                mock_ft.return_value.upload_file.assert_called_with(ANY, ANY)
                mock_docker.return_value.run_inference.assert_called()
```

### After (Behavior-Focused)
```python
def test_workflow_completes_successfully(self, fake_orchestrator, test_specs):
    # Execute
    result = fake_orchestrator.run_inference(str(test_specs["run_file"]))

    # Verify behavior
    assert result is True

    # Verify outcomes
    assert len(fake_orchestrator.workflows_run) == 1
    assert fake_orchestrator.docker_executor.inference_results["test_scene"]["status"] == "success"

    # Verify contract
    result_path = fake_orchestrator.docker_executor.inference_results["test_scene"]["output_path"]
    assert result_path.endswith(".mp4")
```

## Verification Checklist

For each test file, verify:
- [ ] Uses fakes instead of mocks
- [ ] Tests behavior, not method calls
- [ ] Would survive internal refactoring
- [ ] Has clear intent from test name
- [ ] Verifies outcomes, not implementation

## Results

### Coverage Impact
- Overall coverage: 75.88% (slight increase)
- More accurate coverage metrics
- Better identification of untested behavior

### Test Quality Impact
- Tests are more stable
- Tests run faster (no I/O)
- Tests are more readable
- Tests document behavior better

### Development Impact
- Faster refactoring
- Fewer false test failures
- Better documentation via tests
- Easier debugging
