I# Logging & Monitoring Infrastructure Implementation Plan

## Executive Summary
This document outlines the implementation plan for improving logging and monitoring in the Cosmos Houdini Experiments project. The implementation focuses on centralized logging, database integration, remote log streaming, and comprehensive monitoring capabilities.

## Current Status (2025-01-07)
- ✅ **Phases 1-3**: Complete (Centralized logging, Database storage, Remote streaming)
- ✅ **Phase 4**: Log Viewer implemented and integrated with Gradio UI
- ⏳ **Phase 5**: GPU Monitoring - Ready to implement
- ⏳ **Phase 6**: Testing & Documentation

### Latest Updates (Session 2):
1. ✅ **Fixed LogViewer timezone issue** - Added `timezone.utc`
2. ✅ **Created minimal Gradio app** - Simplified from 1600+ to 250 lines
3. ✅ **Integrated with `cosmos ui` command** - Works via CLI
4. ✅ **Unified log streaming approach** - File-based logs consistently

### Key Architecture Decisions:
- **File-based logs are superior to Docker logs** for our use case
- Scripts write to `/workspace/outputs/{prompt_name}/run.log`
- RemoteLogStreamer reads these files with position tracking
- Logs persist after container stops (can review failed runs)
- Single source of truth for both CLI and Gradio UI

### What the Current System Does:
1. **During execution**: Scripts redirect output to log files
2. **For monitoring**: RemoteLogStreamer reads files in real-time
3. **For UI**: LogViewer displays with color coding and filtering
4. **For persistence**: Logs saved locally and paths stored in database

## Current Implementation Status

### ✅ Phase 1: Centralized Logging System (COMPLETED)

#### What Was Implemented:
1. **Loguru Integration**
   - Added `loguru==0.7.2` to requirements.txt
   - Created `cosmos_workflow/utils/logging.py` with centralized configuration
   - Replaced all `print()` and `logging` calls with loguru logger

2. **Unified Inference Methods**
   - Removed duplicate `run_inference_with_logging()` method
   - Made `run_id` REQUIRED parameter in `run_inference()`
   - Method now returns dict with status, log_path, and prompt_name

3. **Enhanced Method Signatures**
   ```python
   # DockerExecutor methods now have tracking IDs:

   def run_inference(self, prompt_file: Path, run_id: str, ...) -> dict
   def run_upscaling(self, prompt_file: Path, run_id: str, ...) -> dict
   def run_prompt_enhancement(self, batch_filename: str, operation_id: Optional[str] = None, ...) -> dict
   ```

4. **Log Directory Structure**
   ```
   outputs/
   ├── {prompt_name}/
   │   └── logs/
   │       └── run_{run_id}.log           # Inference logs
   ├── {prompt_name}_upscaled/
   │   └── logs/
   │       └── run_{run_id}.log           # Upscaling logs
   └── prompt_enhancement/
       └── logs/
           └── op_{operation_id}.log      # Enhancement logs
   ```

5. **Updated All Callers**
   - WorkflowOrchestrator passes run_id to all methods
   - Tests updated for new signatures
   - Fakes updated to match real implementations

---

## ✅ Phase 2: Database Schema Updates (COMPLETED)

### Objective
Add minimal fields for log tracking and error messages.

### Steps

#### 2.1 Update Run Model
**Files to modify:**
- `cosmos_workflow/database/models.py`

**Implementation:**
```python
class Run(Base):
    # ... existing fields ...

    # New fields for logging
    log_path = Column(String(500), nullable=True)  # Local log file path
    error_message = Column(Text, nullable=True)     # Brief error description
```

#### 2.2 Create Migration
```bash
# Generate migration
alembic revision --autogenerate -m "Add log_path and error_message to Run"

# Review and apply
alembic upgrade head
```

#### 2.3 Update Service Layer
**Files to modify:**
- `cosmos_workflow/services/workflow_service.py`

**Implementation:**
```python
def update_run_with_log(self, run_id: str, log_path: str) -> dict:
    """Update run with log path."""
    run = self.get_run(run_id)
    if run:
        run.log_path = str(log_path)
        self.db.commit()
    return self._run_to_dict(run)

def update_run_error(self, run_id: str, error_message: str) -> dict:
    """Update run with error message."""
    run = self.get_run(run_id)
    if run:
        run.status = "failed"
        run.error_message = error_message[:1000]  # Truncate if needed
        self.db.commit()
    return self._run_to_dict(run)
```

