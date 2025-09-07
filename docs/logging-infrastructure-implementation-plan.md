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

## 🔄 Phase 2: Database Schema Updates (NEXT - 1 day)

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
# After successful inference
if result.get("log_path"):
    self.service.update_run_with_log(run_id, result["log_path"])

# On failure
except Exception as e:
    self.service.update_run_error(run_id, str(e))
```

**Verification Checklist:**
- [ ] Migration runs without errors
- [ ] Existing data preserved
- [ ] Log paths stored correctly
- [ ] Error messages saved on failure

---

## Phase 3: Efficient Remote Log Streaming (2 days)

### Objective
Implement seek-based log streaming from remote (like Nvidia's approach).

### Steps

#### 3.1 Create Log Streamer
**Files to create:**
- `cosmos_workflow/monitoring/log_streamer.py`

**Implementation:**
```python
class RemoteLogStreamer:
    """Stream logs from remote using seek position tracking."""

    def stream_remote_log(
        self,
        remote_path: str,
        local_path: Path,
        poll_interval: float = 2.0,
        timeout: int = 3600
    ) -> None:
        """Stream remote log to local file using seek position."""
        # Implementation using tail -c +{position} for efficiency
```

#### 3.2 Integrate into Docker Executor
Modify `run_inference()` to stream logs during execution:
```python
# Start remote execution (non-blocking)
self._run_inference_script(prompt_name, num_gpu, cuda_devices)

# Stream logs while running
streamer = RemoteLogStreamer(self.ssh_manager)
remote_log = f"{self.remote_dir}/outputs/{prompt_name}/run.log"
streamer.stream_remote_log(remote_log, local_log_path)
```

**Verification Checklist:**
- [ ] Logs stream during execution
- [ ] Seek position tracking works
- [ ] No duplicate content in logs
- [ ] Final log is complete

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
| 2. Database Schema | 1 day | 🔄 NEXT | Phase 1 | Low |
| 3. Remote Log Streaming | 2 days | Pending | Phase 1, 2 | Medium |
| 4. GPU Monitoring | 1 day | Pending | Phase 1 | Low |
| 5. Container Tracking | 1 day | Pending | Phase 1 | Low |
| 6. Error Recovery | 2 days | Pending | Phase 1, 2 | Medium |
| 7. Testing | 2 days | Pending | All phases | Low |
| 8. Documentation | 1 day | Pending | All phases | Low |

**Total Remaining: 10 days**

## Success Metrics

- [x] All runs create logs automatically
- [ ] Logs accessible via database log_path
- [ ] Failed runs have error messages
- [ ] GPU utilization visible in status
- [x] No duplicate logging methods
- [ ] Efficient log streaming (< 3MB/min bandwidth)
- [ ] Clean diagnostic collection on errors
- [x] All tests passing

## Next Steps for Phase 2

1. Create Alembic migration for database schema
2. Add `log_path` and `error_message` fields to Run model
3. Implement `update_run_with_log()` and `update_run_error()` methods
4. Update WorkflowOrchestrator to call these methods
5. Test database updates work correctly
6. Verify existing data is preserved

---

*Document Version: 3.0 (Consolidated)*
*Last Updated: 2025-01-07*
*Phase 1 Completed By: Assistant*
*Author: NAT*