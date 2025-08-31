# Comprehensive Test Suite Fix Plan
*Created: 2025-08-31*
*Branch: feature/parallel-development*

## Executive Summary

This document provides a detailed, actionable plan to fix the Cosmos Workflow Orchestrator test suite. The fixes address schema mismatches, over-mocking, poor coverage, and test isolation issues identified in the TEST_SUITE_INVESTIGATION_REPORT.

**Goal**: Transform the test suite from a fragile, over-mocked system to a robust, behavior-driven test suite that actually validates code correctness.

---

## Phase 1: Immediate Schema Fixes (Day 1)
*Estimated Time: 1-2 hours*

### 1.1 Fix conftest.py Fixtures

#### RunSpec Fixture (Line 96-106)
```python
# CURRENT (BROKEN):
@pytest.fixture
def sample_run_spec(sample_prompt_spec):
    return RunSpec(
        id="test_rs_456",
        prompt_spec_id=sample_prompt_spec.id,  # ❌ WRONG field name
        # Missing 'name' field                 # ❌ Missing required field
        control_weights={"depth": 0.3, "segmentation": 0.4},
        parameters={"num_steps": 35, "guidance_scale": 8.0, "seed": 42},
        execution_status="pending",           # ❌ Should be enum
        output_path="outputs/test_run",
        timestamp=datetime.now().isoformat(),
    )

# FIXED:
from cosmos_workflow.prompts.schemas import ExecutionStatus

@pytest.fixture
def sample_run_spec(sample_prompt_spec):
    return RunSpec(
        id="test_rs_456",
        prompt_id=sample_prompt_spec.id,      # ✅ Correct field
        name="test_run",                      # ✅ Added required field
        control_weights={"depth": 0.3, "segmentation": 0.4},
        parameters={"num_steps": 35, "guidance": 8.0, "seed": 42},  # ✅ guidance not guidance_scale
        timestamp=datetime.now().isoformat(),
        execution_status=ExecutionStatus.PENDING,  # ✅ Using enum
        output_path="outputs/test_run",
    )
```

#### PromptSpec Fixture (Line 79-92)
```python
# Add optional fields for completeness:
@pytest.fixture
def sample_prompt_spec(temp_dir):
    return PromptSpec(
        id="test_ps_123",
        name="test_scene",
        prompt="A futuristic city",
        negative_prompt="blurry, dark",
        input_video_path=str(temp_dir / "test_video.mp4"),
        control_inputs={
            "depth": str(temp_dir / "depth.mp4"),
            "segmentation": str(temp_dir / "segmentation.mp4"),
        },
        timestamp=datetime.now().isoformat(),
        is_upsampled=False,           # ✅ Add optional field
        parent_prompt_text=None,      # ✅ Add optional field
    )
```

#### Factory Fixture (Line 185-189)
```python
# Fix create_test_spec factory:
def _create_spec(spec_type="prompt", **kwargs):
    # ... existing code ...
    else:  # run spec
        spec = RunSpec(
            id=kwargs.get("id", "test_rs_001"),
            prompt_id=kwargs.get("prompt_id", "test_ps_001"),  # ✅ Fix field name
            name=kwargs.get("name", "test_run"),               # ✅ Add required field
            control_weights=kwargs.get("control_weights", {}),
            parameters=kwargs.get("parameters", {}),
            timestamp=kwargs.get("timestamp", datetime.now().isoformat()),
            execution_status=kwargs.get("execution_status", ExecutionStatus.PENDING),  # ✅ Use enum
            output_path=kwargs.get("output_path", None),
        )
```

### 1.2 Fix Inline Schema Usage

#### Files to Fix:
1. `tests/integration/test_workflow_orchestration.py` (lines 117, 200)
2. `tests/unit/prompts/test_cosmos_converter.py`
3. `tests/integration/test_upsample_workflow.py`
4. `tests/integration/test_upsample_integration.py`
5. `tests/system/test_end_to_end_pipeline.py`
6. `tests/properties/test_invariants.py`

