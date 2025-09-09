"""Tests for StatusChecker class - container status checking and downloading."""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

from cosmos_workflow.execution.status_checker import StatusChecker


class TestStatusChecker:
    """Test StatusChecker behavioral functionality."""

    def test_init_with_dependencies(self):
        """Test StatusChecker initialization with required dependencies."""
        # Arrange
        mock_ssh_manager = MagicMock()
        mock_config_manager = MagicMock()
        mock_file_transfer = MagicMock()

        # Act
        checker = StatusChecker(
            ssh_manager=mock_ssh_manager,
            config_manager=mock_config_manager,
            file_transfer_service=mock_file_transfer,
        )

        # Assert
        assert checker.ssh_manager == mock_ssh_manager
        assert checker.config_manager == mock_config_manager
        assert checker.file_transfer == mock_file_transfer

    def test_parse_completion_marker_with_exit_code(self):
        """Test parsing [COSMOS_COMPLETE] marker with exit code."""
        # Arrange
        checker = StatusChecker(MagicMock(), MagicMock(), MagicMock())
        log_content = """
        Processing frame 1...
        Processing frame 2...
        [COSMOS_COMPLETE] exit_code=0
        """

        # Act
        exit_code = checker.parse_completion_marker(log_content)

        # Assert
        assert exit_code == 0

    def test_parse_completion_marker_with_failure(self):
        """Test parsing completion marker with non-zero exit code."""
        # Arrange
        checker = StatusChecker(MagicMock(), MagicMock(), MagicMock())
        log_content = """
        Error: Something went wrong
        [COSMOS_COMPLETE] exit_code=1
        """

        # Act
        exit_code = checker.parse_completion_marker(log_content)

        # Assert
        assert exit_code == 1

    def test_parse_completion_marker_not_found(self):
        """Test parsing when completion marker is not present."""
        # Arrange
        checker = StatusChecker(MagicMock(), MagicMock(), MagicMock())
        log_content = "Still running... no completion marker"

        # Act
        exit_code = checker.parse_completion_marker(log_content)

        # Assert
        assert exit_code is None

    def test_check_container_status_running(self):
        """Test checking status of a running container."""
        # Arrange
        mock_ssh = MagicMock()
        mock_remote_executor = MagicMock()
        checker = StatusChecker(mock_ssh, MagicMock(), MagicMock())
        checker.remote_executor = mock_remote_executor

        # Mock docker inspect showing container is running
        mock_remote_executor.execute.return_value = (0, '{"Running": true, "ExitCode": null}', "")

        # Act
        status = checker.check_container_status("cosmos_transfer_test123")

        # Assert
        assert status == {"running": True, "exit_code": None}
        mock_remote_executor.execute.assert_called_once_with(
            "sudo docker inspect cosmos_transfer_test123 --format '{{json .State}}'"
        )

    def test_check_container_status_completed(self):
        """Test checking status of a completed container."""
        # Arrange
        mock_ssh = MagicMock()
        mock_remote_executor = MagicMock()
        checker = StatusChecker(mock_ssh, MagicMock(), MagicMock())
        checker.remote_executor = mock_remote_executor

        # Mock docker inspect showing container stopped with exit code 0
        mock_remote_executor.execute.return_value = (0, '{"Running": false, "ExitCode": 0}', "")

        # Act
        status = checker.check_container_status("cosmos_transfer_test123")

        # Assert
        assert status == {"running": False, "exit_code": 0}

    def test_check_container_status_failed(self):
        """Test checking status of a failed container."""
        # Arrange
        mock_ssh = MagicMock()
        mock_remote_executor = MagicMock()
        checker = StatusChecker(mock_ssh, MagicMock(), MagicMock())
        checker.remote_executor = mock_remote_executor

        # Mock docker inspect showing container failed
        mock_remote_executor.execute.return_value = (0, '{"Running": false, "ExitCode": 1}', "")

        # Act
        status = checker.check_container_status("cosmos_transfer_failed")

        # Assert
        assert status == {"running": False, "exit_code": 1}

    def test_check_container_status_not_found(self):
        """Test checking status when container doesn't exist."""
        # Arrange
        mock_ssh = MagicMock()
        mock_remote_executor = MagicMock()
        checker = StatusChecker(mock_ssh, MagicMock(), MagicMock())
        checker.remote_executor = mock_remote_executor

        # Mock docker inspect error
        mock_remote_executor.execute.return_value = (
            1,
            "",
            "Error: No such object: cosmos_transfer_missing",
        )

        # Act
        status = checker.check_container_status("cosmos_transfer_missing")

        # Assert
        assert status == {"running": False, "exit_code": -1}

    def test_check_run_completion_from_logs(self):
        """Test checking run completion by reading container logs."""
        # Arrange
        mock_ssh = MagicMock()
        mock_config = MagicMock()
        mock_config.get_remote_config.return_value = MagicMock(remote_dir="/workspace")
        mock_remote_executor = MagicMock()

        checker = StatusChecker(mock_ssh, mock_config, MagicMock())
        checker.remote_executor = mock_remote_executor

        # Mock reading log file with completion marker
        mock_remote_executor.execute.return_value = (
            0,
            "Processing...\n[COSMOS_COMPLETE] exit_code=0\n",
            "",
        )

        # Act
        exit_code = checker.check_run_completion("run_test123")

        # Assert
        assert exit_code == 0
        mock_remote_executor.execute.assert_called_with(
            "cat /workspace/outputs/run_run_test123/run.log 2>/dev/null || echo ''"
        )

    def test_download_outputs_for_inference(self):
        """Test downloading output files for completed inference run."""
        # Arrange
        mock_ssh = MagicMock()
        mock_config = MagicMock()
        mock_config.get_remote_config.return_value = MagicMock(remote_dir="/workspace")
        mock_file_transfer = MagicMock()
        mock_file_transfer.download_file.return_value = True

        checker = StatusChecker(mock_ssh, mock_config, mock_file_transfer)

        run_data = {"id": "run_test123", "model_type": "inference"}

        # Act
        outputs = checker.download_outputs(run_data)

        # Assert
        assert outputs is not None
        assert "output_path" in outputs
        assert "run_test123" in outputs["output_path"]
        assert "output.mp4" in outputs["output_path"]
        assert "completed_at" in outputs
        mock_file_transfer.download_file.assert_called_once_with(
            "/workspace/outputs/run_run_test123/output.mp4",
            Path("outputs/run_run_test123/outputs/output.mp4"),
        )

    def test_download_outputs_for_enhancement(self):
        """Test downloading output files for completed enhancement run."""
        # Arrange
        mock_ssh = MagicMock()
        mock_config = MagicMock()
        mock_config.get_remote_config.return_value = MagicMock(remote_dir="/workspace")
        mock_file_transfer = MagicMock()
        mock_file_transfer.download_file.return_value = True
        mock_json_handler = MagicMock()
        mock_json_handler.read_json.return_value = [{"upsampled_prompt": "Enhanced text"}]

        checker = StatusChecker(mock_ssh, mock_config, mock_file_transfer)
        checker.json_handler = mock_json_handler

        run_data = {"id": "run_enhance123", "model_type": "enhancement"}

        # Act
        outputs = checker.download_outputs(run_data)

        # Assert
        assert outputs is not None
        assert "enhanced_text" in outputs
        assert outputs["enhanced_text"] == "Enhanced text"
        assert "completed_at" in outputs
        mock_file_transfer.download_file.assert_called_once()

    def test_download_outputs_for_upscaling(self):
        """Test downloading output files for completed upscaling run."""
        # Arrange
        mock_ssh = MagicMock()
        mock_config = MagicMock()
        mock_config.get_remote_config.return_value = MagicMock(remote_dir="/workspace")
        mock_file_transfer = MagicMock()
        mock_file_transfer.download_file.return_value = True

        checker = StatusChecker(mock_ssh, mock_config, mock_file_transfer)

        run_data = {"id": "run_upscale123", "model_type": "upscaling"}

        # Act
        outputs = checker.download_outputs(run_data)

        # Assert
        assert outputs is not None
        assert "output_path" in outputs
        assert "run_upscale123" in outputs["output_path"]
        assert "output_4k.mp4" in outputs["output_path"]
        assert "completed_at" in outputs

    def test_download_outputs_handles_failure(self):
        """Test handling download failures gracefully."""
        # Arrange
        mock_ssh = MagicMock()
        mock_config = MagicMock()
        mock_config.get_remote_config.return_value = MagicMock(remote_dir="/workspace")
        mock_file_transfer = MagicMock()
        mock_file_transfer.download_file.side_effect = Exception("Connection failed")

        checker = StatusChecker(mock_ssh, mock_config, mock_file_transfer)

        run_data = {"id": "run_test123", "model_type": "inference"}

        # Act
        outputs = checker.download_outputs(run_data)

        # Assert
        assert outputs is None

    def test_sync_run_status_when_still_running(self):
        """Test syncing status when container is still running."""
        # Arrange
        mock_ssh = MagicMock()
        mock_remote_executor = MagicMock()
        mock_service = MagicMock()

        checker = StatusChecker(mock_ssh, MagicMock(), MagicMock())
        checker.remote_executor = mock_remote_executor

        # Container still running
        mock_remote_executor.execute.return_value = (0, '{"Running": true, "ExitCode": null}', "")

        run_data = {"id": "run_test123", "status": "running", "model_type": "inference"}

        # Act
        updated_run = checker.sync_run_status(run_data, mock_service)

        # Assert
        assert updated_run["status"] == "running"
        mock_service.update_run_status.assert_not_called()

    def test_sync_run_status_when_completed_successfully(self):
        """Test syncing status when container completed successfully."""
        # Arrange
        mock_ssh = MagicMock()
        mock_config = MagicMock()
        mock_config.get_remote_config.return_value = MagicMock(remote_dir="/workspace")
        mock_file_transfer = MagicMock()
        mock_file_transfer.download_file.return_value = True
        mock_remote_executor = MagicMock()
        mock_service = MagicMock()

        checker = StatusChecker(mock_ssh, mock_config, mock_file_transfer)
        checker.remote_executor = mock_remote_executor

        # Container completed successfully
        mock_remote_executor.execute.side_effect = [
            (0, '{"Running": false, "ExitCode": 0}', ""),  # docker inspect
            (0, "[COSMOS_COMPLETE] exit_code=0", ""),  # cat log file
        ]

        run_data = {"id": "run_test123", "status": "running", "model_type": "inference"}

        # Act
        updated_run = checker.sync_run_status(run_data, mock_service)

        # Assert
        assert updated_run["status"] == "completed"
        assert "outputs" in updated_run
        assert "output_path" in updated_run["outputs"]
        mock_service.update_run_status.assert_called_once_with("run_test123", "completed")
        mock_service.update_run.assert_called_once_with(
            "run_test123", outputs=updated_run["outputs"]
        )
        mock_file_transfer.download_file.assert_called_once()

    def test_sync_run_status_when_failed(self):
        """Test syncing status when container failed."""
        # Arrange
        mock_ssh = MagicMock()
        mock_config = MagicMock()
        mock_config.get_remote_config.return_value = MagicMock(remote_dir="/workspace")
        mock_remote_executor = MagicMock()
        mock_service = MagicMock()

        checker = StatusChecker(mock_ssh, mock_config, MagicMock())
        checker.remote_executor = mock_remote_executor

        # Container failed
        mock_remote_executor.execute.side_effect = [
            (0, '{"Running": false, "ExitCode": 1}', ""),  # docker inspect
            (0, "[COSMOS_COMPLETE] exit_code=1", ""),  # cat log file
        ]

        run_data = {"id": "run_test123", "status": "running", "model_type": "inference"}

        # Act
        updated_run = checker.sync_run_status(run_data, mock_service)

        # Assert
        assert updated_run["status"] == "failed"
        mock_service.update_run_status.assert_called_once_with("run_test123", "failed")
        mock_service.update_run.assert_called_once()

    def test_sync_run_status_caching(self):
        """Test that status checks are cached to avoid repeated SSH calls."""
        # Arrange
        mock_ssh = MagicMock()
        mock_remote_executor = MagicMock()
        mock_service = MagicMock()

        checker = StatusChecker(mock_ssh, MagicMock(), MagicMock())
        checker.remote_executor = mock_remote_executor

        # Container completed
        mock_remote_executor.execute.side_effect = [
            (0, '{"Running": false, "ExitCode": 0}', ""),  # First check
            (0, "[COSMOS_COMPLETE] exit_code=0", ""),  # Log check
        ]

        run_data = {"id": "run_test123", "status": "running", "model_type": "inference"}

        # Act - check twice
        updated_run1 = checker.sync_run_status(run_data, mock_service)
        updated_run2 = checker.sync_run_status(run_data, mock_service)

        # Assert - should only check once due to caching
        assert updated_run1 == updated_run2
        assert mock_remote_executor.execute.call_count == 2  # docker inspect + log read
        mock_service.update_run_status.assert_called_once()  # Only updated once


