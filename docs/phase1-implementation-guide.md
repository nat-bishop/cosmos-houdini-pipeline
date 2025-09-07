# Phase 1: Centralized Logging Implementation Guide

## Overview
This guide provides step-by-step instructions for implementing centralized logging with Loguru, removing duplicate logging methods, and establishing a unified logging approach.

## Step 1.1: Install and Configure Loguru

### A. Update requirements.txt
Add loguru to the project dependencies:
```python
# Add this line to requirements.txt
loguru==0.7.2
```

Then install:
```bash
pip install loguru==0.7.2
```

### B. Create the logging module
Create a new file `cosmos_workflow/utils/logging.py`:

```python
#!/usr/bin/env python3
"""Centralized logging configuration for Cosmos workflow.

This module provides a configured logger instance using loguru,
which should be imported and used throughout the application.
"""

import os
import sys
from pathlib import Path
from typing import Optional

from loguru import logger as _base_logger

# Remove default logger
_base_logger.remove()

def init_logger(
    level: str = None,
    log_file: Optional[Path] = None,
    rotation: str = "100 MB",
    retention: str = "7 days",
    colorize: bool = True
) -> "logger":
    """Initialize and configure the logger.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR). Defaults to env var or INFO.
        log_file: Optional file path for log output
        rotation: When to rotate log file (size or time)
        retention: How long to keep old log files
        colorize: Whether to colorize console output

    Returns:
        Configured logger instance
    """
    # Determine log level
    if level is None:
        level = os.environ.get("LOG_LEVEL", "INFO")

    # Console handler with clean format
    _base_logger.add(
        sys.stdout,
        level=level,
        format="[{time:HH:mm:ss}|<level>{level: <8}</level>|{name}:{line}] {message}",
        colorize=colorize,
        backtrace=True,
        diagnose=False  # Don't show variables in production
    )

    # File handler if specified
    if log_file:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        _base_logger.add(
            log_file,
            level="DEBUG",  # File gets everything
            format="[{time:YYYY-MM-DD HH:mm:ss}|{level}|{name}:{function}:{line}] {message}",
            rotation=rotation,
            retention=retention,
            encoding="utf8",
            backtrace=True,
            diagnose=True  # Include variables in file logs
        )

    return _base_logger

# Initialize default logger for import
logger = init_logger()

# Convenience function for run-specific loggers
def get_run_logger(run_id: str, prompt_name: str) -> "logger":
    """Get a logger configured for a specific run.

    Args:
        run_id: The run ID
        prompt_name: The prompt name

    Returns:
        Logger instance configured for this run
    """
    log_dir = Path(f"outputs/{prompt_name}/logs")
    log_file = log_dir / f"orchestration_{run_id}.log"

    # Create a bound logger with run context
    run_logger = logger.bind(run_id=run_id, prompt=prompt_name)

    # Add file handler for this run
    run_logger.add(
        log_file,
        level="DEBUG",
        format="[{time:HH:mm:ss}|{level}|{extra[run_id]}] {message}",
        filter=lambda record: record["extra"].get("run_id") == run_id
    )

    return run_logger

# Export both logger and functions
__all__ = ["logger", "init_logger", "get_run_logger"]
```

## Step 1.2: Unify Inference Methods

### A. Update docker_executor.py

Remove the duplicate `run_inference_with_logging` method and update `run_inference`:

```python
# cosmos_workflow/execution/docker_executor.py

from cosmos_workflow.utils.logging import logger, get_run_logger

class DockerExecutor:

    def run_inference(
        self,
        prompt_file: Path,
        num_gpu: int = 1,
        cuda_devices: str = "0",
        run_id: Optional[str] = None
    ) -> dict:
        """Run Cosmos-Transfer1 inference on remote instance.

        Note: Logging is now always enabled. The run.log file on remote
        is created by tee in the bash script and will be streamed locally.

        Args:
            prompt_file: Name of prompt file (without path)
            num_gpu: Number of GPUs to use
            cuda_devices: CUDA device IDs to use
            run_id: Optional run ID for tracking

        Returns:
            Dict with log_path and status
        """
        prompt_name = prompt_file.stem

        # Setup run-specific logger if run_id provided
        if run_id:
            run_logger = get_run_logger(run_id, prompt_name)
        else:
            run_logger = logger

        run_logger.info(f"Starting inference for prompt: {prompt_name}")
        run_logger.debug(f"GPU config: num_gpu={num_gpu}, devices={cuda_devices}")

        # Create output directory on remote
        remote_output_dir = f"{self.remote_dir}/outputs/{prompt_name}"
        self.remote_executor.create_directory(remote_output_dir)

        # Setup local log path
        log_dir = Path(f"outputs/{prompt_name}/logs")
        log_dir.mkdir(parents=True, exist_ok=True)

        if run_id:
            local_log_path = log_dir / f"run_{run_id}.log"
        else:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            local_log_path = log_dir / f"run_{timestamp}.log"

        try:
            # Execute inference using bash script
            run_logger.info("Executing inference script on remote...")
            self._run_inference_script(prompt_name, num_gpu, cuda_devices)

            # Note: In Phase 3, we'll add log streaming here
            # For now, just log that inference completed

            run_logger.info(f"Inference completed successfully for {prompt_name}")

            return {
                "status": "success",
                "log_path": str(local_log_path),
                "prompt_name": prompt_name
            }

        except Exception as e:
            run_logger.error(f"Inference failed for {prompt_name}: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "log_path": str(local_log_path)
            }

    # DELETE this method entirely
    # def run_inference_with_logging(...):
    #     """This method is removed - use run_inference instead"""
    #     pass
```

