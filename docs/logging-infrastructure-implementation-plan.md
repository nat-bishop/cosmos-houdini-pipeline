# Logging & Monitoring Infrastructure Implementation Plan

## Executive Summary
This document outlines a detailed, step-by-step plan to improve the logging and monitoring infrastructure for the Cosmos Houdini Experiments project. The implementation focuses on safety, incremental changes, and continuous verification.

## Current State Analysis

### Existing Infrastructure
- **Logging**: Basic Python logging with print statements and file writes
- **Streaming**: Docker logs via SSH with real-time output
- **Run Tracking**: SQLAlchemy database with status field
- **Monitoring**: Limited to `cosmos status` command
- **Error Handling**: Basic try-catch with minimal context

### Key Issues
1. No centralized logging system
2. Failed runs lack diagnostic information
3. No persistent log storage for runs
4. Limited GPU/container monitoring
5. Inconsistent logging interfaces across modules
6. No live log viewing in Gradio UI

## Implementation Phases

---

## Phase 1: Centralized Logging System (2-3 days)

### Objective
Establish a unified logging infrastructure using Loguru, similar to cosmos-transfer1.

### Steps

#### 1.1 Install and Configure Loguru
```bash
# Add to requirements.txt
loguru==0.7.2
```

**Files to modify:**
- `requirements.txt`
- `cosmos_workflow/utils/logging.py` (new file)

**Implementation:**
```python
# cosmos_workflow/utils/logging.py
import os
import sys
from pathlib import Path
from loguru import logger

def init_logger(
    level: str = "INFO",
    log_file: Path | None = None,
    rotation: str = "100 MB"
):
    """Initialize centralized logger."""
    logger.remove()  # Remove default handler

    # Console handler
    logger.add(
        sys.stdout,
        level=level,
        format="[{time:MM-DD HH:mm:ss}|{level}|{name}:{line}] {message}",
        colorize=True
    )

    # File handler if specified
    if log_file:
        logger.add(
            log_file,
            level=level,
            rotation=rotation,
            retention="7 days",
            encoding="utf8"
        )

    return logger
```

**Verification:**
- [ ] Test logger initialization
- [ ] Verify console output formatting
- [ ] Check file rotation works
- [ ] Test log levels

#### 1.2 Create Run-Specific Loggers
**Files to modify:**
- `cosmos_workflow/workflows/workflow_orchestrator.py`
- `cosmos_workflow/api/workflow_operations.py`

**Implementation:**
```python
def create_run_logger(run_id: str, prompt_name: str) -> Path:
    """Create logger for specific run."""
    log_dir = Path(f"outputs/{prompt_name}/logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / f"run_{run_id}_{datetime.now():%Y%m%d_%H%M%S}.log"

    # Create run-specific logger
    run_logger = logger.bind(run_id=run_id)
    run_logger.add(log_file, level="DEBUG")

    return log_file
```

**Verification:**
- [ ] Test run logger creation
- [ ] Verify log directory structure
- [ ] Check log file naming convention
- [ ] Test concurrent run logging

#### 1.3 Replace Existing Logging
**Files to modify (in order):**
- `cosmos_workflow/execution/docker_executor.py`
- `cosmos_workflow/workflows/workflow_orchestrator.py`
- `cosmos_workflow/services/workflow_service.py`
- `cosmos_workflow/connection/ssh_manager.py`
- `cosmos_workflow/transfer/file_transfer.py`

**Migration Strategy:**
1. Import new logger at top of each file
2. Replace `print()` statements with `logger.info()`
3. Replace `logging.error()` with `logger.error()`
4. Add structured logging for important events

**Verification per file:**
- [ ] All print statements replaced
- [ ] Error handling includes context
- [ ] No regression in functionality
- [ ] Log output is readable

### Safety Checks
- [ ] Run existing tests after each file modification
- [ ] Test basic workflow: create prompt → inference → status
- [ ] Verify no log files are created in wrong locations
- [ ] Check log file permissions

