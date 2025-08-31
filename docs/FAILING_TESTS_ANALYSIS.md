# Failing Tests Analysis

## Summary
- **Total Failing**: 30 tests
- **Can Fix Now**: ~12 tests (SFTP and simple import issues)
- **Need Refactoring**: ~12 tests (outdated integration tests)
- **Need Infrastructure**: 6 tests (system tests requiring GPU/Docker)

## Categories of Failures

### 1. SFTP Tests (9 tests) - ✅ CAN FIX NOW
**Location**: `tests/integration/test_sftp_workflow.py`

**Issue**: Mock configuration doesn't match current implementation
- Tests mock `ssh_client.open_sftp()`
- Code uses `ssh_manager.get_sftp()` context manager

**Fix Applied**: Updated mock_ssh_manager to properly mock get_sftp()
```python
mock_ssh_manager.get_sftp.return_value.__enter__ = lambda self: mock_sftp_client
```

**Status**: First test fixed, others need same pattern applied

### 2. Workflow Orchestration Tests (10 tests) - ❌ NEED MAJOR REFACTORING
**Location**:
- `tests/integration/test_workflow_orchestration.py` (6 tests)
- `tests/integration/test_workflow_orchestration_refactored.py` (5 tests)

**Issue**: Tests expect methods that no longer exist
```python
AttributeError: <class 'PromptSpecManager'> does not have the attribute 'load_by_id'
```

**Why Can't Fix Now**:
- Architecture has changed significantly
- Methods like `load_by_id` were removed
- Would require rewriting tests from scratch
- Not worth effort for solo project

### 3. Performance Tests (3 tests) - ✅ PARTIALLY FIXABLE
**Location**: `tests/performance/test_gpu_and_perf.py`

#### a. Import Error - ✅ FIXED
```python
NameError: name 'np' is not defined
```
**Fix**: Added `import numpy as np`

#### b. CUDA Tests - ❌ NEED CUDA
- `test_torch_determinism` - Requires torch with CUDA
- `test_deterministic_fixture_works` - Requires CUDA device

**Why Can't Fix**: No CUDA available on development machine

### 4. System Tests (6 tests) - ❌ NEED INFRASTRUCTURE
**Location**:
- `tests/system/test_end_to_end_pipeline.py` (2 tests)
- `tests/system/test_performance.py` (4 tests)

**Issues**:
- Require actual Docker daemon running
- Need SSH connection to real server
- Expect NVIDIA Cosmos model to be available
- Need GPU for inference

**Why Can't Fix Now**:
- These are production smoke tests
- Require full infrastructure setup
- Not meant for local development

### 5. Other Integration Tests (2 tests) - ❌ MIXED
**Location**:
- `tests/integration/test_prompt_smart_naming.py` - Outdated mocking
- `tests/integration/test_upsample_integration.py` - Needs cosmos_transfer1 module

## Recommended Actions

### Immediate Fixes (Do Now)
1. ✅ Fix remaining SFTP tests (apply same mock pattern)
2. ✅ Fix numpy import in performance tests
3. ✅ Mark CUDA-requiring tests with `@pytest.mark.skipif(not torch.cuda.is_available())`

### Don't Fix (Not Worth Effort)
1. ❌ Workflow orchestration integration tests - Architecture too different
2. ❌ System tests - Need production environment
3. ❌ CUDA performance tests - Hardware dependent

### Future Considerations
1. Remove or archive outdated integration tests
2. Create new integration tests if multi-dev collaboration needed
3. Set up docker-compose for integration testing (if needed)

## Test Commands

### Run Only Working Tests
```bash
# Unit tests only (all pass)
pytest tests/unit/ -q

# Skip optional tests
pytest tests/ -m "not optional" -q

# Run with coverage
pytest tests/unit/ --cov=cosmos_workflow
```

### Run Specific Categories
```bash
# SFTP tests (after fixes)
pytest tests/integration/test_sftp_workflow.py -v

# Performance tests (skip CUDA)
pytest tests/performance/ -m "not cuda" -v

# System tests (need infrastructure)
pytest tests/system/ -v  # Will fail without setup
```

## Conclusion

For a **solo professional project**, focus on:
1. **Unit tests** - 436 passing, good coverage
2. **Fix simple issues** - SFTP mocks, imports
3. **Skip infrastructure tests** - Not needed for development

The failing integration/system tests don't impact development workflow and can be ignored until production deployment is needed.
