# GPU Operations Unification Plan

## Executive Summary

Unify three GPU operations (inference, upscaling, prompt enhancement) as atomic database runs to provide consistent tracking, monitoring, and UI integration. This plan maintains backward compatibility while fixing architectural issues and implementing non-blocking execution with proper database synchronization.

## Current State Analysis

### Operation Types (After Phase 5)
| Operation | Database Run | Execution | Status | Issues |
|-----------|--------------|-----------|--------|--------|
| **Inference** | ✅ Yes (model_type="transfer") | ✅ Async with monitoring | ✅ Working | None |
| **Upscaling** | ✅ Yes (model_type="upscale") | ✅ Async with monitoring | ✅ Working | None |
| **Enhancement** | ✅ Yes (model_type="enhance") | ✅ Async with monitoring | ✅ Working | None |

### Problems Solved (Phases 1-5)
1. ✅ **Upscaling has independent tracking** - separate run_id and database entry
2. ✅ **Enhancement tracked in database** - proper run with model_type="enhance"
3. ✅ **Consistent patterns** - all operations follow same approach
4. ✅ **Log streaming clarified** - removed obsolete references
5. ✅ **UI can show all GPU work** - unified status tracking
6. ✅ **Database synchronization** - runs automatically update when containers complete
7. ✅ **No more orphaned containers** - monitoring ensures proper cleanup
8. ✅ **Proper completion detection** - background threads track container lifecycle
9. ✅ **Non-blocking execution** - all operations return immediately

### Remaining Issues (Phase 6-7)
1. **CLI improvements** - re-enable combined inference+upscaling workflow
2. **UI enhancements** - run type badges, parent-child relationships
3. **Legacy code cleanup** - unused methods and outdated comments still present
4. **Remote log download** - download GPU logs for debugging

## Solution Architecture

### Core Principle: One GPU Operation = One Database Run

Every GPU operation creates a database run with:
- Unique `run_id` for tracking
- Appropriate `model_type` ("transfer", "upscale", "enhance")
- Status lifecycle (pending → running → completed/failed)
- JSON `execution_config` for operation-specific data
- JSON `outputs` for flexible results
- `log_path` for operation logs

### Database Schema (No Changes Needed!)

Current `Run` model already supports this:
```python
Run:
  - id: String (primary key)
  - model_type: String  # "transfer", "upscale", "enhance"
  - prompt_id: String (FK)
  - status: String
  - execution_config: JSON  # Flexible configuration
  - outputs: JSON  # Flexible results
  - log_path: String
```

### Linking Related Runs

Use `execution_config` JSON to establish relationships:
```json
// Upscale run
{
  "parent_run_id": "run_abc123",  // Links to inference run
  "control_weight": 0.5,
  "input_video": "outputs/prompt_name/output.mp4"
}

// Enhancement run
{
  "model": "pixtral",
  "offload": true,
  "batch_size": 1
}
```

## Implementation Phases

### Phase 1: Clean Up Obsolete Code ✅ COMPLETED
**What was done**:
- Removed misleading docstrings about "seek-based position tracking" from DockerExecutor
- Removed `--stream` flag from CLI commands (inference, enhance)
- Removed unused `stream_logs` parameter from entire call chain
- Updated docstrings to reflect actual behavior (returns immediately with "started" status)
- Confirmed that log streaming works via `cosmos status --stream` using `docker logs -f`

**Key decision**: Kept streaming simple - only via `cosmos status --stream`, not during execution

### Phase 2: Prompt Enhancement as Database Run ✅ COMPLETED
**Goal**: Make prompt enhancement a proper database run

**What was done**:
1. Created database runs with `model_type="enhance"`
2. Replaced `operation_id` with proper `run_id` tracking
3. Implemented async execution pattern (returns immediately with status)
4. Enhanced text stored in `outputs` JSON field
5. Added JSONHandler wrapper for all JSON operations (CLAUDE.md compliance)
6. Added model_type validation to ensure only valid types are used
7. Track actual execution duration instead of hardcoded values
8. Full TDD implementation with comprehensive unit and integration tests

**Input**: Takes `prompt_id` as input (operates on prompt text)