### Rollback Plan
- Git commit after each successful file modification
- Keep original logging import as fallback
- Test suite must pass before proceeding

---

## Phase 2: Database Schema Updates (1 day)

### Objective
Add log tracking fields to database models.

### Steps

#### 2.1 Update Run Model
**Files to modify:**
- `cosmos_workflow/database/models.py`

**Implementation:**
```python
class Run(Base):
    # ... existing fields ...

    # New fields for logging
    log_path = Column(String(500), nullable=True)
    container_id = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    error_traceback = Column(Text, nullable=True)
    gpu_info = Column(JSON, nullable=True)  # Store GPU state at run time
    diagnostics_path = Column(String(500), nullable=True)
```

#### 2.2 Create Migration
```bash
# Generate migration
alembic revision --autogenerate -m "Add logging fields to Run model"

# Review migration file
# Apply migration
alembic upgrade head
```

**Verification:**
- [ ] Migration runs without errors
- [ ] Existing data preserved
- [ ] New fields accessible via ORM
- [ ] Rollback migration works

#### 2.3 Update Service Layer
**Files to modify:**
- `cosmos_workflow/services/workflow_service.py`

**Implementation:**
```python
def update_run_logging(
    self,
    run_id: str,
    log_path: str | None = None,
    container_id: str | None = None,
    error_info: dict | None = None
) -> dict:
    """Update run with logging information."""
    run = self.get_run(run_id)
    if not run:
        raise ValueError(f"Run not found: {run_id}")

    if log_path:
        run.log_path = str(log_path)
    if container_id:
        run.container_id = container_id
    if error_info:
        run.error_message = error_info.get("message")
        run.error_traceback = error_info.get("traceback")

    self.db.commit()
    return self._run_to_dict(run)
```

**Verification:**
- [ ] Test updating run with log path
- [ ] Test error info storage
- [ ] Verify data persistence
- [ ] Check JSON field handling

### Safety Checks
- [ ] Backup database before migration
- [ ] Test on development database first
- [ ] Verify no data loss
- [ ] Test rollback procedure

---

## Phase 3: Gradio Log Viewer Integration (2 days)

### Objective
Add live log viewing to Gradio interface.

### Steps

#### 3.1 Create Log Viewer Component
**Files to create:**
- `cosmos_workflow/ui/components/log_viewer.py`

**Implementation:**
```python
import gradio as gr
from pathlib import Path

def create_log_viewer(
    log_file: str | Path | None = None,
    num_lines: int = 100,
    update_interval: float = 1.0
) -> tuple[gr.Timer, gr.Textbox]:
    """Create Gradio log viewer component."""

    def tail_logs() -> str:
        if not log_file or not Path(log_file).exists():
            return "No log file available"

        try:
            with open(log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                return "".join(lines[-num_lines:])
        except Exception as e:
            return f"Error reading log: {e}"

    timer = gr.Timer(value=update_interval, active=True)
    log_display = gr.Textbox(
        label="Logs",
        lines=20,
        max_lines=30,
        autoscroll=True,
        value=tail_logs,
        interactive=False
    )

    timer.tick(fn=tail_logs, outputs=log_display, api_name=False)

    return timer, log_display
```

#### 3.2 Integrate into Main UI
**Files to modify:**
- `cosmos_workflow/ui/app.py`

**Implementation:**
```python
# Add to create_interface()
with gr.Accordion("Execution Logs", open=False):
    log_file_dropdown = gr.Dropdown(
        label="Select Log File",
        choices=[],
        interactive=True
    )
    log_timer, log_display = create_log_viewer()

    def update_log_selection(prompt_id):
        """Update available log files for prompt."""
        log_dir = Path(f"outputs/{prompt_id}/logs")
        if log_dir.exists():
            logs = sorted(log_dir.glob("*.log"))
            return gr.update(choices=[str(l) for l in logs])
        return gr.update(choices=[])
```

**Verification:**
- [ ] Log viewer updates in real-time
- [ ] File selection works
- [ ] No UI performance degradation
- [ ] Handles large log files

