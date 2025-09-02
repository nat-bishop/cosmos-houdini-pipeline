#!/usr/bin/env python3
"""Common utilities for workflow operations.

Provides reusable functions for workflow orchestration.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def ensure_path_exists(path: Path) -> Path:
    """Ensure a directory path exists, creating it if necessary.

    Args:
        path: Path to ensure exists (file or directory).

    Returns:
        The directory path that was created or verified.
    """
    path = Path(path)
    # Check if it's a file path (has an extension) or already exists as a file
    if path.suffix or path.is_file():
        path = path.parent
    path.mkdir(parents=True, exist_ok=True)
    return path


def format_duration(seconds: float) -> str:
    """Format duration in seconds to a human-readable string.

    Args:
        seconds: Duration in seconds.

    Returns:
        Human-readable duration string (e.g., "2h 15m 30s").
    """
    hours, remainder = divmod(int(seconds), 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"


def log_workflow_event(
    event_type: str, workflow_name: str, metadata: dict[str, Any], log_dir: Path = Path("notes")
) -> None:
    """Log a workflow event to the run history.

    Args:
        event_type: Type of event (e.g., "SUCCESS", "FAILED", "STARTED")
        workflow_name: Name of the workflow
        metadata: Additional metadata to log
        log_dir: Directory for log files
    """
    ensure_path_exists(log_dir)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    log_entry = f"{timestamp} | {event_type} | workflow={workflow_name}"

    for key, value in metadata.items():
        log_entry += f" | {key}={value}"

    log_entry += "\n"

    run_history_file = log_dir / "run_history.log"
    with open(run_history_file, "a") as f:
        f.write(log_entry)

    logger.info("Logged %s event to {run_history_file}", event_type)


def validate_gpu_configuration(num_gpu: int, cuda_devices: str) -> bool:
    """Validate GPU configuration parameters.

    Args:
        num_gpu: Number of GPUs to use.
        cuda_devices: Comma-separated CUDA device IDs.

    Returns:
        True if configuration is valid, False otherwise.
    """
    if num_gpu <= 0:
        logger.error("Invalid num_gpu: %s", num_gpu)
        return False

    device_list = cuda_devices.split(",")
    if len(device_list) != num_gpu:
        logger.error("num_gpu (%s) doesn't match device count ({len(device_list)})", num_gpu)
        return False

    try:
        device_ids = [int(d.strip()) for d in device_list]
        if any(d < 0 for d in device_ids):
            logger.error("Invalid CUDA device ID in: %s", cuda_devices)
            return False
    except ValueError:
        logger.error("Invalid CUDA device string: %s", cuda_devices)
        return False

    return True
