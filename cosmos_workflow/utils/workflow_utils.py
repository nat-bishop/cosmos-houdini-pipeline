#!/usr/bin/env python3
"""Common utilities for workflow operations.

Provides reusable functions for workflow orchestration.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path

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


def ensure_directory(path: Path | str) -> Path:
    """Ensure directory exists, creating if needed.

    Simplified version for when you know you want a directory.

    Args:
        path: Directory path to ensure exists.

    Returns:
        The Path object for the directory.
    """
    path = Path(path) if isinstance(path, str) else path
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_log_path(operation: str, identifier: str, run_id: str | None = None) -> Path:
    """Get standardized log path for any operation.

    Args:
        operation: Type of operation (e.g., "inference", "upscaling", "batch")
        identifier: Unique identifier (e.g., prompt_name, batch_name)
        run_id: Optional run ID for the log file

    Returns:
        Path to the log file.
    """
    log_dir = Path(f"outputs/{identifier}/{operation}_logs")
    ensure_directory(log_dir)

    if run_id:
        return log_dir / f"{operation}_{run_id}.log"
    else:
        # Use timestamp if no run_id provided
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        return log_dir / f"{operation}_{timestamp}.log"


def sanitize_remote_path(path: str) -> str:
    """Convert Windows paths to POSIX for remote systems.

    Args:
        path: Path string that may contain backslashes.

    Returns:
        Path string with forward slashes only.
    """
    return path.replace("\\", "/")


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