#### 3.3 Add Run-Specific Log Viewing
**Implementation:**
```python
def show_run_logs(run_id: str):
    """Display logs for specific run."""
    run = workflow_service.get_run(run_id)
    if run and run.get("log_path"):
        return create_log_viewer(run["log_path"])
    return None, gr.update(value="No logs available for this run")
```

**Verification:**
- [ ] Logs display for active runs
- [ ] Historical logs accessible
- [ ] Proper error handling
- [ ] UI remains responsive

### Safety Checks
- [ ] Test with concurrent users
- [ ] Verify no file handle leaks
- [ ] Check memory usage with large logs
- [ ] Test log rotation handling

---

## Phase 4: Enhanced GPU Monitoring (1 day)

### Objective
Add comprehensive GPU monitoring to status command.

### Steps

#### 4.1 Create GPU Monitor Module
**Files to create:**
- `cosmos_workflow/monitoring/gpu_monitor.py`

**Implementation:**
```python
import json
from typing import Dict, Any
from cosmos_workflow.connection import SSHManager

class GPUMonitor:
    """Monitor GPU status on remote instance."""

    def __init__(self, ssh_manager: SSHManager):
        self.ssh = ssh_manager

    def get_gpu_status(self) -> Dict[str, Any]:
        """Get detailed GPU status."""
        try:
            # Query comprehensive GPU info
            cmd = (
                "nvidia-smi --query-gpu="
                "name,memory.used,memory.total,utilization.gpu,"
                "temperature.gpu,power.draw,power.limit "
                "--format=csv,noheader,nounits"
            )

            output = self.ssh.execute_command_success(cmd, stream_output=False)

            # Parse output
            values = output.strip().split(", ")

            return {
                "name": values[0],
                "memory_used_mb": int(values[1]),
                "memory_total_mb": int(values[2]),
                "utilization_percent": int(values[3]),
                "temperature_celsius": int(values[4]),
                "power_draw_watts": float(values[5]),
                "power_limit_watts": float(values[6]),
                "memory_usage_percent": round(
                    int(values[1]) / int(values[2]) * 100, 1
                )
            }
        except Exception as e:
            logger.error(f"Failed to get GPU status: {e}")
            return {}

    def get_gpu_processes(self) -> list[Dict[str, Any]]:
        """Get processes running on GPU."""
        try:
            cmd = (
                "nvidia-smi --query-compute-apps="
                "pid,name,used_memory "
                "--format=csv,noheader,nounits"
            )

            output = self.ssh.execute_command_success(cmd, stream_output=False)

            processes = []
            for line in output.strip().split("\n"):
                if line:
                    values = line.split(", ")
                    processes.append({
                        "pid": int(values[0]),
                        "name": values[1],
                        "memory_mb": int(values[2])
                    })

            return processes
        except Exception as e:
            logger.error(f"Failed to get GPU processes: {e}")
            return []
```

#### 4.2 Integrate into Status Command
**Files to modify:**
- `cosmos_workflow/api/workflow_operations.py`
- `cosmos_workflow/cli/status.py`

**Implementation updates to check_status():**
```python
def check_status(self) -> dict[str, Any]:
    """Enhanced status check with GPU monitoring."""
    # ... existing code ...

    # Add GPU monitoring
    gpu_monitor = GPUMonitor(self.orchestrator.ssh_manager)
    gpu_status = gpu_monitor.get_gpu_status()
    gpu_processes = gpu_monitor.get_gpu_processes()

    # Check if our container is using GPU
    running_job = None
    if containers and gpu_processes:
        for process in gpu_processes:
            # Match process to container
            for container in containers:
                if container.get("pid") == process["pid"]:
                    running_job = {
                        "container_id": container["id"],
                        "prompt_id": container.get("labels", {}).get("prompt_id"),
                        "gpu_memory_mb": process["memory_mb"]
                    }

    return {
        "ssh_status": ssh_status,
        "docker_status": docker_status,
        "gpu_info": gpu_status,
        "gpu_processes": gpu_processes,
        "containers": containers,
        "running_job": running_job
    }
```

