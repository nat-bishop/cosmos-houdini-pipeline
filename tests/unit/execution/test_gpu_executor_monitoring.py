"""Tests for GPU executor container monitoring functionality."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from cosmos_workflow.execution.gpu_executor import GPUExecutor


class TestContainerStatusChecking:
    """Test container status checking functionality."""

    def test_get_container_status_running(self):
        """Test getting status of a running container."""
        # Arrange
        gpu_executor = GPUExecutor()
        gpu_executor._initialize_services()
        gpu_executor.remote_executor = MagicMock()
        gpu_executor.json_handler = MagicMock()

        # Mock docker inspect output for running container
        docker_state = {"Running": True, "ExitCode": 0, "Status": "running", "Error": ""}
        gpu_executor.remote_executor.execute_command.return_value = '{"Running": true}'
        gpu_executor.json_handler.parse_json.return_value = docker_state

        # Act
        status = gpu_executor._get_container_status("cosmos_transfer_abc12345")

        # Assert
        assert status["running"] is True
        assert status["exit_code"] == 0
        assert status["status"] == "running"
        assert status["error"] == ""
        gpu_executor.remote_executor.execute_command.assert_called_once_with(
            "sudo docker inspect cosmos_transfer_abc12345 --format '{{json .State}}'"
        )

    def test_get_container_status_stopped_success(self):
        """Test getting status of a successfully completed container."""
        # Arrange
        gpu_executor = GPUExecutor()
        gpu_executor._initialize_services()
        gpu_executor.remote_executor = MagicMock()
        gpu_executor.json_handler = MagicMock()

        # Mock docker inspect output for stopped container
        docker_state = {"Running": False, "ExitCode": 0, "Status": "exited", "Error": ""}
        gpu_executor.remote_executor.execute_command.return_value = '{"Running": false}'
        gpu_executor.json_handler.parse_json.return_value = docker_state

        # Act
        status = gpu_executor._get_container_status("cosmos_transfer_abc12345")

        # Assert
        assert status["running"] is False
        assert status["exit_code"] == 0
        assert status["status"] == "exited"

    def test_get_container_status_stopped_failed(self):
        """Test getting status of a failed container."""
        # Arrange
        gpu_executor = GPUExecutor()
        gpu_executor._initialize_services()
        gpu_executor.remote_executor = MagicMock()
        gpu_executor.json_handler = MagicMock()

        # Mock docker inspect output for failed container
        docker_state = {
            "Running": False,
            "ExitCode": 1,
            "Status": "exited",
            "Error": "Container failed",
        }
        gpu_executor.remote_executor.execute_command.return_value = '{"Running": false}'
        gpu_executor.json_handler.parse_json.return_value = docker_state

        # Act
        status = gpu_executor._get_container_status("cosmos_enhance_def45678")

        # Assert
        assert status["running"] is False
        assert status["exit_code"] == 1
        assert status["error"] == "Container failed"

    def test_get_container_status_not_found(self):
        """Test getting status when container doesn't exist."""
        # Arrange
        gpu_executor = GPUExecutor()
        gpu_executor._initialize_services()
        gpu_executor.remote_executor = MagicMock()
        gpu_executor.remote_executor.execute_command.side_effect = Exception("Container not found")

        # Act
        status = gpu_executor._get_container_status("non_existent_container")

        # Assert
        assert status["running"] is False
        assert status["exit_code"] is None
        assert status["status"] == "not_found"