#### 2.4 Wire Up in Orchestrator
Update `WorkflowOrchestrator.execute_run()` to call these methods:
```python
# After successful inference (using unified method)
if result.get("log_path"):
    self.service.update_run(run_id, log_path=result["log_path"])

# On failure
except Exception as e:
    self.service.update_run(run_id, error_message=str(e))
```

**What Was Actually Implemented:**
1. **Database Model Updates**
   - Added `log_path` (String(500), nullable) to Run model
   - Added `error_message` (Text, nullable) to Run model
   - No migration needed (recreating database)

2. **Unified Service Method**
   - Enhanced `update_run()` to handle log_path and error_message
   - Automatic status="failed" when error_message provided
   - Automatic completed_at timestamp on failure
   - Error message truncation at 1000 chars

3. **Backward Compatibility**
   - `update_run_with_log()` now delegates to `update_run()`
   - `update_run_error()` now delegates to `update_run()`
   - Marked as deprecated but kept for compatibility

4. **WorkflowOrchestrator Integration**
   - Uses unified `update_run()` method
   - Accepts optional service parameter
   - WorkflowOperations passes service to orchestrator

**Verification Checklist:**
- [x] Database fields created correctly
- [x] Log paths stored correctly
- [x] Error messages saved on failure
- [x] All 31 Phase 2 tests passing

---

## ✅ Phase 3: Efficient Remote Log Streaming (COMPLETED)

