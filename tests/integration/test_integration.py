"""
Integration tests for the Cosmos-Transfer1 workflow system.

This module tests the complete system integration, including all services
working together to execute complete workflows.
"""

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from cosmos_workflow.config.config_manager import ConfigManager
from cosmos_workflow.connection.ssh_manager import SSHManager
from cosmos_workflow.execution.docker_executor import DockerExecutor
from cosmos_workflow.transfer.file_transfer import FileTransferService
from cosmos_workflow.workflows.workflow_orchestrator import WorkflowOrchestrator


class TestSystemIntegration:
    """Integration tests for the complete Cosmos-Transfer1 system."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Create temporary test directory structure
        self.temp_dir = tempfile.mkdtemp()

        # Create test prompt file
        self.test_prompt_file = Path(self.temp_dir) / "test_prompt.json"
        self.test_prompt_file.write_text(
            json.dumps(
                {
                    "prompt": "A beautiful sunset over the ocean",
                    "negative_prompt": "blurry, low quality",
                    "num_frames": 24,
                    "fps": 24,
                }
            )
        )

        # Create test video directory
        self.test_video_dir = Path(self.temp_dir) / "inputs" / "videos" / "test_prompt"
        self.test_video_dir.mkdir(parents=True)

        # Create mock video files
        for i in range(3):
            (self.test_video_dir / f"frame_{i:03d}.png").write_text(f"Mock frame {i}")

        # Create test scripts directory
        self.test_scripts_dir = Path(self.temp_dir) / "scripts"
        self.test_scripts_dir.mkdir()
        (self.test_scripts_dir / "inference.sh").write_text("#!/bin/bash\necho 'Running inference'")
        (self.test_scripts_dir / "upscale.sh").write_text("#!/bin/bash\necho 'Running upscaling'")

        # Create mock config file
        self.config_file = Path(self.temp_dir) / "config.toml"
        self.config_file.write_text(
            """[remote]
host = "192.168.1.100"
user = "ubuntu"
port = 22
ssh_key = "./test_ssh_key"
remote_dir = "/home/ubuntu/cosmos-transfer1"

[paths]
local_prompts_dir = "./inputs/prompts"
local_videos_dir = "./inputs/videos"
local_outputs_dir = "./outputs"
local_notes_dir = "./notes"