class TestContainerMonitoring:
    """Test background container monitoring functionality."""

    @patch("cosmos_workflow.execution.gpu_executor.threading.Thread")
    def test_monitor_container_completion_starts_thread(self, mock_thread):
        """Test that monitoring starts a background thread."""
        # Arrange
        gpu_executor = GPUExecutor()
        gpu_executor._initialize_services()
        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance

        completion_handler = MagicMock()

        # Act
        gpu_executor._monitor_container_completion(
            run_id="run_test123",
            container_name="cosmos_transfer_test1234",
            completion_handler=completion_handler,
            timeout_seconds=30,
        )

        # Assert
        mock_thread.assert_called_once()
        assert mock_thread.call_args[1]["daemon"] is True
        mock_thread_instance.start.assert_called_once()

    @patch("time.sleep")
    def test_monitor_detects_successful_completion(self, mock_sleep):
        """Test monitor detects when container completes successfully."""
        # Arrange
        gpu_executor = GPUExecutor()
        gpu_executor._initialize_services()
        gpu_executor.config_manager = MagicMock()
        gpu_executor.config_manager.get_timeouts.return_value = {"docker_execution": 3600}

        # Mock container status progression: running -> completed
        gpu_executor._get_container_status = MagicMock(
            side_effect=[
                {"running": True, "exit_code": None, "status": "running"},
                {"running": True, "exit_code": None, "status": "running"},
                {"running": False, "exit_code": 0, "status": "exited"},
            ]
        )

        completion_handler = MagicMock()

        # Act - call the internal monitor function directly to test synchronously
        gpu_executor._monitor_container_internal(
            run_id="run_test123",
            container_name="cosmos_transfer_test1234",
            completion_handler=completion_handler,
            timeout_seconds=30,
        )

        # Assert
        completion_handler.assert_called_once_with("run_test123", 0, "cosmos_transfer_test1234")
        assert mock_sleep.call_count == 2  # Two sleep calls before completion

    @patch("time.sleep")
    def test_monitor_detects_container_failure(self, mock_sleep):
        """Test monitor detects when container fails."""
        # Arrange
        gpu_executor = GPUExecutor()
        gpu_executor._initialize_services()

        # Mock container status: running -> failed
        gpu_executor._get_container_status = MagicMock(
            side_effect=[
                {"running": True, "exit_code": None, "status": "running"},
                {"running": False, "exit_code": 1, "status": "exited", "error": "Out of memory"},
            ]
        )

        completion_handler = MagicMock()

        # Act
        gpu_executor._monitor_container_internal(
            run_id="run_test456",
            container_name="cosmos_enhance_test4567",
            completion_handler=completion_handler,
            timeout_seconds=30,
        )

        # Assert
        completion_handler.assert_called_once_with("run_test456", 1, "cosmos_enhance_test4567")
        assert mock_sleep.call_count == 1

    @patch("time.sleep")
    def test_monitor_handles_timeout(self, mock_sleep):
        """Test monitor handles timeout and kills container."""
        # Arrange
        gpu_executor = GPUExecutor()
        gpu_executor._initialize_services()
        gpu_executor.kill_container = MagicMock(return_value=True)

        # Mock container always running
        gpu_executor._get_container_status = MagicMock(
            return_value={"running": True, "exit_code": None, "status": "running"}
        )

        completion_handler = MagicMock()

        # Act - use very short timeout
        gpu_executor._monitor_container_internal(
            run_id="run_timeout",
            container_name="cosmos_transfer_timeout",
            completion_handler=completion_handler,
            timeout_seconds=11,  # Just over 2 intervals
        )

        # Assert
        gpu_executor.kill_container.assert_called_once_with("cosmos_transfer_timeout")
        completion_handler.assert_called_once_with("run_timeout", -1, "cosmos_transfer_timeout")

    @patch("time.sleep")
    def test_monitor_handles_exception(self, mock_sleep):
        """Test monitor handles exceptions gracefully."""
        # Arrange
        gpu_executor = GPUExecutor()
        gpu_executor._initialize_services()

        # Mock exception during status check
        gpu_executor._get_container_status = MagicMock(side_effect=Exception("SSH connection lost"))

        completion_handler = MagicMock()

        # Act
        gpu_executor._monitor_container_internal(
            run_id="run_error",
            container_name="cosmos_transfer_error",
            completion_handler=completion_handler,
            timeout_seconds=30,
        )

        # Assert
        completion_handler.assert_called_once_with("run_error", -1, "cosmos_transfer_error")


