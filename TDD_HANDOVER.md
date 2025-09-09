# TDD Implementation Handover - Status Checker Feature

## Current Status
We are implementing a StatusChecker feature using TDD to replace broken async monitoring. Currently at **Gate 2** of the TDD workflow.

## Problem Being Solved
- Background daemon threads die when CLI exits, preventing database updates
- Containers complete on remote server but local database never updates
- File downloads fail because they depend on the broken monitoring

## Solution Architecture
- **StatusChecker class**: Reads container logs for `[COSMOS_COMPLETE]` markers with exit codes
- **Lazy evaluation**: DataRepository automatically syncs status when `get_run()` or `list_runs()` is called
- **Automatic downloads**: Files download on first status check after completion
- **No background threads**: Everything happens synchronously when data is queried

## TDD Progress

### ✅ Completed
1. **Gate 1**: Written comprehensive failing tests
   - `tests/unit/execution/test_status_checker.py` - Tests for StatusChecker class
   - `tests/unit/services/test_data_repository_lazy_sync.py` - Tests for DataRepository integration

### 🔄 Current Gate
2. **Gate 2**: Verify tests fail correctly
   - Tests fail as expected (ModuleNotFoundError) because StatusChecker doesn't exist yet

### 📋 TODO List
1. ✅ Write failing tests for StatusChecker class
2. ✅ Write failing tests for DataRepository lazy sync
3. 🔄 Verify all tests fail correctly
4. ⏳ Commit failing tests (Gate 3)
5. ⏳ Implement StatusChecker class
6. ⏳ Integrate StatusChecker with DataRepository
7. ⏳ Update scripts to write exit codes
8. ⏳ Remove broken async monitoring code
9. ⏳ Run overfit-verifier agent
10. ⏳ Run doc-drafter agent for documentation
11. ⏳ Run code-reviewer agent
12. ⏳ Final lint and coverage checks

## Key Files to Review

### Tests (Already Created)
- `tests/unit/execution/test_status_checker.py`
- `tests/unit/services/test_data_repository_lazy_sync.py`

### Files to Implement
- `cosmos_workflow/execution/status_checker.py` (NEW - needs creation)
- `cosmos_workflow/services/data_repository.py` (needs modification for lazy sync)

### Files to Modify for Exit Codes
- `scripts/inference.sh` - Add exit code to completion marker
- `scripts/upscale.sh` - Add exit code to completion marker
- `cosmos_workflow/execution/docker_executor.py` - Update completion markers

### Files with Code to Remove
- `cosmos_workflow/execution/gpu_executor.py` - Remove all monitoring methods (lines 74-551)

## Implementation Details

### StatusChecker Methods Needed
- `parse_completion_marker()` - Extract exit code from logs
- `check_container_status()` - Check if container is running via docker inspect
- `check_run_completion()` - Read log file for completion marker
- `download_outputs()` - Download appropriate files based on model_type
- `sync_run_status()` - Main method that orchestrates status check and downloads

### Download Patterns
- **Inference**: Download `output.mp4` to `outputs/run_{id}/outputs/output.mp4`
- **Enhancement**: Download `batch_results.json`, parse for enhanced_text
- **Upscaling**: Download `output_4k.mp4` to `outputs/run_{id}/outputs/output_4k.mp4`

### DataRepository Integration
- Add `initialize_status_checker()` method
- Modify `get_run()` to call `sync_run_status()` for running runs
- Modify `list_runs()` to sync all running runs in the list

## Important Context
- Must use established wrappers (RemoteCommandExecutor, FileTransferService)
- No raw paramiko or subprocess calls
- Follow existing patterns in codebase
- Maintain abstraction layers
- Use pathlib.Path for file operations

## Next Steps
1. Continue with Gate 3: Commit the failing tests
2. Gate 4: Implement StatusChecker class to make tests pass
3. Important: When implementing downloads, review existing patterns in `gpu_executor._handle_*_completion()` methods
4. Ensure lazy loading is clearly documented - status only syncs when queried

## Research Needed
If unclear about implementation details, use the research agent to:
- Review how FileTransferService.download_file() works
- Understand RemoteCommandExecutor usage patterns
- Check how DataRepository.update_run() handles outputs field
- Review existing download logic in gpu_executor completion handlers

## Testing Commands
```bash
# Run StatusChecker tests
pytest tests/unit/execution/test_status_checker.py -xvs

# Run DataRepository lazy sync tests
pytest tests/unit/services/test_data_repository_lazy_sync.py -xvs

# Check existing tests still pass
pytest tests/unit/execution/test_gpu_executor.py -xvs
```

## Critical Requirements
- Downloads must happen automatically on first status check after completion
- No background threads or async code
- GUI compatibility through polling (Gradio app uses CosmosAPI)
- Maintain backward compatibility with existing database
- Clear error messages if downloads fail

This implementation will solve the core issue where daemon threads die when CLI exits, ensuring reliable status updates and file downloads through lazy evaluation.