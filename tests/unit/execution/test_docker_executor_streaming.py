#!/usr/bin/env python3
"""Tests for DockerExecutor with log streaming integration."""

import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

from cosmos_workflow.execution.docker_executor import DockerExecutor


class TestDockerExecutorLogStreaming:
    """Test DockerExecutor with RemoteLogStreamer integration."""

    def test_run_inference_with_streaming(self):
        """Test that run_inference streams logs during execution."""
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

            # Create a side effect for execute_docker that simulates a longer running process
            def simulate_docker_execution(*args, **kwargs):
                # Simulate a 2-second execution
                time.sleep(0.1)
                return "Docker execution completed"

            mock_executor.execute_docker.side_effect = simulate_docker_execution

            # Mock RemoteLogStreamer
            with patch(
                "cosmos_workflow.execution.docker_executor.RemoteLogStreamer"
            ) as mock_streamer_class:
                mock_streamer = MagicMock()
                mock_streamer_class.return_value = mock_streamer

                # Track if streaming happened in parallel
                streaming_started = threading.Event()
                streaming_completed = threading.Event()

                def simulate_streaming(*args, **kwargs):
                    streaming_started.set()
                    # Simulate streaming for a bit
                    time.sleep(0.05)
                    streaming_completed.set()

                mock_streamer.stream_remote_log.side_effect = simulate_streaming

                # Run inference
                prompt_file = Path("test_prompt.txt")
                run_id = "run_12345"

                result = docker_executor.run_inference(prompt_file, run_id)

                # Verify RemoteLogStreamer was created with ssh_manager
                mock_streamer_class.assert_called_once_with(ssh_manager)

                # Verify streaming was called with correct parameters
                assert mock_streamer.stream_remote_log.called
                call_args = mock_streamer.stream_remote_log.call_args

                # Check remote path
                assert "/workspace/outputs/test_prompt/run.log" in str(call_args[0][0])

                # Check local path (platform-agnostic)
                local_path = call_args[0][1]
                assert isinstance(local_path, Path)
                # Check path components separately for cross-platform compatibility
                assert "run_run_12345.log" in str(local_path)
                assert "test_prompt" in str(local_path)
                assert "logs" in str(local_path)

                # Verify result
                assert result["status"] == "success"
                assert result["log_path"] == str(local_path)
                assert result["prompt_name"] == "test_prompt"

    def test_run_inference_starts_streaming_in_background(self):
        """Test that log streaming runs in background during Docker execution."""
        ssh_manager = MagicMock()
        docker_executor = DockerExecutor(ssh_manager, "/workspace", "nvidia/cuda:11.8")

        with patch(
            "cosmos_workflow.execution.docker_executor.RemoteCommandExecutor"
        ) as mock_executor_class:
            mock_executor = MagicMock()
            mock_executor_class.return_value = mock_executor

            execution_order = []

            def track_docker_execution(*args, **kwargs):
                execution_order.append("docker_start")
                time.sleep(0.1)
                execution_order.append("docker_end")
                return "Done"

            mock_executor.execute_docker.side_effect = track_docker_execution

            with patch(
                "cosmos_workflow.execution.docker_executor.RemoteLogStreamer"
            ) as mock_streamer_class:
                mock_streamer = MagicMock()
                mock_streamer_class.return_value = mock_streamer

                def track_streaming(*args, **kwargs):
                    execution_order.append("stream_start")
                    time.sleep(0.05)
                    execution_order.append("stream_end")

                mock_streamer.stream_remote_log.side_effect = track_streaming

                # Mock threading to track background execution
                with patch(
                    "cosmos_workflow.execution.docker_executor.threading.Thread"
                ) as mock_thread:
                    mock_thread_instance = MagicMock()
                    mock_thread.return_value = mock_thread_instance

                    # Run inference
                    prompt_file = Path("test.txt")
                    docker_executor.run_inference(prompt_file, "run_123")

                    # Verify thread was created for streaming
                    mock_thread.assert_called_once()
                    thread_kwargs = mock_thread.call_args[1]
                    assert thread_kwargs["target"] == mock_streamer.stream_remote_log
                    assert thread_kwargs["daemon"] is True

                    # Verify thread was started
                    mock_thread_instance.start.assert_called_once()

    def test_run_inference_handles_streaming_failure_gracefully(self):
        """Test that Docker execution continues even if streaming fails."""
        ssh_manager = MagicMock()

        with patch(
            "cosmos_workflow.execution.docker_executor.RemoteCommandExecutor"
        ) as mock_executor_class:
            mock_executor = MagicMock()
            mock_executor_class.return_value = mock_executor

            # Mock directory creation and Docker execution
            mock_executor.create_directory.return_value = None
            mock_executor.execute_docker.return_value = "Success"

            # Create docker executor after mocking RemoteCommandExecutor
            docker_executor = DockerExecutor(ssh_manager, "/workspace", "nvidia/cuda:11.8")

            with patch(
                "cosmos_workflow.execution.docker_executor.RemoteLogStreamer"
            ) as mock_streamer_class:
                mock_streamer = MagicMock()
                mock_streamer_class.return_value = mock_streamer

                # Mock threading.Thread to prevent actual thread execution
                with patch(
                    "cosmos_workflow.execution.docker_executor.threading.Thread"
                ) as mock_thread:
                    mock_thread_instance = MagicMock()
                    mock_thread.return_value = mock_thread_instance
                    # Mock join method to do nothing (no wait)
                    mock_thread_instance.join.return_value = None

                    # Simulate streaming error that would be logged but not crash
                    mock_streamer.stream_remote_log.side_effect = RuntimeError(
                        "SSH connection lost"
                    )

                    # Run inference - should still succeed
                    prompt_file = Path("test.txt")
                    result = docker_executor.run_inference(prompt_file, "run_123")

                    # Result should indicate success despite streaming issues
                    assert result["status"] == "success"
                    assert "log_path" in result

                    # Verify Docker execution was not affected
                    mock_executor.execute_docker.assert_called_once()

                    # Verify thread was created and started (even though streaming would fail)
                    mock_thread_instance.start.assert_called_once()
                    mock_thread_instance.join.assert_called_once()

    def test_run_upscaling_with_streaming(self):
        """Test that run_upscaling also streams logs during execution."""
        ssh_manager = MagicMock()
        docker_executor = DockerExecutor(ssh_manager, "/workspace", "nvidia/cuda:11.8")

        with patch(
            "cosmos_workflow.execution.docker_executor.RemoteCommandExecutor"
        ) as mock_executor_class:
            mock_executor = MagicMock()
            mock_executor_class.return_value = mock_executor

            # Mock file existence check
            mock_executor.file_exists.return_value = True
            mock_executor.write_file.return_value = None
            mock_executor.execute_docker.return_value = "Success"

            with patch(
                "cosmos_workflow.execution.docker_executor.RemoteLogStreamer"
            ) as mock_streamer_class:
                mock_streamer = MagicMock()
                mock_streamer_class.return_value = mock_streamer

                # Run upscaling
                prompt_file = Path("test_prompt.txt")
                run_id = "run_456"

                result = docker_executor.run_upscaling(prompt_file, run_id, control_weight=0.7)

                # Verify streaming was called for upscaling
                mock_streamer.stream_remote_log.assert_called_once()
                call_args = mock_streamer.stream_remote_log.call_args

                # Check paths for upscaling
                assert "/workspace/outputs/test_prompt_upscaled/run.log" in str(call_args[0][0])
                local_path = call_args[0][1]
                # Platform-agnostic path checking
                assert "run_run_456.log" in str(local_path)
                assert "test_prompt_upscaled" in str(local_path)
                assert "logs" in str(local_path)

                # Verify result
                assert result["status"] == "success"
                assert result["log_path"] == str(local_path)