### Phase 3: Fix Upscaling as Separate Run ✅ COMPLETED
**Goal**: Make upscaling an independent database run

**What was done**:
1. ✅ Created `upscale_run()` method in CosmosAPI that creates separate runs with `model_type="upscale"`
2. ✅ Added `execute_upscaling_run()` method to GPUExecutor for independent upscaling execution
3. ✅ Created new CLI command "cosmos upscale <run_id>" for post-inference upscaling
4. ✅ Fixed DockerExecutor constructor mismatch in GPUExecutor
5. ✅ Removed upscaling parameters from execute_run and quick_inference methods
6. ✅ Independent status tracking and logs for each upscaling operation
7. ✅ Links to parent inference run via `execution_config["parent_run_id"]` for traceability
8. ✅ Complete "One GPU Operation = One Database Run" implementation

**Critical insight implemented**: Takes `run_id` as input (not `prompt_id`) since it operates on the output video of a specific inference run

### Phase 4: Unified Status Tracking ✅ COMPLETED
**Goal**: Single source of truth for GPU operations

**What was done**:
1. ✅ Added `get_active_operations()` method to CosmosAPI for unified operation tracking
2. ✅ Enhanced `check_status()` to include active run details with operation type, run ID, and prompt
3. ✅ Implemented `_generate_container_name()` for consistent container naming: `cosmos_{model_type}_{run_id[:8]}`
4. ✅ Enhanced status command to display what's actually running instead of just container presence
5. ✅ Added detection and warnings for orphaned containers and zombie runs
6. ✅ Simplified tracking for single-container system with multiple container warnings
7. ✅ Status now shows operation type (INFERENCE, UPSCALE, ENHANCE) with run and prompt IDs
8. ✅ Better debugging through clear container-to-run relationship tracking
9. ✅ Fixed container naming in bash scripts (inference.sh, upscale.sh) to include run_id

**Implementation Pattern**:
```python
# Container naming convention
container_name = f"cosmos_{model_type}_{run_id[:8]}"

# Status includes active run details
status = {
    "active_run": {"id": "run_abc123", "model_type": "transfer", "prompt_id": "ps_xyz"},
    "container": {"name": "cosmos_transfer_abc12345", "status": "Up 5 minutes"}
}
```

**Success criteria achieved**:
- ✅ `cosmos status` shows all GPU operations with detailed information
- ✅ Can identify which container belongs to which run via naming convention
- ✅ Detects inconsistent states (orphaned containers, zombie runs)
- ✅ UI can display unified GPU activity with operation details

### Phase 5: Background Monitoring and Non-Blocking Operations ✅ COMPLETED
**Goal**: Non-blocking execution with background database synchronization

**What was implemented**:

**Container Monitoring System**:
- Added `_get_container_status()` method to check Docker container status via `docker inspect`
- Added `_monitor_container_completion()` to launch background monitoring threads
- Added `_monitor_container_internal()` that runs in thread to poll container status every 5 seconds
- Uses configurable timeout from config.toml (docker_execution = 3600 seconds)
- Kills containers on timeout to prevent resource leaks

**Completion Handlers**:
- `_handle_inference_completion()` - downloads outputs and updates database when inference completes
- `_handle_enhancement_completion()` - downloads enhanced text and updates database
- `_handle_upscaling_completion()` - downloads 4K video and updates database
- All handlers properly handle success (exit code 0), failure, and timeout (exit code -1)

**Updated Execute Methods**:
- `execute_run()`, `execute_enhancement_run()`, `execute_upscaling_run()` now:
  - Detect "started" status from DockerExecutor
  - Launch background monitoring thread immediately
  - Return immediately with "started" status for non-blocking operation
  - Let monitor handle completion, downloads, and database updates automatically

**API Layer Integration**:
- CosmosAPI now passes service to GPUExecutor for database updates
- `quick_inference()`, `enhance_prompt()`, `upscale_run()` handle "started" status correctly
- Return partial results immediately when operations start in background

**Critical Issues Fixed**:
- Database automatically updates when containers complete (no more orphaned "running" runs)
- No more downloading outputs before they exist
- Enhancement no longer polls for files inefficiently
- Proper timeout handling with container cleanup
- All operations are truly non-blocking with background synchronization

