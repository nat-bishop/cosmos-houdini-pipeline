# GPU Operations Unification Plan

## Executive Summary

Unify three GPU operations (inference, upscaling, prompt enhancement) as atomic database runs to provide consistent tracking, monitoring, and UI integration. This plan maintains backward compatibility while fixing architectural issues with upscaling.

## Current State Analysis

### Operation Types
| Operation | Database Run | Execution | Status | Issues |
|-----------|--------------|-----------|--------|--------|
| **Inference** | ✅ Yes (model_type="transfer") | Async (background) | Working | None |
| **Upscaling** | ❌ Shares inference run | Async (background) | Broken | No separate tracking, overwrites logs |
| **Enhancement** | ❌ No (uses operation_id) | Sync (blocking) | Working | Not tracked in database |

### Problems to Solve
1. **Upscaling lacks independent tracking** - shares run_id with inference
2. **Enhancement not in database** - uses ad-hoc operation_id
3. **Inconsistent patterns** - different approaches for similar operations
4. **Log streaming confusion** - obsolete references to "seek-based position tracking"
5. **UI can't show all GPU work** - no unified source of truth

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

### Phase 2: Prompt Enhancement as Database Run
**Goal**: Make prompt enhancement a proper database run

**Key changes needed**:
1. Create database run with `model_type="enhance"`
2. Use `run_id` instead of `operation_id`
3. Convert from blocking to async execution for consistency
4. Store enhanced text in `outputs` JSON field

**Input**: Takes `prompt_id` as input (operates on prompt text)

### Phase 3: Fix Upscaling as Separate Run
**Goal**: Make upscaling an independent database run

**Key changes needed**:
1. Create separate run with `model_type="upscale"`
2. Link to parent inference run via `execution_config["parent_run_id"]`
3. Independent status tracking and logs

**Critical insight**: Takes `run_id` as input (not `prompt_id`) since it operates on the output video of a specific inference run

### Phase 4: Unified Status Tracking
**Goal**: Single source of truth for GPU operations

**Changes**:
1. Query database for active runs (all types)
2. Match runs to Docker containers via naming convention
3. Provide unified status API
4. Support filtering by model_type

**Implementation**:
```python
# Container naming convention
container_name = f"cosmos_{model_type}_{run_id[:8]}"

# Status check
active_runs = service.get_runs_by_status("running")
containers = docker_executor.get_containers()
# Match by name pattern
```

**Success criteria**:
- `cosmos status` shows all GPU operations
- Can identify which container belongs to which run
- UI can display unified GPU activity

### Phase 5: CLI and UI Updates
**Goal**: User-facing improvements

**CLI Changes**:
1. Re-enable `--upscale` flag (creates two runs internally)
2. Add `cosmos upscale <run_id>` for post-inference upscaling
3. Add `cosmos enhance <prompt_id>` as standalone command
4. Update `cosmos status` to show run types

**UI Changes**:
1. Display run type badges/icons
2. Show parent-child relationships
3. Group related runs visually
4. Add filters for run types

**Success criteria**:
- All commands create proper database runs
- UI clearly shows operation types
- Related runs are visually connected

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

1. **All GPU operations tracked in database** (measurable)
2. **Each operation has independent logs** (verifiable)
3. **UI shows all active GPU work** (observable)
4. **No breaking changes to existing workflows** (testable)
5. **Consistent patterns across codebase** (reviewable)

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

## Phase 6: Remote Log Download

### Goal
Download remote GPU logs back to local machine for debugging and monitoring

### Changes Required
1. After each GPU operation completes, download the remote log file
2. Store in local run directory: `outputs/run_{run_id}/logs/`
3. Update DockerExecutor methods to return both local and remote log paths
4. Implement log download in WorkflowOrchestrator after operation completion

### Implementation
- Add `download_log()` method to FileTransferService
- Call after each GPU operation (inference, upscaling, enhancement)
- Store alongside local orchestration logs
- Handle missing logs gracefully (operation may have failed before creating log)