### B. Update workflow_orchestrator.py

Remove the `enable_logging` logic:

```python
# cosmos_workflow/workflows/workflow_orchestrator.py

from cosmos_workflow.utils.logging import logger

class WorkflowOrchestrator:

    def execute_run(self, run_dict: dict, prompt_dict: dict, **kwargs) -> dict:
        """Execute a single run on GPU infrastructure.

        Note: Logging is now always enabled, no need for enable_logging flag.
        """
        prompt_name = prompt_dict["id"]
        run_id = run_dict["id"]

        logger.info(f"Executing run {run_id} for prompt {prompt_name}")

        # Remove this entire block:
        # log_path = None
        # if kwargs.get("enable_logging", False):
        #     log_dir = Path(f"outputs/run_{run_id}")
        #     ...

        try:
            # ... existing upload code ...

            # Update inference call - always pass run_id for logging
            result = self.docker_executor.run_inference(
                prompt_file,
                num_gpu=1,
                cuda_devices="0",
                run_id=run_id  # Always pass run_id
            )

            # Store log path if available
            if result.get("log_path"):
                # This will be implemented in Phase 2
                # self.service.update_run_with_log(run_id, result["log_path"])
                logger.debug(f"Log path for run {run_id}: {result['log_path']}")

            # ... rest of existing code ...
```

## Step 1.3: Replace Print Statements

### Migration Guide

For each file in the codebase, follow this pattern:

1. **Add import at top of file:**
```python
from cosmos_workflow.utils.logging import logger
```

2. **Replace print statements:**
```python
# OLD:
print(f"Connecting to {host}:{port}")

# NEW:
logger.info(f"Connecting to {host}:{port}")
```

3. **Replace logging.* calls:**
```python
# OLD:
import logging
logging.error(f"Failed to connect: {e}")

# NEW:
logger.error(f"Failed to connect: {e}")
```

4. **Use appropriate log levels:**
- `logger.debug()` - Detailed diagnostic info
- `logger.info()` - General informational messages
- `logger.warning()` - Warning messages
- `logger.error()` - Error messages (with exceptions)
- `logger.critical()` - Critical failures

### Files to Update (Priority Order)

1. **cosmos_workflow/execution/docker_executor.py**
   - Replace all print() and logging.info/error calls
   - Remove run_inference_with_logging method

2. **cosmos_workflow/workflows/workflow_orchestrator.py**
   - Remove enable_logging parameter handling
   - Replace print statements

3. **cosmos_workflow/connection/ssh_manager.py**
   - Replace connection status prints

4. **cosmos_workflow/transfer/file_transfer.py**
   - Replace transfer progress prints

5. **cosmos_workflow/services/workflow_service.py**
   - Replace any debug prints

6. **cosmos_workflow/cli/*.py**
   - Keep console.print() for user output
   - Use logger for internal diagnostics

## Step 1.4: Testing Phase 1

### Unit Test Updates

Update tests to work with new logging:

```python
# tests/unit/execution/test_docker_executor.py

def test_run_inference_always_logs(mock_ssh_manager):
    """Test that run_inference always creates logs."""
    executor = DockerExecutor(mock_ssh_manager, "/remote", "cosmos:latest")

    result = executor.run_inference(
        Path("test_prompt.json"),
        run_id="test_run_123"
    )

    # Should always have a log path
    assert "log_path" in result
    assert "test_run_123" in result["log_path"]

def test_run_inference_with_logging_removed():
    """Verify run_inference_with_logging method is removed."""
    executor = DockerExecutor(...)
    assert not hasattr(executor, "run_inference_with_logging")
```

### Manual Testing Checklist

1. **Basic Logging Test:**
```bash
# Set log level via environment
export LOG_LEVEL=DEBUG

# Run a command and verify logging
cosmos create prompt "test" inputs/test_video

# Check for log output with proper format
# [HH:MM:SS|INFO    |module:line] Message
```

2. **File Logging Test:**
```python
# In Python console
from cosmos_workflow.utils.logging import get_run_logger

logger = get_run_logger("test_run", "test_prompt")
logger.info("Test message")

# Verify file created at:
# outputs/test_prompt/logs/orchestration_test_run.log
```

3. **No Duplicate Methods Test:**
```bash
# This should fail (method doesn't exist)
python -c "from cosmos_workflow.execution.docker_executor import DockerExecutor; DockerExecutor(...).run_inference_with_logging(...)"
```

## Verification Checklist

- [ ] Loguru installed successfully
- [ ] cosmos_workflow/utils/logging.py created
- [ ] run_inference_with_logging method removed
- [ ] enable_logging parameter removed
- [ ] Print statements replaced in priority files
- [ ] Tests updated and passing
- [ ] Log format consistent across application
- [ ] No regression in existing functionality

## Common Issues & Solutions

### Issue: Import errors
```python
# If you see: ImportError: cannot import name 'logger'
# Solution: Ensure cosmos_workflow/utils/__init__.py exists
```

### Issue: Log file not created
```python
# Check directory permissions
# Ensure Path.mkdir(parents=True, exist_ok=True) is used
```

### Issue: Colors in log file
```python
# File handlers should have colorize=False (default)
# Only console should have colorize=True
```

## Next Steps

After completing Phase 1:
1. Commit changes with clear message
2. Run full test suite
3. Document any issues encountered
4. Proceed to Phase 2: Database Schema Updates

---

*Phase 1 Implementation Guide v1.0*
*Estimated Time: 2-3 days*
*Dependencies: None*