#### Search and Replace Pattern:
```bash
# Find all RunSpec creations
grep -r "RunSpec(" tests/ --include="*.py" | grep -v conftest

# Fix each occurrence:
# - prompt_spec_id → prompt_id
# - Add name field
# - execution_status string → ExecutionStatus enum
# - guidance_scale → guidance
```

### 1.3 Fix Method Name Issues

#### WorkflowOrchestrator.check_status()
```python
# Find usage:
grep -r "check_status" tests/

# Likely renamed to one of:
# - get_status()
# - monitor_status()
# - status()
# Or removed entirely - check WorkflowOrchestrator class
```

### 1.4 Validation Commands

```bash
# After fixes, run these commands to validate:

# 1. Check schema tests pass
pytest tests/unit/prompts/test_schemas.py -v

# 2. Check fixtures work
pytest tests/conftest.py::sample_prompt_spec -v
pytest tests/conftest.py::sample_run_spec -v

# 3. Run integration tests
pytest tests/integration/test_workflow_orchestration.py -v --tb=short

# 4. Check for remaining schema errors
pytest tests/ -k "RunSpec or PromptSpec" --tb=line
```

---

## Phase 2: Mock Reduction Strategy (Days 2-3)
*Estimated Time: 2 days*

### 2.1 Identify Boundary vs Internal Mocks

#### External Boundaries (KEEP mocked):
```python
# These should remain mocked:
- SSHManager (network boundary)
- Docker API calls (system boundary)
- SFTP operations (network boundary)
- AI/LLM services (external service)
- File system operations (sometimes)
```

#### Internal Components (REMOVE mocks):
```python
# These should use real implementations:
- PromptSpecManager
- RunSpecManager
- SchemaUtils
- DirectoryManager
- CommandBuilder
- All validation logic
- All data transformation logic
```

### 2.2 Refactor Test Files

#### Priority Order for Refactoring:
1. **test_workflow_orchestration.py** (highest impact)
2. **test_prompt_spec_manager.py**
3. **test_run_spec_manager.py**
4. **test_docker_executor.py**
5. **test_file_transfer.py**

#### Refactoring Pattern:

```python
# BEFORE (Over-mocked):
def test_workflow(mock_config, mock_ssh, mock_docker, mock_transfer):
    orchestrator = WorkflowOrchestrator()
    orchestrator.ssh_manager = mock_ssh
    orchestrator.docker_executor = mock_docker
    orchestrator.file_transfer = mock_transfer

    # Only tests method calls, not actual behavior
    orchestrator.run_inference(spec)
    mock_docker.run_inference.assert_called_once()

# AFTER (Properly mocked):
def test_workflow(temp_dir):
    # Create real orchestrator with real internal components
    orchestrator = WorkflowOrchestrator(config_path=temp_dir / "config.toml")

    # Mock ONLY external boundaries
    with patch.object(orchestrator.ssh_manager, 'execute_command') as mock_ssh:
        mock_ssh.return_value = (0, "Success", "")

        # Test actual behavior
        result = orchestrator.run_inference(spec)

        # Assert on outcomes, not implementation
        assert result.status == ExecutionStatus.SUCCESS
        assert (temp_dir / "outputs").exists()
```

### 2.3 Create Test Doubles Strategy

#### 1. Fakes for Complex External Systems
```python
class FakeSSHManager:
    """Fake SSH that simulates behavior without network"""
    def __init__(self):
        self.commands_executed = []
        self.files_transferred = []

    def execute_command(self, cmd, timeout=None):
        self.commands_executed.append(cmd)
        # Simulate real responses based on command
        if "docker run" in cmd:
            return (0, "Container started", "")
        return (0, "", "")
```

#### 2. Builders for Test Data
```python
class PromptSpecBuilder:
    """Builder for creating test PromptSpecs"""
    def __init__(self):
        self.spec = self._default_spec()

    def with_prompt(self, prompt):
        self.spec.prompt = prompt
        return self

    def with_video(self, path):
        self.spec.input_video_path = path
        return self

    def build(self):
        return self.spec
```

