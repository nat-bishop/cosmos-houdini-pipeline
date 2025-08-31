# TODO: Test Fixes for Next Session

## 🎯 Priority: Fix Schema Mismatches in Tests

### Context
We successfully reverted tests from using fakes to using real implementations with mocked boundaries. This means tests will actually catch bugs now. However, the tests are failing because the codebase evolved and the test fixtures haven't been updated to match.

## 📋 Tasks to Complete

### 1. Fix RunSpec Schema in conftest.py (HIGH PRIORITY)
**File:** `tests/conftest.py`
**Line:** ~98

**Current (broken):**
```python
@pytest.fixture
def sample_run_spec(sample_prompt_spec):
    return RunSpec(
        id="test_rs_456",
        prompt_spec_id=sample_prompt_spec.id,  # ❌ WRONG - field renamed
        # Missing 'name' field                 # ❌ WRONG - field required
        control_weights={"depth": 0.3, "segmentation": 0.4},
        parameters={"num_steps": 35, "guidance_scale": 8.0, "seed": 42},
        execution_status="pending",
        output_path="outputs/test_run",
        timestamp=datetime.now().isoformat(),
    )
```

**Fix to:**
```python
@pytest.fixture
def sample_run_spec(sample_prompt_spec):
    return RunSpec(
        id="test_rs_456",
        prompt_id=sample_prompt_spec.id,       # ✅ Correct field name
        name="test_run",                       # ✅ Add required field
        control_weights={"depth": 0.3, "segmentation": 0.4},
        parameters={"num_steps": 35, "guidance_scale": 8.0, "seed": 42},
        execution_status="pending",
        output_path="outputs/test_run",
        timestamp=datetime.now().isoformat(),
    )
```

### 2. Check for Other Schema Mismatches (MEDIUM PRIORITY)
Run tests and fix any other schema issues:
```bash
# Run integration tests to find schema issues
pytest tests/integration/test_workflow_orchestration.py -v

# Look for errors like:
# - "unexpected keyword argument"
# - "missing required argument"
# - "no attribute"
```

Common schema changes to look for:
- Field renames (like prompt_spec_id → prompt_id)
- New required fields (like 'name')
- Removed fields
- Type changes

### 3. Fix Method Name Changes (MEDIUM PRIORITY)
Some methods may have been renamed. Look for AttributeError in tests:
- `_get_video_directories` might not exist anymore
- `_generate_control_spec` might have changed
- Check if these are now private or renamed

### 4. Verify Tests Actually Work (HIGH PRIORITY)
After fixing schemas, verify the tests:
```bash
# Run the critical test files we fixed
pytest tests/integration/test_workflow_orchestration.py -v
pytest tests/integration/test_sftp_workflow.py -v
pytest tests/unit/execution/test_docker_executor.py -v
pytest tests/performance/test_gpu_and_perf.py::test_workflow_simulation_performance -v
```

## ✅ What's Already Fixed

1. **Reverted fake-based tests** - Tests now use real implementations
2. **Fixed import issues** - FileTransferManager → FileTransferService
3. **Fixed performance test** - Now tests real WorkflowOrchestrator
4. **Removed misleading docs** - Deleted behavior-testing guides

## 🔍 Quick Diagnostic Commands

```bash
# Find all RunSpec usage in tests
grep -r "RunSpec(" tests/ --include="*.py"

# Find all PromptSpec usage in tests
grep -r "PromptSpec(" tests/ --include="*.py"

# Check what the actual schemas look like
cat cosmos_workflow/prompts/schemas.py | grep -A 10 "class RunSpec"
cat cosmos_workflow/prompts/schemas.py | grep -A 10 "class PromptSpec"
```

## 💡 Why This Matters

**Current State:** Tests use real implementations but fail due to schema mismatches
**Goal:** Tests pass and actually verify your code works
**Benefit:** You can code fast with AI and trust tests to catch bugs

## 📝 For Claude in Next Session

When you start a new session, tell Claude:
1. "Check TODO_TOMORROW_TEST_FIXES.md for test fixes needed"
2. "Tests were reverted from fakes to real implementations but have schema mismatches"
3. "Priority is fixing conftest.py RunSpec to match current schema"

## Estimated Time
- **Schema fixes:** 15-30 minutes
- **Verification:** 10 minutes
- **Total:** 30-45 minutes

## Success Criteria
- [ ] conftest.py fixtures match current schemas
- [ ] Integration tests pass (or at least don't fail on schema issues)
- [ ] Performance test runs without errors
- [ ] Tests actually test real code (not fakes)

---
*Note: The testing approach is now correct (real implementations with mocked boundaries). We just need to update the test fixtures to match the evolved codebase.*