### Phase 6: CLI and UI Updates
**Goal**: User-facing improvements

**CLI Changes**:
1. Re-enable `--upscale` flag (creates two runs internally)
2. ✅ Add `cosmos upscale <run_id>` for post-inference upscaling
3. ✅ Add `cosmos prompt-enhance <prompt_id>` as standalone command
4. ✅ Update `cosmos status` to show run types

**UI Changes**:
1. Display run type badges/icons
2. Show parent-child relationships
3. Group related runs visually
4. Add filters for run types

**Success criteria**:
- All commands create proper database runs
- UI clearly shows operation types
- Related runs are visually connected

### Phase 7: Legacy Code Removal
**Goal**: Clean up obsolete and unused code

**Identified for Removal**:
1. `run_prompt_upsampling()` method in GPUExecutor (replaced by enhancement)
2. Outdated comments referencing old streaming patterns
3. Broken/unused code paths in various modules
4. TODO comments that are no longer relevant
5. Backward compatibility code that's no longer needed

## Testing Strategy

### Unit Tests
- Mock database and Docker interactions
- Test each operation type independently
- Verify proper run creation and status updates

### Integration Tests
- Use fake implementations (per CLAUDE.md)
- Test operation sequences (inference → upscale)
- Verify parent-child relationships

### Manual Testing Checklist
- [ ] Create and run inference
- [ ] Create and run upscaling
- [ ] Create and run enhancement
- [ ] Check database has correct entries
- [ ] Verify logs are separate
- [ ] Test error scenarios

## Rollback Plan

Each phase is independent and can be rolled back:
- **Phase 1**: No rollback needed (cleanup only)
- **Phase 2**: Keep operation_id code as fallback
- **Phase 3**: Upscaling already broken, disable if issues
- **Phase 4**: Maintain old status check in parallel
- **Phase 5**: Feature flags for new UI elements

## Success Metrics

### Completed ✅
1. ✅ **All GPU operations tracked in database** - inference, upscaling, enhancement all create runs
2. ✅ **Each operation has independent logs** - separate log files per run_id
3. ✅ **UI shows all active GPU work** - unified status tracking implemented
4. ✅ **No breaking changes to existing workflows** - backward compatible
5. ✅ **Consistent patterns across codebase** - all operations follow same pattern
6. ✅ **Database stays synchronized** - automatic updates via monitoring
7. ✅ **Non-blocking execution** - operations return immediately
8. ✅ **Proper resource cleanup** - containers killed on timeout

### Remaining
1. ⏳ **CLI combined workflows** - re-enable --upscale flag for single command
2. ⏳ **UI relationship display** - show parent-child run connections
3. ⏳ **Legacy code removal** - clean up unused methods

## Zen of Python Alignment

- **Explicit is better than implicit**: Clear run types, not hidden parameters
- **Simple is better than complex**: One pattern for all GPU operations
- **Flat is better than nested**: Direct run relationships, not complex hierarchies
- **Readability counts**: Clear model_type indicates operation purpose
- **Special cases aren't special enough**: All GPU ops follow same pattern
- **There should be one obvious way**: Database runs for everything
- **Now is better than never**: Fix the broken upscaling
- **Although never is often better than *right* now**: Phased approach
- **If implementation is easy to explain**: One GPU op = one database run

## Notes for Implementation

- Database schema already supports all changes (no migrations needed)
- Keep operations atomic and independent
- Each phase delivers value independently
- All run directory names should be based on run_id (e.g., `outputs/run_{run_id}/`)
  - This applies to inference, upscaling, and prompt enhancement
  - Ensures consistent directory structure across all operations
  - Makes it easy to find outputs for any run

## Phase 8: Remote Log Download

### Goal
Download remote GPU logs back to local machine for debugging and monitoring

### Changes Required
1. After each GPU operation completes, download the remote log file
2. Store in local run directory: `outputs/run_{run_id}/logs/`
3. Update DockerExecutor methods to return both local and remote log paths
4. Implement log download in GPUExecutor after operation completion

### Implementation
- Add `download_log()` method to FileTransferService
- Call after each GPU operation (inference, upscaling, enhancement)
- Store alongside local orchestration logs
- Handle missing logs gracefully (operation may have failed before creating log)