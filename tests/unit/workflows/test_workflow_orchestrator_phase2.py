"""Tests for Phase 2 WorkflowOrchestrator integration with logging."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from cosmos_workflow.workflows.workflow_orchestrator import WorkflowOrchestrator


class TestWorkflowOrchestratorPhase2:
    """Test WorkflowOrchestrator integration with WorkflowService logging methods."""

    @pytest.fixture
    def mock_config_manager(self):
        """Create a mock config manager."""
        with patch("cosmos_workflow.workflows.workflow_orchestrator.ConfigManager") as MockConfig:
            mock_config = MockConfig.return_value

            # Mock remote config
            mock_remote_config = Mock()
            mock_remote_config.remote_dir = "/remote/cosmos"
            mock_remote_config.docker_image = "cosmos:latest"
            mock_config.get_remote_config.return_value = mock_remote_config

            # Mock SSH options
            mock_ssh_options = Mock()
            mock_config.get_ssh_options.return_value = mock_ssh_options

            yield mock_config

    @pytest.fixture
    def mock_ssh_manager(self):
        """Create a mock SSH manager."""
        with patch("cosmos_workflow.workflows.workflow_orchestrator.SSHManager") as MockSSH:
            mock_ssh = MockSSH.return_value
            mock_ssh.__enter__ = Mock(return_value=mock_ssh)
            mock_ssh.__exit__ = Mock(return_value=None)
            mock_ssh.execute_command_success = Mock()
            yield mock_ssh

    @pytest.fixture
    def mock_file_transfer(self):
        """Create a mock file transfer service."""
        with patch("cosmos_workflow.workflows.workflow_orchestrator.FileTransferService") as MockFT:
            mock_ft = MockFT.return_value
            mock_ft.upload_file = Mock()
            mock_ft.download_results = Mock()
            yield mock_ft

    @pytest.fixture
    def mock_docker_executor(self):
        """Create a mock docker executor."""
        with patch("cosmos_workflow.workflows.workflow_orchestrator.DockerExecutor") as MockDocker:
            mock_docker = MockDocker.return_value

            def mock_run_inference(prompt_file, run_id, **kwargs):
                prompt_name = f"run_{run_id}"
                return {
                    "status": "success",
                    "log_path": f"outputs/{prompt_name}/logs/run.log",
                    "prompt_name": prompt_name,
                }

            def mock_run_upscaling(prompt_file, run_id, **kwargs):
                prompt_name = f"run_{run_id}"
                return {
                    "status": "success",
                    "log_path": f"outputs/{prompt_name}_upscaled/logs/run.log",
                    "prompt_name": f"{prompt_name}_upscaled",
                }

            mock_docker.run_inference = Mock(side_effect=mock_run_inference)
            mock_docker.run_upscaling = Mock(side_effect=mock_run_upscaling)
            yield mock_docker

    @pytest.fixture
    def workflow_orchestrator(self, mock_config_manager):
        """Create WorkflowOrchestrator instance."""
        orchestrator = WorkflowOrchestrator()
        orchestrator.config_manager = mock_config_manager
        return orchestrator

    @pytest.fixture
    def mock_workflow_service(self):
        """Create a mock workflow service."""
        mock_service = Mock()
        # Mock the unified update_run method
        mock_service.update_run = Mock(return_value={"id": "rs_test123", "status": "updated"})
        # Keep the deprecated methods for backward compatibility tests
        mock_service.update_run_with_log = Mock(
            return_value={"id": "rs_test123", "log_path": "outputs/run_rs_test123/logs/run.log"}
        )
        mock_service.update_run_error = Mock(
            return_value={"id": "rs_test123", "status": "failed", "error_message": "Test error"}
        )
        return mock_service

    def test_orchestrator_has_service_attribute(self, workflow_orchestrator):
        """Test that WorkflowOrchestrator has a service attribute for Phase 2."""
        # The service attribute will be set when implementation is done
        # For now, we're testing that it can be set
        mock_service = Mock()
        workflow_orchestrator.service = mock_service
        assert hasattr(workflow_orchestrator, "service")

    def test_execute_run_calls_update_run_with_log_on_success(
        self,
        workflow_orchestrator,
        mock_ssh_manager,
        mock_file_transfer,
        mock_docker_executor,
        mock_workflow_service,
    ):
        """Test that execute_run calls update_run_with_log when inference succeeds."""
        # Set up the orchestrator with mocks
        orchestrator = workflow_orchestrator
        orchestrator.ssh_manager = mock_ssh_manager
        orchestrator.file_transfer = mock_file_transfer
        orchestrator.docker_executor = mock_docker_executor
        orchestrator.service = mock_workflow_service

        # Prepare test data
        run_dict = {
            "id": "rs_test123",
            "prompt_id": "ps_test456",
            "model_type": "transfer",
            "status": "running",
            "execution_config": {"gpu": "A100"},
            "outputs": {},
            "metadata": {},
        }

        prompt_dict = {
            "id": "ps_test456",
            "model_type": "transfer",
            "prompt_text": "Test prompt",
            "inputs": {"video": "/path/to/video.mp4"},
            "parameters": {"num_steps": 10},
        }

        # Execute run
        result = orchestrator.execute_run(run_dict, prompt_dict)

        # Verify update_run was called with log_path
        mock_workflow_service.update_run.assert_called_once_with(
            "rs_test123", log_path="outputs/run_rs_test123/logs/run.log"
        )

        # Verify result
        assert result["status"] == "success"

    def test_execute_run_calls_update_run_error_on_failure(
        self,
        workflow_orchestrator,
        mock_ssh_manager,
        mock_file_transfer,
        mock_docker_executor,
        mock_workflow_service,
    ):
        """Test that execute_run calls update_run_error when inference fails."""
        # Set up the orchestrator with mocks
        orchestrator = workflow_orchestrator
        orchestrator.ssh_manager = mock_ssh_manager
        orchestrator.file_transfer = mock_file_transfer
        orchestrator.docker_executor = mock_docker_executor
        orchestrator.service = mock_workflow_service

        # Make docker_executor.run_inference raise an exception
        error_msg = "Docker container failed to start"
        mock_docker_executor.run_inference.side_effect = Exception(error_msg)

        # Prepare test data
        run_dict = {
            "id": "rs_test789",
            "prompt_id": "ps_test456",
            "model_type": "transfer",
            "status": "running",
            "execution_config": {"gpu": "A100"},
            "outputs": {},
            "metadata": {},
        }

        prompt_dict = {
            "id": "ps_test456",
            "model_type": "transfer",
            "prompt_text": "Test prompt",
            "inputs": {"video": "/path/to/video.mp4"},
            "parameters": {"num_steps": 10},
        }

        # Execute run
        result = orchestrator.execute_run(run_dict, prompt_dict)

        # Verify update_run was called with error_message
        mock_workflow_service.update_run.assert_called_once_with(
            "rs_test789", error_message=error_msg
        )

        # Verify result
        assert result["status"] == "failed"
        assert result["error"] == error_msg

    @pytest.mark.skip(reason="Upscaling is temporarily disabled - see ROADMAP.md")
    def test_execute_run_with_upscaling_updates_log_paths(
        self,
        workflow_orchestrator,
        mock_ssh_manager,
        mock_file_transfer,
        mock_docker_executor,
        mock_workflow_service,
    ):
        """Test that execute_run updates log paths for both inference and upscaling."""
        # Set up the orchestrator with mocks
        orchestrator = workflow_orchestrator
        orchestrator.ssh_manager = mock_ssh_manager
        orchestrator.file_transfer = mock_file_transfer
        orchestrator.docker_executor = mock_docker_executor
        orchestrator.service = mock_workflow_service

        # Prepare test data
        run_dict = {
            "id": "rs_upscale123",
            "prompt_id": "ps_test456",
            "model_type": "transfer",
            "status": "running",
            "execution_config": {"gpu": "A100"},
            "outputs": {},
            "metadata": {},
        }

        prompt_dict = {
            "id": "ps_test456",
            "model_type": "transfer",
            "prompt_text": "Test prompt",
            "inputs": {"video": "/path/to/video.mp4"},
            "parameters": {"num_steps": 10},
        }

        # Execute run with upscaling
        result = orchestrator.execute_run(run_dict, prompt_dict, upscale=True, upscale_weight=0.7)

        # Verify update_run was called for both operations
        assert mock_workflow_service.update_run.call_count == 2

        # Check the calls
        calls = mock_workflow_service.update_run.call_args_list
        assert calls[0] == (
            ("rs_upscale123",),
            {"log_path": "outputs/run_rs_upscale123/logs/run.log"},
        )
        assert calls[1] == (
            ("rs_upscale123",),
            {"log_path": "outputs/run_rs_upscale123_upscaled/logs/run.log"},
        )

        # Verify result
        assert result["status"] == "success"
        assert result["upscaled"] is True

    def test_execute_run_handles_missing_log_path(
        self,
        workflow_orchestrator,
        mock_ssh_manager,
        mock_file_transfer,
        mock_docker_executor,
        mock_workflow_service,
    ):
        """Test that execute_run handles cases where log_path is not returned."""
        # Set up the orchestrator with mocks
        orchestrator = workflow_orchestrator
        orchestrator.ssh_manager = mock_ssh_manager
        orchestrator.file_transfer = mock_file_transfer
        orchestrator.docker_executor = mock_docker_executor
        orchestrator.service = mock_workflow_service

        # Override the mock to return result without log_path
        mock_docker_executor.run_inference.side_effect = None
        mock_docker_executor.run_inference.return_value = {
            "status": "success",
            "prompt_name": "run_rs_nopath",
        }

        # Prepare test data
        run_dict = {
            "id": "rs_nopath",
            "prompt_id": "ps_test456",
            "model_type": "transfer",
            "status": "running",
            "execution_config": {"gpu": "A100"},
            "outputs": {},
            "metadata": {},
        }

        prompt_dict = {
            "id": "ps_test456",
            "model_type": "transfer",
            "prompt_text": "Test prompt",
            "inputs": {"video": "/path/to/video.mp4"},
            "parameters": {"num_steps": 10},
        }

        # Execute run
        result = orchestrator.execute_run(run_dict, prompt_dict)

        # Verify update_run was NOT called
        mock_workflow_service.update_run.assert_not_called()

        # Verify result still succeeds
        assert result["status"] == "success"

    def test_execute_run_error_message_truncation(
        self,
        workflow_orchestrator,
        mock_ssh_manager,
        mock_file_transfer,
        mock_docker_executor,
        mock_workflow_service,
    ):
        """Test that execute_run handles very long error messages."""
        # Set up the orchestrator with mocks
        orchestrator = workflow_orchestrator
        orchestrator.ssh_manager = mock_ssh_manager
        orchestrator.file_transfer = mock_file_transfer
        orchestrator.docker_executor = mock_docker_executor
        orchestrator.service = mock_workflow_service

        # Create a very long error message
        long_error = "Error: " + "x" * 2000
        mock_docker_executor.run_inference.side_effect = Exception(long_error)

        # Prepare test data
        run_dict = {
            "id": "rs_long_err",
            "prompt_id": "ps_test456",
            "model_type": "transfer",
            "status": "running",
            "execution_config": {"gpu": "A100"},
            "outputs": {},
            "metadata": {},
        }

        prompt_dict = {
            "id": "ps_test456",
            "model_type": "transfer",
            "prompt_text": "Test prompt",
            "inputs": {"video": "/path/to/video.mp4"},
            "parameters": {"num_steps": 10},
        }

        # Execute run
        result = orchestrator.execute_run(run_dict, prompt_dict)

        # Verify update_run was called with the full error
        # (truncation happens in the service layer)
        mock_workflow_service.update_run.assert_called_once_with(
            "rs_long_err", error_message=long_error
        )

        # Verify result
        assert result["status"] == "failed"

    def test_execute_run_preserves_log_on_late_failure(
        self,
        workflow_orchestrator,
        mock_ssh_manager,
        mock_file_transfer,
        mock_docker_executor,
        mock_workflow_service,
    ):
        """Test that log path is preserved if failure happens after logging starts."""
        # Set up the orchestrator with mocks
        orchestrator = workflow_orchestrator
        orchestrator.ssh_manager = mock_ssh_manager
        orchestrator.file_transfer = mock_file_transfer
        orchestrator.docker_executor = mock_docker_executor
        orchestrator.service = mock_workflow_service

        # Make download_results fail after inference succeeds
        mock_file_transfer.download_results.side_effect = Exception("Download failed")

        # Prepare test data
        run_dict = {
            "id": "rs_late_fail",
            "prompt_id": "ps_test456",
            "model_type": "transfer",
            "status": "running",
            "execution_config": {"gpu": "A100"},
            "outputs": {},
            "metadata": {},
        }

        prompt_dict = {
            "id": "ps_test456",
            "model_type": "transfer",
            "prompt_text": "Test prompt",
            "inputs": {"video": "/path/to/video.mp4"},
            "parameters": {"num_steps": 10},
        }

        # Execute run
        result = orchestrator.execute_run(run_dict, prompt_dict)

        # Verify update_run was called twice (once for log, once for error)
        assert mock_workflow_service.update_run.call_count == 2
        calls = mock_workflow_service.update_run.call_args_list
        assert calls[0] == (
            ("rs_late_fail",),
            {"log_path": "outputs/run_rs_late_fail/logs/run.log"},
        )
        assert calls[1] == (("rs_late_fail",), {"error_message": "Download failed"})

        # Verify result
        assert result["status"] == "failed"
        assert result["error"] == "Download failed"

    @patch("cosmos_workflow.workflows.workflow_orchestrator.Path")
    @patch("cosmos_workflow.workflows.workflow_orchestrator.tempfile.TemporaryDirectory")
    def test_execute_run_with_service_none_doesnt_crash(
        self,
        mock_temp_dir,
        mock_path,
        workflow_orchestrator,
        mock_ssh_manager,
        mock_file_transfer,
        mock_docker_executor,
    ):
        """Test that execute_run works even if service is None (backward compatibility)."""
        # Set up temp directory mock
        mock_temp_context = MagicMock()
        mock_temp_context.__enter__.return_value = "/tmp/test"
        mock_temp_context.__exit__.return_value = None
        mock_temp_dir.return_value = mock_temp_context

        # Set up path mock
        mock_path_instance = MagicMock()
        mock_path.return_value = mock_path_instance

        # Set up the orchestrator with mocks but NO service
        orchestrator = workflow_orchestrator
        orchestrator.ssh_manager = mock_ssh_manager
        orchestrator.file_transfer = mock_file_transfer
        orchestrator.docker_executor = mock_docker_executor
        orchestrator.service = None  # No service attached

        # Prepare test data
        run_dict = {
            "id": "rs_no_service",
            "prompt_id": "ps_test456",
            "model_type": "transfer",
            "status": "running",
            "execution_config": {"gpu": "A100"},
            "outputs": {},
            "metadata": {},
        }

        prompt_dict = {
            "id": "ps_test456",
            "model_type": "transfer",
            "prompt_text": "Test prompt",
            "inputs": {},  # No video files to avoid Path issues
            "parameters": {"num_steps": 10},
        }

        # Execute run - should not crash
        result = orchestrator.execute_run(run_dict, prompt_dict)

        # Verify result
        assert result["status"] == "success"