class TestCompletionHandlers:
    """Test operation-specific completion handlers."""

    def test_handle_inference_completion_success(self):
        """Test handling successful inference completion."""
        # Arrange
        gpu_executor = GPUExecutor()
        gpu_executor._initialize_services()
        gpu_executor.service = MagicMock()
        gpu_executor._download_outputs = MagicMock(return_value=Path("outputs/run_test/output.mp4"))

        # Mock that output file exists
        with patch("pathlib.Path.exists", return_value=True):
            # Act
            gpu_executor._handle_inference_completion("run_test123", 0, "cosmos_transfer_test1234")

        # Assert
        gpu_executor._download_outputs.assert_called_once()
        gpu_executor.service.update_run.assert_called_once()
        gpu_executor.service.update_run_status.assert_called_once_with("run_test123", "completed")

    def test_handle_inference_completion_failed_container(self):
        """Test handling failed inference container."""
        # Arrange
        gpu_executor = GPUExecutor()
        gpu_executor._initialize_services()
        gpu_executor.service = MagicMock()

        # Act
        gpu_executor._handle_inference_completion("run_test123", 1, "cosmos_transfer_test1234")

        # Assert
        gpu_executor.service.update_run_status.assert_called_once_with("run_test123", "failed")
        gpu_executor.service.update_run.assert_called_once()
        assert "exit code 1" in str(gpu_executor.service.update_run.call_args)

    def test_handle_inference_completion_timeout(self):
        """Test handling inference timeout."""
        # Arrange
        gpu_executor = GPUExecutor()
        gpu_executor._initialize_services()
        gpu_executor.service = MagicMock()

        # Act - exit code -1 indicates timeout
        gpu_executor._handle_inference_completion("run_timeout", -1, "cosmos_transfer_timeout")

        # Assert
        gpu_executor.service.update_run_status.assert_called_once_with("run_timeout", "failed")
        gpu_executor.service.update_run.assert_called_once()
        assert "timeout" in str(gpu_executor.service.update_run.call_args).lower()

    def test_handle_enhancement_completion_success(self):
        """Test handling successful enhancement completion."""
        # Arrange
        gpu_executor = GPUExecutor()
        gpu_executor._initialize_services()
        gpu_executor.service = MagicMock()
        gpu_executor.config_manager = MagicMock()
        gpu_executor.config_manager.get_remote_config.return_value = MagicMock(remote_dir="/remote")
        gpu_executor.file_transfer = MagicMock()
        gpu_executor.json_handler = MagicMock()

        # Mock enhanced text results
        gpu_executor.json_handler.read_json.return_value = [
            {"upsampled_prompt": "Enhanced prompt text here"}
        ]

        # Act
        gpu_executor._handle_enhancement_completion("run_enhance123", 0, "cosmos_enhance_test")

        # Assert
        gpu_executor.file_transfer.download_file.assert_called_once()
        gpu_executor.service.update_run.assert_called_once()
        assert "Enhanced prompt text here" in str(gpu_executor.service.update_run.call_args)
        gpu_executor.service.update_run_status.assert_called_once_with(
            "run_enhance123", "completed"
        )

    def test_handle_upscaling_completion_success(self):
        """Test handling successful upscaling completion."""
        # Arrange
        gpu_executor = GPUExecutor()
        gpu_executor._initialize_services()
        gpu_executor.service = MagicMock()
        gpu_executor._download_outputs = MagicMock(
            return_value=Path("outputs/run_upscale/output_4k.mp4")
        )

        # Mock that output file exists
        with patch("pathlib.Path.exists", return_value=True):
            # Act
            gpu_executor._handle_upscaling_completion("run_upscale123", 0, "cosmos_upscale_test")

        # Assert
        gpu_executor._download_outputs.assert_called_once_with(
            "run_upscale123", Path("outputs/run_run_upscale123"), upscaled=True
        )
        gpu_executor.service.update_run.assert_called_once()
        gpu_executor.service.update_run_status.assert_called_once_with(
            "run_upscale123", "completed"
        )