[docker]
image = "cosmos-transfer1:latest"
"""
        )

        # Mock ConfigManager to avoid validation errors
        with patch(
            "cosmos_workflow.workflows.workflow_orchestrator.ConfigManager"
        ) as mock_config_class:
            # Create mock config manager
            mock_config_manager = Mock()
            mock_config_class.return_value = mock_config_manager

            # Mock remote config
            mock_remote_config = Mock()
            mock_remote_config.remote_dir = "/home/ubuntu/cosmos-transfer1"
            mock_remote_config.docker_image = "cosmos-transfer1:latest"
            mock_remote_config.host = "192.168.1.100"
            mock_config_manager.get_remote_config.return_value = mock_remote_config

            # Mock SSH options
            mock_ssh_options = {"host": "192.168.1.100", "user": "ubuntu"}
            mock_config_manager.get_ssh_options.return_value = mock_ssh_options

            # Mock local config
            mock_local_config = Mock()
            mock_local_config.notes_dir = Path(self.temp_dir) / "notes"
            mock_config_manager.get_local_config.return_value = mock_local_config

            # Initialize WorkflowOrchestrator
            self.orchestrator = WorkflowOrchestrator(str(self.config_file))

    def teardown_method(self):
        """Clean up test fixtures after each test method."""
        import shutil

        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    @patch("cosmos_workflow.workflows.workflow_orchestrator.SSHManager")
    @patch("cosmos_workflow.workflows.workflow_orchestrator.FileTransferService")
    @patch("cosmos_workflow.workflows.workflow_orchestrator.DockerExecutor")
    def test_complete_workflow_integration(
        self, mock_docker_class, mock_file_transfer_class, mock_ssh_class
    ):
        """Test complete end-to-end workflow integration."""
        # Mock all services with realistic behavior
        mock_ssh_manager = Mock()
        mock_ssh_manager.__enter__ = Mock(return_value=mock_ssh_manager)
        mock_ssh_manager.__exit__ = Mock(return_value=None)
        mock_ssh_class.return_value = mock_ssh_manager

        mock_file_transfer = Mock()
        mock_file_transfer_class.return_value = mock_file_transfer

        mock_docker_executor = Mock()
        mock_docker_class.return_value = mock_docker_executor

        # Mock config manager methods
        mock_remote_config = Mock()
        mock_remote_config.remote_dir = "/home/ubuntu/cosmos-transfer1"
        mock_remote_config.docker_image = "cosmos-transfer1:latest"
        mock_remote_config.host = "192.168.1.100"
        self.orchestrator.config_manager.get_remote_config.return_value = mock_remote_config

        mock_ssh_options = {
            "host": "192.168.1.100",
            "user": "ubuntu",
            "key_file": "~/.ssh/test.pem",
        }
        self.orchestrator.config_manager.get_ssh_options.return_value = mock_ssh_options

        mock_local_config = Mock()
        mock_local_config.notes_dir = Path(self.temp_dir) / "notes"
        self.orchestrator.config_manager.get_local_config.return_value = mock_local_config

        # Run complete workflow
        result = self.orchestrator.run_full_cycle(
            self.test_prompt_file, num_gpu=2, cuda_devices="0,1", upscale_weight=0.7
        )

        # Verify complete workflow execution
        assert result["status"] == "success"
        assert result["prompt_name"] == "test_prompt"
        assert result["upscaled"] is True
        assert result["upscale_weight"] == 0.7
        assert result["num_gpu"] == 2
        assert result["cuda_devices"] == "0,1"

        # Verify all workflow steps were executed in correct order
        mock_file_transfer.upload_prompt_and_videos.assert_called_once()
        mock_docker_executor.run_inference.assert_called_once()
        mock_docker_executor.run_upscaling.assert_called_once()
        mock_file_transfer.download_results.assert_called_once()

        # Verify SSH context manager was used properly
        mock_ssh_manager.__enter__.assert_called_once()
        mock_ssh_manager.__exit__.assert_called_once()

        # Verify logging was performed
        log_file = mock_local_config.notes_dir / "run_history.log"
        assert log_file.exists()

    @patch("cosmos_workflow.workflows.workflow_orchestrator.SSHManager")
    @patch("cosmos_workflow.workflows.workflow_orchestrator.FileTransferService")
    @patch("cosmos_workflow.workflows.workflow_orchestrator.DockerExecutor")
    def test_workflow_with_custom_video_directory(
        self, mock_docker_class, mock_file_transfer_class, mock_ssh_class
    ):
        """Test workflow with custom video directory structure."""
        # Mock all services
        mock_ssh_manager = Mock()
        mock_ssh_manager.__enter__ = Mock(return_value=mock_ssh_manager)
        mock_ssh_manager.__exit__ = Mock(return_value=None)
        mock_ssh_class.return_value = mock_ssh_manager

        mock_file_transfer = Mock()
        mock_file_transfer_class.return_value = mock_file_transfer

        mock_docker_executor = Mock()
        mock_docker_class.return_value = mock_docker_executor

        # Mock config manager methods
        mock_remote_config = Mock()
        mock_remote_config.remote_dir = "/home/ubuntu/cosmos-transfer1"
        mock_remote_config.docker_image = "cosmos-transfer1:latest"
        self.orchestrator.config_manager.get_remote_config.return_value = mock_remote_config

        mock_ssh_options = {"host": "192.168.1.100", "user": "ubuntu"}
        self.orchestrator.config_manager.get_ssh_options.return_value = mock_ssh_options

        mock_local_config = Mock()
        mock_local_config.notes_dir = Path(self.temp_dir) / "notes"
        self.orchestrator.config_manager.get_local_config.return_value = mock_local_config

        # Run workflow with custom video subdirectory
        result = self.orchestrator.run_full_cycle(
            self.test_prompt_file, videos_subdir="custom_videos", num_gpu=1, cuda_devices="0"
        )

        # Verify custom video directory was used
        mock_file_transfer.upload_prompt_and_videos.assert_called_once()
        call_args = mock_file_transfer.upload_prompt_and_videos.call_args
        video_dirs = call_args[0][1]
        assert len(video_dirs) == 1
        assert video_dirs[0] == Path("inputs/videos/custom_videos")

        # Verify workflow completed successfully
        assert result["status"] == "success"
        assert result["upscaled"] is True

    @patch("cosmos_workflow.workflows.workflow_orchestrator.SSHManager")
    @patch("cosmos_workflow.workflows.workflow_orchestrator.FileTransferService")
    @patch("cosmos_workflow.workflows.workflow_orchestrator.DockerExecutor")
    def test_workflow_failure_recovery_and_logging(
        self, mock_docker_class, mock_file_transfer_class, mock_ssh_class
    ):
        """Test workflow failure handling and recovery logging."""
        # Mock all services
        mock_ssh_manager = Mock()
        mock_ssh_manager.__enter__ = Mock(return_value=mock_ssh_manager)
        mock_ssh_manager.__exit__ = Mock(return_value=None)
        mock_ssh_class.return_value = mock_ssh_manager

        mock_file_transfer = Mock()
        mock_file_transfer.upload_prompt_and_videos.side_effect = RuntimeError(
            "Network connection failed"
        )
        mock_file_transfer_class.return_value = mock_file_transfer

        mock_docker_executor = Mock()
        mock_docker_class.return_value = mock_docker_executor

        # Mock config manager methods
        mock_remote_config = Mock()
        mock_remote_config.remote_dir = "/home/ubuntu/cosmos-transfer1"
        mock_remote_config.docker_image = "cosmos-transfer1:latest"
        self.orchestrator.config_manager.get_remote_config.return_value = mock_remote_config

        mock_ssh_options = {"host": "192.168.1.100", "user": "ubuntu"}
        self.orchestrator.config_manager.get_ssh_options.return_value = mock_ssh_options

        mock_local_config = Mock()
        mock_local_config.notes_dir = Path(self.temp_dir) / "notes"
        self.orchestrator.config_manager.get_local_config.return_value = mock_local_config

        # Should raise RuntimeError with proper error message
        with pytest.raises(RuntimeError, match="Workflow failed: Network connection failed"):
            self.orchestrator.run_full_cycle(self.test_prompt_file)

        # Verify failure was logged
        log_file = mock_local_config.notes_dir / "run_history.log"
        assert log_file.exists()

        # Check log content for failure entry
        with open(log_file, "r") as f:
            log_content = f.read()
            assert "FAILED" in log_content
            assert "Network connection failed" in log_content

    @patch("cosmos_workflow.workflows.workflow_orchestrator.SSHManager")
    @patch("cosmos_workflow.workflows.workflow_orchestrator.FileTransferService")
    @patch("cosmos_workflow.workflows.workflow_orchestrator.DockerExecutor")
    def test_inference_only_workflow_integration(
        self, mock_docker_class, mock_file_transfer_class, mock_ssh_class
    ):
        """Test inference-only workflow integration."""
        # Mock all services
        mock_ssh_manager = Mock()
        mock_ssh_manager.__enter__ = Mock(return_value=mock_ssh_manager)
        mock_ssh_manager.__exit__ = Mock(return_value=None)
        mock_ssh_class.return_value = mock_ssh_manager

        mock_file_transfer = Mock()
        mock_file_transfer_class.return_value = mock_file_transfer

        mock_docker_executor = Mock()
        mock_docker_class.return_value = mock_docker_executor

        # Mock config manager methods
        mock_remote_config = Mock()
        mock_remote_config.remote_dir = "/home/ubuntu/cosmos-transfer1"
        mock_remote_config.docker_image = "cosmos-transfer1:latest"
        self.orchestrator.config_manager.get_remote_config.return_value = mock_remote_config

        mock_ssh_options = {"host": "192.168.1.100", "user": "ubuntu"}
        self.orchestrator.config_manager.get_ssh_options.return_value = mock_ssh_options

        # Run inference-only workflow
        result = self.orchestrator.run_inference_only(
            self.test_prompt_file, num_gpu=4, cuda_devices="0,1,2,3"
        )

        # Verify inference-only execution
        assert result["status"] == "success"
        assert result["prompt_name"] == "test_prompt"
        assert result["num_gpu"] == 4
        assert result["cuda_devices"] == "0,1,2,3"

        # Verify only inference was executed
        mock_file_transfer.upload_prompt_and_videos.assert_called_once()
        mock_docker_executor.run_inference.assert_called_once()
        mock_docker_executor.run_upscaling.assert_not_called()
        mock_file_transfer.download_results.assert_called_once()

    @patch("cosmos_workflow.workflows.workflow_orchestrator.SSHManager")
    @patch("cosmos_workflow.workflows.workflow_orchestrator.FileTransferService")
    @patch("cosmos_workflow.workflows.workflow_orchestrator.DockerExecutor")
    def test_upscaling_only_workflow_integration(
        self, mock_docker_class, mock_file_transfer_class, mock_ssh_class
    ):
        """Test upscaling-only workflow integration."""
        # Mock all services
        mock_ssh_manager = Mock()
        mock_ssh_manager.__enter__ = Mock(return_value=mock_ssh_manager)
        mock_ssh_manager.__exit__ = Mock(return_value=None)
        mock_ssh_class.return_value = mock_ssh_manager

        mock_file_transfer = Mock()
        mock_file_transfer_class.return_value = mock_file_transfer

        mock_docker_executor = Mock()
        mock_docker_class.return_value = mock_docker_executor

        # Mock config manager methods
        mock_remote_config = Mock()
        mock_remote_config.remote_dir = "/home/ubuntu/cosmos-transfer1"
        mock_remote_config.docker_image = "cosmos-transfer1:latest"
        self.orchestrator.config_manager.get_remote_config.return_value = mock_remote_config

        mock_ssh_options = {"host": "192.168.1.100", "user": "ubuntu"}
        self.orchestrator.config_manager.get_ssh_options.return_value = mock_ssh_options

        # Run upscaling-only workflow
        result = self.orchestrator.run_upscaling_only(
            self.test_prompt_file, upscale_weight=0.9, num_gpu=2, cuda_devices="0,1"
        )

        # Verify upscaling-only execution
        assert result["status"] == "success"
        assert result["prompt_name"] == "test_prompt"
        assert result["upscale_weight"] == 0.9
        assert result["num_gpu"] == 2
        assert result["cuda_devices"] == "0,1"

        # Verify only upscaling was executed
        mock_file_transfer.upload_prompt_and_videos.assert_not_called()
        mock_docker_executor.run_inference.assert_not_called()
        mock_docker_executor.run_upscaling.assert_called_once()
        mock_file_transfer.download_results.assert_called_once()

    @patch("cosmos_workflow.workflows.workflow_orchestrator.SSHManager")
    @patch("cosmos_workflow.workflows.workflow_orchestrator.FileTransferService")
    @patch("cosmos_workflow.workflows.workflow_orchestrator.DockerExecutor")
    def test_system_status_check_integration(
        self, mock_docker_class, mock_file_transfer_class, mock_ssh_class
    ):
        """Test complete system status check integration."""
        # Mock all services
        mock_ssh_manager = Mock()
        mock_ssh_manager.__enter__ = Mock(return_value=mock_ssh_manager)
        mock_ssh_manager.__exit__ = Mock(return_value=None)
        mock_ssh_class.return_value = mock_ssh_manager

        mock_file_transfer = Mock()
        mock_file_transfer.file_exists_remote.return_value = True
        mock_file_transfer_class.return_value = mock_file_transfer

        mock_docker_executor = Mock()
        mock_docker_status = {
            "docker_running": True,
            "docker_info": "Docker version 20.10.0",
            "available_images": "cosmos-transfer1:latest",
            "running_containers": "No running containers",
        }
        mock_docker_executor.get_docker_status.return_value = mock_docker_status
        mock_docker_class.return_value = mock_docker_executor

        # Mock config manager methods
        mock_remote_config = Mock()
        mock_remote_config.remote_dir = "/home/ubuntu/cosmos-transfer1"
        self.orchestrator.config_manager.get_remote_config.return_value = mock_remote_config

        mock_ssh_options = {"host": "192.168.1.100", "user": "ubuntu"}
        self.orchestrator.config_manager.get_ssh_options.return_value = mock_ssh_options

        # Check system status
        status = self.orchestrator.check_remote_status()

        # Verify complete status information
        assert status["ssh_status"] == "connected"
        assert status["docker_status"] == mock_docker_status
        assert status["remote_directory_exists"] is True
        assert status["remote_directory"] == "/home/ubuntu/cosmos-transfer1"

        # Verify all status checks were performed
        mock_docker_executor.get_docker_status.assert_called_once()
        mock_file_transfer.file_exists_remote.assert_called_once_with(
            "/home/ubuntu/cosmos-transfer1"
        )
        mock_ssh_manager.__enter__.assert_called_once()
        mock_ssh_manager.__exit__.assert_called_once()

    @patch("cosmos_workflow.workflows.workflow_orchestrator.SSHManager")
    @patch("cosmos_workflow.workflows.workflow_orchestrator.FileTransferService")
    @patch("cosmos_workflow.workflows.workflow_orchestrator.DockerExecutor")
    def test_workflow_with_no_upscale_flag(
        self, mock_docker_class, mock_file_transfer_class, mock_ssh_class
    ):
        """Test workflow with upscaling explicitly disabled."""
        # Mock all services
        mock_ssh_manager = Mock()
        mock_ssh_manager.__enter__ = Mock(return_value=mock_ssh_manager)
        mock_ssh_manager.__exit__ = Mock(return_value=None)
        mock_ssh_class.return_value = mock_ssh_manager

        mock_file_transfer = Mock()
        mock_file_transfer_class.return_value = mock_file_transfer

        mock_docker_executor = Mock()
        mock_docker_class.return_value = mock_docker_executor

        # Mock config manager methods
        mock_remote_config = Mock()
        mock_remote_config.remote_dir = "/home/ubuntu/cosmos-transfer1"
        mock_remote_config.docker_image = "cosmos-transfer1:latest"
        self.orchestrator.config_manager.get_remote_config.return_value = mock_remote_config

        mock_ssh_options = {"host": "192.168.1.100", "user": "ubuntu"}
        self.orchestrator.config_manager.get_ssh_options.return_value = mock_ssh_options

        mock_local_config = Mock()
        mock_local_config.notes_dir = Path(self.temp_dir) / "notes"
        self.orchestrator.config_manager.get_local_config.return_value = mock_local_config

        # Run workflow with no upscale
        result = self.orchestrator.run_full_cycle(
            self.test_prompt_file, no_upscale=True, num_gpu=1, cuda_devices="0"
        )

        # Verify upscaling was skipped
        assert result["status"] == "success"
        assert result["upscaled"] is False

        # Verify workflow steps
        mock_file_transfer.upload_prompt_and_videos.assert_called_once()
        mock_docker_executor.run_inference.assert_called_once()
        mock_docker_executor.run_upscaling.assert_not_called()
        mock_file_transfer.download_results.assert_called_once()

        # Verify logging reflects no upscaling
        log_file = mock_local_config.notes_dir / "run_history.log"
        assert log_file.exists()

        with open(log_file, "r") as f:
            log_content = f.read()
            assert "upscaled=False" in log_content


if __name__ == "__main__":
    pytest.main([__file__])
