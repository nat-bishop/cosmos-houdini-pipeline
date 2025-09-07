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

### Phase 1: Clean Up Obsolete Code (Low Risk)
**Goal**: Remove confusion before making functional changes

**Tasks**:
1. Remove misleading docstrings about "seek-based position tracking"
2. Remove unused `stream_logs` parameters throughout codebase
3. Update documentation to reflect actual Docker container streaming
4. Remove orphaned test files for old streaming implementation

**Files to modify**:
- `cosmos_workflow/execution/docker_executor.py` (docstrings)
- `cosmos_workflow/workflows/workflow_orchestrator.py` (parameters)
- `cosmos_workflow/api/workflow_operations.py` (already has working docker logs)
- Various test files

**Success criteria**:
- No references to "seek-based position tracking"
- No unused `stream_logs` parameters
- All tests pass

### Phase 2: Prompt Enhancement as Database Run
**Goal**: Establish pattern with working feature

**Changes**:
1. Create database run with `model_type="enhance"`
2. Change from `operation_id` to `run_id`
3. Convert from blocking to async execution (consistency)
4. Store enhanced prompt info in `outputs` JSON

**Implementation**:
```python
# In WorkflowOperations.enhance_prompt()
run = service.create_run(
    prompt_id=prompt_id,
    model_type="enhance",
    execution_config={
        "model": "pixtral",
        "offload": True
    }
)

# In DockerExecutor.run_prompt_enhancement()
# Accept run_id instead of operation_id
# Run in background like inference
```

**Success criteria**:
- Enhancement creates database run
- Can track enhancement progress
- Logs properly associated with run

### Phase 3: Fix Upscaling as Separate Run
**Goal**: Make upscaling truly independent

**Changes**:
1. Create separate run with `model_type="upscale"`
2. Link to parent inference run via `execution_config`
3. Independent status tracking and logs
4. Proper error handling for missing input video

**Implementation**:
```python
# After inference completes
upscale_run = service.create_run(
    prompt_id=prompt_id,
    model_type="upscale",
    execution_config={
        "parent_run_id": inference_run_id,
        "control_weight": 0.5,
        "input_video": f"outputs/{prompt_name}/output.mp4"
    }
)
```

**Success criteria**:
- Upscaling has its own run_id
- Parent-child relationship preserved
- Independent log files
- Can upscale any completed inference

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

## Timeline Estimate

- **Phase 1**: 1-2 hours (cleanup)
- **Phase 2**: 2-3 hours (enhancement integration)
- **Phase 3**: 3-4 hours (upscaling fix)
- **Phase 4**: 2-3 hours (status unification)
- **Phase 5**: 2-3 hours (CLI/UI updates)

Total: 10-15 hours of focused work

## Notes

- Database schema already supports this (well-designed!)
- Container log streaming via Docker is sufficient
- Each phase delivers value independently
- Maintains backward compatibility throughout