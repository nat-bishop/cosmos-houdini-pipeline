"""
CORRECT Integration tests that actually test your REAL code.
This is what your tests should look like for catching bugs.
"""

import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

# Import your REAL implementations, not fakes!
from cosmos_workflow.workflows.workflow_orchestrator import WorkflowOrchestrator
from cosmos_workflow.prompts.prompt_spec import PromptSpec
from cosmos_workflow.prompts.run_spec import RunSpec


class TestWorkflowOrchestratorReal:
    """Tests that actually verify your code works."""
    
    @pytest.fixture
    def test_config(self):
        """Test configuration."""
        return {
            "ssh": {
                "host": "test.gpu.server",
                "username": "test_user",
                "key_file": "/fake/key"
            },
            "docker": {
                "image": "cosmos:test",
                "gpu_device": 0
            },
            "paths": {
                "remote_base": "/test/remote",
                "local_output": "/test/output"
            }
        }
    
    @pytest.fixture
    def mock_ssh_client(self):
        """Mock ONLY the SSH boundary - can't test against real SSH."""
        mock = Mock()
        mock.exec_command.return_value = (0, "success", "")
        mock.open_sftp.return_value = Mock()  # Mock SFTP client
        return mock
    
    @pytest.fixture
    def real_orchestrator(self, test_config, mock_ssh_client):
        """REAL orchestrator that runs YOUR actual code."""
        with patch('paramiko.SSHClient') as mock_ssh_class:
            mock_ssh_class.return_value = mock_ssh_client
            
            # This is your REAL WorkflowOrchestrator!
            orchestrator = WorkflowOrchestrator(test_config)
            yield orchestrator
    
    def test_validation_logic_catches_invalid_specs(self, real_orchestrator):
        """This tests YOUR REAL validation logic."""
        invalid_spec = {
            "name": "test",
            # Missing required "prompt" field
        }
        
        # This runs YOUR actual validation code
        with pytest.raises(ValueError) as exc:
            real_orchestrator.validate_prompt_spec(invalid_spec)
        
        # If your validation logic is broken, this test WILL fail
        assert "prompt" in str(exc.value).lower()
    
    def test_retry_mechanism_actually_retries(self, real_orchestrator, mock_ssh_client):
        """This tests YOUR REAL retry logic."""
        # Make SSH fail twice, then succeed
        call_count = 0
        def exec_side_effect(cmd):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise ConnectionError("Network error")
            return (0, "success", "")
        
        mock_ssh_client.exec_command.side_effect = exec_side_effect
        
        # Run your REAL retry logic
        spec = {
            "id": "test_001",
            "name": "test",
            "prompt": "test prompt",
            "input_video_path": "/test/video.mp4"
        }
        
        result = real_orchestrator.run_workflow(spec, max_retries=3)
        
        # Verify YOUR retry logic actually worked
        assert call_count == 3  # Should have retried
        assert result is not None  # Should have succeeded
    
    def test_docker_command_generation(self, real_orchestrator):
        """This tests YOUR REAL Docker command building logic."""
        spec = {
            "prompt": "test scene",
            "control_weights": {"depth": 0.5, "edge": 0.3},
            "num_steps": 35,
            "guidance_scale": 8.0
        }
        
        # Run YOUR actual command building code
        cmd = real_orchestrator.build_docker_command(spec)
        
        # Verify YOUR logic built the command correctly
        assert "docker run" in cmd
        assert "--gpus" in cmd
        assert "depth" in cmd
        assert "0.5" in cmd
        # If your command building is broken, this WILL catch it
    
    def test_error_handling_formats_correctly(self, real_orchestrator, mock_ssh_client):
        """This tests YOUR REAL error handling."""
        # Make SSH fail with specific error
        mock_ssh_client.exec_command.side_effect = PermissionError("Access denied")
        
        spec = {
            "id": "test_001", 
            "name": "test",
            "prompt": "test prompt",
            "input_video_path": "/test/video.mp4"
        }
        
        # Run YOUR actual error handling code
        result = real_orchestrator.run_workflow(spec)
        
        # Verify YOUR error handling worked
        assert result["status"] == "failed"
        assert "Access denied" in result["error"]
        # If error handling is broken, test fails
    
    def test_file_upload_with_correct_paths(self, real_orchestrator, mock_ssh_client):
        """This tests YOUR REAL file upload logic."""
        mock_sftp = Mock()
        mock_ssh_client.open_sftp.return_value = mock_sftp
        
        spec = {
            "id": "test_001",
            "name": "test", 
            "prompt": "test prompt",
            "input_video_path": "/local/video.mp4"
        }
        
        # Run YOUR actual upload logic
        real_orchestrator.upload_files(spec)
        
        # Verify YOUR path construction logic
        mock_sftp.put.assert_called()
        call_args = mock_sftp.put.call_args[0]
        assert "/local/video.mp4" in call_args[0]
        assert "/test/remote" in call_args[1]  # From config
    
    def test_workflow_cleanup_on_failure(self, real_orchestrator, mock_ssh_client):
        """This tests YOUR REAL cleanup logic."""
        # Track cleanup calls
        cleanup_commands = []
        
        def track_cleanup(cmd):
            cleanup_commands.append(cmd)
            if "docker run" in cmd:
                raise RuntimeError("Container failed")
            return (0, "", "")
        
        mock_ssh_client.exec_command.side_effect = track_cleanup
        
        spec = {
            "id": "test_001",
            "name": "test",
            "prompt": "test prompt", 
            "input_video_path": "/test/video.mp4"
        }
        
        # Run workflow that will fail
        result = real_orchestrator.run_workflow(spec)
        
        # Verify YOUR cleanup logic ran
        cleanup_cmds = [c for c in cleanup_commands if "docker" in c and "rm" in c]
        assert len(cleanup_cmds) > 0  # Should have cleaned up
        assert result["status"] == "failed"


class TestPromptSpecValidation:
    """Test your REAL PromptSpec validation logic."""
    
    def test_prompt_spec_validation(self):
        """Test YOUR actual PromptSpec class."""
        # This uses your REAL PromptSpec class
        with pytest.raises(ValueError):
            # YOUR validation should catch this
            spec = PromptSpec(
                id="test",
                name="test",
                prompt="",  # Empty prompt should fail
                input_video_path="/test.mp4"
            )
    
    def test_run_spec_validation(self):
        """Test YOUR actual RunSpec class."""
        # This uses your REAL RunSpec class  
        with pytest.raises(ValueError):
            # YOUR validation should catch this
            spec = RunSpec(
                id="test",
                prompt_spec_id="ps_001",
                num_steps=-1,  # Invalid steps
                guidance_scale=8.0
            )


# This is the key difference:
# - FakeWorkflowOrchestrator = Doesn't run any of your code
# - WorkflowOrchestrator with mocked SSH = Runs ALL your code except SSH
# 
# The second option actually tests that your code works!