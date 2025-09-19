#!/usr/bin/env python3
"""Centralized logging configuration for Cosmos workflow.

This module provides a configured logger instance using loguru,
which should be imported and used throughout the application.
"""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger as _base_logger

# Remove default logger
_base_logger.remove()


def init_logger(
    level: str | None = None,
    log_file: Path | None = None,
    file_level: str | None = None,
    retention: str = "30 days",
    colorize: bool = True,
) -> "logger":
    """Initialize and configure the logger.

    Args:
        level: Console log level (DEBUG, INFO, WARNING, ERROR). Defaults to env var or INFO.
        log_file: Optional file path for log output
        file_level: File log level. Defaults to same as console level.
        retention: How long to keep old log files (note: only works with rotation enabled)
        colorize: Whether to colorize console output

    Returns:
        Configured logger instance
    """
    # Determine log levels
    if level is None:
        level = os.environ.get("LOG_LEVEL", "INFO")

    if file_level is None:
        # File defaults to same as console, but can be overridden
        file_level = os.environ.get("FILE_LOG_LEVEL", level)

    # Console handler with clean format
    _base_logger.add(
        sys.stdout,
        level=level,
        format="[{time:HH:mm:ss}|<level>{level: <8}</level>|{name}:{line}] {message}",
        colorize=colorize,
        backtrace=True,
        diagnose=False,  # Don't show variables in production
    )

    # File handler if specified
    if log_file:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        _base_logger.add(
            log_file,
            level=file_level,  # Configurable file log level
            format="[{time:YYYY-MM-DD HH:mm:ss}|{level}|{name}:{function}:{line}] {message}",
            rotation=None,  # No rotation with date-based files to avoid Windows issues
            retention=retention,  # Note: retention doesn't work without rotation
            encoding="utf8",
            backtrace=True,
            diagnose=True,  # Include variables in file logs
            enqueue=True,  # Critical: Thread-safe and multiprocess-safe logging
        )

    return _base_logger


# Initialize default logger for import with file output
# Create logs directory structure
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# Date-based log file - each day gets its own file automatically
# This avoids rotation issues while keeping logs organized
log_filename = f"cosmos_{datetime.now(timezone.utc):%Y-%m-%d}.log"
logger = init_logger(
    log_file=log_dir / log_filename,
    retention="30 days",  # Clean up old daily logs after 30 days
)


# Convenience function for run-specific loggers
def get_run_logger(run_id: str, prompt_name: str) -> "logger":
    """Get a logger configured for a specific run.

    Args:
        run_id: The run ID
        prompt_name: The prompt name

    Returns:
        Logger instance configured for this run
    """
    log_dir = Path(f"outputs/run_{run_id}/logs")
    log_file = log_dir / f"{run_id}.log"

    # Create a bound logger with run context
    run_logger = logger.bind(run_id=run_id, prompt=prompt_name)

    # Add file handler for this run
    run_logger.add(
        log_file,
        level="DEBUG",
        format="[{time:HH:mm:ss}|{level}|{extra[run_id]}] {message}",
        filter=lambda record: record["extra"].get("run_id") == run_id,
        enqueue=True,  # Thread-safe and multiprocess-safe logging
    )

    return run_logger


# Export both logger and functions
__all__ = ["get_run_logger", "init_logger", "logger"]
