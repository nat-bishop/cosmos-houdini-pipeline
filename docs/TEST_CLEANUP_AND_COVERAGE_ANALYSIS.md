# Test Cleanup and Coverage Analysis

## Current Coverage: 66.93% (Unit Tests Only)

## Skipped Tests Analysis (8 tests)

### Should REMOVE (4 tests):
1. **System end-to-end tests** (2) - `test_end_to_end_pipeline.py`
   - Use non-existent `VideoProcessor` class
   - Would need complete rewrite
   - **Recommendation**: DELETE - outdated and not fixable

2. **Flaky integration test** (1) - `test_end_to_end_upsample_integration`
   - Test isolation issues
   - **Recommendation**: DELETE - unreliable

3. **AI functionality test** (1) - `test_generate_ai_description_success`
   - Complex transformers mocking
   - **Recommendation**: DELETE - too complex for value provided

### Should KEEP (4 tests):
1. **CUDA/GPU tests** (2) - `test_gpu_and_perf.py`
   - Legitimate skip when no GPU
   - **Recommendation**: KEEP - useful when GPU available

2. **Cosmos module tests** (2) - `test_upsample_integration.py`
   - Skip when cosmos_transfer1 not installed
   - **Recommendation**: KEEP - documents external dependency

## Low Coverage Areas (Priority Order)

### 1. 🔴 CRITICAL - Core Workflows (Almost No Coverage!)
```
workflows/resolution_tester.py        0.00% coverage  (95 lines uncovered)
workflows/upsample_integration.py     8.90% coverage  (107 lines uncovered)
workflows/workflow_orchestrator.py   13.66% coverage  (109 lines uncovered)
```
**Impact**: These are CORE business logic files with almost no tests!

### 2. 🟠 HIGH - Prompt Management
```
prompts/prompt_manager.py           25.81% coverage  (87 lines uncovered)
```
**Impact**: Critical for prompt handling, needs tests

### 3. 🟡 MEDIUM - CLI Commands
```
cli.py                               54.82% coverage  (185 lines uncovered)
```
**Impact**: User-facing commands partially tested

### 4. 🟡 MEDIUM - AI/Video Processing
```
local_ai/video_metadata.py          67.75% coverage  (102 lines uncovered)
prompts/cosmos_converter.py         70.52% coverage  (37 lines uncovered)
```
**Impact**: Important features but not critical path

### 5. ✅ GOOD - Well Tested Areas
```
prompts/prompt_spec_manager.py      100.00% coverage
execution/command_builder.py         98.43% coverage
utils/smart_naming.py                98.36% coverage
utils/workflow_utils.py              98.42% coverage
```

## Recommended Actions

### Immediate (Remove Outdated Tests)
```bash
# Remove outdated system tests
rm tests/system/test_end_to_end_pipeline.py

# Remove flaky integration test
# Edit test_upsample_integration.py to remove test_end_to_end_upsample_integration

# Remove complex AI mock test
# Edit test_ai_functionality.py to remove test_generate_ai_description_success
```

### Priority 1: Add Tests for Core Workflows
The workflow files are the HEART of your application with almost NO tests!

1. **workflow_orchestrator.py** - Add tests for:
   - `run_workflow()` method
   - `execute_inference()` method
   - Error handling paths

2. **upsample_integration.py** - Add tests for:
   - Upsampling logic
   - Batch processing
   - Integration points

3. **resolution_tester.py** - Add tests for:
   - Resolution testing logic
   - Validation methods

### Priority 2: Add Tests for Prompt Manager
- Test prompt creation/update/delete
- Test validation logic
- Test error cases

### Priority 3: CLI Integration Tests
- Test main command flows
- Test argument parsing
- Test error messages

## Quick Wins for Coverage

### Add these simple test files:
```python
# tests/unit/workflows/test_resolution_tester.py
# Even basic tests would add 95 lines of coverage!

# tests/unit/prompts/test_prompt_manager_basic.py
# Basic CRUD tests would add significant coverage
```

## Summary

### Current State:
- **66.93%** coverage (acceptable but could be better)
- **8 skipped tests** (4 should be removed, 4 are legitimate)
- **Critical gap**: Workflow orchestration has almost no tests!

### Recommended Target:
- Remove 4 outdated tests → cleaner codebase
- Add workflow tests → reach **75-80%** coverage
- Focus on business logic, not UI/CLI coverage

### Most Important:
**Your core business logic (workflows) has 0-13% coverage!** This is where bugs will hurt most. Adding even basic tests here would:
1. Significantly boost coverage
2. Protect your most important code
3. Give confidence in the core functionality
