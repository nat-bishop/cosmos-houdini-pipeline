"""Tests for GPU executor container monitoring functionality."""

from unittest.mock import MagicMock, patch

from cosmos_workflow.execution.gpu_executor import GPUExecutor


class TestThreadSafeDownload:
    """Test thread-safe download functionality."""

    @patch("paramiko.SSHClient")
    def test_thread_safe_download_success(self, mock_ssh_client):
        """Test successful file download in thread-safe manner."""
        # Arrange
        gpu_executor = GPUExecutor()
        gpu_executor._initialize_services()
        gpu_executor.config_manager = MagicMock()
        gpu_executor.config_manager.get_ssh_options.return_value = {
            "hostname": "test.host",
            "username": "test_user",
            "password": "test_pass",
            "port": 22,
        }

        # Mock SSH and SFTP
        mock_ssh_instance = MagicMock()
        mock_sftp = MagicMock()
        mock_ssh_client.return_value = mock_ssh_instance
        mock_ssh_instance.open_sftp.return_value = mock_sftp

        # Act
        result = gpu_executor._thread_safe_download("/remote/path/file.mp4", "/local/path/file.mp4")

        # Assert
        assert result is True
        mock_ssh_instance.connect.assert_called_once()
        mock_sftp.get.assert_called_once_with("/remote/path/file.mp4", "/local/path/file.mp4")
        mock_sftp.close.assert_called_once()
        mock_ssh_instance.close.assert_called_once()

    @patch("paramiko.SSHClient")
    def test_thread_safe_download_failure(self, mock_ssh_client):
        """Test handling of download failures."""
        # Arrange
        gpu_executor = GPUExecutor()
        gpu_executor._initialize_services()
        gpu_executor.config_manager = MagicMock()
        gpu_executor.config_manager.get_ssh_options.return_value = {
            "hostname": "test.host",
            "username": "test_user",
            "password": "test_pass",
            "port": 22,
        }

        # Mock SSH connection failure
        mock_ssh_instance = MagicMock()
        mock_ssh_client.return_value = mock_ssh_instance
        mock_ssh_instance.connect.side_effect = Exception("Connection failed")

        # Act
        result = gpu_executor._thread_safe_download("/remote/path/file.mp4", "/local/path/file.mp4")

        # Assert
        assert result is False
        mock_ssh_instance.close.assert_called_once()


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
    @patch("paramiko.SSHClient")
    def test_monitor_detects_successful_completion(self, mock_ssh_client, mock_sleep):
        """Test monitor detects when container completes successfully."""
        # Arrange
        gpu_executor = GPUExecutor()
        gpu_executor._initialize_services()
        gpu_executor.config_manager = MagicMock()
        gpu_executor.config_manager.get_timeouts.return_value = {"docker_execution": 3600}
        gpu_executor.config_manager.get_ssh_options.return_value = {
            "hostname": "test.host",
            "username": "test_user",
            "password": "test_pass",
            "port": 22,
        }

        # Mock SSH and container status progression: running -> completed
        mock_ssh_instance = MagicMock()
        mock_ssh_client.return_value = mock_ssh_instance
        mock_ssh_instance.exec_command.side_effect = [
            (None, MagicMock(read=lambda: b'{"Running": true, "ExitCode": null}'), None),
            (None, MagicMock(read=lambda: b'{"Running": true, "ExitCode": null}'), None),
            (None, MagicMock(read=lambda: b'{"Running": false, "ExitCode": 0}'), None),
        ]

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
    @patch("paramiko.SSHClient")
    def test_monitor_detects_container_failure(self, mock_ssh_client, mock_sleep):
        """Test monitor detects when container fails."""
        # Arrange
        gpu_executor = GPUExecutor()
        gpu_executor._initialize_services()
        gpu_executor.config_manager = MagicMock()
        gpu_executor.config_manager.get_ssh_options.return_value = {
            "hostname": "test.host",
            "username": "test_user",
            "password": "test_pass",
            "port": 22,
        }

        # Mock SSH and container status: running -> failed
        mock_ssh_instance = MagicMock()
        mock_ssh_client.return_value = mock_ssh_instance
        mock_ssh_instance.exec_command.side_effect = [
            (None, MagicMock(read=lambda: b'{"Running": true, "ExitCode": null}'), None),
            (None, MagicMock(read=lambda: b'{"Running": false, "ExitCode": 1}'), None),
        ]

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
    @patch("paramiko.SSHClient")
    def test_monitor_handles_timeout(self, mock_ssh_client, mock_sleep):
        """Test monitor handles timeout and kills container."""
        # Arrange
        gpu_executor = GPUExecutor()
        gpu_executor._initialize_services()
        gpu_executor.kill_container = MagicMock(return_value=True)
        gpu_executor.config_manager = MagicMock()
        gpu_executor.config_manager.get_ssh_options.return_value = {
            "hostname": "test.host",
            "username": "test_user",
            "password": "test_pass",
            "port": 22,
        }

        # Mock SSH and container always running
        mock_ssh_instance = MagicMock()
        mock_ssh_client.return_value = mock_ssh_instance
        mock_ssh_instance.exec_command.return_value = (
            None,
            MagicMock(read=lambda: b'{"Running": true, "ExitCode": null}'),
            None,
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
    @patch("paramiko.SSHClient")
    def test_monitor_handles_exception(self, mock_ssh_client, mock_sleep):
        """Test monitor handles exceptions gracefully."""
        # Arrange
        gpu_executor = GPUExecutor()
        gpu_executor._initialize_services()
        gpu_executor.config_manager = MagicMock()
        gpu_executor.config_manager.get_ssh_options.return_value = {
            "hostname": "test.host",
            "username": "test_user",
            "password": "test_pass",
            "port": 22,
        }

        # Mock SSH connection failure
        mock_ssh_instance = MagicMock()
        mock_ssh_client.return_value = mock_ssh_instance
        mock_ssh_instance.exec_command.side_effect = Exception("SSH connection lost")

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

    @patch("cosmos_workflow.execution.gpu_executor.GPUExecutor._thread_safe_download")
    def test_handle_inference_completion_success(self, mock_download):
        """Test handling successful inference completion."""
        # Arrange
        gpu_executor = GPUExecutor()
        gpu_executor._initialize_services()
        gpu_executor.service = MagicMock()
        gpu_executor.config_manager = MagicMock()
        gpu_executor.config_manager.get_remote_config.return_value = MagicMock(remote_dir="/remote")
        mock_download.return_value = True

        # Mock that output file exists
        with patch("pathlib.Path.exists", return_value=True):
            # Act
            gpu_executor._handle_inference_completion("run_test123", 0, "cosmos_transfer_test1234")

        # Assert
        mock_download.assert_called()
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

    @patch("cosmos_workflow.execution.gpu_executor.GPUExecutor._thread_safe_download")
    def test_handle_enhancement_completion_success(self, mock_download):
        """Test handling successful enhancement completion."""
        # Arrange
        gpu_executor = GPUExecutor()
        gpu_executor._initialize_services()
        gpu_executor.service = MagicMock()
        gpu_executor.config_manager = MagicMock()
        gpu_executor.config_manager.get_remote_config.return_value = MagicMock(remote_dir="/remote")
        gpu_executor.json_handler = MagicMock()
        mock_download.return_value = True

        # Mock enhanced text results
        gpu_executor.json_handler.read_json.return_value = [
            {"upsampled_prompt": "Enhanced prompt text here"}
        ]

        # Act
        gpu_executor._handle_enhancement_completion("run_enhance123", 0, "cosmos_enhance_test")

        # Assert
        mock_download.assert_called_once()
        gpu_executor.service.update_run.assert_called_once()
        assert "Enhanced prompt text here" in str(gpu_executor.service.update_run.call_args)
        gpu_executor.service.update_run_status.assert_called_once_with(
            "run_enhance123", "completed"
        )

    @patch("cosmos_workflow.execution.gpu_executor.GPUExecutor._thread_safe_download")
    def test_handle_upscaling_completion_success(self, mock_download):
        """Test handling successful upscaling completion."""
        # Arrange
        gpu_executor = GPUExecutor()
        gpu_executor._initialize_services()
        gpu_executor.service = MagicMock()
        gpu_executor.config_manager = MagicMock()
        gpu_executor.config_manager.get_remote_config.return_value = MagicMock(remote_dir="/remote")
        mock_download.return_value = True

        # Mock that output file exists
        with patch("pathlib.Path.exists", return_value=True):
            # Act
            gpu_executor._handle_upscaling_completion("run_upscale123", 0, "cosmos_upscale_test")

        # Assert
        mock_download.assert_called()
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
            container_name="cosmos_transfer_run_test",
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