**Verification:**
- [ ] GPU stats display correctly
- [ ] Process detection works
- [ ] Running job identification
- [ ] Error handling for missing GPU

### Safety Checks
- [ ] Handle nvidia-smi not available
- [ ] Test with no GPU processes
- [ ] Verify SSH connection handling
- [ ] Check performance impact

---

## Phase 5: Container Activity Tracking (1 day)

### Objective
Track and display current container activities.

### Steps

#### 5.1 Add Container Metadata
**Files to modify:**
- `cosmos_workflow/execution/docker_executor.py`

**Implementation:**
```python
def run_inference_with_tracking(
    self,
    prompt_name: str,
    run_id: str,
    log_callback: callable = None,
    **kwargs
):
    """Run inference with activity tracking."""

    # Add labels to container for tracking
    builder = DockerCommandBuilder(self.docker_image)
    builder.add_label("prompt_id", prompt_name)
    builder.add_label("run_id", run_id)
    builder.add_label("start_time", datetime.now().isoformat())
    builder.add_label("operation", "inference")

    # ... rest of implementation ...

    # Get container ID after starting
    container_id = self._get_latest_container_id()

    if log_callback:
        log_callback({"container_id": container_id})

    return container_id
```

#### 5.2 Create Activity Monitor
**Files to create:**
- `cosmos_workflow/monitoring/activity_monitor.py`

**Implementation:**
```python
class ActivityMonitor:
    """Monitor container activities."""

    def get_container_activity(self, container_id: str) -> dict:
        """Get current activity of container."""
        try:
            cmd = f"sudo docker inspect {container_id}"
            output = self.ssh.execute_command_success(cmd)

            info = json.loads(output)[0]
            labels = info.get("Config", {}).get("Labels", {})
            state = info.get("State", {})

            return {
                "container_id": container_id,
                "prompt_id": labels.get("prompt_id"),
                "run_id": labels.get("run_id"),
                "operation": labels.get("operation"),
                "running": state.get("Running", False),
                "started_at": state.get("StartedAt"),
                "status": state.get("Status")
            }
        except Exception as e:
            logger.error(f"Failed to get container activity: {e}")
            return {}
```

**Verification:**
- [ ] Container labels set correctly
- [ ] Activity tracking works
- [ ] Status reflects actual state
- [ ] Handles missing containers

### Safety Checks
- [ ] No sensitive data in labels
- [ ] Container cleanup still works
- [ ] Performance impact minimal
- [ ] Backwards compatibility

---

## Phase 6: Error Recovery & Diagnostics (2 days)

### Objective
Implement comprehensive error handling and diagnostics.

### Steps

#### 6.1 Create Diagnostic Collector
**Files to create:**
- `cosmos_workflow/monitoring/diagnostics.py`

**Implementation:**
```python
class DiagnosticCollector:
    """Collect diagnostics on failure."""

    def collect_diagnostics(
        self,
        run_id: str,
        container_id: str = None
    ) -> Path:
        """Collect comprehensive diagnostics."""

        diag_dir = Path(f"outputs/diagnostics/{run_id}")
        diag_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Collect container logs
        if container_id:
            logs = self._get_container_logs(container_id)
            (diag_dir / f"container_logs_{timestamp}.txt").write_text(logs)

        # Collect GPU state
        gpu_state = self._get_gpu_state()
        (diag_dir / f"gpu_state_{timestamp}.json").write_text(
            json.dumps(gpu_state, indent=2)
        )

        # Collect system resources
        system_info = self._get_system_info()
        (diag_dir / f"system_info_{timestamp}.json").write_text(
            json.dumps(system_info, indent=2)
        )

        # Create summary
        summary = {
            "run_id": run_id,
            "container_id": container_id,
            "timestamp": timestamp,
            "files": list(diag_dir.glob("*"))
        }

        (diag_dir / "summary.json").write_text(
            json.dumps(summary, indent=2, default=str)
        )

        return diag_dir
```