class TestDataRepositoryIntegration:
    """Test DataRepository lazy sync integration."""

    @patch("cosmos_workflow.services.data_repository.StatusChecker")
    def test_get_run_triggers_status_sync(self, mock_checker_class):
        """Test that get_run triggers status sync for running runs."""
        from cosmos_workflow.services.data_repository import DataRepository

        # Arrange
        mock_db = MagicMock()
        mock_checker = MagicMock()
        mock_checker_class.return_value = mock_checker

        repo = DataRepository(mock_db)
        repo.status_checker = mock_checker

        # Mock a running run
        mock_run = MagicMock()
        mock_run.id = "run_test123"
        mock_run.status = "running"
        mock_run.model_type = "inference"

        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_run

        # Mock status sync returning completed
        mock_checker.sync_run_status.return_value = {
            "id": "run_test123",
            "status": "completed",
            "outputs": {"output_path": "/path/to/output.mp4"},
        }

        # Act
        result = repo.get_run("run_test123")

        # Assert
        assert result["status"] == "completed"
        mock_checker.sync_run_status.assert_called_once()

    @patch("cosmos_workflow.services.data_repository.StatusChecker")
    def test_get_run_skips_sync_for_completed(self, mock_checker_class):
        """Test that get_run skips sync for already completed runs."""
        from cosmos_workflow.services.data_repository import DataRepository

        # Arrange
        mock_db = MagicMock()
        mock_checker = MagicMock()
        mock_checker_class.return_value = mock_checker

        repo = DataRepository(mock_db)
        repo.status_checker = mock_checker

        # Mock a completed run
        mock_run = MagicMock()
        mock_run.id = "run_test123"
        mock_run.status = "completed"

        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_run

        # Act
        result = repo.get_run("run_test123")

        # Assert
        assert result["status"] == "completed"
        mock_checker.sync_run_status.assert_not_called()

    @patch("cosmos_workflow.services.data_repository.StatusChecker")
    def test_list_runs_syncs_multiple_running(self, mock_checker_class):
        """Test that list_runs syncs status for all running runs."""
        from cosmos_workflow.services.data_repository import DataRepository

        # Arrange
        mock_db = MagicMock()
        mock_checker = MagicMock()
        mock_checker_class.return_value = mock_checker

        repo = DataRepository(mock_db)
        repo.status_checker = mock_checker

        # Mock multiple runs with different statuses
        mock_runs = [
            self._create_mock_run("run1", "completed"),
            self._create_mock_run("run2", "running"),
            self._create_mock_run("run3", "running"),
            self._create_mock_run("run4", "failed"),
        ]

        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__.return_value = mock_session
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value.order_by.return_value.limit.return_value.all.return_value = (
            mock_runs
        )

        # Mock status sync
        def sync_side_effect(run_data, service):
            if run_data["id"] == "run2":
                run_data["status"] = "completed"
            return run_data

        mock_checker.sync_run_status.side_effect = sync_side_effect

        # Act
        results = repo.list_runs()

        # Assert
        assert len(results) == 4
        assert results[0]["status"] == "completed"  # Already completed
        assert results[1]["status"] == "completed"  # Synced to completed
        assert results[2]["status"] == "running"  # Still running
        assert results[3]["status"] == "failed"  # Already failed
        assert mock_checker.sync_run_status.call_count == 2  # Only for running runs

    def _create_mock_run(self, run_id, status):
        """Helper to create mock run objects."""
        mock_run = MagicMock()
        mock_run.id = run_id
        mock_run.status = status
        mock_run.prompt_id = "ps_test"
        mock_run.model_type = "inference"
        mock_run.execution_config = {}
        mock_run.outputs = {}
        mock_run.run_metadata = {}
        mock_run.created_at = datetime.now(timezone.utc)
        mock_run.updated_at = datetime.now(timezone.utc)
        mock_run.log_path = None
        mock_run.completed_at = None
        mock_run.error_message = None
        return mock_run
