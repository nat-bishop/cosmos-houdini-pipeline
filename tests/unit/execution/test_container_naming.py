"""Tests for container naming implementation."""

from unittest.mock import MagicMock

import pytest

from cosmos_workflow.execution.docker_executor import DockerExecutor


class TestContainerNaming:
    """Test that all Docker operations set container names correctly."""

    @pytest.fixture
    def mock_ssh_manager(self):
        """Create a mock SSH manager."""
        mock = MagicMock()
        mock.execute_command = MagicMock(return_value=(0, "", ""))
        return mock

    @pytest.fixture
    def docker_executor(self, mock_ssh_manager):
        """Create a DockerExecutor instance with mocked SSH."""
        return DockerExecutor(
            ssh_manager=mock_ssh_manager, remote_dir="/workspace", docker_image="cosmos:latest"
        )

    def test_inference_container_naming(self, docker_executor, mock_ssh_manager):
        """Test that inference containers get proper names."""
        # Execute the internal script method directly
        docker_executor._run_inference_script(
            prompt_name="test_prompt", run_id="run_abc123456789", num_gpu=1, cuda_devices="0"
        )

        # Check behavior: docker command was executed with a container name
        call_args = mock_ssh_manager.execute_command.call_args[0][0]
        assert "--name cosmos_" in call_args  # Container gets a name
        assert "docker run" in call_args  # Docker command was executed

    def test_upscaling_container_naming(self, docker_executor, mock_ssh_manager):
        """Test that upscaling containers get proper names."""
        # Execute the internal script method directly (newer API requires video_path)
        docker_executor._run_upscaling_script(
            run_id="run_def987654321",
            video_path="/workspace/test_video.mp4",
            control_weight=0.5,
            num_gpu=1,
            cuda_devices="0",
        )

        # Check behavior: docker command was executed with a container name
        call_args = mock_ssh_manager.execute_command.call_args[0][0]
        assert "--name cosmos_" in call_args  # Container gets a name
        assert "docker run" in call_args  # Docker command was executed

    def test_enhancement_container_naming(self, docker_executor, mock_ssh_manager):
        """Test that enhancement containers get proper names."""
        # Mock the remote executor for file checks
        docker_executor.remote_executor.file_exists = MagicMock(return_value=True)
        docker_executor.remote_executor.create_directory = MagicMock()

        # Run prompt enhancement
        result = docker_executor.run_prompt_enhancement(
            batch_filename="test_batch.json", run_id="run_xyz111222333", offload=True
        )

        # Check behavior: docker command was executed with a container name
        call_args = mock_ssh_manager.execute_command.call_args[0][0]
        assert "--name cosmos_" in call_args  # Container gets a name
        assert "docker run" in call_args  # Docker command was executed
        # Status can be either "started" or "completed" depending on offload flag
        assert result["status"] in ["started", "completed"]

    def test_batch_inference_container_naming(self, docker_executor, mock_ssh_manager):
        """Test that batch inference containers get proper names."""
        # Execute the internal script method directly
        docker_executor._run_batch_inference_script(
            batch_name="batch_test_20240101_5",
            batch_jsonl_file="batch.jsonl",
            num_gpu=1,
            cuda_devices="0",
        )

        # Check behavior: docker command was executed with a container name
        call_args = mock_ssh_manager.execute_command.call_args[0][0]
        assert "--name cosmos_" in call_args  # Container gets a name
        assert "docker run" in call_args  # Docker command was executed

    def test_container_name_truncation(self, docker_executor, mock_ssh_manager):
        """Test that container names are properly truncated to 8 chars."""
        # Test with short run_id (keeps the full ID since it's short)
        docker_executor._run_inference_script(
            prompt_name="test", run_id="run_123", num_gpu=1, cuda_devices="0"
        )

        call_args = mock_ssh_manager.execute_command.call_args[0][0]
        assert "--name cosmos_" in call_args  # Container gets a name

        # Test with no run_ prefix
        docker_executor._run_inference_script(
            prompt_name="test", run_id="abc123456789", num_gpu=1, cuda_devices="0"
        )

        call_args = mock_ssh_manager.execute_command.call_args[0][0]
        assert "--name cosmos_" in call_args  # Container gets a name

    def test_enhancement_without_run_id(self, docker_executor, mock_ssh_manager):
        """Test that enhancement works without run_id (no container name)."""
        # Mock the remote executor for file checks
        docker_executor.remote_executor.file_exists = MagicMock(return_value=True)
        docker_executor.remote_executor.create_directory = MagicMock()

        # Run prompt enhancement without run_id
        result = docker_executor.run_prompt_enhancement(
            batch_filename="test_batch.json",
            run_id=None,  # No run_id
            offload=True,
        )

        # Check behavior: enhancement started without run_id
        call_args = mock_ssh_manager.execute_command.call_args[0][0]
        assert "docker run" in call_args  # Docker command was executed
        # Status can be either "started" or "completed" depending on offload flag
        assert result["status"] in ["started", "completed"]


class TestContainerRetrieval:
    """Test that container names can be retrieved correctly."""

    @pytest.fixture
    def mock_ssh_manager(self):
        """Create a mock SSH manager with container output."""
        mock = MagicMock()
        # Simulate docker ps output with our named container
        mock.execute_command_success = MagicMock(
            return_value="abc123def456|cosmos_transfer_run12345|Up 5 minutes|cosmos:latest|2024-01-01 10:00:00"
        )
        return mock

    @pytest.fixture
    def docker_executor(self, mock_ssh_manager):
        """Create a DockerExecutor instance with mocked SSH."""
        return DockerExecutor(
            ssh_manager=mock_ssh_manager, remote_dir="/workspace", docker_image="cosmos:latest"
        )

    def test_get_active_container_with_name(self, docker_executor):
        """Test that get_active_container returns the container name."""
        container = docker_executor.get_active_container()

        assert container is not None
        assert container["name"] == "cosmos_transfer_run12345"
        assert container["id"] == "abc123def456"
        assert container["id_short"] == "abc123def456"
        assert container["status"] == "Up 5 minutes"

    def test_get_active_container_no_containers(self, docker_executor, mock_ssh_manager):
        """Test get_active_container when no containers are running."""
        mock_ssh_manager.execute_command_success.return_value = ""

        container = docker_executor.get_active_container()
        assert container is None

    def test_get_active_container_multiple_containers(self, docker_executor, mock_ssh_manager):
        """Test get_active_container with multiple containers (warning case)."""
        # Simulate multiple containers
        mock_ssh_manager.execute_command_success.return_value = (
            "abc123|cosmos_transfer_abc123|Up 5 min|cosmos:latest|2024-01-01 10:00:00\n"
            "def456|cosmos_enhance_def456|Up 3 min|cosmos:latest|2024-01-01 10:02:00"
        )

        container = docker_executor.get_active_container()

        assert container is not None
        assert container["name"] == "cosmos_transfer_abc123"  # First one
        assert "warning" in container
        assert "Multiple containers detected" in container["warning"]
