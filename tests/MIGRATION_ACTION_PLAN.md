# Test Suite Migration Action Plan
*Start here for systematic test improvement*

## 🎯 Mission
Transform 53 test files from mock-heavy implementation testing to behavior-driven testing using fakes. The infrastructure is ready - we just need to apply it systematically.

## 📊 Current State (as of 2025-08-31)
- **Total test files**: 55
- **Files already refactored**: 2 ✅
  - `tests/integration/test_workflow_orchestration_refactored.py`
  - `tests/unit/execution/test_docker_executor_refactored.py`
- **Files needing refactoring**: 53 ❌
- **Mock occurrences to eliminate**: ~1,800
- **assert_called patterns to remove**: 157

## 🛠️ Available Infrastructure (Already Created)

### 1. Fake Implementations
**Location**: `tests/fixtures/fakes.py`
- `FakeSSHManager` - Replace SSH mocks
- `FakeFileTransferService` - Replace file transfer mocks
- `FakeDockerExecutor` - Replace Docker mocks
- `FakeWorkflowOrchestrator` - Replace orchestrator mocks
- `FakePromptSpec/FakeRunSpec` - Test data objects

### 2. Reference Documentation
- `tests/BEHAVIOR_TESTING_GUIDE.md` - How to write behavior tests
- `tests/TEST_SUITE_INVESTIGATION_REPORT.md` - Original problems to fix
- `tests/contracts/test_ssh_contract.py` - Example contract tests
- `tests/properties/test_invariants.py` - Example property tests

### 3. Example Refactored Files
Use these as templates:
- `test_workflow_orchestration_refactored.py` - Shows how to refactor integration tests
- `test_docker_executor_refactored.py` - Shows how to refactor unit tests

## 📋 Step-by-Step Migration Process

### For Each Test File:

#### 1. Identify Current Problems
```bash
# Check mock usage in the file
grep -c "mock\|Mock\|patch" tests/path/to/test_file.py

# Check for assert_called patterns
grep -c "assert_called\|assert_any_call" tests/path/to/test_file.py

# Run the test to ensure it passes before refactoring
python -m pytest tests/path/to/test_file.py -xvs
```

#### 2. Create Refactored Version
```python
# Create new file with _refactored suffix
# tests/path/to/test_file_refactored.py

# Import fakes instead of mocks
from tests.fixtures.fakes import FakeSSHManager, FakeDockerExecutor

# Replace mock fixtures with fake fixtures
@pytest.fixture
def fake_ssh():
    return FakeSSHManager()
```

#### 3. Transform Each Test Method

**BEFORE (Bad):**
```python
def test_workflow_execution(self):
    with patch('module.SSHManager') as mock_ssh:
        mock_ssh.return_value.execute_command.return_value = (0, "output", "")
        result = workflow.run()
        mock_ssh.return_value.execute_command.assert_called_once_with("docker run")
```

**AFTER (Good):**
```python
def test_workflow_execution(self, fake_orchestrator):
    # Execute behavior
    result = fake_orchestrator.run_inference("spec.json")

    # Verify outcomes, not calls
    assert result is True
    assert len(fake_orchestrator.docker_executor.containers_run) == 1
    assert fake_orchestrator.docker_executor.inference_results["test"]["status"] == "success"
```

#### 4. Test the Refactored Version
```bash
# Run new test to ensure it works
python -m pytest tests/path/to/test_file_refactored.py -xvs

# Run both to ensure compatibility
python -m pytest tests/path/to/test_file*.py -xvs
```

#### 5. Replace Original When Ready
```bash
# Backup original
mv tests/path/to/test_file.py tests/path/to/test_file_old.py

# Use refactored version
mv tests/path/to/test_file_refactored.py tests/path/to/test_file.py

# Test again
python -m pytest tests/path/to/test_file.py -xvs

# If successful, remove backup
rm tests/path/to/test_file_old.py
```

## 🎯 Priority Order for Migration

### Phase 1: Highest Impact (Week 1)
Fix the most mock-heavy files first for maximum improvement:

1. **tests/integration/test_sftp_workflow.py** (8 failures, heavy mocking)
   - Current: String/Path issues, wrong method signatures
   - Fix: Use FakeFileTransferService

2. **tests/integration/test_video_pipeline.py** (7 failures, wrong signatures)
   - Current: Wrong CosmosVideoConverter constructor
   - Fix: Use proper method signatures from actual classes

