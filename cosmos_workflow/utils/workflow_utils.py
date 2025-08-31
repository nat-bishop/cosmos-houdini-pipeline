#!/usr/bin/env python3
"""Common utilities for workflow operations.
Provides reusable functions and abstractions for workflow orchestration.
"""

import logging
from collections.abc import Callable
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class WorkflowStep:
    """Represents a single step in a workflow."""

    def __init__(
        self, name: str, function: Callable, emoji: str = "➡️", description: str | None = None
    ):
        self.name = name
        self.function = function
        self.emoji = emoji
        self.description = description or name

    def execute(self, *args, **kwargs) -> Any:
        """Execute the workflow step with logging."""
        logger.info("Executing step: %s", self.name)
        print(f"\n{self.emoji} {self.description}")
        return self.function(*args, **kwargs)


class WorkflowExecutor:
    """Executes a series of workflow steps with proper error handling."""

    def __init__(self, name: str = "workflow"):
        self.name = name
        self.steps: list[WorkflowStep] = []
        self.start_time: datetime | None = None
        self.end_time: datetime | None = None

    def add_step(self, step: WorkflowStep) -> "WorkflowExecutor":
        """Add a step to the workflow."""
        self.steps.append(step)
        return self

    def execute(self, context: dict[str, Any], stop_on_error: bool = True) -> dict[str, Any]:
        """Execute all workflow steps.

        Args:
            context: Shared context passed between steps
            stop_on_error: Whether to stop execution on first error

        Returns:
            Execution result with status and metadata
        """
        self.start_time = datetime.now()
        steps_completed = []

        try:
            for step in self.steps:
                try:
                    result = step.execute(**context)
                    steps_completed.append(step.name)

                    # Update context if step returns a dict
                    if isinstance(result, dict):
                        context.update(result)

                except Exception as e:
                    logger.error("Step %s failed: {e}", step.name)
                    if stop_on_error:
                        raise
                    else:
                        context[f"{step.name}_error"] = str(e)

            self.end_time = datetime.now()
            duration = self.end_time - self.start_time

            return {
                "status": "success",
                "workflow": self.name,
                "steps_completed": steps_completed,
                "start_time": self.start_time.isoformat(),
                "end_time": self.end_time.isoformat(),
                "duration_seconds": duration.total_seconds(),
                "context": context,
            }

        except Exception as e:
            self.end_time = datetime.now()
            duration = self.end_time - self.start_time

            return {
                "status": "failed",
                "workflow": self.name,
                "steps_completed": steps_completed,
                "start_time": self.start_time.isoformat(),
                "end_time": self.end_time.isoformat(),
                "duration_seconds": duration.total_seconds(),
                "error": str(e),
                "context": context,
            }


def with_retry(max_attempts: int = 3, delay: float = 1.0):
    """Decorator to retry a function on failure.

    Args:
        max_attempts: Maximum number of retry attempts
        delay: Delay between retries in seconds
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            import time

            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning("Attempt %s failed: {e}. Retrying...", attempt + 1)
                        time.sleep(delay)
                    else:
                        logger.error("All %s attempts failed", max_attempts)

            raise last_exception

        return wrapper

    return decorator


def ensure_path_exists(path: Path) -> Path:
    """Ensure a directory path exists, creating it if necessary."""
    path = Path(path)
    # Check if it's a file path (has an extension) or already exists as a file
    if path.suffix or path.is_file():
        path = path.parent
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_video_directories(prompt_file: Path, videos_subdir: str | None = None) -> list[Path]:
    """Get video directories based on prompt file and optional override.

    Args:
        prompt_file: Path to prompt file
        videos_subdir: Optional subdirectory override

    Returns:
        List of video directory paths
    """
    if videos_subdir:
        return [Path(f"inputs/videos/{videos_subdir}")]
    else:
        prompt_name = prompt_file.stem
        return [Path(f"inputs/videos/{prompt_name}")]


def format_duration(seconds: float) -> str:
    """Format duration in seconds to a human-readable string."""
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

    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    log_entry = f"{timestamp} | {event_type} | workflow={workflow_name}"

    for key, value in metadata.items():
        log_entry += f" | {key}={value}"

    log_entry += "\n"

    run_history_file = log_dir / "run_history.log"
    with open(run_history_file, "a") as f:
        f.write(log_entry)

    logger.info("Logged %s event to {run_history_file}", event_type)


class ServiceManager:
    """Manages initialization and cleanup of workflow services."""

    def __init__(self):
        self.services: dict[str, Any] = {}
        self.initialized = False

    def register_service(self, name: str, service: Any) -> None:
        """Register a service."""
        self.services[name] = service

    def get_service(self, name: str) -> Any:
        """Get a registered service."""
        if name not in self.services:
            raise KeyError(f"Service {name} not registered")
        return self.services[name]

    def initialize_all(self) -> None:
        """Initialize all registered services."""
        if self.initialized:
            return

        for name, service in self.services.items():
            if hasattr(service, "initialize"):
                logger.info("Initializing service: %s", name)
                service.initialize()

        self.initialized = True

    def cleanup_all(self) -> None:
        """Cleanup all registered services."""
        for name, service in self.services.items():
            if hasattr(service, "cleanup"):
                logger.info("Cleaning up service: %s", name)
                service.cleanup()

        self.initialized = False

    def __enter__(self):
        """Context manager entry."""
        self.initialize_all()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup_all()


def validate_gpu_configuration(num_gpu: int, cuda_devices: str) -> bool:
    """Validate GPU configuration parameters.

    Args:
        num_gpu: Number of GPUs to use
        cuda_devices: Comma-separated CUDA device IDs

    Returns:
        True if configuration is valid
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


def merge_configs(*configs: dict[str, Any]) -> dict[str, Any]:
    """Merge multiple configuration dictionaries.
    Later configs override earlier ones.

    Args:
        *configs: Configuration dictionaries to merge

    Returns:
        Merged configuration dictionary
    """
    result = {}
    for config in configs:
        if config:
            result.update(config)
    return result
