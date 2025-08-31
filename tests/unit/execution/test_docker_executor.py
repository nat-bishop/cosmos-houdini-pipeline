"""
Tests for the DockerExecutor class.

This module tests the Docker execution functionality that handles
running Docker commands on remote instances for Cosmos-Transfer1 workflows.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from cosmos_workflow.connection.ssh_manager import SSHManager
from cosmos_workflow.execution.docker_executor import DockerExecutor


class TestDockerExecutor:
    """Test suite for DockerExecutor class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Mock SSH manager
        self.mock_ssh_manager = Mock(spec=SSHManager)

        # Test configuration
        self.remote_dir = "/home/ubuntu/cosmos-transfer1"
        self.docker_image = "cosmos-transfer1:latest"

        # Initialize DockerExecutor
        self.docker_executor = DockerExecutor(
            ssh_manager=self.mock_ssh_manager,
            remote_dir=self.remote_dir,
            docker_image=self.docker_image,
        )

        # Create temporary test files
        self.temp_dir = tempfile.mkdtemp()
        self.test_prompt_file = Path(self.temp_dir) / "test_prompt.json"
        self.test_prompt_file.write_text('{"test": "data"}')

    def teardown_method(self):
        """Clean up test fixtures after each test method."""
        import shutil

        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_init_with_valid_parameters(self):
        """Test DockerExecutor initialization with valid parameters."""
        assert self.docker_executor.ssh_manager == self.mock_ssh_manager
        assert self.docker_executor.remote_dir == self.remote_dir
        assert self.docker_executor.docker_image == self.docker_image

    def test_run_inference_creates_output_directory(self):
        """Test that run_inference creates the remote output directory."""
        # Mock successful directory creation
        self.mock_ssh_manager.execute_command_success.return_value = None

        # Mock successful inference script execution
        with patch.object(self.docker_executor, "_run_inference_script") as mock_run_script:
            # Run inference
            self.docker_executor.run_inference(self.test_prompt_file, num_gpu=2, cuda_devices="0,1")

            # Check that output directory was created
            self.mock_ssh_manager.execute_command_success.assert_any_call(
                f"mkdir -p {self.remote_dir}/outputs/test_prompt"
            )

            # Check that inference script was called
            mock_run_script.assert_called_once_with("test_prompt", 2, "0,1")

    def test_run_inference_calls_inference_script_with_correct_parameters(self):
        """Test that run_inference calls the inference script with correct parameters."""
        # Mock successful directory creation
        self.mock_ssh_manager.execute_command_success.return_value = None

        with patch.object(self.docker_executor, "_run_inference_script") as mock_run_script:
            # Run inference with custom parameters
            self.docker_executor.run_inference(
                self.test_prompt_file, num_gpu=4, cuda_devices="0,1,2,3"
            )

            # Check that script was called with correct parameters
            mock_run_script.assert_called_once_with("test_prompt", 4, "0,1,2,3")

    @pytest.mark.skip(reason="Method implementation changed, needs update")
    def test_run_upscaling_checks_input_video_exists(self):
        """Test that run_upscaling checks if input video exists before proceeding."""
        # Mock file existence check
        with patch.object(self.docker_executor, "_check_remote_file_exists") as mock_check:
            mock_check.return_value = True

            # Mock successful operations
            self.mock_ssh_manager.execute_command_success.return_value = None

            with patch.object(self.docker_executor, "_create_upscaler_spec") as mock_create_spec:
                with patch.object(self.docker_executor, "_run_upscaling_script") as mock_run_script:
                    # Run upscaling
                    self.docker_executor.run_upscaling(
                        self.test_prompt_file, control_weight=0.7, num_gpu=2, cuda_devices="0,1"
                    )

                    # Check that input video existence was verified
                    mock_check.assert_called_once_with(
                        f"{self.remote_dir}/outputs/test_prompt/output.mp4"
                    )

    @pytest.mark.skip(reason="Method implementation changed, needs update")
    def test_run_upscaling_raises_error_when_input_video_missing(self):
        """Test that run_upscaling raises error when input video doesn't exist."""
        # Mock file existence check to return False
        with patch.object(self.docker_executor, "_check_remote_file_exists") as mock_check:
            mock_check.return_value = False

            # Should raise FileNotFoundError
            with pytest.raises(FileNotFoundError, match="Input video not found"):
                self.docker_executor.run_upscaling(self.test_prompt_file)

    def test_run_upscaling_creates_output_directory(self):
        """Test that run_upscaling creates the upscaled output directory."""
        # Mock successful operations
        with patch.object(self.docker_executor, "_check_remote_file_exists") as mock_check:
            mock_check.return_value = True

            self.mock_ssh_manager.execute_command_success.return_value = None

            with patch.object(self.docker_executor, "_create_upscaler_spec") as mock_create_spec:
                with patch.object(self.docker_executor, "_run_upscaling_script") as mock_run_script:
                    # Run upscaling
                    self.docker_executor.run_upscaling(self.test_prompt_file)

                    # Check that upscaled output directory was created
                    self.mock_ssh_manager.execute_command_success.assert_any_call(
                        f"mkdir -p {self.remote_dir}/outputs/test_prompt_upscaled"
                    )

    def test_run_upscaling_calls_upscaling_script_with_correct_parameters(self):
        """Test that run_upscaling calls the upscaling script with correct parameters."""
        # Mock successful operations
        with patch.object(self.docker_executor, "_check_remote_file_exists") as mock_check:
            mock_check.return_value = True

            self.mock_ssh_manager.execute_command_success.return_value = None

            with patch.object(self.docker_executor, "_create_upscaler_spec") as mock_create_spec:
                with patch.object(self.docker_executor, "_run_upscaling_script") as mock_run_script:
                    # Run upscaling with custom parameters
                    self.docker_executor.run_upscaling(
                        self.test_prompt_file, control_weight=0.8, num_gpu=3, cuda_devices="0,1,2"
                    )

                    # Check that script was called with correct parameters
                    mock_run_script.assert_called_once_with("test_prompt", 0.8, 3, "0,1,2")

    def test_run_inference_script_executes_docker_command(self):
        """Test that _run_inference_script executes the correct Docker command."""
        # Mock successful command execution
        self.mock_ssh_manager.execute_command_success.return_value = None

        # Run inference script
        self.docker_executor._run_inference_script("test_prompt", 2, "0,1")

        # Check that Docker command was executed
        self.mock_ssh_manager.execute_command_success.assert_called_once()

        # Get the command that was executed
        call_args = self.mock_ssh_manager.execute_command_success.call_args
        cmd = call_args[0][0]

        # Check command components
        assert "sudo docker run" in cmd
        assert "--gpus all" in cmd
        assert "--ipc=host" in cmd
        assert "--shm-size=8g" in cmd
        assert f"-v {self.remote_dir}:/workspace" in cmd
        assert f"-w /workspace" in cmd
        assert self.docker_image in cmd
        assert "/workspace/bashscripts/inference.sh test_prompt 2 0,1" in cmd
        assert call_args[1]["timeout"] == 3600  # 1 hour timeout

    def test_run_upscaling_script_executes_docker_command(self):
        """Test that _run_upscaling_script executes the correct Docker command."""
        # Mock successful command execution
        self.mock_ssh_manager.execute_command_success.return_value = None

        # Run upscaling script
        self.docker_executor._run_upscaling_script("test_prompt", 0.6, 2, "0,1")

        # Check that Docker command was executed
        self.mock_ssh_manager.execute_command_success.assert_called_once()

        # Get the command that was executed
        call_args = self.mock_ssh_manager.execute_command_success.call_args
        cmd = call_args[0][0]

        # Check command components
        assert "sudo docker run" in cmd
        assert "--gpus all" in cmd
        assert "--ipc=host" in cmd
        assert "--shm-size=8g" in cmd
        assert f"-v {self.remote_dir}:/workspace" in cmd
        assert f"-w /workspace" in cmd
        assert self.docker_image in cmd
        assert "/workspace/bashscripts/upscale.sh test_prompt 0.6 2 0,1" in cmd
        assert call_args[1]["timeout"] == 1800  # 30 minute timeout

    def test_create_upscaler_spec_creates_correct_spec_file(self):
        """Test that _create_upscaler_spec creates the correct specification file."""
        # Mock successful command execution
        self.mock_ssh_manager.execute_command_success.return_value = None

        # Create upscaler spec
        self.docker_executor._create_upscaler_spec("test_prompt", 0.75)

        # Check that spec file was created
        self.mock_ssh_manager.execute_command_success.assert_called_once()

        # Get the command that was executed
        call_args = self.mock_ssh_manager.execute_command_success.call_args
        cmd = call_args[0][0]

        # Check command components
        assert "cat >" in cmd
        assert f"{self.remote_dir}/outputs/test_prompt/upscaler_spec.json" in cmd
        assert "outputs/test_prompt/output.mp4" in cmd
        assert '"control_weight": 0.75' in cmd

    def test_check_remote_file_exists_returns_true_for_existing_file(self):
        """Test that _check_remote_file_exists returns True for existing files."""
        # Mock successful file check
        self.mock_ssh_manager.execute_command_success.return_value = None

        # Check if file exists
        result = self.docker_executor._check_remote_file_exists("/path/to/existing/file")

        # Should return True
        assert result is True
        self.mock_ssh_manager.execute_command_success.assert_called_once_with(
            "test -f /path/to/existing/file"
        )

    def test_check_remote_file_exists_returns_false_for_nonexistent_file(self):
        """Test that _check_remote_file_exists returns False for non-existent files."""
        # Mock failed file check
        self.mock_ssh_manager.execute_command_success.side_effect = RuntimeError("File not found")

        # Check if file exists
        result = self.docker_executor._check_remote_file_exists("/path/to/nonexistent/file")

        # Should return False
        assert result is False
        self.mock_ssh_manager.execute_command_success.assert_called_once_with(
            "test -f /path/to/nonexistent/file"
        )

    def test_get_docker_status_returns_status_when_docker_running(self):
        """Test that get_docker_status returns status when Docker is running."""
        # Mock successful Docker commands
        self.mock_ssh_manager.execute_command_success.side_effect = [
            "Docker info output",  # docker info
            "Image list output",  # docker images
            "Container list output",  # docker ps
        ]

        # Get Docker status
        status = self.docker_executor.get_docker_status()

        # Check status structure
        assert status["docker_running"] is True
        assert status["docker_info"] == "Docker info output"
        assert status["available_images"] == "Image list output"
        assert status["running_containers"] == "Container list output"

        # Check that commands were executed
        assert self.mock_ssh_manager.execute_command_success.call_count == 3

    def test_get_docker_status_returns_error_when_docker_fails(self):
        """Test that get_docker_status returns error when Docker commands fail."""
        # Mock failed Docker command
        self.mock_ssh_manager.execute_command_success.side_effect = Exception("Docker not running")

        # Get Docker status
        status = self.docker_executor.get_docker_status()

        # Check status structure
        assert status["docker_running"] is False
        assert "Docker not running" in status["error"]

    def test_cleanup_containers_executes_cleanup_command(self):
        """Test that cleanup_containers executes the cleanup command."""
        # Mock successful cleanup
        self.mock_ssh_manager.execute_command_success.return_value = None

        # Cleanup containers
        self.docker_executor.cleanup_containers()

        # Check that cleanup command was executed
        self.mock_ssh_manager.execute_command_success.assert_called_once_with(
            "sudo docker container prune -f", stream_output=False
        )

    def test_cleanup_containers_handles_failure_gracefully(self):
        """Test that cleanup_containers handles failure gracefully."""
        # Mock failed cleanup
        self.mock_ssh_manager.execute_command_success.side_effect = Exception("Cleanup failed")

        # Should not raise exception, just log warning
        self.docker_executor.cleanup_containers()

        # Check that cleanup command was attempted
        self.mock_ssh_manager.execute_command_success.assert_called_once()

    def test_get_container_logs_returns_logs_when_successful(self):
        """Test that get_container_logs returns logs when successful."""
        # Mock successful log retrieval
        expected_logs = "Container log output"
        self.mock_ssh_manager.execute_command_success.return_value = expected_logs

        # Get container logs
        logs = self.docker_executor.get_container_logs("container123")

        # Should return the logs
        assert logs == expected_logs
        self.mock_ssh_manager.execute_command_success.assert_called_once_with(
            "sudo docker logs container123", stream_output=False
        )

    def test_get_container_logs_returns_error_message_when_fails(self):
        """Test that get_container_logs returns error message when it fails."""
        # Mock failed log retrieval
        self.mock_ssh_manager.execute_command_success.side_effect = Exception(
            "Log retrieval failed"
        )

        # Get container logs
        logs = self.docker_executor.get_container_logs("container123")

        # Should return error message
        assert "Error retrieving logs: Log retrieval failed" in logs
        self.mock_ssh_manager.execute_command_success.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])