3. **tests/integration/test_workflow_orchestration.py** (8 errors, fixture issues)
   - Current: Heavy mocking of all components
   - Fix: Use FakeWorkflowOrchestrator
   - Note: Refactored version exists - just replace!

4. **tests/unit/execution/test_docker_executor.py**
   - Note: Refactored version exists - just replace!

### Phase 2: Core Components (Week 1-2)
5. **tests/unit/connection/test_ssh_manager.py**
6. **tests/unit/connection/test_file_transfer.py**
7. **tests/unit/prompts/test_prompt_manager.py**
8. **tests/unit/local_ai/test_local_ai.py**

### Phase 3: Remaining Files (Week 2)
- All other test files in order of mock usage

## ✅ Success Criteria for Each File

### Must Have:
- [ ] Zero use of `mock.assert_called*` methods
- [ ] Zero patching of internal methods
- [ ] All tests pass
- [ ] Uses fakes from `tests/fixtures/fakes.py`
- [ ] Tests verify outcomes, not implementation

### Should Have:
- [ ] Clear test names describing behavior
- [ ] Proper test isolation (no shared state)
- [ ] Uses pytest fixtures properly
- [ ] Groups related tests in classes

## 📈 How to Track Progress

### After Each File:
```bash
# Measure improvement
echo "=== PROGRESS CHECK ==="
echo "Files refactored:"
find tests -name "*_refactored.py" | wc -l

echo "Mock usage in refactored files (should be low):"
grep -c "mock\|Mock\|patch" tests/*_refactored.py 2>/dev/null | grep -v ":0$"

echo "Remaining assert_called patterns:"
grep -r "assert_called" tests/ --include="*.py" | grep -v "_refactored.py" | wc -l
```

### Run Test Coverage:
```bash
# Check coverage improvement
python -m pytest tests/ --cov=cosmos_workflow --cov-report=term-missing
```

## 🚨 Common Pitfalls to Avoid

### DON'T:
- Don't just rename mocks to fakes - actually change the testing approach
- Don't test implementation details (method calls, internal state)
- Don't use `patch` for internal components
- Don't assert on mock call counts or order

### DO:
- Test behavior and outcomes
- Use fakes that maintain contracts
- Test at system boundaries
- Verify the results, not the process

## 🔧 Tools and Commands

### Quick File Analysis:
```bash
# Show worst offenders (most mocks)
for f in tests/**/*.py; do
  count=$(grep -c "mock\|Mock\|patch" "$f" 2>/dev/null)
  echo "$count $f"
done | sort -rn | head -10
```

### Test Running:
```bash
# Test single file
python -m pytest tests/path/to/file.py -xvs

# Test with coverage
python -m pytest tests/path/to/file.py --cov=cosmos_workflow --cov-report=term-missing

# Test all refactored files
python -m pytest tests/**/*_refactored.py -xvs
```

### Validation:
```bash
# Ensure no assert_called in refactored files
grep -r "assert_called" tests/*_refactored.py
# Should return nothing
```

## 📝 Example Migration Checklist

For each file, copy this checklist:

```markdown
### File: tests/[path/to/file].py
- [ ] Current test count: ___
- [ ] Current mock count: ___
- [ ] Current assert_called count: ___
- [ ] Created _refactored version
- [ ] Replaced mocks with fakes
- [ ] Converted to behavior testing
- [ ] All tests pass
- [ ] No assert_called patterns
- [ ] Replaced original file
- [ ] Deleted backup
- [ ] Final mock count: 0
- [ ] Final assert_called count: 0
```

## 🎯 Expected Outcomes

### When Complete:
- Mock usage: 1,936 → <100 (boundary mocks only)
- assert_called: 157 → 0
- Files using fakes: 6 → 55
- Behavior-focused tests: 100%
- Tests survive refactoring: ✅

### Time Estimate:
- 1 file per 30-60 minutes
- 53 files × 45 min average = ~40 hours
- With focus: 1 week full-time or 2-3 weeks part-time

## 🚀 Start Here

1. Open this file: `tests/MIGRATION_ACTION_PLAN.md`
2. Start with Phase 1, File 1: `tests/integration/test_sftp_workflow.py`
3. Follow the step-by-step process
4. Track progress with the checklist
5. Commit after each successful file migration

## 💡 Remember

The hard work is done - infrastructure is built, patterns are established, examples exist. This is just systematic application of the proven approach. Each file you migrate makes the test suite more maintainable and refactoring-safe.

**Goal**: Transform the test suite from a refactoring impediment to a refactoring enabler.