#### 6.2 Integrate Error Recovery
**Files to modify:**
- `cosmos_workflow/workflows/workflow_orchestrator.py`

**Implementation:**
```python
def execute_run_with_recovery(self, run_dict, prompt_dict, **kwargs):
    """Execute run with error recovery."""
    max_retries = kwargs.get("max_retries", 2)
    retry_count = 0

    while retry_count <= max_retries:
        try:
            # Attempt execution
            result = self._execute_run_internal(run_dict, prompt_dict, **kwargs)

            if result["status"] == "success":
                return result

        except Exception as e:
            logger.error(f"Run {run_dict['id']} failed (attempt {retry_count + 1}): {e}")

            # Collect diagnostics
            if retry_count == max_retries:
                diag_collector = DiagnosticCollector(self.ssh_manager)
                diag_path = diag_collector.collect_diagnostics(
                    run_dict["id"],
                    container_id=run_dict.get("container_id")
                )

                # Update run with error info
                self.service.update_run_logging(
                    run_dict["id"],
                    error_info={
                        "message": str(e),
                        "traceback": traceback.format_exc(),
                        "diagnostics_path": str(diag_path)
                    }
                )

                raise

            # Exponential backoff
            wait_time = 2 ** retry_count * 10
            logger.info(f"Retrying in {wait_time} seconds...")
            time.sleep(wait_time)
            retry_count += 1
```

**Verification:**
- [ ] Diagnostics collected on failure
- [ ] Retry mechanism works
- [ ] Error info stored in database
- [ ] No infinite retry loops

### Safety Checks
- [ ] Disk space usage monitored
- [ ] Old diagnostics cleaned up
- [ ] Sensitive data not exposed
- [ ] Recovery doesn't corrupt state

---

## Phase 7: Integration Testing & Optimization (2 days)

### Objective
Comprehensive testing and performance optimization.

### Steps

#### 7.1 Create Integration Tests
**Files to create:**
- `tests/integration/test_logging_infrastructure.py`

**Test Coverage:**
- [ ] Run with logging enabled
- [ ] Log viewer in Gradio
- [ ] GPU monitoring accuracy
- [ ] Error recovery mechanism
- [ ] Diagnostic collection
- [ ] Container tracking

#### 7.2 Performance Testing
- [ ] Log file size impact
- [ ] Streaming performance
- [ ] Database query optimization
- [ ] Memory usage monitoring
- [ ] Concurrent run handling

#### 7.3 Documentation Updates
**Files to update:**
- `README.md` - New logging features
- `docs/architecture.md` - Logging architecture
- `CHANGELOG.md` - Version changes

---

## Rollback Procedures

### For Each Phase
1. Git tag before starting phase: `git tag pre-phase-X`
2. Create feature branch: `git checkout -b logging-phase-X`
3. Test after each component
4. Merge only after verification

### Emergency Rollback
```bash
# Rollback code
git checkout pre-phase-X

# Rollback database
alembic downgrade -1

# Clear log files
rm -rf outputs/*/logs/
rm -rf outputs/diagnostics/
```

---

## Success Metrics

### Functional Metrics
- [ ] All runs create log files
- [ ] Failed runs have diagnostics
- [ ] GPU utilization visible in status
- [ ] Live logs viewable in Gradio
- [ ] Container activities tracked

### Performance Metrics
- [ ] Log streaming < 100ms latency
- [ ] Status command < 2s response
- [ ] Log files < 100MB per run
- [ ] No memory leaks after 100 runs

### Quality Metrics
- [ ] 100% test coverage for new code
- [ ] No regression in existing features
- [ ] Error messages actionable
- [ ] Logs contain sufficient context

---

## Risk Mitigation

### Technical Risks
1. **Log File Growth**
   - Mitigation: Rotation, compression, cleanup

2. **Performance Impact**
   - Mitigation: Async logging, buffering

