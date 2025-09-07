# Logging & Monitoring Infrastructure Implementation Plan v2

## Executive Summary
This document outlines a streamlined plan to improve logging and monitoring for the Cosmos Houdini Experiments project. The implementation focuses on minimal changes, efficiency, and working with the existing remote execution model.

**Key Architecture Facts:**
- Scripts run on remote GPU instances inside Docker containers
- Logs are captured via `tee` in bash scripts to `outputs/${PROMPT_NAME}/run.log` on remote
- Files are transferred back via SFTP after completion
- We'll use seek-based position tracking (like Nvidia) to efficiently stream logs

## Current State Analysis

### Existing Issues
1. Split logging methods (`run_inference` vs `run_inference_with_logging`)
2. Docker log following doesn't work well (containers stop)
3. Logging only enabled for UI, not CLI
4. No persistent log storage in database
5. Poor error diagnostics

### What's Working Well
- SFTP file transfer is efficient and reliable (keep as-is)
- `tee` in bash scripts captures output effectively
- Basic status tracking in database

## Implementation Phases

---

## Phase 1: Centralized Logging System (2-3 days)

### Objective
Establish unified logging with Loguru and remove duplicate methods.

### Steps

#### 1.1 Install and Configure Loguru
```bash
# Add to requirements.txt
loguru==0.7.2
```

