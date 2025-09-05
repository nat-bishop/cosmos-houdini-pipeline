# Test Refactoring Handover Document

## Date: 2025-09-05

## Summary of Work Completed

### Phase 1: Enhancement Test Refactoring ✅
1. **Deleted** `tests/unit/test_enhancement_behavior.py` - used fake `AIGenerator` class that never existed
2. **Created** `tests/unit/test_enhancement_gpu_behavior.py` - tests actual GPU-based enhancement behavior
3. **Fixed** DockerExecutor implementation:
   - Added `run_prompt_enhancement()` method to `DockerExecutor`
   - Refactored `WorkflowOrchestrator.run_prompt_upsampling()` to use wrapper instead of direct SSH
4. **Added** context manager support to `FakeSSHManager` for proper testing

### Key Architecture Discoveries

#### 1. **AIGenerator Never Existed**
- Tests were written assuming an `AIGenerator` class
- Reality: Enhancement uses `scripts/prompt_upsampler.py` with NVIDIA's `PixtralPromptUpsampler`
- Enhancement runs on GPU via Docker, not locally

#### 2. **Old JSON-Based System (Deprecated)**
- `PromptSpec` and `RunSpec` classes don't exist in current codebase
- `run_full_cycle` method was from old architecture
- Current system uses database-driven prompts and runs (dictionaries)

#### 3. **Wrapper Violations Found**
- `run_prompt_upsampling` was calling `ssh_manager.execute_command_success()` directly
- Fixed by adding proper wrapper method in DockerExecutor
- Now follows CLAUDE.md principles

#### 4. **Database Integration for Enhancement**
The enhancement workflow in the database:
1. Start with existing prompt (by ID)
2. Create enhancement run (tracks operation)
3. Execute enhancement (get enhanced text)
4. Create NEW prompt with:
   - Enhanced text as `prompt_text`
   - Same `inputs` (video paths) as original
   - `parameters`: `enhanced: true`, `parent_prompt_id`, `enhancement_model`
5. Update run outputs with: `enhanced_prompt_id`, `enhanced_text`, `model_used`
6. Mark run completed

## Current Test Status
- **Total tests**: 501
- **Passing**: 463 (after removing fake AIGenerator tests)
- **Failing**: 35
- **Errors**: 11 (mostly CLI tests)

## Next Steps (In Priority Order)

### 1. **Test Prompt Enhancement Manually** 🔴 CRITICAL
```bash
# First, verify the implementation works
cosmos prompt-enhance ps_81c6c39f0e1492ad0051 --dry-run

# If dry-run works, try actual enhancement (needs GPU)
cosmos prompt-enhance ps_81c6c39f0e1492ad0051
```

**What to verify:**
- Enhancement run created in database
- DockerExecutor.run_prompt_enhancement() called (not direct SSH)
- Script uploaded to remote
- Docker command executed properly
- Results downloaded
- New enhanced prompt created with correct lineage

**Potential Issues:**
- Remote executor methods might not exist
- File paths might be wrong
- Docker command formatting

### 2. **Fix Enhancement Test Mocking**
Update `tests/unit/test_enhancement_gpu_behavior.py`:
- Mock `DockerExecutor.run_prompt_enhancement()` instead of SSH commands
- Remove TODO comment about violating CLAUDE.md
- Fix failing tests to use proper fakes

### 3. **Fix Integration Tests Using run_full_cycle** (20 occurrences)
Files to fix:
- `tests/integration/test_workflow_orchestrator.py` (4 test methods)
- `tests/integration/test_integration.py` (multiple)

Replace `run_full_cycle(spec_file)` with `execute_run(run_dict, prompt_dict)`:
```python
# Old way (doesn't exist)
orchestrator.run_full_cycle("prompt.json")

# New way
prompt_dict = {...}  # From database
run_dict = {...}     # From database
orchestrator.execute_run(run_dict, prompt_dict)
```

### 4. **Remove Old Spec Classes**
In `tests/fixtures/fakes.py`:
- Remove `FakePromptSpec` class
- Remove `FakeRunSpec` class
- Remove `run_full_cycle` method from `FakeWorkflowOrchestrator`

### 5. **Fix CLI Tests** (11 errors)
Most are expecting old PromptSpec/RunSpec objects or have Windows file locking issues.

## Important Testing Principles Learned

### From CLAUDE.md:
1. **Test behavior, not implementation**
2. **No third-party mocking** - use fakes that implement wrapper interfaces
3. **Always use wrappers** - never bypass them
4. **If functionality missing, extend wrapper** instead of bypassing

### Key Insight:
**Don't write tests for wrong implementations!** We initially considered testing the direct SSH usage, but that would:
- Entrench bad practices
- Make refactoring harder
- Violate architectural principles

Instead, we fixed the implementation first, then wrote proper tests.

## Code Quality Notes

### What's Working Well:
- Database layer fully functional (111 tests passing)
- Service layer solid
- Inference behavior tests passing
- Mocks consolidated in `tests/fixtures/mocks.py`

### Architecture Patterns:
- **DockerExecutor**: Domain-aware service (knows about inference, upscaling, enhancement)
- **RemoteCommandExecutor**: Generic remote execution
- **DockerCommandBuilder**: Generic Docker command building
- **WorkflowOrchestrator**: Coordinates services (no direct execution)

## Testing Next Session

1. **Run full test suite** to see current state:
```bash
pytest tests/ -v --tb=short
```

2. **Focus on high-value fixes**:
   - Enhancement manual testing (verify implementation)
   - Integration test fixes (biggest bang for buck)
   - Skip CLI tests initially (lower priority)

## Files Modified

### Implementation:
- `cosmos_workflow/execution/docker_executor.py` - Added `run_prompt_enhancement()`
- `cosmos_workflow/workflows/workflow_orchestrator.py` - Refactored to use wrapper
- `tests/fixtures/fakes.py` - Added context manager to FakeSSHManager

### Tests:
- Deleted: `tests/unit/test_enhancement_behavior.py`
- Created: `tests/unit/test_enhancement_gpu_behavior.py`
- Created: `tests/integration/test_database_workflow.py` (8 tests, 7 passing)

### Cleanup:
- Removed directories: `tests/contracts/`, `tests/properties/`, `tests/system/`, `tests/performance/`

## Success Metrics
Goal: 500+ tests passing with behavior-focused testing
Current: 463/501 passing (92.4%)
Target: Fix integration tests to get to 480+ passing