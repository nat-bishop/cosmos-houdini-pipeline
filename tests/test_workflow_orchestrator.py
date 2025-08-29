"""
Tests for the WorkflowOrchestrator class.

This module tests the workflow orchestration functionality that coordinates
all services to run complete Cosmos-Transfer1 workflows.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import os
from datetime import datetime
from cosmos_workflow.workflows.workflow_orchestrator import WorkflowOrchestrator
from cosmos_workflow.config.config_manager import ConfigManager
from cosmos_workflow.connection.ssh_manager import SSHManager
from cosmos_workflow.transfer.file_transfer import FileTransferService
from cosmos_workflow.execution.docker_executor import DockerExecutor


class TestWorkflowOrchestrator:
    """Test suite for WorkflowOrchestrator class."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Create temporary test files
        self.temp_dir = tempfile.mkdtemp()
        self.test_prompt_file = Path(self.temp_dir) / "test_prompt.json"
        self.test_prompt_file.write_text('{"test": "data"}')
        
        # Create mock config file
        self.config_file = Path(self.temp_dir) / "config.toml"
        self.config_file.write_text("""[remote]
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
""")
        
        # Mock ConfigManager to avoid validation errors
        with patch('cosmos_workflow.workflows.workflow_orchestrator.ConfigManager') as mock_config_class:
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
            
            # Initialize WorkflowOrchestrator with test config
            self.orchestrator = WorkflowOrchestrator(str(self.config_file))
    
    def teardown_method(self):
        """Clean up test fixtures after each test method."""
        import shutil
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_init_with_config_file(self):
        """Test WorkflowOrchestrator initialization with config file."""
        assert self.orchestrator.config_manager is not None
        assert self.orchestrator.ssh_manager is None
        assert self.orchestrator.file_transfer is None
        assert self.orchestrator.docker_executor is None
    
    @patch('cosmos_workflow.workflows.workflow_orchestrator.SSHManager')
    @patch('cosmos_workflow.workflows.workflow_orchestrator.FileTransferService')
    @patch('cosmos_workflow.workflows.workflow_orchestrator.DockerExecutor')
    def test_initialize_services_creates_all_services(self, mock_docker_class, mock_file_transfer_class, mock_ssh_class):
        """Test that _initialize_services creates all required services."""
        # Mock SSH manager
        mock_ssh_manager = Mock()
        mock_ssh_class.return_value = mock_ssh_manager
        
        # Mock file transfer service
        mock_file_transfer = Mock()
        mock_file_transfer_class.return_value = mock_file_transfer
        
        # Mock docker executor
        mock_docker_executor = Mock()
        mock_docker_class.return_value = mock_docker_executor
        
        # Mock config manager methods
        mock_remote_config = Mock()
        mock_remote_config.remote_dir = "/home/ubuntu/cosmos-transfer1"
        mock_remote_config.docker_image = "cosmos-transfer1:latest"
        self.orchestrator.config_manager.get_remote_config.return_value = mock_remote_config
        
        mock_ssh_options = {"host": "192.168.1.100", "user": "ubuntu"}
        self.orchestrator.config_manager.get_ssh_options.return_value = mock_ssh_options
        
        # Initialize services
        self.orchestrator._initialize_services()
        
        # Check that all services were created
        assert self.orchestrator.ssh_manager == mock_ssh_manager
        assert self.orchestrator.file_transfer == mock_file_transfer
        assert self.orchestrator.docker_executor == mock_docker_executor
        
        # Check that services were created with correct parameters
        mock_ssh_class.assert_called_once_with(mock_ssh_options)
        mock_file_transfer_class.assert_called_once_with(mock_ssh_manager, mock_remote_config.remote_dir)
        mock_docker_class.assert_called_once_with(mock_ssh_manager, mock_remote_config.remote_dir, mock_remote_config.docker_image)
    
    @patch('cosmos_workflow.workflows.workflow_orchestrator.SSHManager')
    @patch('cosmos_workflow.workflows.workflow_orchestrator.FileTransferService')
    @patch('cosmos_workflow.workflows.workflow_orchestrator.DockerExecutor')
    def test_run_full_cycle_successful_workflow(self, mock_docker_class, mock_file_transfer_class, mock_ssh_class):
        """Test successful execution of full cycle workflow."""
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
        mock_remote_config.host = "192.168.1.100"
        self.orchestrator.config_manager.get_remote_config.return_value = mock_remote_config
        
        mock_ssh_options = {"host": "192.168.1.100", "user": "ubuntu"}
        self.orchestrator.config_manager.get_ssh_options.return_value = mock_ssh_options
        
        mock_local_config = Mock()
        mock_local_config.notes_dir = Path(self.temp_dir) / "notes"
        self.orchestrator.config_manager.get_local_config.return_value = mock_local_config
        
        # Run full cycle workflow
        result = self.orchestrator.run_full_cycle(
            self.test_prompt_file,
            num_gpu=2,
            cuda_devices="0,1",
            upscale_weight=0.6
        )
        
        # Check result structure
        assert result["status"] == "success"
        assert result["prompt_name"] == "test_prompt"
        assert result["upscaled"] is True
        assert result["upscale_weight"] == 0.6
        assert result["num_gpu"] == 2
        assert result["cuda_devices"] == "0,1"
        assert "start_time" in result
        assert "end_time" in result
        assert "duration_seconds" in result
        
        # Check that all workflow steps were executed
        mock_file_transfer.upload_prompt_and_videos.assert_called_once()
        mock_docker_executor.run_inference.assert_called_once()
        mock_docker_executor.run_upscaling.assert_called_once()
        mock_file_transfer.download_results.assert_called_once()
        
        # Check that SSH context manager was used
        mock_ssh_manager.__enter__.assert_called_once()
        mock_ssh_manager.__exit__.assert_called_once()
    
    @patch('cosmos_workflow.workflows.workflow_orchestrator.SSHManager')
    @patch('cosmos_workflow.workflows.workflow_orchestrator.FileTransferService')
    @patch('cosmos_workflow.workflows.workflow_orchestrator.DockerExecutor')
    def test_run_full_cycle_with_no_upscale(self, mock_docker_class, mock_file_transfer_class, mock_ssh_class):
        """Test full cycle workflow with upscaling disabled."""
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
        
        # Run full cycle workflow with no upscale
        result = self.orchestrator.run_full_cycle(
            self.test_prompt_file,
            no_upscale=True,
            num_gpu=1,
            cuda_devices="0"
        )
        
        # Check result structure
        assert result["status"] == "success"
        assert result["upscaled"] is False
        
        # Check that upscaling was skipped
        mock_docker_executor.run_inference.assert_called_once()
        mock_docker_executor.run_upscaling.assert_not_called()
    
    @patch('cosmos_workflow.workflows.workflow_orchestrator.SSHManager')
    @patch('cosmos_workflow.workflows.workflow_orchestrator.FileTransferService')
    @patch('cosmos_workflow.workflows.workflow_orchestrator.DockerExecutor')
    def test_run_full_cycle_with_custom_video_subdir(self, mock_docker_class, mock_file_transfer_class, mock_ssh_class):
        """Test full cycle workflow with custom video subdirectory."""
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
        
        # Run full cycle workflow with custom video subdir
        result = self.orchestrator.run_full_cycle(
            self.test_prompt_file,
            videos_subdir="custom_videos",
            num_gpu=1,
            cuda_devices="0"
        )
        
        # Check that file transfer was called with custom video directory
        mock_file_transfer.upload_prompt_and_videos.assert_called_once()
        call_args = mock_file_transfer.upload_prompt_and_videos.call_args
        video_dirs = call_args[0][1]
        assert len(video_dirs) == 1
        assert video_dirs[0] == Path("inputs/videos/custom_videos")
        
        # Verify workflow completed successfully
        assert result["status"] == "success"
        assert result["upscaled"] is True
    
    @patch('cosmos_workflow.workflows.workflow_orchestrator.SSHManager')
    @patch('cosmos_workflow.workflows.workflow_orchestrator.FileTransferService')
    @patch('cosmos_workflow.workflows.workflow_orchestrator.DockerExecutor')
    def test_run_full_cycle_workflow_failure(self, mock_docker_class, mock_file_transfer_class, mock_ssh_class):
        """Test full cycle workflow failure handling."""
        # Mock all services
        mock_ssh_manager = Mock()
        mock_ssh_manager.__enter__ = Mock(return_value=mock_ssh_manager)
        mock_ssh_manager.__exit__ = Mock(return_value=None)
        mock_ssh_class.return_value = mock_ssh_manager
        
        mock_file_transfer = Mock()
        mock_file_transfer.upload_prompt_and_videos.side_effect = RuntimeError("Upload failed")
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
        
        # Should raise RuntimeError
        with pytest.raises(RuntimeError, match="Workflow failed: Upload failed"):
            self.orchestrator.run_full_cycle(self.test_prompt_file)
    
    @patch('cosmos_workflow.workflows.workflow_orchestrator.SSHManager')
    @patch('cosmos_workflow.workflows.workflow_orchestrator.FileTransferService')
    @patch('cosmos_workflow.workflows.workflow_orchestrator.DockerExecutor')
    def test_run_inference_only(self, mock_docker_class, mock_file_transfer_class, mock_ssh_class):
        """Test inference-only workflow execution."""
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
        
        # Run inference only
        result = self.orchestrator.run_inference_only(
            self.test_prompt_file,
            num_gpu=2,
            cuda_devices="0,1"
        )
        
        # Check result structure
        assert result["status"] == "success"
        assert result["prompt_name"] == "test_prompt"
        assert result["num_gpu"] == 2
        assert result["cuda_devices"] == "0,1"
        
        # Check that only inference was run
        mock_file_transfer.upload_prompt_and_videos.assert_called_once()
        mock_docker_executor.run_inference.assert_called_once()
        mock_docker_executor.run_upscaling.assert_not_called()
        mock_file_transfer.download_results.assert_called_once()
    
    @patch('cosmos_workflow.workflows.workflow_orchestrator.SSHManager')
    @patch('cosmos_workflow.workflows.workflow_orchestrator.FileTransferService')
    @patch('cosmos_workflow.workflows.workflow_orchestrator.DockerExecutor')
    def test_run_upscaling_only(self, mock_docker_class, mock_file_transfer_class, mock_ssh_class):
        """Test upscaling-only workflow execution."""
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
        
        # Run upscaling only
        result = self.orchestrator.run_upscaling_only(
            self.test_prompt_file,
            upscale_weight=0.7,
            num_gpu=1,
            cuda_devices="0"
        )
        
        # Check result structure
        assert result["status"] == "success"
        assert result["prompt_name"] == "test_prompt"
        assert result["upscale_weight"] == 0.7
        assert result["num_gpu"] == 1
        assert result["cuda_devices"] == "0"
        
        # Check that only upscaling was run
        mock_file_transfer.upload_prompt_and_videos.assert_not_called()
        mock_docker_executor.run_inference.assert_not_called()
        mock_docker_executor.run_upscaling.assert_called_once()
        mock_file_transfer.download_results.assert_called_once()
    
    @patch('cosmos_workflow.workflows.workflow_orchestrator.SSHManager')
    @patch('cosmos_workflow.workflows.workflow_orchestrator.FileTransferService')
    @patch('cosmos_workflow.workflows.workflow_orchestrator.DockerExecutor')
    def test_check_remote_status(self, mock_docker_class, mock_file_transfer_class, mock_ssh_class):
        """Test remote status checking functionality."""
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
            "docker_info": "Docker info",
            "available_images": "Image list",
            "running_containers": "Container list"
        }
        mock_docker_executor.get_docker_status.return_value = mock_docker_status
        mock_docker_class.return_value = mock_docker_executor
        
        # Mock config manager methods
        mock_remote_config = Mock()
        mock_remote_config.remote_dir = "/home/ubuntu/cosmos-transfer1"
        self.orchestrator.config_manager.get_remote_config.return_value = mock_remote_config
        
        mock_ssh_options = {"host": "192.168.1.100", "user": "ubuntu"}
        self.orchestrator.config_manager.get_ssh_options.return_value = mock_ssh_options
        
        # Check remote status
        status = self.orchestrator.check_remote_status()
        
        # Check status structure
        assert status["ssh_status"] == "connected"
        assert status["docker_status"] == mock_docker_status
        assert status["remote_directory_exists"] is True
        assert status["remote_directory"] == "/home/ubuntu/cosmos-transfer1"
        
        # Check that services were used
        mock_docker_executor.get_docker_status.assert_called_once()
        mock_file_transfer.file_exists_remote.assert_called_once_with("/home/ubuntu/cosmos-transfer1")
    
    @patch('cosmos_workflow.workflows.workflow_orchestrator.SSHManager')
    @patch('cosmos_workflow.workflows.workflow_orchestrator.FileTransferService')
    @patch('cosmos_workflow.workflows.workflow_orchestrator.DockerExecutor')
    def test_check_remote_status_ssh_failure(self, mock_docker_class, mock_file_transfer_class, mock_ssh_class):
        """Test remote status checking when SSH fails."""
        # Mock all services
        mock_ssh_manager = Mock()
        # Use MagicMock to properly handle magic methods
        mock_ssh_manager = MagicMock()
        mock_ssh_manager.__enter__.side_effect = Exception("SSH connection failed")
        mock_ssh_class.return_value = mock_ssh_manager
        
        mock_file_transfer = Mock()
        mock_file_transfer_class.return_value = mock_file_transfer
        
        mock_docker_executor = Mock()
        mock_docker_class.return_value = mock_docker_executor
        
        # Mock config manager methods
        mock_remote_config = Mock()
        mock_remote_config.remote_dir = "/home/ubuntu/cosmos-transfer1"
        self.orchestrator.config_manager.get_remote_config.return_value = mock_remote_config
        
        mock_ssh_options = {"host": "192.168.1.100", "user": "ubuntu"}
        self.orchestrator.config_manager.get_ssh_options.return_value = mock_ssh_options
        
        # Check remote status
        status = self.orchestrator.check_remote_status()
        
        # Check status structure
        assert status["ssh_status"] == "failed"
        assert "SSH connection failed" in status["error"]
    
    def test_log_workflow_completion(self):
        """Test workflow completion logging."""
        # Mock config manager
        with patch.object(self.orchestrator, 'config_manager') as mock_config:
            # Mock local config
            mock_local_config = Mock()
            mock_local_config.notes_dir = Path(self.temp_dir) / "notes"
            mock_config.get_local_config.return_value = mock_local_config
            
            # Mock remote config
            mock_remote_config = Mock()
            mock_remote_config.host = "192.168.1.100"
            mock_config.get_remote_config.return_value = mock_remote_config
            
            # Log workflow completion
            self.orchestrator._log_workflow_completion(
                self.test_prompt_file,
                upscaled=True,
                upscale_weight=0.8,
                num_gpu=2
            )
            
            # Check that log file was created
            log_file = mock_local_config.notes_dir / "run_history.log"
            assert log_file.exists()
            
            # Check log content
            with open(log_file, 'r') as f:
                log_content = f.read()
                assert "test_prompt.json" in log_content
                assert "outputs/test_prompt" in log_content
                assert "192.168.1.100" in log_content
                assert "num_gpu=2" in log_content
                assert "upscaled=True" in log_content
                assert "upscale_weight=0.8" in log_content
    
    def test_log_workflow_failure(self):
        """Test workflow failure logging."""
        # Mock config manager
        with patch.object(self.orchestrator, 'config_manager') as mock_config:
            # Mock local config
            mock_local_config = Mock()
            mock_local_config.notes_dir = Path(self.temp_dir) / "notes"
            mock_config.get_local_config.return_value = mock_local_config
            
            # Log workflow failure
            duration = datetime.now() - datetime.now()  # 0 duration
            self.orchestrator._log_workflow_failure(
                self.test_prompt_file,
                "Test error message",
                duration
            )
            
            # Check that log file was created
            log_file = mock_local_config.notes_dir / "run_history.log"
            assert log_file.exists()
            
            # Check log content
            with open(log_file, 'r') as f:
                log_content = f.read()
                assert "FAILED" in log_content
                assert "test_prompt.json" in log_content
                assert "Test error message" in log_content


if __name__ == "__main__":
    pytest.main([__file__])

