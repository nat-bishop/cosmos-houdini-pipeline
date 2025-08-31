#!/usr/bin/env python3
"""
Test workflow utilities module.
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from cosmos_workflow.utils.workflow_utils import (
    ServiceManager,
    WorkflowExecutor,
    WorkflowStep,
    ensure_path_exists,
    format_duration,
    get_video_directories,
    log_workflow_event,
    merge_configs,
    validate_gpu_configuration,
    with_retry,
)


class TestWorkflowStep:
    """Test WorkflowStep class."""

    def test_init(self):
        """Test WorkflowStep initialization."""
        func = MagicMock()
        step = WorkflowStep("test_step", func, "🔧", "Test Step")

        assert step.name == "test_step"
        assert step.function == func
        assert step.emoji == "🔧"
        assert step.description == "Test Step"

    def test_init_default_description(self):
        """Test WorkflowStep with default description."""
        func = MagicMock()
        step = WorkflowStep("test_step", func)

        assert step.description == "test_step"

    def test_execute(self, capsys):
        """Test WorkflowStep execution."""
        func = MagicMock(return_value="result")
        step = WorkflowStep("test_step", func, "🔧", "Test Step")

        result = step.execute(arg1="value1", arg2="value2")

        assert result == "result"
        func.assert_called_once_with(arg1="value1", arg2="value2")

        captured = capsys.readouterr()
        assert "🔧 Test Step" in captured.out


class TestWorkflowExecutor:
    """Test WorkflowExecutor class."""

    def test_init(self):
        """Test WorkflowExecutor initialization."""
        executor = WorkflowExecutor("test_workflow")

        assert executor.name == "test_workflow"
        assert executor.steps == []
        assert executor.start_time is None
        assert executor.end_time is None

    def test_add_step(self):
        """Test adding steps to workflow."""
        executor = WorkflowExecutor()
        step1 = WorkflowStep("step1", MagicMock())
        step2 = WorkflowStep("step2", MagicMock())

        executor.add_step(step1).add_step(step2)

        assert len(executor.steps) == 2
        assert executor.steps[0] == step1
        assert executor.steps[1] == step2

    def test_execute_success(self):
        """Test successful workflow execution."""
        func1 = MagicMock(return_value={"result1": "value1"})
        func2 = MagicMock(return_value={"result2": "value2"})

        executor = WorkflowExecutor("test_workflow")
        executor.add_step(WorkflowStep("step1", func1))
        executor.add_step(WorkflowStep("step2", func2))

        context = {"initial": "context"}
        result = executor.execute(context)

        assert result["status"] == "success"
        assert result["workflow"] == "test_workflow"
        assert result["steps_completed"] == ["step1", "step2"]
        assert "start_time" in result
        assert "end_time" in result
        assert "duration_seconds" in result
        assert result["context"]["initial"] == "context"
        assert result["context"]["result1"] == "value1"
        assert result["context"]["result2"] == "value2"

    def test_execute_failure(self):
        """Test workflow execution with failure."""
        func1 = MagicMock(return_value={"result1": "value1"})
        func2 = MagicMock(side_effect=RuntimeError("Step failed"))

        executor = WorkflowExecutor("test_workflow")
        executor.add_step(WorkflowStep("step1", func1))
        executor.add_step(WorkflowStep("step2", func2))

        context = {"initial": "context"}
        result = executor.execute(context)

        assert result["status"] == "failed"
        assert result["workflow"] == "test_workflow"
        assert result["steps_completed"] == ["step1"]
        assert "error" in result
        assert "Step failed" in result["error"]

    def test_execute_continue_on_error(self):
        """Test workflow execution continuing after error."""
        func1 = MagicMock(return_value={"result1": "value1"})
        func2 = MagicMock(side_effect=RuntimeError("Step failed"))
        func3 = MagicMock(return_value={"result3": "value3"})

        executor = WorkflowExecutor("test_workflow")
        executor.add_step(WorkflowStep("step1", func1))
        executor.add_step(WorkflowStep("step2", func2))
        executor.add_step(WorkflowStep("step3", func3))

        context = {"initial": "context"}
        result = executor.execute(context, stop_on_error=False)

        assert result["status"] == "success"
        assert result["steps_completed"] == ["step1", "step3"]
        assert "step2_error" in result["context"]


class TestServiceManager:
    """Test ServiceManager class."""

    def test_register_and_get_service(self):
        """Test registering and retrieving services."""
        manager = ServiceManager()
        service1 = MagicMock()
        service2 = MagicMock()

        manager.register_service("service1", service1)
        manager.register_service("service2", service2)

        assert manager.get_service("service1") == service1
        assert manager.get_service("service2") == service2

    def test_get_unregistered_service(self):
        """Test getting unregistered service raises error."""
        manager = ServiceManager()

        with pytest.raises(KeyError, match="Service unknown not registered"):
            manager.get_service("unknown")

    def test_initialize_all(self):
        """Test initializing all services."""
        manager = ServiceManager()

        service1 = MagicMock()
        service1.initialize = MagicMock()
        service2 = MagicMock()
        # service2 has no initialize method

        manager.register_service("service1", service1)
        manager.register_service("service2", service2)

        manager.initialize_all()

        service1.initialize.assert_called_once()
        assert manager.initialized is True

        # Calling again should not reinitialize
        manager.initialize_all()
        assert service1.initialize.call_count == 1

    def test_cleanup_all(self):
        """Test cleaning up all services."""
        manager = ServiceManager()

        service1 = MagicMock()
        service1.cleanup = MagicMock()
        service2 = MagicMock()
        # service2 has no cleanup method

        manager.register_service("service1", service1)
        manager.register_service("service2", service2)

        manager.initialized = True
        manager.cleanup_all()

        service1.cleanup.assert_called_once()
        assert manager.initialized is False

    def test_context_manager(self):
        """Test ServiceManager as context manager."""
        manager = ServiceManager()

        service = MagicMock()
        service.initialize = MagicMock()
        service.cleanup = MagicMock()

        manager.register_service("service", service)

        with manager:
            service.initialize.assert_called_once()
            assert manager.initialized is True

        service.cleanup.assert_called_once()
        assert manager.initialized is False


class TestRetryDecorator:
    """Test with_retry decorator."""

    def test_success_first_try(self):
        """Test function succeeds on first try."""

        @with_retry(max_attempts=3, delay=0.01)
        def test_func():
            return "success"

        result = test_func()
        assert result == "success"

    def test_success_after_retry(self):
        """Test function succeeds after retry."""
        attempt_count = 0

        @with_retry(max_attempts=3, delay=0.01)
        def test_func():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                raise RuntimeError("Failed")
            return "success"

        result = test_func()
        assert result == "success"
        assert attempt_count == 2

    def test_all_attempts_fail(self):
        """Test all retry attempts fail."""
        attempt_count = 0

        @with_retry(max_attempts=3, delay=0.01)
        def test_func():
            nonlocal attempt_count
            attempt_count += 1
            raise RuntimeError(f"Failed attempt {attempt_count}")

        with pytest.raises(RuntimeError, match="Failed attempt 3"):
            test_func()

        assert attempt_count == 3


class TestUtilityFunctions:
    """Test utility functions."""

    def test_ensure_path_exists(self, tmp_path):
        """Test ensure_path_exists creates directories."""
        test_dir = tmp_path / "test" / "nested" / "dir"

        result = ensure_path_exists(test_dir)

        assert test_dir.exists()
        assert test_dir.is_dir()
        assert result == test_dir

    def test_ensure_path_exists_with_file(self, tmp_path):
        """Test ensure_path_exists with file path."""
        test_file = tmp_path / "test" / "file.txt"

        result = ensure_path_exists(test_file)

        assert test_file.parent.exists()
        assert test_file.parent.is_dir()
        assert result == test_file.parent

    def test_get_video_directories_with_subdir(self):
        """Test get_video_directories with subdirectory override."""
        prompt_file = Path("prompts/test_prompt.json")

        dirs = get_video_directories(prompt_file, "custom_videos")

        assert len(dirs) == 1
        assert dirs[0] == Path("inputs/videos/custom_videos")

    def test_get_video_directories_from_prompt_name(self):
        """Test get_video_directories from prompt filename."""
        prompt_file = Path("prompts/test_prompt.json")

        dirs = get_video_directories(prompt_file)

        assert len(dirs) == 1
        assert dirs[0] == Path("inputs/videos/test_prompt")

    def test_format_duration_seconds(self):
        """Test format_duration for seconds only."""
        assert format_duration(45) == "45s"
        assert format_duration(59) == "59s"

    def test_format_duration_minutes(self):
        """Test format_duration for minutes and seconds."""
        assert format_duration(65) == "1m 5s"
        assert format_duration(125) == "2m 5s"
        assert format_duration(3599) == "59m 59s"

    def test_format_duration_hours(self):
        """Test format_duration for hours, minutes and seconds."""
        assert format_duration(3600) == "1h 0m 0s"
        assert format_duration(3665) == "1h 1m 5s"
        assert format_duration(7325) == "2h 2m 5s"

    @patch("builtins.open", new_callable=mock_open)
    @patch("cosmos_workflow.utils.workflow_utils.ensure_path_exists")
    def test_log_workflow_event(self, mock_ensure_path, mock_file):
        """Test log_workflow_event writes to file."""
        log_workflow_event(
            "SUCCESS", "test_workflow", {"prompt": "test.json", "duration": "5m"}, Path("notes")
        )

        mock_ensure_path.assert_called_once_with(Path("notes"))
        mock_file.assert_called_once_with(Path("notes/run_history.log"), "a")

        handle = mock_file()
        written_content = handle.write.call_args[0][0]

        assert "SUCCESS" in written_content
        assert "workflow=test_workflow" in written_content
        assert "prompt=test.json" in written_content
        assert "duration=5m" in written_content

    def test_validate_gpu_configuration_valid(self):
        """Test validate_gpu_configuration with valid config."""
        assert validate_gpu_configuration(1, "0") is True
        assert validate_gpu_configuration(2, "0,1") is True
        assert validate_gpu_configuration(4, "0,1,2,3") is True

    def test_validate_gpu_configuration_invalid(self):
        """Test validate_gpu_configuration with invalid config."""
        assert validate_gpu_configuration(0, "0") is False  # Invalid num_gpu
        assert validate_gpu_configuration(-1, "0") is False  # Negative num_gpu
        assert validate_gpu_configuration(2, "0") is False  # Mismatch count
        assert validate_gpu_configuration(1, "0,1") is False  # Mismatch count
        assert validate_gpu_configuration(1, "-1") is False  # Negative device ID
        assert validate_gpu_configuration(1, "abc") is False  # Invalid device string

    def test_merge_configs(self):
        """Test merge_configs function."""
        config1 = {"a": 1, "b": 2}
        config2 = {"b": 3, "c": 4}
        config3 = {"c": 5, "d": 6}

        result = merge_configs(config1, config2, config3)

        assert result == {"a": 1, "b": 3, "c": 5, "d": 6}

    def test_merge_configs_with_none(self):
        """Test merge_configs with None values."""
        config1 = {"a": 1}
        config2 = None
        config3 = {"b": 2}

        result = merge_configs(config1, config2, config3)

        assert result == {"a": 1, "b": 2}