---

## Phase 3: Coverage Improvement Plan (Days 4-7)
*Estimated Time: 4 days*

### 3.1 Priority Components for Coverage

| Component | Current | Target | Priority | Approach |
|-----------|---------|--------|----------|----------|
| smart_naming.py | 8.20% | 80% | HIGH | Add unit tests for name generation |
| prompt_manager.py | 12.90% | 85% | HIGH | Test all CRUD operations |
| workflow_orchestrator.py | 13.66% | 90% | CRITICAL | Integration tests with fakes |
| upsample_integration.py | 11.32% | 75% | MEDIUM | Test upsampling workflow |

### 3.2 Test Coverage Strategy

#### For Each Low-Coverage Component:

1. **Identify Critical Paths**
   ```python
   # List all public methods
   # Identify happy paths
   # Identify error paths
   # Identify edge cases
   ```

2. **Write Behavior Tests**
   ```python
   def test_smart_naming_generates_descriptive_name():
       """Test that smart naming produces meaningful names"""
       namer = SmartNaming()
       name = namer.generate_name("A sunset over mountains")

       assert "sunset" in name.lower() or "mountain" in name.lower()
       assert len(name) < 50
       assert name.replace("_", "").isalnum()
   ```

3. **Add Edge Case Tests**
   ```python
   def test_smart_naming_handles_empty_prompt():
       """Test graceful handling of empty input"""
       namer = SmartNaming()
       name = namer.generate_name("")

       assert name == "unnamed_prompt"
   ```

### 3.3 Coverage Measurement

```bash
# Run coverage for specific modules
pytest tests/ --cov=cosmos_workflow.workflows.workflow_orchestrator --cov-report=term-missing

# Generate HTML report
pytest tests/ --cov=cosmos_workflow --cov-report=html

# Focus on uncovered lines
pytest tests/ --cov=cosmos_workflow --cov-report=term-missing | grep -E "^cosmos_workflow"
```

---

## Phase 4: Test Isolation Fixes (Day 8)
*Estimated Time: 1 day*

### 4.1 Resource Management

#### Replace setup/teardown with fixtures:
```python
# BEFORE (Can leak resources):
def setup_method(self):
    self.temp_dir = tempfile.mkdtemp()

def teardown_method(self):
    if self.temp_dir and os.path.exists(self.temp_dir):
        shutil.rmtree(self.temp_dir)

# AFTER (Guaranteed cleanup):
@pytest.fixture
def test_workspace(tmp_path):
    """Provides isolated workspace for each test"""
    workspace = tmp_path / "test_workspace"
    workspace.mkdir()
    yield workspace
    # Automatic cleanup by pytest
```

### 4.2 Test Independence

#### Ensure tests don't affect each other:
```python
# Add to conftest.py
@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset any singleton state between tests"""
    yield
    # Reset any global state here
    ConfigManager._instance = None
```

### 4.3 Parallel Test Execution

```bash
# Enable parallel execution
pip install pytest-xdist

# Run tests in parallel
pytest tests/ -n auto

# Fix any tests that fail in parallel
# Usually due to:
# - Shared file paths
# - Port conflicts
# - Global state
```

---

## Phase 5: Contract Testing (Day 9)
*Estimated Time: 1 day*

### 5.1 Define Contracts for External Systems

```python
# tests/contracts/test_ssh_contract.py
class TestSSHContract:
    """Verify SSH interface contract"""

    def test_execute_command_returns_tuple(self, ssh_manager):
        """SSH execute must return (exit_code, stdout, stderr)"""
        result = ssh_manager.execute_command("echo test")

        assert isinstance(result, tuple)
        assert len(result) == 3
        assert isinstance(result[0], int)
        assert isinstance(result[1], str)
        assert isinstance(result[2], str)
```

### 5.2 Docker Contract Tests

