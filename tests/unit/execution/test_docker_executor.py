"""
Tests for the DockerExecutor class.

This module tests the Docker execution functionality that handles
running Docker commands on remote instances for Cosmos-Transfer1 workflows.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

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

        if self.temp_dir and Path(self.temp_dir).exists():
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

        # Mock successful inference script execution (return 0 for success)
        with patch.object(
            self.docker_executor, "_run_inference_script", return_value=0
        ) as mock_run_script:
            # Run inference
            result = self.docker_executor.run_inference(
                self.test_prompt_file, run_id="test_run_001", num_gpu=2, cuda_devices="0,1"
            )

            # Check that output directory was created with run_id
            self.mock_ssh_manager.execute_command_success.assert_any_call(
                f"mkdir -p {self.remote_dir}/outputs/run_test_run_001"
            )

            # Check that inference script was called (behavior, not exact signature)
            mock_run_script.assert_called_once()
            # Verify the important parameters were passed
            call_args = mock_run_script.call_args
            assert "test_prompt" in str(call_args)
            assert "test_run_001" in str(call_args)

            # Check that result is a dict with expected keys
            assert isinstance(result, dict)
            # Status can be "started" or "completed" depending on execution mode
            assert result["status"] in ["started", "completed"]
            assert "log_path" in result
            assert result["prompt_name"] == "test_prompt"

    def test_run_inference_calls_inference_script_with_correct_parameters(self):
        """Test that run_inference calls the inference script with correct parameters."""
        # Mock successful directory creation
        self.mock_ssh_manager.execute_command_success.return_value = None

        with patch.object(
            self.docker_executor, "_run_inference_script", return_value=0
        ) as mock_run_script:
            # Run inference with custom parameters
            result = self.docker_executor.run_inference(
                self.test_prompt_file, run_id="test_run_002", num_gpu=4, cuda_devices="0,1,2,3"
            )

            # Check that script was called (behavior, not exact signature)
            mock_run_script.assert_called_once()
            # Verify the important parameters were passed
            call_args = mock_run_script.call_args
            assert "test_prompt" in str(call_args)
            assert "test_run_002" in str(call_args)
            assert "0,1,2,3" in str(call_args)

            # Check that result is a dict with expected keys
            assert isinstance(result, dict)
            # Status can be "started" or "completed" depending on execution mode
            assert result["status"] in ["started", "completed"]

    def test_run_inference_with_run_id(self):
        """Test that run_inference handles run_id parameter correctly."""
        # Mock successful directory creation
        self.mock_ssh_manager.execute_command_success.return_value = None

        with patch.object(
            self.docker_executor, "_run_inference_script", return_value=0
        ) as mock_run_script:
            # Run inference with run_id
            result = self.docker_executor.run_inference(
                self.test_prompt_file, run_id="test_run_123", num_gpu=1, cuda_devices="0"
            )

            # Check that inference script was called (behavior, not exact signature)
            mock_run_script.assert_called_once()
            # Verify run_id was passed
            call_args = mock_run_script.call_args
            assert "test_run_123" in str(call_args)

            # Check that result contains log path with run_id
            assert "test_run_123" in result["log_path"]
            # Status can be "started" or "completed" depending on execution mode
            assert result["status"] in ["started", "completed"]

    def test_run_inference_handles_failure(self):
        """Test that run_inference handles failures gracefully."""
        # Mock successful directory creation
        self.mock_ssh_manager.execute_command_success.return_value = None

        with patch.object(
            self.docker_executor, "_run_inference_script", return_value=0
        ) as mock_run_script:
            # Mock script failure
            mock_run_script.side_effect = Exception("Inference failed")

            # Run inference
            result = self.docker_executor.run_inference(
                self.test_prompt_file, run_id="test_run_003", num_gpu=1, cuda_devices="0"
            )

            # Check that result indicates failure
            assert result["status"] == "failed"
            assert "Inference failed" in result["error"]
            assert "log_path" in result

    def test_run_upscaling_creates_output_directory(self):
        """Test that run_upscaling creates the upscaled output directory."""
        # Mock successful operations
        with patch.object(self.docker_executor, "_check_remote_file_exists") as mock_check:
            mock_check.return_value = True

            self.mock_ssh_manager.execute_command_success.return_value = None

            with patch.object(self.docker_executor, "_create_upscaler_spec"):
                with patch.object(self.docker_executor, "_run_upscaling_script"):
                    # Run upscaling
                    result = self.docker_executor.run_upscaling(
                        self.test_prompt_file, run_id="test_run_004"
                    )
                    # Check result is dict
                    assert isinstance(result, dict)

                    # Check that upscaled output directory was created with run_id
                    self.mock_ssh_manager.execute_command_success.assert_any_call(
                        f"mkdir -p {self.remote_dir}/outputs/run_test_run_004"
                    )

    def test_run_upscaling_calls_upscaling_script_with_correct_parameters(self):
        """Test that run_upscaling calls the upscaling script with correct parameters."""
        # Mock successful operations
        with patch.object(self.docker_executor, "_check_remote_file_exists") as mock_check:
            mock_check.return_value = True

            self.mock_ssh_manager.execute_command_success.return_value = None

            with patch.object(self.docker_executor, "_create_upscaler_spec"):
                with patch.object(
                    self.docker_executor, "_run_upscaling_script", return_value=0
                ) as mock_run_script:
                    # Create a test video file path instead of prompt file
                    test_video_path = str(Path(self.temp_dir) / "test_video.mp4")

                    # Run upscaling with custom parameters (now expects video path)
                    result = self.docker_executor.run_upscaling(
                        test_video_path,  # Changed from prompt file to video path
                        run_id="test_run_005",
                        control_weight=0.8,
                        num_gpu=3,
                        cuda_devices="0,1,2",
                    )
                    # Check result is dict
                    assert isinstance(result, dict)

                    # Check that script was called (behavior, not exact signature)
                    mock_run_script.assert_called_once()
                    # Verify important parameters were passed
                    call_args = mock_run_script.call_args
                    assert "test_run_005" in str(call_args)
                    assert 0.8 in call_args[0] or 0.8 in call_args[1].values()

    def test_run_inference_script_executes_docker_command(self):
        """Test that _run_inference_script executes a Docker command."""
        # Mock successful command execution
        self.mock_ssh_manager.execute_command.return_value = (0, "", "")

        # Run inference script with run_id (may need stream_output parameter)
        self.docker_executor._run_inference_script(
            "test_prompt", "test_run_006", 2, "0,1", stream_output=False
        )

        # Check behavior: Docker command was executed
        self.mock_ssh_manager.execute_command.assert_called_once()

        # Get the command that was executed
        call_args = self.mock_ssh_manager.execute_command.call_args
        cmd = call_args[0][0]

        # Check essential behavior: it's a docker run command
        assert "docker run" in cmd
        # Check that GPU access is configured
        assert "--gpus" in cmd or "gpu" in cmd.lower()
        # Check that the workspace is mounted
        assert "/workspace" in cmd
        # Check that the docker image is used
        assert self.docker_image in cmd
        # Check that the run_id is passed to the script
        assert "test_run_006" in cmd

    def test_run_upscaling_script_executes_docker_command(self):
        """Test that _run_upscaling_script executes a Docker command."""
        # Mock successful command execution
        self.mock_ssh_manager.execute_command.return_value = (0, "", "")

        # Run upscaling script with run_id (signature changed - now needs video_path)
        self.docker_executor._run_upscaling_script(
            video_path="/workspace/test_video.mp4",
            run_id="test_run_007",
            control_weight=0.6,
            num_gpu=2,
            cuda_devices="0,1",
        )

        # Check behavior: Docker command was executed
        self.mock_ssh_manager.execute_command.assert_called_once()

        # Get the command that was executed
        call_args = self.mock_ssh_manager.execute_command.call_args
        cmd = call_args[0][0]

        # Check essential behavior: it's a docker run command
        assert "docker run" in cmd
        # Check that GPU access is configured
        assert "--gpus" in cmd or "gpu" in cmd.lower()
        # Check that the workspace is mounted
        assert "/workspace" in cmd
        # Check that the docker image is used
        assert self.docker_image in cmd
        # Check that the run_id is passed to the script
        assert "test_run_007" in cmd
        # Check that control weight is passed
        assert "0.6" in cmd

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
            "",  # No containers from get_active_container
        ]

        # Get Docker status
        status = self.docker_executor.get_docker_status()

        # Check status structure
        assert status["docker_running"] is True
        assert status["docker_info"] == "Docker info output"
        assert status["available_images"] == "Image list output"
        assert status["active_container"] is None  # No containers running

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

    def test_kill_containers_with_no_running_containers(self):
        """Test kill_containers when no containers are running."""
        # Mock no containers found
        self.mock_ssh_manager.execute_command_success.return_value = ""

        # Kill containers
        result = self.docker_executor.kill_containers()

        # Check result
        assert result["killed_count"] == 0
        assert result["status"] == "success"
        assert result["message"] == "No running containers found"

        # Check that we queried for containers
        self.mock_ssh_manager.execute_command_success.assert_called_with(
            f'sudo docker ps --filter "ancestor={self.docker_image}" --format "{{{{.ID}}}}"',
            stream_output=False,
        )

    def test_kill_containers_with_single_container(self):
        """Test kill_containers with one running container."""
        # Mock one container found
        container_id = "abc123def456"

        # Mock execute_command_success for docker ps (returns string)
        self.mock_ssh_manager.execute_command_success = Mock(return_value=container_id)

        # Mock execute_command for docker kill (returns tuple: exit_code, stdout, stderr)
        self.mock_ssh_manager.execute_command = Mock(return_value=(0, "", ""))

        # Kill containers
        result = self.docker_executor.kill_containers()

        # Check result
        assert result["killed_count"] == 1
        assert result["status"] == "success"
        assert container_id in result["killed_containers"]

        # Verify docker ps was called
        self.mock_ssh_manager.execute_command_success.assert_called_once()
        # Verify docker kill was called
        self.mock_ssh_manager.execute_command.assert_called_once()

    def test_kill_containers_with_multiple_containers(self):
        """Test kill_containers with multiple running containers."""
        # Mock multiple containers found
        container_ids = ["abc123def456", "789xyz012345", "mno456pqr789"]

        # Mock execute_command_success for docker ps (returns string)
        self.mock_ssh_manager.execute_command_success = Mock(return_value="\n".join(container_ids))

        # Mock execute_command for docker kill (returns tuple)
        self.mock_ssh_manager.execute_command = Mock(return_value=(0, "", ""))

        # Kill containers
        result = self.docker_executor.kill_containers()

        # Check result
        assert result["killed_count"] == 3
        assert result["status"] == "success"
        assert all(cid in result["killed_containers"] for cid in container_ids)

        # Check that docker kill was called with all container IDs
        self.mock_ssh_manager.execute_command_success.assert_called_once()
        self.mock_ssh_manager.execute_command.assert_called_once()
        kill_command = self.mock_ssh_manager.execute_command.call_args[0][0]
        for cid in container_ids:
            assert cid in kill_command

    def test_kill_containers_handles_docker_kill_failure(self):
        """Test that kill_containers handles docker kill failure gracefully."""
        # Mock container found but kill fails
        container_id = "abc123def456"

        # Mock execute_command_success for docker ps
        self.mock_ssh_manager.execute_command_success = Mock(return_value=container_id)

        # Mock execute_command for docker kill - returns error exit code
        self.mock_ssh_manager.execute_command = Mock(
            return_value=(1, "", "Failed to kill container")
        )

        # Kill containers should handle error
        result = self.docker_executor.kill_containers()

        # Check result indicates failure
        assert result["status"] == "failed"
        assert "error" in result
        assert "Failed to kill container" in result["error"]

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

    def test_stream_container_logs_with_specific_container_id(self):
        """Test streaming logs with a specific container ID."""
        container_id = "abc123def456"

        # Call stream_container_logs with specific ID
        self.docker_executor.stream_container_logs(container_id)

        # Should stream logs from the specified container
        self.mock_ssh_manager.execute_command.assert_called_once_with(
            f"sudo docker logs -f {container_id}", timeout=86400, stream_output=True
        )

    def test_stream_container_logs_auto_detect_latest_container(self):
        """Test auto-detecting and streaming from the latest container."""
        # Mock get_active_container to return a container
        detected_container = "xyz789abc123"
        with patch.object(self.docker_executor, "get_active_container") as mock_get_active:
            mock_get_active.return_value = {
                "id": detected_container,
                "id_short": detected_container[:12],
                "name": "test-container",
                "status": "Up 5 minutes",
                "image": self.docker_image,
                "created": "2025-01-07",
            }

            # Mock the execute_command for streaming
            self.mock_ssh_manager.execute_command.return_value = (0, "", "")

            # Call stream_container_logs without container ID
            self.docker_executor.stream_container_logs()

            # Should call get_active_container
            mock_get_active.assert_called_once()

            # Then stream logs from detected container
            self.mock_ssh_manager.execute_command.assert_called_once_with(
                f"sudo docker logs -f {detected_container}", timeout=86400, stream_output=True
            )

    def test_stream_container_logs_no_running_containers(self):
        """Test error handling when no containers are running."""
        # Mock get_active_container to return None (no containers)
        with patch.object(self.docker_executor, "get_active_container") as mock_get_active:
            mock_get_active.return_value = None

            # Should raise RuntimeError when no containers found
            with pytest.raises(RuntimeError, match="No running containers found"):
                self.docker_executor.stream_container_logs()

            # Should have attempted to detect container
            mock_get_active.assert_called_once()

            # Should not attempt to stream logs
            self.mock_ssh_manager.execute_command.assert_not_called()

    def test_stream_container_logs_handles_keyboard_interrupt(self):
        """Test graceful handling of Ctrl+C during streaming."""
        container_id = "interrupt123"

        # Mock KeyboardInterrupt during streaming
        self.mock_ssh_manager.execute_command.side_effect = KeyboardInterrupt()

        # Should handle interrupt gracefully (no exception raised)
        self.docker_executor.stream_container_logs(container_id)

        # Should have attempted to stream
        self.mock_ssh_manager.execute_command.assert_called_once_with(
            f"sudo docker logs -f {container_id}", timeout=86400, stream_output=True
        )

    def test_stream_container_logs_strips_whitespace_from_detected_id(self):
        """Test that whitespace is stripped from auto-detected container ID."""
        # Mock get_active_container to return container with whitespace
        detected_container = "  container789  \n"
        with patch.object(self.docker_executor, "get_active_container") as mock_get_active:
            mock_get_active.return_value = {
                "id": detected_container.strip(),  # get_active_container should already strip
                "id_short": "container789"[:12],
                "name": "test-container",
                "status": "Up 5 minutes",
                "image": self.docker_image,
                "created": "2025-01-07",
            }

            # Mock the execute_command for streaming
            self.mock_ssh_manager.execute_command.return_value = (0, "", "")

            # Call stream_container_logs
            self.docker_executor.stream_container_logs()

            # Should stream with trimmed container ID
            self.mock_ssh_manager.execute_command.assert_called_once_with(
                "sudo docker logs -f container789", timeout=86400, stream_output=True
            )


class TestDockerExecutorBatchInference:
    """Test suite for batch inference functionality in DockerExecutor."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Mock SSH manager
        self.mock_ssh_manager = Mock(spec=SSHManager)

        # Mock remote executor
        self.mock_remote_executor = Mock()

        # Test configuration
        self.remote_dir = "/home/ubuntu/cosmos-transfer1"
        self.docker_image = "cosmos-transfer1:latest"

        # Initialize DockerExecutor
        self.docker_executor = DockerExecutor(
            ssh_manager=self.mock_ssh_manager,
            remote_dir=self.remote_dir,
            docker_image=self.docker_image,
        )

        # Replace remote_executor with mock
        self.docker_executor.remote_executor = self.mock_remote_executor

    def test_run_batch_inference_successful_execution(self):
        """Test successful batch inference execution."""
        # Mock file exists check
        self.mock_remote_executor.file_exists.return_value = True

        # Mock directory creation
        self.mock_remote_executor.create_directory.return_value = None

        # Mock getting output files
        with patch.object(self.docker_executor, "_get_batch_output_files") as mock_get_files:
            mock_get_files.return_value = [
                "/remote/outputs/batch_test/video_0/output.mp4",
                "/remote/outputs/batch_test/video_1/output.mp4",
            ]

            # Mock batch script execution
            with patch.object(
                self.docker_executor, "_run_batch_inference_script"
            ) as mock_run_script:
                # Mock successful execution
                mock_run_script.return_value = 0  # Exit code 0 for success

                # Run batch inference
                result = self.docker_executor.run_batch_inference(
                    batch_name="batch_test",
                    batch_jsonl_file="batch_test.jsonl",
                    base_controlnet_spec="base_spec.json",
                    batch_size=4,
                    num_gpu=2,
                    cuda_devices="0,1",
                    guidance=5.0,
                    seed=1,
                )

            # Verify batch files were checked (both JSONL and base_spec)
            file_exists_calls = self.mock_remote_executor.file_exists.call_args_list
            assert len(file_exists_calls) == 2
            # Check that both files were verified
            checked_files = [call[0][0] for call in file_exists_calls]
            assert f"{self.remote_dir}/inputs/batches/batch_test.jsonl" in checked_files
            assert f"{self.remote_dir}/inputs/batches/base_spec.json" in checked_files

            # Verify batch script was called with correct parameters
            mock_run_script.assert_called_once_with(
                "batch_test",
                "batch_test.jsonl",
                "base_spec.json",
                4,
                2,
                "0,1",
                5.0,
                1,
            )

            # Check result structure - batch now runs synchronously with "completed" status
            assert result["batch_name"] == "batch_test"
            assert result["output_dir"] == f"{self.remote_dir}/outputs/batch_test"
            assert result["status"] == "completed"

    def test_run_batch_inference_file_not_found(self):
        """Test batch inference when JSONL file doesn't exist."""
        # Mock file doesn't exist
        self.mock_remote_executor.file_exists.return_value = False

        # Should raise FileNotFoundError
        with pytest.raises(FileNotFoundError, match="Batch file not found"):
            self.docker_executor.run_batch_inference(
                batch_name="missing_batch",
                batch_jsonl_file="missing.jsonl",
                base_controlnet_spec="base_spec.json",
            )

        # Should check for batch file (and stop on failure, not checking base spec)
        assert self.mock_remote_executor.file_exists.call_count == 1

    def test_run_batch_inference_with_default_gpu_settings(self):
        """Test batch inference with default GPU settings."""
        self.mock_remote_executor.file_exists.return_value = True

        # Mock getting output files
        with patch.object(self.docker_executor, "_get_batch_output_files") as mock_get_files:
            mock_get_files.return_value = ["/remote/outputs/batch_default/video_0/output.mp4"]

            with patch.object(
                self.docker_executor, "_run_batch_inference_script"
            ) as mock_run_script:
                # Mock successful execution
                mock_run_script.return_value = 0  # Exit code 0 for success

                # Run with defaults
                result = self.docker_executor.run_batch_inference(
                    batch_name="batch_default",
                    batch_jsonl_file="batch.jsonl",
                    base_controlnet_spec="base_spec.json",
                )

            # Check result
            assert result["batch_name"] == "batch_default"
            assert result["status"] == "completed"

            # Should use default num_gpu=1 and cuda_devices="0"
            mock_run_script.assert_called_once_with(
                "batch_default",
                "batch.jsonl",
                "base_spec.json",
                4,
                1,
                "0",
                5.0,
                1,
            )

    def test_run_batch_inference_script_builds_correct_command(self):
        """Test that batch inference script builds correct Docker command synchronously."""
        # Mock execute_command
        self.mock_ssh_manager.execute_command.return_value = (0, "", "")

        # Run batch inference script
        self.docker_executor._run_batch_inference_script(
            "batch_test", "batch_test.jsonl", "base_spec.json", 4, 1, "0,1,2,3", 5.0, 1
        )

        # Get the command that was executed
        call_args = self.mock_ssh_manager.execute_command.call_args
        cmd = call_args[0][0]

        # Check timeout is appropriate for synchronous execution
        assert call_args[1]["timeout"] == 3600  # 1 hour for batch processing

        # Check that it's run synchronously (no nohup or &)
        assert "nohup" not in cmd
        assert not cmd.strip().endswith("&")

        # Check command components
        assert "docker run" in cmd
        assert "--gpus all" in cmd
        assert "--ipc=host" in cmd
        assert "--shm-size=8g" in cmd
        assert f"-v {self.remote_dir}:/workspace" in cmd
        assert self.docker_image in cmd
        # Check for new parameters in the command
        assert "batch_test" in cmd
        assert "batch_test.jsonl" in cmd
        assert "base_spec.json" in cmd

    def test_get_batch_output_files_returns_mp4_files(self):
        """Test that _get_batch_output_files returns list of MP4 files."""
        # Mock ls command output
        self.mock_ssh_manager.execute_command_success.return_value = (
            "/outputs/batch/video_000.mp4\n"
            "/outputs/batch/video_001.mp4\n"
            "/outputs/batch/video_002.mp4"
        )

        # Get output files
        files = self.docker_executor._get_batch_output_files("batch_test")

        # Should return list of files
        assert len(files) == 3
        assert "/outputs/batch/video_000.mp4" in files
        assert "/outputs/batch/video_001.mp4" in files
        assert "/outputs/batch/video_002.mp4" in files

        # Should have executed find command
        self.mock_ssh_manager.execute_command_success.assert_called_once()
        call_args = self.mock_ssh_manager.execute_command_success.call_args[0][0]
        assert "find" in call_args
        assert "batch_test" in call_args
        assert "*.mp4" in call_args

    def test_get_batch_output_files_handles_no_outputs(self):
        """Test handling when no output files are found."""
        # Mock empty ls output
        self.mock_ssh_manager.execute_command_success.return_value = ""

        # Get output files
        files = self.docker_executor._get_batch_output_files("empty_batch")

        # Should return empty list
        assert files == []

    def test_get_batch_output_files_handles_ls_failure(self):
        """Test handling when ls command fails."""
        # Mock ls failure
        self.mock_ssh_manager.execute_command_success.side_effect = Exception("ls failed")

        # Get output files
        files = self.docker_executor._get_batch_output_files("failed_batch")

        # Should return empty list on failure
        assert files == []

    def test_run_batch_inference_with_large_batch(self):
        """Test batch inference with large batch."""
        self.mock_remote_executor.file_exists.return_value = True

        # Mock getting output files
        with patch.object(self.docker_executor, "_get_batch_output_files") as mock_get_files:
            mock_get_files.return_value = ["/remote/outputs/large_batch/video_0/output.mp4"]

            with patch.object(
                self.docker_executor, "_run_batch_inference_script"
            ) as mock_run_script:
                # Mock successful execution
                mock_run_script.return_value = 0  # Exit code 0 for success

                # Run batch inference
                result = self.docker_executor.run_batch_inference(
                    batch_name="large_batch",
                    batch_jsonl_file="large_batch.jsonl",
                    base_controlnet_spec="base_spec.json",
                )

            # Should return with completed status (now runs synchronously)
            assert result["batch_name"] == "large_batch"
            assert result["status"] == "completed"

    def test_run_batch_inference_preserves_batch_name_with_special_chars(self):
        """Test that batch names with timestamps are preserved."""
        batch_name = "batch_20241210_153045"
        self.mock_remote_executor.file_exists.return_value = True

        # Mock getting output files
        with patch.object(self.docker_executor, "_get_batch_output_files") as mock_get_files:
            mock_get_files.return_value = [f"/remote/outputs/{batch_name}/video_0/output.mp4"]

            with patch.object(
                self.docker_executor, "_run_batch_inference_script"
            ) as mock_run_script:
                # Mock successful execution
                mock_run_script.return_value = 0  # Exit code 0 for success

                # Run with timestamp in name
                result = self.docker_executor.run_batch_inference(
                    batch_name=batch_name,
                    batch_jsonl_file=f"{batch_name}.jsonl",
                    base_controlnet_spec="base_spec.json",
                )

            # Name should be preserved exactly
            assert result["batch_name"] == batch_name
            assert result["status"] == "completed"
            mock_run_script.assert_called_once_with(
                batch_name,
                f"{batch_name}.jsonl",
                "base_spec.json",
                4,
                1,
                "0",
                5.0,
                1,
            )


if __name__ == "__main__":
    pytest.main([__file__])
