# Test Suite Improvement Plan - Handover Document
**Date:** 2025-09-05
**Author:** Previous Session
**Status:** Ready for Implementation
**Priority:** HIGH - Must complete before Chunk 5

## Executive Summary

After completing Chunks 1-4 of the service layer refactoring, we have a working production system but a broken test suite. This document outlines a clear plan to fix the tests properly, following Python's Zen principles of simplicity and clarity.

**Key Decision:** NO backward compatibility. Clean break from the old system.

## Current State Analysis

### What's Working ✅
- **Production code:** Fully functional with database-first approach
- **Core tests:** 111/111 passing (database & service layers)
- **Test isolation:** All unit tests properly mock external services (no real GPU/SSH)

### What's Broken ❌
- **74 failing tests** that expect the old JSON-based system
- **Test stubs deleted** but 4 files still try to import them
- **Old interface calls:** Tests calling `orchestrator.run()` which is now `execute_run()`
- **0% CLI coverage** despite fully implemented CLI commands

### Critical Issues Found

1. **Coupling Problems:**
   - Tests are testing implementation details, not behavior
   - Tests break when internal structure changes
   - Example: Tests expect `PromptSpec` objects instead of database dicts

2. **Duplicate Code:**
   - Mock fixtures repeated across multiple test files
   - Each test recreates similar SSH/Docker/FileTransfer mocks
   - No single source of truth for test mocks

3. **Directory Clutter:**
   - 7 test directories but only 3 actively used
   - `contracts/`, `properties/`, `system/`, `performance/` rarely used
   - Adds complexity without value

## Implementation Plan

### Phase 1: Delete Old Tests (2 hours)

**Files to DELETE completely:**
```
tests/unit/workflows/test_workflow_orchestrator.py (430 lines)
tests/integration/test_upsample_integration.py
tests/integration/test_upsample_workflow.py
tests/integration/test_workflow_orchestration_simple.py
tests/unit/workflows/test_upsample_smart_naming.py
```

**Why delete?** They test the OLD system that no longer exists. No point fixing them.

### Phase 2: Consolidate Mocks (1 hour)

**Create:** `tests/fixtures/mocks.py`
```python
"""Single source of truth for all test mocks.
No duplication, easy to maintain."""

def create_mock_ssh_manager():
    """Standard SSH mock for all tests."""
    ssh = MagicMock()
    ssh.__enter__ = MagicMock(return_value=ssh)
    ssh.__exit__ = MagicMock(return_value=None)
    ssh.execute_command.return_value = (0, "Success", "")
    return ssh

def create_mock_docker_executor():
    """Standard Docker mock for all tests."""
    docker = MagicMock()
    docker.run_inference.return_value = (0, "Inference complete", "")
    docker.run_upscaling.return_value = (0, "Upscaling complete", "")
    docker.get_docker_status.return_value = {"status": "ready"}
    return docker

def create_mock_file_transfer():
    """Standard file transfer mock for all tests."""
    transfer = MagicMock()
    transfer.upload_file.return_value = True
    transfer.download_results.return_value = {"success": True}
    return transfer
```

**Update:** `conftest.py` to use these instead of duplicating

### Phase 3: Write Behavior Tests (3 hours)

**New test files to create:**

1. **`tests/unit/test_inference_behavior.py`**
   - Test that inference uploads files, runs Docker, downloads results
   - NOT how it stores data internally

2. **`tests/unit/test_enhancement_behavior.py`**
   - Test that enhancement creates run, calls AI, creates new prompt
   - NOT what objects it uses

3. **`tests/integration/test_database_workflow.py`**
   - Test complete flow: create prompt → run → query
   - Using actual database (in-memory)

**Test Pattern Example:**
```python
def test_inference_executes_gpu_workflow():
    """Test BEHAVIOR: inference should execute on GPU.

    This will still pass even if internal implementation changes.
    """
    # Given
    prompt = {"id": "ps_123", "prompt_text": "A city"}
    run = {"id": "rs_456", "status": "pending"}

    # When
    orchestrator = WorkflowOrchestrator()
    result = orchestrator.execute_run(run, prompt)

    # Then
    assert mock_ssh.connect.called  # Connected to GPU
    assert mock_docker.run_inference.called  # Ran inference
    assert "output_path" in result  # Got results
```

### Phase 4: Clean Directory Structure (30 mins)

**Delete these directories:**
- `tests/contracts/` - Only 1 file, not used
- `tests/properties/` - Empty
- `tests/system/` - Only 1 file, not used
- `tests/performance/` - Only 1 file, not used

**Final structure:**
```
tests/
├── fixtures/      # Shared test fixtures and mocks
├── integration/   # Integration tests
└── unit/         # Unit tests
```

### Phase 5: Fix Module Organization (Optional - 1 hour)

**Current issue:** `cosmos_workflow/local_ai/` mixes different concerns

**Split into:**
- `cosmos_workflow/validation/` - Sequence validation
- `cosmos_workflow/ai_tools/` - AI generation tools

## Success Criteria

✅ All tests pass (500+ tests)
✅ CLI coverage > 80%
✅ Total coverage > 60%
✅ No test stubs or compatibility layers
✅ Tests don't break when refactoring internals
✅ Clean, simple directory structure

## Testing Principles Going Forward

### DO ✅
- Test behavior, not implementation
- Use database fixtures for real objects
- Mock at boundaries (SSH, Docker, files)
- Keep tests simple and readable
- One assertion per test when possible

### DON'T ❌
- Test internal object structure
- Create compatibility layers
- Mock database operations in unit tests
- Write tests for test infrastructure
- Use complex test hierarchies

## Verification Commands

After each phase, run:
```bash
# Check no regressions
pytest tests/unit/services tests/unit/database -x

# Check fixed tests
pytest tests/unit -x

# Monitor coverage
pytest --cov=cosmos_workflow --cov-report=term

# Check for import errors
python -c "import tests.conftest"
```

## Example: Good vs Bad Tests

### Bad Test (Implementation-focused) ❌
```python
def test_creates_prompt_spec_object():
    spec = PromptSpec(id="ps_123", name="test")
    assert spec.id == "ps_123"
    assert hasattr(spec, 'to_dict')
    # Breaks when we switch to database
```

### Good Test (Behavior-focused) ✅
```python
def test_creates_prompt_with_unique_id():
    prompt = service.create_prompt(
        model_type="transfer",
        prompt_text="A city"
    )
    assert prompt["id"].startswith("ps_")
    assert len(prompt["id"]) == 36
    # Still passes after database migration
```

## Next Session Instructions

1. **Start here:** Delete the 5 old test files listed in Phase 1
2. **Then:** Create `tests/fixtures/mocks.py` with consolidated mocks
3. **Important:** Don't add ANY compatibility code - let tests fail loudly
4. **Focus:** Test behavior that users care about, not internal details
5. **Remember:** Simple is better than complex (Zen of Python)

## Risk Mitigation

- **Risk:** Deleting tests loses coverage
- **Mitigation:** New behavior tests provide better coverage

- **Risk:** Breaking working tests
- **Mitigation:** Run core tests after each change

- **Risk:** Over-engineering the solution
- **Mitigation:** Keep it simple - no abstractions unless needed

## Timeline

**Total: 6.5 hours**
- Phase 1: 2 hours
- Phase 2: 1 hour
- Phase 3: 3 hours
- Phase 4: 30 minutes
- Phase 5: Optional

Can be completed in one focused session.

---

*Remember: The goal is simple, maintainable tests that verify the system works, not how it works internally.*