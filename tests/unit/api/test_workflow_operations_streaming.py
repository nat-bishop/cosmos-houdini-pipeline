"""Tests for WorkflowOperations streaming functionality.

Tests the unified stream_container_logs method that supports both
CLI (stdout) and Gradio (callback) modes.
"""

import time
from unittest.mock import MagicMock, patch

import pytest

from cosmos_workflow.api.cosmos_api import CosmosAPI


class TestStreamContainerLogs:
    """Test the stream_container_logs method."""

    @pytest.fixture
    def mock_ssh_manager(self):
        """Create mock SSH manager."""
        ssh_manager = MagicMock()
        ssh_manager.execute_command.return_value = (0, "log line 1\nlog line 2", "")
        return ssh_manager

    @pytest.fixture
    def mock_docker_executor(self):
        """Create mock Docker executor."""
        docker_executor = MagicMock()
        return docker_executor

    @pytest.fixture
    def mock_orchestrator(self, mock_ssh_manager, mock_docker_executor):
        """Create mock orchestrator with SSH and Docker."""
        orchestrator = MagicMock()
        orchestrator.ssh_manager = mock_ssh_manager
        orchestrator.docker_executor = mock_docker_executor
        return orchestrator

    @pytest.fixture
    def ops(self, mock_orchestrator):
        """Create WorkflowOperations with mocked orchestrator."""
        with patch("cosmos_workflow.api.cosmos_api.init_database"):
            with patch("cosmos_workflow.api.cosmos_api.DataRepository"):
                with patch("cosmos_workflow.api.cosmos_api.GPUExecutor"):
                    ops = CosmosAPI(MagicMock())
                    ops.orchestrator = mock_orchestrator
                    return ops

    def test_stream_container_logs_cli_mode(self, ops, mock_ssh_manager):
        """Test streaming to stdout for CLI (no callback)."""
        container_id = "abc123"

        # Call without callback (CLI mode)
        ops.stream_container_logs(container_id)

        # Should call SSH execute_command with stream_output=True
        mock_ssh_manager.execute_command.assert_called_once_with(
            f"sudo docker logs -f {container_id}", timeout=86400, stream_output=True
        )

    def test_stream_container_logs_gradio_mode(self, ops, mock_ssh_manager):
        """Test streaming with callback for Gradio."""
        container_id = "abc123"
        received_lines = []

        def callback(line):
            received_lines.append(line)

        # Call with callback (Gradio mode)
        ops.stream_container_logs(container_id, callback=callback)

        # Give thread time to execute
        time.sleep(0.1)

        # Should call SSH execute_command with stream_output=False
        mock_ssh_manager.execute_command.assert_called_once_with(
            f"sudo docker logs -f {container_id}", timeout=3600, stream_output=False
        )

        # Check callback received the lines
        assert "log line 1" in received_lines
        assert "log line 2" in received_lines

    def test_stream_container_logs_gradio_with_stderr(self, ops, mock_ssh_manager):
        """Test that stderr is properly prefixed in Gradio mode."""
        container_id = "abc123"
        mock_ssh_manager.execute_command.return_value = (
            1,
            "stdout line",
            "error line 1\nerror line 2",
        )

        received_lines = []

        def callback(line):
            received_lines.append(line)

        # Call with callback
        ops.stream_container_logs(container_id, callback=callback)

        # Give thread time to execute
        time.sleep(0.1)

        # Check callback received both stdout and stderr
        assert "stdout line" in received_lines
        assert "[ERROR] error line 1" in received_lines
        assert "[ERROR] error line 2" in received_lines

    def test_stream_container_logs_gradio_handles_exception(self, ops, mock_ssh_manager):
        """Test that exceptions are handled gracefully in Gradio mode."""
        container_id = "abc123"
        mock_ssh_manager.execute_command.side_effect = Exception("Connection lost")

        received_lines = []

        def callback(line):
            received_lines.append(line)

        # Call with callback
        ops.stream_container_logs(container_id, callback=callback)

        # Give thread time to execute
        time.sleep(0.1)

        # Check callback received error message
        assert any("[ERROR] Stream failed: Connection lost" in line for line in received_lines)

    def test_stream_container_logs_threading_in_gradio_mode(self, ops, mock_ssh_manager):
        """Test that Gradio mode uses threading to avoid blocking."""
        container_id = "abc123"

        # Make execute_command block for a bit
        def slow_execute(*args, **kwargs):
            time.sleep(0.05)
            return (0, "log line", "")

        mock_ssh_manager.execute_command = slow_execute

        # Track if main thread was blocked
        start_time = time.time()

        # Call with callback - should return immediately
        ops.stream_container_logs(container_id, callback=lambda x: None)

        elapsed = time.time() - start_time

        # Should return almost immediately (not wait for execute_command)
        assert elapsed < 0.01, "stream_container_logs blocked the main thread"

    def test_stream_container_logs_filters_empty_lines(self, ops, mock_ssh_manager):
        """Test that empty lines are filtered out in Gradio mode."""
        container_id = "abc123"
        mock_ssh_manager.execute_command.return_value = (
            0,
            "line 1\n\nline 2\n\n\n",  # Multiple empty lines
            "\nerror 1\n\n",  # Empty lines in stderr too
        )

        received_lines = []

        def callback(line):
            received_lines.append(line)

        # Call with callback
        ops.stream_container_logs(container_id, callback=callback)

        # Give thread time to execute
        time.sleep(0.1)

        # Should only receive non-empty lines
        assert received_lines == ["line 1", "line 2", "[ERROR] error 1"]
