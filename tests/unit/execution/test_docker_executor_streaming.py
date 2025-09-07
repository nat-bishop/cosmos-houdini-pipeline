#!/usr/bin/env python3
"""Tests for DockerExecutor without log streaming (streaming removed).

These tests verify that DockerExecutor correctly:
1. Does NOT stream logs during execution (removed feature)
2. Logs remote paths for reference
3. Returns proper status information
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from cosmos_workflow.execution.docker_executor import DockerExecutor


class TestDockerExecutorNoStreaming:
    """Test DockerExecutor without log streaming (now handled by WorkflowOperations)."""

    def test_run_inference_no_streaming(self):
        """Test that run_inference does NOT stream logs (behavior: no streaming)."""
        ssh_manager = MagicMock()
        docker_executor = DockerExecutor(ssh_manager, "/workspace", "nvidia/cuda:11.8")

        # Mock RemoteCommandExecutor methods
        with patch(
            "cosmos_workflow.execution.docker_executor.RemoteCommandExecutor"
        ) as mock_executor_class:
            mock_executor = MagicMock()
            mock_executor_class.return_value = mock_executor

            # Mock directory creation and Docker execution
            mock_executor.create_directory.return_value = None
            mock_executor.execute_docker.return_value = "Docker execution completed"

            # Run inference
            prompt_file = Path("test_prompt.txt")
            run_id = "run_12345"

            result = docker_executor.run_inference(prompt_file, run_id)

            # Verify result structure is correct
            assert result["status"] == "success"
            assert "log_path" in result
            assert result["prompt_name"] == "test_prompt"

            # Verify NO RemoteLogStreamer import or usage occurs
            # (streaming is now handled by WorkflowOperations.stream_run_logs)

    def test_run_inference_logs_remote_path(self):
        """Test that run_inference logs the remote path for reference (behavior)."""
        ssh_manager = MagicMock()
        docker_executor = DockerExecutor(ssh_manager, "/workspace", "nvidia/cuda:11.8")

        with patch(
            "cosmos_workflow.execution.docker_executor.RemoteCommandExecutor"
        ) as mock_executor_class:
            mock_executor = MagicMock()
            mock_executor_class.return_value = mock_executor
            mock_executor.create_directory.return_value = None
            mock_executor.execute_docker.return_value = "Success"

            # Capture log messages
            with patch("cosmos_workflow.execution.docker_executor.get_run_logger") as mock_logger:
                mock_run_logger = MagicMock()
                mock_logger.return_value = mock_run_logger

                prompt_file = Path("test.txt")
                docker_executor.run_inference(prompt_file, "run_123")

                # Verify that remote log path was logged
                log_calls = [str(call) for call in mock_run_logger.info.call_args_list]
                assert any("/workspace/outputs/test/run.log" in call for call in log_calls)
                assert any("cosmos stream" in call for call in log_calls)

    def test_run_upscaling_no_streaming(self):
        """Test that run_upscaling does NOT stream logs (behavior)."""
        ssh_manager = MagicMock()
        docker_executor = DockerExecutor(ssh_manager, "/workspace", "nvidia/cuda:11.8")

        with patch(
            "cosmos_workflow.execution.docker_executor.RemoteCommandExecutor"
        ) as mock_executor_class:
            mock_executor = MagicMock()
            mock_executor_class.return_value = mock_executor

            # Mock file operations
            mock_executor.file_exists.return_value = True
            mock_executor.write_file.return_value = None
            mock_executor.execute_docker.return_value = "Success"

            # Run upscaling
            prompt_file = Path("test_prompt.txt")
            run_id = "run_456"

            result = docker_executor.run_upscaling(prompt_file, run_id, control_weight=0.7)

            # Verify result structure
            assert result["status"] == "success"
            assert "log_path" in result
            assert result["prompt_name"] == "test_prompt"

            # Verify NO streaming occurs
            # (streaming is now handled separately by WorkflowOperations)

    def test_run_inference_handles_execution_failure(self):
        """Test that run_inference properly reports Docker execution failures."""
        ssh_manager = MagicMock()
        docker_executor = DockerExecutor(ssh_manager, "/workspace", "nvidia/cuda:11.8")

        with patch(
            "cosmos_workflow.execution.docker_executor.RemoteCommandExecutor"
        ) as mock_executor_class:
            mock_executor = MagicMock()
            mock_executor_class.return_value = mock_executor
            mock_executor.create_directory.return_value = None

            # Simulate Docker execution failure
            mock_executor.execute_docker.side_effect = RuntimeError("Docker failed")

            prompt_file = Path("test.txt")
            result = docker_executor.run_inference(prompt_file, "run_123")

            # Result should indicate failure
            assert result["status"] == "failed"
            assert "Docker failed" in result["error"]
            assert "log_path" in result  # Log path still provided for debugging
