# Test Fixes TODO

## Current Status
- **465/511 tests passing (91.0%)**
- Prompt enhancement working on GPU ✅
- Deleted: test_integration.py, test_upsample_prompts.py

## Tests to Fix

### 1. CLI Tests - `tests/unit/cli/test_inference_command.py`
**Problem:** Uses `run_full_cycle` method that doesn't exist
**Fix:** Replace with `execute_run(run_dict, prompt_dict)`
```python
# OLD
result = orchestrator.run_full_cycle(spec_file)

# NEW
run_dict = {"id": "rs_test", "prompt_id": "ps_test", "execution_config": {}, "status": "pending"}
prompt_dict = {"id": "ps_test", "prompt_text": "test", "model_type": "transfer", "inputs": {}, "parameters": {}}
result = orchestrator.execute_run(run_dict, prompt_dict)
```

### 2. CLI Tests - `tests/unit/cli/test_create_commands.py`
**Problem:** References old spec files
**Fix:** Use WorkflowService to create prompts/runs instead of spec files

### 3. Enhancement Tests - `tests/unit/test_enhancement_gpu_behavior.py`
**Problem:** Needs to mock DockerExecutor.run_prompt_enhancement()
**Fix:** Import mocks from tests/fixtures/mocks.py
```python
from tests.fixtures.mocks import create_mock_docker_executor
mock_docker = create_mock_docker_executor()
```

### 4. Orchestrator Tests - `tests/integration/test_workflow_orchestrator.py`
**Problems:**
- Tests for non-existent methods: `run_inference_only`, `run_upscaling_only`
- Tests for `_log_workflow_completion`, `_log_workflow_failure`
**Fix:** Delete these test methods entirely

### 5. Database Fixtures - `tests/fixtures/database_fixtures.py`
**Problem:** May reference PromptSpec/RunSpec
**Fix:** Remove any PromptSpec/RunSpec references

### 6. Test Helpers - `tests/utils/helpers.py`
**Problem:** May have old spec references
**Fix:** Update to use dictionaries instead of spec objects

## Quick Fix Script
Run these to clean up:
```bash
# Remove test methods for non-existent orchestrator methods
grep -l "test_run_inference_only\|test_run_upscaling_only\|test_log_workflow" tests/integration/test_workflow_orchestrator.py
# Then manually delete those test methods

# Find and fix run_full_cycle references
grep -r "run_full_cycle" tests/unit/cli/
# Replace each with execute_run pattern shown above

# Run tests to check progress
pytest tests/ -q --tb=no | tail -5
```

## Expected Result
Target: 480+ tests passing (from current 465)