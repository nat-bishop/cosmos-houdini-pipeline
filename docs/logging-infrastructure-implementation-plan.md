# Logging & Monitoring Infrastructure Implementation Plan

## Executive Summary
This document outlines the implementation plan for improving logging and monitoring in the Cosmos Houdini Experiments project. The implementation focuses on centralized logging, database integration, remote log streaming, and comprehensive monitoring capabilities.

**Key Architecture Facts:**
- Scripts run on remote GPU instances inside Docker containers
- Logs are captured via `tee` in bash scripts to `outputs/${PROMPT_NAME}/run.log` on remote
- Files are transferred back via SFTP after completion
- We use seek-based position tracking for efficient log streaming

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

## Phase 4: Enhanced GPU Monitoring (1 day)

### Objective
Add GPU utilization monitoring to status command.

### Steps

#### 4.1 Create GPU Monitor
**Files to create:**
- `cosmos_workflow/monitoring/gpu_monitor.py`

**Implementation:**
```python
class GPUMonitor:
    """Monitor GPU status on remote instance."""

    def get_gpu_status(self) -> Dict[str, Any]:
        """Get GPU status with caching."""
        # Query nvidia-smi for GPU metrics
        # Return utilization, memory, temperature, etc.
```

#### 4.2 Integrate into Status Command
Update `WorkflowOperations.check_status()` to include GPU info.

**Verification Checklist:**
- [ ] GPU stats display correctly
- [ ] Cache prevents excessive SSH calls
- [ ] Running job detection works

---

## Phase 5: Container Activity Tracking (1 day)

### Objective
Track container activities with minimal overhead.

### Steps

#### 5.1 Add Container Labels
Update `DockerCommandBuilder` to add tracking labels:
```python
def add_run_labels(self, run_id: str, prompt_id: str):
    """Add labels for tracking."""
    self.add_option(f"--label run_id={run_id}")
    self.add_option(f"--label prompt_id={prompt_id}")
    self.add_option(f"--label start_time={datetime.now().isoformat()}")
```

#### 5.2 Query Container Info
```python
def get_container_info(self, run_id: str) -> dict:
    """Get container info for a run."""
    cmd = f"sudo docker ps -a --filter 'label=run_id={run_id}' --format json"
    # Parse and return container info
```

**Verification Checklist:**
- [ ] Container labels set correctly
- [ ] Can query by run_id
- [ ] No performance impact

---

## Phase 6: Error Recovery & Diagnostics (2 days)

### Objective
Improve error handling and diagnostics collection.

### Steps

#### 6.1 Enhanced Error Handling
Wrap all GPU operations with proper error handling and diagnostic collection.

#### 6.2 Diagnostic Collection
On failure, automatically collect:
- GPU state
- Container logs
- System resources
- Recent commands

Store diagnostics in `outputs/{prompt_id}/diagnostics/`

**Verification Checklist:**
- [ ] Errors stored in database
- [ ] Diagnostics collected on failure
- [ ] No crash on diagnostic failure

---

## Phase 7: Testing & Optimization (2 days)

### Objective
Comprehensive testing of the logging infrastructure.

### Test Coverage Required:
- [ ] Unified logging method works
- [ ] Log streaming doesn't miss content
- [ ] Database fields populated correctly
- [ ] GPU monitoring accuracy
- [ ] Error handling robust
- [ ] No memory leaks in streaming
- [ ] Performance acceptable

### Performance Targets:
- Log streaming latency < 3 seconds
- GPU status query < 1 second (with cache)
- No zombie SSH connections
- Log files < 100MB per run

---

## Phase 8: Documentation Updates (1 day)

### Objective
Update project documentation with new logging standards.

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

## Timeline Summary

| Phase | Duration | Status | Dependencies | Risk Level |
|-------|----------|--------|--------------|------------|
| 1. Centralized Logging | 2-3 days | ✅ DONE | None | Low |
| 2. Database Schema | 1 day | ✅ DONE | Phase 1 | Low |
| 3. Remote Log Streaming | 2 days | ✅ DONE | Phase 1, 2 | Medium |
| 4. GPU Monitoring | 1 day | Pending | Phase 1 | Low |
| 5. Container Tracking | 1 day | Pending | Phase 1 | Low |
| 6. Error Recovery | 2 days | Pending | Phase 1, 2 | Medium |
| 7. Testing | 2 days | Pending | All phases | Low |
| 8. Documentation | 1 day | Pending | All phases | Low |

**Total Remaining: 7 days**

## Success Metrics

- [x] All runs create logs automatically
- [x] Logs accessible via database log_path
- [x] Failed runs have error messages
- [ ] GPU utilization visible in status
- [x] No duplicate logging methods
- [x] Efficient log streaming (< 3MB/min bandwidth)
- [ ] Clean diagnostic collection on errors
- [x] All tests passing
- [x] Real-time log streaming during execution
- [x] Seek-based position tracking implemented
- [x] Background streaming without execution blocking

## Next Steps for Phase 4

1. Create GPUMonitor class for remote GPU status
2. Integrate GPU monitoring into status command
3. Add caching to prevent excessive SSH calls
4. Display GPU utilization, memory, and temperature
5. Test GPU status accuracy

---

*Document Version: 4.0 (Phase 3 Complete)*
*Last Updated: 2025-09-07*
*Phase 1-3 Completed By: Assistant*
*Author: NAT*