**Files to create:**
- `cosmos_workflow/utils/logging.py`

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

    # Console handler with clean format
    logger.add(
        sys.stdout,
        level=level,
        format="[{time:HH:mm:ss}|{level}|{name}:{line}] {message}",
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

# Initialize default logger
logger = init_logger()
```

#### 1.2 Unify Inference Methods
**Files to modify:**
- `cosmos_workflow/execution/docker_executor.py` - Remove `run_inference_with_logging`, enhance `run_inference`
- `cosmos_workflow/workflows/workflow_orchestrator.py` - Remove `enable_logging` logic

**New unified method:**
```python
def run_inference(self, prompt_file: Path, num_gpu: int = 1, cuda_devices: str = "0", run_id: str = None) -> dict:
    """Run inference with automatic logging."""
    prompt_name = prompt_file.stem

    # Always setup logging
    log_dir = Path(f"outputs/{prompt_name}/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    local_log_path = log_dir / f"run_{run_id}.log"

    logger.info(f"Starting inference for {prompt_name} (run: {run_id})")

    # Start remote execution
    self._run_inference_script(prompt_name, num_gpu, cuda_devices)

    # Stream logs from remote
    remote_log = f"{self.remote_dir}/outputs/{prompt_name}/run.log"
    self._stream_remote_log(remote_log, local_log_path)

    return {"log_path": str(local_log_path)}
```

#### 1.3 Replace Existing Logging
**Migration order:**
1. Import new logger in each file
2. Replace `print()` with `logger.info()`
3. Replace `logging.error()` with `logger.error()`
4. Remove `enable_logging` parameters

**Verification:**
- [ ] All methods use unified logging
- [ ] No duplicate with/without logging methods
- [ ] CLI and UI both get logs
- [ ] Tests still pass

---

## Phase 2: Database Schema Updates (1 day)

### Objective
Add minimal fields for log tracking and error messages.

### Steps

#### 2.1 Update Run Model
**Files to modify:**
- `cosmos_workflow/database/models.py`

**Implementation:**
```python
class Run(Base):
    # ... existing fields (including status - keep it!) ...

    # New minimal fields
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

**Verification:**
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
import time
from pathlib import Path
from typing import Optional
from cosmos_workflow.utils.logging import logger

class RemoteLogStreamer:
    """Stream logs from remote using seek position tracking."""

    def __init__(self, ssh_manager):
        self.ssh = ssh_manager

    def stream_remote_log(
        self,
        remote_path: str,
        local_path: Path,
        poll_interval: float = 2.0,
        timeout: int = 3600
    ) -> None:
        """Stream remote log to local file using seek position."""

        last_position = 0
        start_time = time.time()

        with open(local_path, 'w') as local_file:
            while time.time() - start_time < timeout:
                try:
                    # Check if remote file exists
                    check_cmd = f"test -f {remote_path} && echo 'exists'"
                    exists = self.ssh.execute_command_success(
                        check_cmd, stream_output=False
                    ).strip()

                    if exists != 'exists':
                        logger.debug(f"Waiting for remote log: {remote_path}")
                        time.sleep(poll_interval)
                        continue

                    # Get file size
                    size_cmd = f"stat -c %s {remote_path} 2>/dev/null"
                    current_size = int(
                        self.ssh.execute_command_success(size_cmd, stream_output=False).strip()
                    )

                    if current_size > last_position:
                        # Read only new content using tail with byte offset
                        tail_cmd = f"tail -c +{last_position + 1} {remote_path}"
                        new_content = self.ssh.execute_command_success(
                            tail_cmd, stream_output=False
                        )

                        if new_content:
                            local_file.write(new_content)
                            local_file.flush()

                            # Log progress
                            bytes_read = len(new_content.encode('utf-8'))
                            logger.debug(f"Streamed {bytes_read} bytes from remote log")

                            last_position = current_size

                    # Check if container is still running
                    if not self._is_container_running():
                        # Final read to get any remaining content
                        if current_size > last_position:
                            continue  # One more read
                        break

                    time.sleep(poll_interval)

                except Exception as e:
                    logger.error(f"Error streaming log: {e}")
                    time.sleep(poll_interval)

        logger.info(f"Log streaming completed. Total bytes: {last_position}")

    def _is_container_running(self) -> bool:
        """Check if any inference container is running."""
        try:
            cmd = "sudo docker ps --format '{{.Image}}' | grep -q cosmos"
            exit_code, _, _ = self.ssh.execute_command(cmd, timeout=5)
            return exit_code == 0
        except:
            return False
```

#### 3.2 Integrate into Docker Executor
**Files to modify:**
- `cosmos_workflow/execution/docker_executor.py`

**Implementation:**
```python
def run_inference(self, prompt_file: Path, num_gpu: int = 1, cuda_devices: str = "0", run_id: str = None) -> dict:
    """Run inference with automatic log streaming."""
    prompt_name = prompt_file.stem

    # Setup logging
    log_dir = Path(f"outputs/{prompt_name}/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    local_log_path = log_dir / f"run_{run_id}.log"

    logger.info(f"Starting inference for {prompt_name}")

    # Start remote execution (non-blocking)
    self._run_inference_script(prompt_name, num_gpu, cuda_devices)

    # Stream logs while running
    streamer = RemoteLogStreamer(self.ssh_manager)
    remote_log = f"{self.remote_dir}/outputs/{prompt_name}/run.log"

    # This blocks until container stops or timeout
    streamer.stream_remote_log(remote_log, local_log_path)

    logger.info(f"Inference completed for {prompt_name}")

    return {"log_path": str(local_log_path)}
```

#### 3.3 Update File Transfer for Final Log
**Files to modify:**
- `cosmos_workflow/transfer/file_transfer.py`

**Implementation:**
```python
def download_results(self, prompt_file: Path, run_id: str = None) -> dict:
    """Download results including final log file."""
    prompt_name = prompt_file.stem

    # Download outputs directory
    remote_out = f"{self.remote_dir}/outputs/{prompt_name}"
    local_out = Path(f"outputs/{prompt_name}")

    if self.file_exists_remote(remote_out):
        self._sftp_download_dir(remote_out, local_out)

        # Ensure we have the final complete log
        remote_log = f"{remote_out}/run.log"
        if run_id and self.file_exists_remote(remote_log):
            final_log_path = local_out / "logs" / f"run_{run_id}_final.log"
            final_log_path.parent.mkdir(exist_ok=True)
            self.download_file(remote_log, final_log_path)

            logger.info(f"Downloaded final log: {final_log_path}")
            return {"final_log": str(final_log_path)}

    return {}
```

**Verification:**
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
from typing import Dict, Any
import json
from cosmos_workflow.utils.logging import logger

class GPUMonitor:
    """Monitor GPU status on remote instance."""

    def __init__(self, ssh_manager):
        self.ssh = ssh_manager
        self._cache = {}
        self._cache_time = 0
        self._cache_ttl = 5  # 5 second cache

    def get_gpu_status(self) -> Dict[str, Any]:
        """Get GPU status with caching."""
        import time

        # Check cache
        if time.time() - self._cache_time < self._cache_ttl:
            return self._cache

        try:
            # Query GPU info
            cmd = (
                "nvidia-smi --query-gpu="
                "name,memory.used,memory.total,utilization.gpu,"
                "temperature.gpu,power.draw "
                "--format=csv,noheader,nounits"
            )

            output = self.ssh.execute_command_success(cmd, stream_output=False)
            values = output.strip().split(", ")

            result = {
                "name": values[0],
                "memory_used_mb": int(values[1]),
                "memory_total_mb": int(values[2]),
                "utilization_percent": int(values[3]),
                "temperature_celsius": int(values[4]),
                "power_watts": float(values[5]),
                "memory_percent": round(int(values[1]) / int(values[2]) * 100, 1)
            }

            # Update cache
            self._cache = result
            self._cache_time = time.time()

            return result

        except Exception as e:
            logger.error(f"Failed to get GPU status: {e}")
            return {}
```

#### 4.2 Integrate into Status Command
**Files to modify:**
- `cosmos_workflow/api/workflow_operations.py`

**Implementation:**
```python
def check_status(self) -> dict:
    """Check remote GPU instance status."""
    from cosmos_workflow.monitoring.gpu_monitor import GPUMonitor

    # ... existing SSH and Docker checks ...

    # Add GPU monitoring
    gpu_monitor = GPUMonitor(self.orchestrator.ssh_manager)
    gpu_info = gpu_monitor.get_gpu_status()

    # Find running job if any
    running_job = None
    if gpu_info.get("utilization_percent", 0) > 10:
        # Check for our containers
        cmd = "sudo docker ps --format '{{.Names}}' | grep cosmos | head -1"
        container = self.ssh_manager.execute_command_success(cmd, stream_output=False).strip()
        if container:
            # Try to find associated run
            # Look for most recent running status
            runs = self.service.list_runs(status="running", limit=1)
            if runs:
                running_job = {
                    "run_id": runs[0]["id"],
                    "prompt_id": runs[0]["prompt_id"],
                    "gpu_utilization": gpu_info["utilization_percent"]
                }

    return {
        "ssh_status": ssh_status,
        "docker_status": docker_status,
        "gpu_info": gpu_info,
        "running_job": running_job
    }
```

**Verification:**
- [ ] GPU stats display correctly
- [ ] Cache prevents excessive SSH calls
- [ ] Running job detection works

---

## Phase 5: Container Activity Tracking (1 day)

### Objective
Track container activities with minimal overhead.

### Steps

#### 5.1 Add Container Labels
**Files to modify:**
- `cosmos_workflow/execution/command_builder.py`

**Implementation:**
```python
def add_run_labels(self, run_id: str, prompt_id: str):
    """Add labels for tracking."""
    self.add_option(f"--label run_id={run_id}")
    self.add_option(f"--label prompt_id={prompt_id}")
    self.add_option(f"--label start_time={datetime.now().isoformat()}")
```

#### 5.2 Query Container Info
**Implementation in docker_executor.py:**
```python
def get_container_info(self, run_id: str) -> dict:
    """Get container info for a run."""
    try:
        cmd = f"sudo docker ps -a --filter 'label=run_id={run_id}' --format json"
        output = self.ssh_manager.execute_command_success(cmd, stream_output=False)
        if output:
            return json.loads(output.split('\n')[0])
    except:
        pass
    return {}
```

**Verification:**
- [ ] Container labels set correctly
- [ ] Can query by run_id
- [ ] No performance impact

---

## Phase 6: Error Recovery & Diagnostics (2 days)

### Objective
Improve error handling and diagnostics collection.

### Steps

#### 6.1 Enhanced Error Handling
**Files to modify:**
- `cosmos_workflow/workflows/workflow_orchestrator.py`

**Implementation:**
```python
def execute_run(self, run_dict, prompt_dict, **kwargs):
    """Execute run with better error handling."""
    run_id = run_dict["id"]

    try:
        # ... execution code ...

        # Update with log path on success
        self.service.update_run_with_log(run_id, log_path)

    except Exception as e:
        logger.error(f"Run {run_id} failed: {e}")

        # Store error in database
        error_msg = str(e)[:1000]  # Truncate for database
        self.service.update_run_error(run_id, error_msg)

        # Collect diagnostics
        self._collect_diagnostics(run_id, prompt_dict["id"])

        raise
```

#### 6.2 Diagnostic Collection
**Implementation:**
```python
def _collect_diagnostics(self, run_id: str, prompt_id: str):
    """Collect diagnostics on failure."""
    try:
        diag_dir = Path(f"outputs/{prompt_id}/diagnostics")
        diag_dir.mkdir(parents=True, exist_ok=True)

        # Save GPU state
        gpu_info = self.gpu_monitor.get_gpu_status()
        (diag_dir / f"gpu_state_{run_id}.json").write_text(
            json.dumps(gpu_info, indent=2)
        )

        # Save container info if available
        container_info = self.docker_executor.get_container_info(run_id)
        if container_info:
            (diag_dir / f"container_{run_id}.json").write_text(
                json.dumps(container_info, indent=2)
            )

        logger.info(f"Diagnostics saved to {diag_dir}")

    except Exception as e:
        logger.error(f"Failed to collect diagnostics: {e}")
```

**Verification:**
- [ ] Errors stored in database
- [ ] Diagnostics collected on failure
- [ ] No crash on diagnostic failure

---

## Phase 7: Testing & Optimization (2 days)

### Objective
Comprehensive testing of the new logging infrastructure.

### Test Coverage
- [ ] Unified logging method works
- [ ] Log streaming doesn't miss content
- [ ] Database fields populated correctly
- [ ] GPU monitoring accuracy
- [ ] Error handling robust
- [ ] No memory leaks in streaming
- [ ] Performance acceptable

### Performance Targets
- Log streaming latency < 3 seconds
- GPU status query < 1 second (with cache)
- No zombie SSH connections
- Log files < 100MB per run

---

## Phase 8: Documentation Updates (1 day)

### Objective
Update project documentation with new logging standards.

### CLAUDE.md Additions
```markdown
## **Logging Standards**

### **Unified Logging**
- All runs automatically create logs (no separate with/without methods)
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

### Other Documentation
- Update README.md with logging features
- Update architecture.md with logging flow
- Add troubleshooting guide

---

## Key Differences from v1

1. **Minimal database changes** - Just log_path and error_message
2. **No Gradio components** - Removed as requested
3. **Unified logging** - Single method, always logs
4. **Seek-based streaming** - Efficient like Nvidia's approach
5. **Keep SFTP** - No changes to file transfer
6. **2-second polling** - "Pretty often" is good enough

## Timeline Summary

| Phase | Duration | Dependencies | Risk Level |
|-------|----------|--------------|------------|
| 1. Centralized Logging | 2-3 days | None | Low |
| 2. Database Schema | 1 day | Phase 1 | Low |
| 3. Remote Log Streaming | 2 days | Phase 1, 2 | Medium |
| 4. GPU Monitoring | 1 day | Phase 1 | Low |
| 5. Container Tracking | 1 day | Phase 1 | Low |
| 6. Error Recovery | 2 days | Phase 1, 2 | Medium |
| 7. Testing | 2 days | All phases | Low |
| 8. Documentation | 1 day | All phases | Low |

**Total: 12-13 days**

## Success Metrics

- [ ] All runs create logs automatically
- [ ] Logs accessible via database log_path
- [ ] Failed runs have error messages
- [ ] GPU utilization visible in status
- [ ] No duplicate logging methods
- [ ] Efficient log streaming (< 3MB/min bandwidth)
- [ ] Clean diagnostic collection on errors

---

*Document Version: 2.0*
*Last Updated: 2025-01-07*
*Author: NAT*