```python
# tests/contracts/test_docker_contract.py
class TestDockerContract:
    """Verify Docker executor contract"""

    def test_run_inference_contract(self, docker_executor):
        """Docker run must accept RunSpec and return status"""
        spec = create_valid_run_spec()
        result = docker_executor.run_inference(spec)

        assert hasattr(result, 'exit_code')
        assert hasattr(result, 'output_path')
        assert hasattr(result, 'logs')
```

---

## Phase 6: Documentation & Maintenance (Day 10)
*Estimated Time: 1 day*

### 6.1 Test Documentation

Create `tests/README.md`:
```markdown
# Test Suite Guide

## Running Tests
- Unit tests: `pytest tests/unit`
- Integration: `pytest tests/integration`
- Full suite: `pytest tests/`

## Test Categories
- unit/ - Isolated component tests
- integration/ - Multi-component tests
- contracts/ - External system contracts
- properties/ - Invariant testing

## Writing Tests
1. Mock only external boundaries
2. Test behavior, not implementation
3. Use fixtures for setup/teardown
4. Ensure test independence
```

### 6.2 CI/CD Integration

```yaml
# .github/workflows/test.yml
name: Test Suite
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
      - name: Install dependencies
        run: pip install -r requirements-dev.txt
      - name: Run tests
        run: pytest tests/ --cov=cosmos_workflow --cov-fail-under=80
```

---

## Implementation Timeline

### Week 1 (Days 1-5)
- **Day 1**: Phase 1 - Schema fixes ✅
- **Day 2-3**: Phase 2 - Mock reduction
- **Day 4-5**: Phase 3 - Coverage improvement (part 1)

### Week 2 (Days 6-10)
- **Day 6-7**: Phase 3 - Coverage improvement (part 2)
- **Day 8**: Phase 4 - Test isolation
- **Day 9**: Phase 5 - Contract testing
- **Day 10**: Phase 6 - Documentation

---

## Success Metrics

### Quantitative Metrics
- [ ] All tests pass without schema errors
- [ ] Core components >80% coverage
- [ ] <30% of tests use mocks
- [ ] All tests pass in parallel execution
- [ ] CI/CD pipeline running

### Qualitative Metrics
- [ ] Tests catch real bugs
- [ ] Tests are maintainable
- [ ] New developers understand tests
- [ ] Tests run fast (<30s for unit, <3min for all)

---

## Quick Wins (Can do immediately)

1. **Fix conftest.py** (15 minutes)
2. **Fix inline RunSpec/PromptSpec** (30 minutes)
3. **Run tests to verify** (10 minutes)
4. **Remove one over-mocked test** (30 minutes)
5. **Add one behavior test** (30 minutes)

---

## Risk Mitigation

### Potential Issues
1. **Risk**: Tests break when reducing mocks
   - **Mitigation**: Fix incrementally, one test at a time

2. **Risk**: Coverage drops initially
   - **Mitigation**: Expected - real coverage is better than fake

3. **Risk**: Tests become slower
   - **Mitigation**: Use test categories, parallelize

---

## Appendix: Helper Scripts

### Find Mock Usage
```bash
#!/bin/bash
# find_mocks.sh
echo "Files using mocks:"
grep -r "Mock\|patch" tests/ --include="*.py" | cut -d: -f1 | sort -u | wc -l

echo "Total mock occurrences:"
grep -r "Mock\|patch" tests/ --include="*.py" | wc -l
```

### Coverage Report
```bash
#!/bin/bash
# coverage_report.sh
pytest tests/ --cov=cosmos_workflow --cov-report=term-missing \
  --cov-report=html --cov-report=json
echo "Report generated in htmlcov/index.html"
```

### Schema Validation
```bash
#!/bin/bash
# validate_schemas.sh
python -c "
from cosmos_workflow.prompts.schemas import PromptSpec, RunSpec
from tests.conftest import sample_prompt_spec, sample_run_spec
print('Schema validation successful')
"
```

---

*This plan is designed to be executed incrementally. Start with Phase 1 for immediate fixes, then proceed through phases as time permits.*
