"""Tests for GPUExecutor upscaling functionality (Phase 3)."""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from cosmos_workflow.execution.gpu_executor import GPUExecutor

# Tests updated to work with the new lazy sync architecture


class TestGPUExecutorUpscaling:
    """Test GPUExecutor upscaling as separate database runs."""

    @pytest.fixture
    def mock_config_manager(self):
        """Create a mock config manager."""
        mock_config = MagicMock()

        # Mock remote config
        mock_remote_config = Mock()
        mock_remote_config.remote_dir = "/remote/cosmos"
        mock_remote_config.docker_image = "cosmos:latest"
        mock_config.get_remote_config.return_value = mock_remote_config

        # Mock SSH options
        mock_ssh_options = Mock()
        mock_ssh_options.host = "gpu-server"
        mock_ssh_options.username = "ubuntu"
        mock_config.get_ssh_options.return_value = mock_ssh_options

        return mock_config

    @pytest.fixture
    def mock_ssh_manager(self):
        """Create a mock SSH manager."""
        mock_ssh = MagicMock()
        mock_ssh.__enter__ = Mock(return_value=mock_ssh)
        mock_ssh.__exit__ = Mock(return_value=None)
        mock_ssh.execute_command_success = Mock()
        return mock_ssh

    @pytest.fixture
    def mock_file_transfer(self):
        """Create a mock file transfer service."""
        mock_ft = MagicMock()
        mock_ft.upload_file = Mock()
        mock_ft.download_results = Mock(
            return_value=Path("outputs/run_rs_upscale456/output_4k.mp4")
        )
        return mock_ft

    @pytest.fixture
    def mock_docker_executor(self):
        """Create a mock docker executor."""
        mock_docker = MagicMock()

        def mock_run_upscaling(video_path, run_id, control_weight, prompt=None, **kwargs):
            return {
                "status": "completed",
                "log_path": f"outputs/run_{run_id}/logs/upscaling.log",
                "video_path": video_path,
            }

        mock_docker.run_upscaling = Mock(side_effect=mock_run_upscaling)
        return mock_docker

    @pytest.fixture
    def mock_json_handler(self):
        """Create a mock JSON handler."""
        with patch("cosmos_workflow.execution.gpu_executor.JSONHandler") as MockJSON:
            mock_handler = MockJSON.return_value
            mock_handler.read_json = Mock()
            mock_handler.write_json = Mock()
            yield mock_handler

    @pytest.fixture
    def gpu_executor(self, mock_config_manager, mock_json_handler):
        """Create GPUExecutor instance with mocks."""
        with patch("cosmos_workflow.execution.gpu_executor.ConfigManager") as MockConfig:
            MockConfig.return_value = mock_config_manager
            executor = GPUExecutor()
            executor.json_handler = mock_json_handler
            return executor

    @pytest.fixture
    def sample_upscale_run(self):
        """Sample upscaling run data."""
        return {
            "id": "rs_upscale456",
            "prompt_id": "ps_test123",
            "model_type": "upscale",
            "status": "pending",
            "execution_config": {
                "parent_run_id": "rs_inference123",
                "control_weight": 0.7,
                "input_video": "outputs/run_rs_inference123/output.mp4",
            },
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    @pytest.fixture
    def sample_parent_run(self):
        """Sample parent inference run data."""
        return {
            "id": "rs_inference123",
            "prompt_id": "ps_test123",
            "model_type": "transfer",
            "status": "completed",
            "outputs": {
                "output_path": "outputs/run_rs_inference123/output.mp4",
                "duration_seconds": 120,
            },
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    @pytest.fixture
    def sample_prompt(self):
        """Sample prompt data."""
        return {
            "id": "ps_test123",
            "model_type": "transfer",
            "prompt_text": "A beautiful landscape",
            "inputs": {"video": "/path/to/video.mp4"},
            "parameters": {"name": "test_prompt"},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    def test_execute_upscaling_run_creates_run_directory(
        self, gpu_executor, sample_upscale_run, sample_parent_run, sample_prompt
    ):
        """Test that execute_upscaling_run creates the run directory."""
        video_path = "outputs/run_rs_inference123/output.mp4"

        with patch.object(gpu_executor, "_initialize_services"):
            with patch.object(gpu_executor, "ssh_manager", create=True) as mock_ssh:
                with patch.object(gpu_executor, "docker_executor", create=True) as mock_docker:
                    with patch.object(gpu_executor, "remote_executor", create=True) as mock_remote:
                        with patch.object(gpu_executor, "file_transfer", create=True):
                            # Setup mocks
                            mock_ssh.__enter__ = Mock(return_value=mock_ssh)
                            mock_ssh.__exit__ = Mock(return_value=None)
                            # Mock ssh_manager.execute_command to return 3-tuple
                            mock_ssh.execute_command = Mock(return_value=(0, "", ""))
                            # GPU executor expects synchronous completion with "completed" or "failed"
                            mock_docker.run_upscaling.return_value = {"status": "completed"}
                            mock_remote.execute_command = Mock()
                            mock_remote.file_exists = Mock(return_value=True)

                            # Act
                            with patch("pathlib.Path.mkdir") as mock_mkdir:
                                with patch("pathlib.Path.exists", return_value=True):
                                    result = gpu_executor.execute_upscaling_run(
                                        sample_upscale_run,
                                        video_path,
                                        prompt_text="Enhanced quality",
                                    )

                            # Assert
                            mock_mkdir.assert_called()
                            assert result["status"] == "completed"
                            assert "run_id" in result
                            assert result["run_id"] == "rs_upscale456"

    def test_execute_upscaling_run_calls_docker_executor(
        self, gpu_executor, sample_upscale_run, sample_parent_run, sample_prompt
    ):
        """Test that execute_upscaling_run calls DockerExecutor.run_upscaling correctly."""
        video_path = "outputs/run_rs_inference123/output.mp4"

        with patch.object(gpu_executor, "_initialize_services"):
            with patch.object(gpu_executor, "ssh_manager", create=True) as mock_ssh:
                with patch.object(gpu_executor, "docker_executor", create=True) as mock_docker:
                    with patch.object(gpu_executor, "remote_executor", create=True) as mock_remote:
                        with patch.object(gpu_executor, "file_transfer", create=True):
                            # Setup mocks
                            mock_ssh.__enter__ = Mock(return_value=mock_ssh)
                            mock_ssh.__exit__ = Mock(return_value=None)
                            # Mock ssh_manager.execute_command to return 3-tuple
                            mock_ssh.execute_command = Mock(return_value=(0, "", ""))
                            # GPU executor expects synchronous completion with "completed" or "failed"
                            mock_docker.run_upscaling.return_value = {"status": "completed"}
                            mock_remote.execute_command = Mock()
                            mock_remote.file_exists = Mock(return_value=True)

                            # Act
                            with patch("pathlib.Path.mkdir"):
                                with patch("pathlib.Path.exists", return_value=True):
                                    gpu_executor.execute_upscaling_run(
                                        sample_upscale_run,
                                        video_path,
                                        prompt_text="Enhanced quality",
                                    )

                            # Assert - check docker executor was called
                            mock_docker.run_upscaling.assert_called_once()
                            call_kwargs = mock_docker.run_upscaling.call_args.kwargs

                            # Check arguments
                            assert call_kwargs["run_id"] == "rs_upscale456"
                            assert call_kwargs["control_weight"] == 0.7
                            assert call_kwargs["prompt"] == "Enhanced quality"

    def test_execute_upscaling_run_with_video_file(self, gpu_executor, sample_upscale_run):
        """Test that execute_upscaling_run works with standalone video files."""
        video_path = "/path/to/standalone/video.mp4"
        sample_upscale_run["execution_config"]["source_run_id"] = None  # No parent run

        with patch.object(gpu_executor, "_initialize_services"):
            with patch.object(gpu_executor, "ssh_manager", create=True) as mock_ssh:
                with patch.object(gpu_executor, "docker_executor", create=True) as mock_docker:
                    with patch.object(gpu_executor, "remote_executor", create=True) as mock_remote:
                        with patch.object(gpu_executor, "file_transfer", create=True) as mock_ft:
                            # Setup mocks
                            mock_ssh.__enter__ = Mock(return_value=mock_ssh)
                            mock_ssh.__exit__ = Mock(return_value=None)
                            # Mock ssh_manager.execute_command to return 3-tuple
                            mock_ssh.execute_command = Mock(return_value=(0, "", ""))
                            # GPU executor expects synchronous completion with "completed" or "failed"
                            mock_docker.run_upscaling.return_value = {"status": "completed"}
                            mock_remote.execute_command = Mock()
                            mock_remote.file_exists = Mock(
                                return_value=False
                            )  # File doesn't exist on remote
                            mock_ft.upload_file = Mock()  # Will need to upload

                            # Act
                            with patch("pathlib.Path.mkdir"):
                                with patch("pathlib.Path.exists", return_value=True):
                                    result = gpu_executor.execute_upscaling_run(
                                        sample_upscale_run, video_path
                                    )

                            # Assert - check video was uploaded
                            mock_ft.upload_file.assert_called()
                            assert result["status"] == "completed"
                            assert "run_id" in result

    def test_execute_upscaling_run_handles_docker_failure(
        self, gpu_executor, sample_upscale_run, sample_parent_run, sample_prompt
    ):
        """Test that execute_upscaling_run handles Docker execution failures."""
        video_path = "outputs/run_rs_inference123/output.mp4"

        with patch.object(gpu_executor, "_initialize_services"):
            with patch.object(gpu_executor, "ssh_manager", create=True) as mock_ssh:
                with patch.object(gpu_executor, "docker_executor", create=True) as mock_docker:
                    with patch.object(gpu_executor, "remote_executor", create=True) as mock_remote:
                        with patch.object(gpu_executor, "file_transfer", create=True):
                            # Setup mocks
                            mock_ssh.__enter__ = Mock(return_value=mock_ssh)
                            mock_ssh.__exit__ = Mock(return_value=None)
                            mock_docker.run_upscaling.side_effect = RuntimeError("Docker failed")
                            mock_remote.execute_command = Mock()
                            mock_remote.file_exists = Mock(return_value=True)

                            # Act & Assert
                            with patch("pathlib.Path.mkdir"):
                                with patch("pathlib.Path.exists", return_value=True):
                                    with pytest.raises(RuntimeError, match="Upscaling failed"):
                                        gpu_executor.execute_upscaling_run(
                                            sample_upscale_run, video_path
                                        )

    def test_execute_upscaling_run_returns_correct_structure(
        self, gpu_executor, sample_upscale_run, sample_parent_run, sample_prompt
    ):
        """Test that execute_upscaling_run returns the expected result structure."""
        video_path = "outputs/run_rs_inference123/output.mp4"

        with patch.object(gpu_executor, "_initialize_services"):
            with patch.object(gpu_executor, "ssh_manager", create=True) as mock_ssh:
                with patch.object(gpu_executor, "docker_executor", create=True) as mock_docker:
                    with patch.object(gpu_executor, "remote_executor", create=True) as mock_remote:
                        with patch.object(gpu_executor, "file_transfer", create=True):
                            # Setup mocks
                            mock_ssh.__enter__ = Mock(return_value=mock_ssh)
                            mock_ssh.__exit__ = Mock(return_value=None)
                            # Mock ssh_manager.execute_command to return 3-tuple
                            mock_ssh.execute_command = Mock(return_value=(0, "", ""))
                            mock_docker.run_upscaling.return_value = {
                                "status": "completed",
                                "duration_seconds": 180,
                            }
                            mock_remote.execute_command = Mock()
                            mock_remote.file_exists = Mock(return_value=True)

                            # Act
                            with patch("pathlib.Path.mkdir"):
                                with patch("pathlib.Path.exists", return_value=True):
                                    result = gpu_executor.execute_upscaling_run(
                                        sample_upscale_run, video_path
                                    )

                            # Assert - check result structure
                            assert "status" in result
                            assert "run_id" in result
                            assert result["status"] == "completed"
                            assert "log_path" in result

    def test_execute_upscaling_run_initializes_services(
        self, gpu_executor, sample_upscale_run, sample_parent_run, sample_prompt
    ):
        """Test that execute_upscaling_run initializes services if needed."""
        video_path = "outputs/run_rs_inference123/output.mp4"

        with patch.object(gpu_executor, "_initialize_services") as mock_init:
            with patch.object(gpu_executor, "ssh_manager", create=True) as mock_ssh:
                with patch.object(gpu_executor, "docker_executor", create=True) as mock_docker:
                    with patch.object(gpu_executor, "remote_executor", create=True) as mock_remote:
                        with patch.object(gpu_executor, "file_transfer", create=True):
                            # Setup mocks
                            mock_ssh.__enter__ = Mock(return_value=mock_ssh)
                            mock_ssh.__exit__ = Mock(return_value=None)
                            # Mock ssh_manager.execute_command to return 3-tuple
                            mock_ssh.execute_command = Mock(return_value=(0, "", ""))
                            # GPU executor expects synchronous completion with "completed" or "failed"
                            mock_docker.run_upscaling.return_value = {"status": "completed"}
                            mock_remote.execute_command = Mock()
                            mock_remote.file_exists = Mock(return_value=True)

                            # Act
                            with patch("pathlib.Path.mkdir"):
                                with patch("pathlib.Path.exists", return_value=True):
                                    gpu_executor.execute_upscaling_run(
                                        sample_upscale_run, video_path
                                    )

                            # Assert - check services were initialized
                            mock_init.assert_called_once()