3. **SSH Connection Issues**
   - Mitigation: Connection pooling, retry logic

4. **Database Migration Failures**
   - Mitigation: Backup, test migrations, rollback plan

### Operational Risks
1. **Disk Space**
   - Monitor usage, implement cleanup

2. **Network Bandwidth**
   - Compress logs, batch operations

3. **Concurrent Access**
   - File locking, database transactions

---

## Timeline Summary

| Phase | Duration | Dependencies | Risk Level |
|-------|----------|--------------|------------|
| 1. Centralized Logging | 2-3 days | None | Low |
| 2. Database Schema | 1 day | Phase 1 | Medium |
| 3. Gradio Integration | 2 days | Phase 1, 2 | Low |
| 4. GPU Monitoring | 1 day | Phase 1 | Low |
| 5. Container Tracking | 1 day | Phase 1, 2 | Low |
| 6. Error Recovery | 2 days | Phase 1, 2, 5 | Medium |
| 7. Testing & Optimization | 2 days | All phases | Low |

**Total Timeline: 11-12 days**

---

## Appendix A: File Change Summary

### New Files
- `cosmos_workflow/utils/logging.py`
- `cosmos_workflow/ui/components/log_viewer.py`
- `cosmos_workflow/monitoring/gpu_monitor.py`
- `cosmos_workflow/monitoring/activity_monitor.py`
- `cosmos_workflow/monitoring/diagnostics.py`
- `tests/integration/test_logging_infrastructure.py`

### Modified Files
- `cosmos_workflow/database/models.py`
- `cosmos_workflow/services/workflow_service.py`
- `cosmos_workflow/workflows/workflow_orchestrator.py`
- `cosmos_workflow/execution/docker_executor.py`
- `cosmos_workflow/api/workflow_operations.py`
- `cosmos_workflow/cli/status.py`
- `cosmos_workflow/ui/app.py`

### Configuration Changes
- `requirements.txt` - Add loguru
- `alembic/versions/` - New migration file

---

## Appendix B: Testing Checklist

### Unit Tests
- [ ] Logger initialization
- [ ] Log file creation
- [ ] GPU monitor parsing
- [ ] Diagnostic collection
- [ ] Error recovery logic

### Integration Tests
- [ ] End-to-end run with logging
- [ ] Gradio log viewer updates
- [ ] Status command enhancements
- [ ] Database field updates
- [ ] Error scenarios

### Manual Tests
- [ ] Create prompt → inference → view logs
- [ ] Trigger failure → check diagnostics
- [ ] Monitor GPU during run
- [ ] Concurrent run logging
- [ ] Log rotation behavior

---

## Appendix C: Monitoring Queries

### Useful SQL Queries
```sql
-- Find failed runs with diagnostics
SELECT id, prompt_id, error_message, diagnostics_path
FROM runs
WHERE status = 'failed'
  AND diagnostics_path IS NOT NULL;

-- Get runs by container
SELECT id, prompt_id, container_id, status
FROM runs
WHERE container_id = ?;

-- Recent runs with logs
SELECT id, prompt_id, log_path, created_at
FROM runs
WHERE log_path IS NOT NULL
ORDER BY created_at DESC
LIMIT 10;
```

### Useful Shell Commands
```bash
# Monitor active containers
watch -n 2 'sudo docker ps --format "table {{.ID}}\t{{.Labels}}\t{{.Status}}"'

# Check GPU utilization
watch -n 1 nvidia-smi

# Tail all recent logs
tail -f outputs/*/logs/*.log

# Find large log files
find outputs -name "*.log" -size +10M

# Clean old diagnostics
find outputs/diagnostics -mtime +7 -delete
```

---

## Sign-off Checklist

### Before Starting
- [ ] Backup current system
- [ ] Document current behavior
- [ ] Review with team
- [ ] Set up test environment

### After Completion
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Performance acceptable
- [ ] Rollback tested
- [ ] Team training completed

---

*Document Version: 1.0*
*Last Updated: 2025-01-06*
*Author: NAT*