class TestExecuteMethodsWithMonitoring:
    """Test that execute methods properly use monitoring."""

    @patch("cosmos_workflow.execution.gpu_executor.GPUExecutor._monitor_container_completion")
    def test_execute_run_with_started_status(self, mock_monitor):
        """Test execute_run launches monitor when status is 'started'."""
        # Arrange
        gpu_executor = GPUExecutor()
        gpu_executor._initialize_services()
        gpu_executor.docker_executor = MagicMock()
        gpu_executor.docker_executor.run_inference.return_value = {"status": "started"}
        gpu_executor.file_transfer = MagicMock()
        gpu_executor.remote_executor = MagicMock()

        run = {"id": "run_test123", "execution_config": {}}
        prompt = {"id": "ps_test", "prompt_text": "Test prompt", "inputs": {}, "parameters": {}}

        # Act
        result = gpu_executor.execute_run(run, prompt)

        # Assert
        assert result["status"] == "started"
        assert result["message"] == "Inference started in background"
        mock_monitor.assert_called_once_with(
            run_id="run_test123",
            container_name="cosmos_transfer_run_test1",
            completion_handler=gpu_executor._handle_inference_completion,
        )

    @patch("cosmos_workflow.execution.gpu_executor.GPUExecutor._monitor_container_completion")
    def test_execute_enhancement_run_with_started_status(self, mock_monitor):
        """Test execute_enhancement_run uses monitor instead of polling."""
        # Arrange
        gpu_executor = GPUExecutor()
        gpu_executor._initialize_services()
        gpu_executor.docker_executor = MagicMock()
        gpu_executor.docker_executor.run_prompt_enhancement.return_value = {"status": "started"}
        gpu_executor.file_transfer = MagicMock()
        gpu_executor.remote_executor = MagicMock()

        run = {"id": "run_enhance123", "execution_config": {"model": "pixtral"}}
        prompt = {"id": "ps_test", "prompt_text": "Test prompt", "inputs": {}}

        # Act
        result = gpu_executor.execute_enhancement_run(run, prompt)

        # Assert
        assert result["status"] == "started"
        assert result["message"] == "Enhancement started in background"
        mock_monitor.assert_called_once_with(
            run_id="run_enhance123",
            container_name="cosmos_enhance_run_enha",
            completion_handler=gpu_executor._handle_enhancement_completion,
        )

    @patch("cosmos_workflow.execution.gpu_executor.GPUExecutor._monitor_container_completion")
    def test_execute_upscaling_run_with_started_status(self, mock_monitor):
        """Test execute_upscaling_run launches monitor when status is 'started'."""
        # Arrange
        gpu_executor = GPUExecutor()
        gpu_executor._initialize_services()
        gpu_executor.docker_executor = MagicMock()
        gpu_executor.docker_executor.run_upscaling.return_value = {"status": "started"}
        gpu_executor.file_transfer = MagicMock()
        gpu_executor.remote_executor = MagicMock()

        upscale_run = {"id": "run_upscale123", "execution_config": {"control_weight": 0.5}}
        parent_run = {"id": "run_parent123", "outputs": {"output_path": "output.mp4"}}
        prompt = {"id": "ps_test", "prompt_text": "Test", "parameters": {"name": "test"}}

        # Act
        result = gpu_executor.execute_upscaling_run(upscale_run, parent_run, prompt)

        # Assert
        assert result["status"] == "started"
        assert result["message"] == "Upscaling started in background"
        mock_monitor.assert_called_once_with(
            run_id="run_upscale123",
            container_name="cosmos_upscale_run_upsc",
            completion_handler=gpu_executor._handle_upscaling_completion,
        )