### Objective
Implement seek-based log streaming from remote (like Nvidia's approach).

### Implementation Summary
**Completed on:** 2025-01-07
**Implementation Time:** ~4 hours
**Test Coverage:** 22 tests, all passing

### What Was Implemented:

#### 3.1 ✅ RemoteLogStreamer Created
**Files created:**
- `cosmos_workflow/monitoring/log_streamer.py` - Complete implementation with seek-based streaming
- `cosmos_workflow/monitoring/__init__.py` - Module initialization
- `tests/unit/monitoring/test_log_streamer.py` - Comprehensive unit tests
- `tests/unit/execution/test_docker_executor_streaming.py` - Integration tests

**Key Features Implemented:**
- **Seek-based position tracking** using `tail -c +position` for efficiency
- **Background thread streaming** during GPU execution without blocking
- **Completion marker detection** for clean termination
- **Timeout handling** with configurable limits (default 3600s)
- **Error resilience** with graceful fallback and logging
- **Automatic directory creation** for local log files
- **Callback support** for real-time log processing
- **Buffer size control** for memory efficiency (8KB default)

#### 3.2 ✅ DockerExecutor Integration
**Files updated:**
- `cosmos_workflow/execution/docker_executor.py` - Integrated streaming into inference and upscaling

**Implementation Details:**
```python
# Real-time log streaming during inference
streamer = RemoteLogStreamer(self.ssh_manager)
stream_thread = threading.Thread(
    target=streamer.stream_remote_log,
    args=(remote_log_path, local_log_path),
    kwargs={
        "poll_interval": 2.0,
        "timeout": 3600,
        "wait_for_file": True,
        "completion_marker": "[COSMOS_COMPLETE]"
    },
    daemon=True
)
stream_thread.start()
```

#### 3.3 ✅ TDD Process Followed
- **Gate 1:** Wrote 18 comprehensive tests for RemoteLogStreamer first
- **Gate 2:** Verified all tests failed as expected (module didn't exist)
- **Gate 3:** Committed failing tests unchanged
- **Gate 4:** Implemented minimal code to pass tests, verified no overfitting
- **Gate 5:** Updated documentation (README, CHANGELOG) via doc-drafter
- **Gate 6:** Code review identified Windows path issue, fixed and verified

**Verification Checklist:**
- [x] Logs stream during execution in background threads
- [x] Seek position tracking prevents re-reading content
- [x] No duplicate content in streamed logs
- [x] Final log is complete and accurate
- [x] Supports both inference and upscaling workflows
- [x] Efficient streaming only reads new content
- [x] Proper error handling and timeout management
- [x] Complete test coverage with 22 unit tests
- [x] No overfitting detected by verifier agent
- [x] All linting checks pass (ruff)
- [x] Cross-platform compatibility verified

---

## ✅ Phase 4: Simple Log Visualization (COMPLETED - SIMPLIFIED)

### Objective
Simple, practical log viewer for monitoring inference runs.

### What Was Implemented:
- **Simplified `log_viewer.py`** (119 lines, down from 245) - Color-coded logs with search/filter
- **Removed `log_viewer_web.py`** (was 368 lines of overengineering)
- **Simplified tests** (185 lines, down from 900+)

### What Was Kept (Useful):
- Color-coded log levels (ERROR=red, WARNING=yellow, INFO=blue)
- Search with highlighting
- Level filtering (ERROR, WARNING, INFO, ALL)
- JSON export for debugging
- Ring buffer (auto-cleanup after 2000 lines)
- HTML escaping for security
- Error detection helpers (`has_errors()`, `get_last_error()`)

### What Was Removed (Not Needed):
- Multiple concurrent streams (you run one job at a time)
- Virtual scrolling (2000 lines is fine for browsers)
- CSV export (JSON is enough)
- Keyboard navigation (mouse works)
- Timezone handling (all same timezone)
- Complex caching (2000 lines searches instantly)

### Integration Status:
**✅ INTEGRATED** - Simple Gradio app created with LogViewer

#### What was implemented:
- Created new minimal Gradio app in `cosmos_workflow/ui/app.py` (225 lines)
- Backed up old complex app to `app_old.py` for reference
- Fixed timezone issues (added timezone.utc)
- Integrated LogViewer with RemoteLogStreamer callbacks
- Added controls: Run ID input, filters, search, clear logs
- Tested with Playwright - all UI elements functional

#### How to use:
```bash
# Start the UI via CLI
cosmos ui

# Or specify a custom port
cosmos ui --port 8080

# Access at http://localhost:7860
# App will auto-detect running jobs
# Click on a run ID to stream its logs
```

#### Architecture:
```
Scripts → Write to log files → RemoteLogStreamer reads → LogViewer displays
         (/workspace/outputs/{prompt_name}/run.log)
```

This file-based approach is superior because:
- Logs persist after container stops
- Can resume from position if disconnected
- Works with database (stores log paths)
- Single source of truth for CLI and UI

---

## Phase 5: GPU Utilization Monitoring (NEW - 1 day)

### Objective
Show actual GPU utilization in `cosmos status` command.

### Steps

#### 5.1 Enhanced Status Command
**Files to update:**
- `cosmos_workflow/cli/status.py`
- `cosmos_workflow/api/workflow_operations.py`

**Implementation:**
```python
def check_gpu_status(ssh_manager) -> dict:
    """Get GPU utilization and current job info."""

    # 1. Check GPU utilization
    cmd = "nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits"
    _, stdout, _ = ssh_manager.execute_command(cmd)

    # Parse: "45, 8192, 24576" -> 45% util, 8GB/24GB memory

    # 2. Check if cosmos container is running
    cmd = "docker ps --filter 'ancestor=cosmos' --format '{{.Names}}'"
    _, container_name, _ = ssh_manager.execute_command(cmd)

    # 3. If container running, get prompt info
    current_job = None
    if container_name:
        # Extract prompt_id from container name or labels
        cmd = f"docker inspect {container_name} --format '{{{{.Config.Labels}}}}'"
        # Parse labels to get prompt_id and run_id

    return {
        "gpu_utilization": 45,  # percentage
        "memory_used": 8192,     # MB
        "memory_total": 24576,   # MB
        "current_job": {
            "prompt_id": "ps_xxxxx",
            "run_id": "run_yyyyy",
            "started_at": "2025-01-07 12:00:00"
        } if current_job else None
    }
```

#### 5.2 Display Format
```
$ cosmos status

GPU Status:
  Utilization: 45%
  Memory: 8.0 GB / 24.0 GB (33%)

Current Job:
  Prompt: ps_12345 - "flying dragon"
  Run ID: run_67890
  Duration: 5 min 23 sec

Status: ✅ GPU Available (running job)
```

**Verification Checklist:**
- [ ] GPU utilization shows correctly
- [ ] Memory usage displays in human-readable format
- [ ] Current job detected when running
- [ ] Works when no job is running
- [ ] Fast response (< 2 seconds)

---

## Phase 6: Testing & Documentation (1 day)

### Objective
Test the simplified system and update docs.

### Test Coverage:
- [x] Simple log viewer works
- [ ] GPU status displays correctly
- [ ] Current job detection works
- [x] Database fields populated
- [x] Log streaming works

### Documentation Updates:
- Update README with new status command output
- Document simplified log viewer
- Remove references to removed features

---

## Unified Operations Architecture

### WorkflowOperations Methods (Session 2 additions):
```python
# Container management
def get_active_containers() -> list[dict]
    # Returns Docker containers with ID, name, status

# Log streaming (unified for CLI and UI)
def stream_logs(container_id=None, callback=None)
    # If callback: streams to callback for UI
    # If no callback: streams to stdout for CLI
```

### Current Flow:
1. **CLI**: `cosmos status --stream` → `ops.stream_logs()` → stdout
2. **UI**: `cosmos ui` → `ops.stream_logs(callback=...)` → LogViewer
3. **Both use same underlying system**: RemoteLogStreamer reading files

### Why File-Based Won:
After extensive analysis, file-based logs are superior to Docker logs because:
- **Already implemented**: Scripts use `tee` to write logs
- **Persistent**: Survive container removal
- **Seekable**: Can resume from position
- **Database-integrated**: Paths stored with runs
- **Unified**: One system for all use cases

## REMOVED PHASES (Not Needed)

### ~~Phase X: Container Activity Tracking~~
**Why removed:** GPU utilization and docker ps tells you everything needed

### ~~Phase X: Error Recovery & Diagnostics~~
**Why removed:** Overengineered - logs already show errors

### ~~Phase X: Progress Indicators~~
**Why removed:** Fragile string matching, not reliable

### ~~Phase X: Smart Error Detection~~
**Why removed:** Users can read error messages themselves

---

## Documentation Standards

### Documentation to Update:

#### CLAUDE.md Additions
```markdown
## **Logging Standards**

### **Unified Logging**
- All runs require a run_id for tracking
- Use Loguru: `from cosmos_workflow.utils.logging import logger`
- Never use print() in production code

### **Log Storage**
- Remote: `outputs/{prompt_name}/run.log` (created by tee in scripts)
- Local: `outputs/{prompt_name}/logs/run_{run_id}.log`
- Log path stored in database Run.log_path field

### **Log Streaming**
- Logs streamed from remote every 2 seconds during execution
- Uses seek-based position tracking for efficiency
- Final complete log downloaded after execution

### **Error Handling**
- Failed runs store error_message in database
- Diagnostics collected in `outputs/{prompt_id}/diagnostics/`
- Always log with context: `logger.error("Failed run %s: %s", run_id, error)`
```

#### Other Documentation:
- Update README.md with logging features
- Update architecture.md with logging flow
- Add troubleshooting guide

---

## Timeline Summary (REVISED)

| Phase | Duration | Status | Dependencies | Notes |
|-------|----------|--------|--------------|-------|
| 1. Centralized Logging | 2-3 days | ✅ DONE | None | Complete |
| 2. Database Schema | 1 day | ✅ DONE | Phase 1 | Complete |
| 3. Remote Log Streaming | 2 days | ✅ DONE | Phase 1, 2 | Complete |
| 4. Simple Log Viewer | 1 day | ✅ DONE | Phase 3 | Simplified from original |
| 5. GPU Monitoring | 1 day | Pending | Phase 1 | Show GPU util & current job |
| 6. Testing & Docs | 1 day | Pending | All phases | Final validation |

**Total Remaining: 2 days** (down from 7 days)

## Success Metrics (REVISED)

**Completed:**
- [x] All runs create logs automatically
- [x] Logs accessible via database log_path
- [x] Failed runs have error messages
- [x] No duplicate logging methods
- [x] Efficient log streaming (< 3MB/min bandwidth)
- [x] All tests passing
- [x] Real-time log streaming during execution
- [x] Seek-based position tracking implemented
- [x] Simple log viewer with search/filter
- [x] Color-coded log levels for quick scanning

**Remaining:**
- [ ] GPU utilization visible in status command
- [ ] Current job detection in status command

**Removed (Not Needed):**
- ~~Clean diagnostic collection on errors~~ (Overengineered)
- ~~Progress indicators~~ (Too fragile)
- ~~Container activity tracking~~ (GPU status is enough)
- ~~Smart error detection~~ (Users can read errors)

## Next Steps

1. **Phase 5**: Implement GPU utilization monitoring
   - Query nvidia-smi for GPU/memory usage
   - Detect running cosmos containers
   - Show current job info if running

2. **Phase 6**: Final testing and documentation
   - Verify GPU monitoring works
   - Update README with new features
   - Clean up any deprecated code

---

*Document Version: 5.0 (Simplified Plan)*
*Last Updated: 2025-01-07*
*Phases 1-4 Completed*
*Author: NAT*