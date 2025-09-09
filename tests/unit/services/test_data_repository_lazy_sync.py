"""Tests for DataRepository lazy sync integration with StatusChecker."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock, patch

from cosmos_workflow.database.models import Run
from cosmos_workflow.services.data_repository import DataRepository


class TestDataRepositoryLazySync:
    """Test DataRepository lazy status synchronization functionality."""

    @patch("cosmos_workflow.services.data_repository.StatusChecker")
    def test_data_repository_initializes_status_checker(self, mock_checker_class):
        """Test that DataRepository initializes StatusChecker with correct dependencies."""
        # Arrange
        mock_db = MagicMock()
        mock_config = MagicMock()

        # Act
        repo = DataRepository(mock_db, mock_config)
        repo.initialize_status_checker()

        # Assert
        assert repo.status_checker is not None
        mock_checker_class.assert_called_once_with(config_manager=mock_config)

    def test_get_run_triggers_sync_for_running_status(self):
        """Test that get_run triggers status sync for running runs."""
        # Arrange
        mock_db = MagicMock()
        mock_status_checker = MagicMock()

        repo = DataRepository(mock_db)
        repo.status_checker = mock_status_checker

        # Mock a running run in database
        mock_run = MagicMock(spec=Run)
        mock_run.id = "run_test123"
        mock_run.status = "running"
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

        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_run

        # Mock status checker returning completed status
        mock_status_checker.sync_run_status.return_value = {
            "id": "run_test123",
            "status": "completed",
            "prompt_id": "ps_test",
            "model_type": "inference",
            "outputs": {"output_path": "outputs/run_test123/output.mp4"},
            "execution_config": {},
            "metadata": {},
            "created_at": mock_run.created_at.isoformat(),
            "updated_at": mock_run.updated_at.isoformat(),
        }

        # Act
        result = repo.get_run("run_test123")

        # Assert
        assert result["status"] == "completed"
        assert result["outputs"]["output_path"] == "outputs/run_test123/output.mp4"
        mock_status_checker.sync_run_status.assert_called_once()

    def test_get_run_skips_sync_for_completed_status(self):
        """Test that get_run skips sync for already completed runs."""
        # Arrange
        mock_db = MagicMock()
        mock_status_checker = MagicMock()

        repo = DataRepository(mock_db)
        repo.status_checker = mock_status_checker

        # Mock a completed run in database
        mock_run = MagicMock(spec=Run)
        mock_run.id = "run_test123"
        mock_run.status = "completed"
        mock_run.outputs = {"output_path": "outputs/run_test123/output.mp4"}
        mock_run.prompt_id = "ps_test"
        mock_run.model_type = "inference"
        mock_run.execution_config = {}
        mock_run.run_metadata = {}
        mock_run.created_at = datetime.now(timezone.utc)
        mock_run.updated_at = datetime.now(timezone.utc)
        mock_run.log_path = None
        mock_run.completed_at = datetime.now(timezone.utc)
        mock_run.error_message = None

        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_run

        # Act
        result = repo.get_run("run_test123")

        # Assert
        assert result["status"] == "completed"
        mock_status_checker.sync_run_status.assert_not_called()

    def test_get_run_skips_sync_for_failed_status(self):
        """Test that get_run skips sync for already failed runs."""
        # Arrange
        mock_db = MagicMock()
        mock_status_checker = MagicMock()

        repo = DataRepository(mock_db)
        repo.status_checker = mock_status_checker

        # Mock a failed run in database
        mock_run = MagicMock(spec=Run)
        mock_run.id = "run_test123"
        mock_run.status = "failed"
        mock_run.error_message = "Container failed"
        mock_run.prompt_id = "ps_test"
        mock_run.model_type = "inference"
        mock_run.execution_config = {}
        mock_run.outputs = {}
        mock_run.run_metadata = {}
        mock_run.created_at = datetime.now(timezone.utc)
        mock_run.updated_at = datetime.now(timezone.utc)
        mock_run.log_path = None
        mock_run.completed_at = None

        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_run

        # Act
        result = repo.get_run("run_test123")

        # Assert
        assert result["status"] == "failed"
        mock_status_checker.sync_run_status.assert_not_called()

    def test_get_run_works_without_status_checker(self):
        """Test that get_run works normally when status_checker is not initialized."""
        # Arrange
        mock_db = MagicMock()

        repo = DataRepository(mock_db)
        # No status_checker initialized

        # Mock a running run in database
        mock_run = MagicMock(spec=Run)
        mock_run.id = "run_test123"
        mock_run.status = "running"
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

        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_run

        # Act
        result = repo.get_run("run_test123")

        # Assert
        assert result["status"] == "running"  # No sync happened

    def test_list_runs_syncs_all_running_runs(self):
        """Test that list_runs syncs status for all running runs."""
        # Arrange
        mock_db = MagicMock()
        mock_status_checker = MagicMock()

        repo = DataRepository(mock_db)
        repo.status_checker = mock_status_checker

        # Create mock runs with different statuses
        now = datetime.now(timezone.utc)
        mock_runs = [
            self._create_mock_run("run1", "completed", now),
            self._create_mock_run("run2", "running", now),
            self._create_mock_run("run3", "running", now),
            self._create_mock_run("run4", "failed", now),
        ]

        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__.return_value = mock_session
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all.return_value = mock_runs

        # Mock status checker syncing run2 to completed
        def sync_side_effect(run_data, service):
            if run_data["id"] == "run2":
                run_data["status"] = "completed"
                run_data["outputs"] = {"output_path": "outputs/run2/output.mp4"}
            return run_data

        mock_status_checker.sync_run_status.side_effect = sync_side_effect

        # Act
        results = repo.list_runs()

        # Assert
        assert len(results) == 4
        assert results[0]["status"] == "completed"  # Already completed
        assert results[1]["status"] == "completed"  # Synced to completed
        assert results[1]["outputs"]["output_path"] == "outputs/run2/output.mp4"
        assert results[2]["status"] == "running"  # Still running after sync
        assert results[3]["status"] == "failed"  # Already failed

        # Should only sync the two running runs
        assert mock_status_checker.sync_run_status.call_count == 2

    def test_list_runs_with_status_filter_only_syncs_matching(self):
        """Test that list_runs with status filter only syncs matching runs."""
        # Arrange
        mock_db = MagicMock()
        mock_status_checker = MagicMock()

        repo = DataRepository(mock_db)
        repo.status_checker = mock_status_checker

        # Create mock runs - only running ones will be returned
        now = datetime.now(timezone.utc)
        mock_runs = [
            self._create_mock_run("run2", "running", now),
            self._create_mock_run("run3", "running", now),
        ]

        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__.return_value = mock_session
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all.return_value = mock_runs

        # Mock status checker behavior - properly mutate the run_data
        def sync_side_effect(run_data, service):
            if run_data["id"] == "run2":
                run_data["status"] = "completed"
                run_data["outputs"] = {"output_path": "outputs/run2/output.mp4"}
            return run_data

        mock_status_checker.sync_run_status.side_effect = sync_side_effect

        # Act
        results = repo.list_runs(status="running")

        # Assert
        assert len(results) == 2
        assert mock_status_checker.sync_run_status.call_count == 2

    def test_list_runs_handles_sync_errors_gracefully(self):
        """Test that list_runs handles sync errors without failing the entire operation."""
        # Arrange
        mock_db = MagicMock()
        mock_status_checker = MagicMock()

        repo = DataRepository(mock_db)
        repo.status_checker = mock_status_checker

        # Create mock runs
        now = datetime.now(timezone.utc)
        mock_runs = [
            self._create_mock_run("run1", "running", now),
            self._create_mock_run("run2", "running", now),
        ]

        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__.return_value = mock_session
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all.return_value = mock_runs

        # Mock status checker throwing error for first run
        def sync_side_effect(run_data, service):
            if run_data["id"] == "run1":
                raise Exception("SSH connection failed")
            return run_data

        mock_status_checker.sync_run_status.side_effect = sync_side_effect

        # Act
        results = repo.list_runs()

        # Assert
        assert len(results) == 2
        assert results[0]["status"] == "running"  # Sync failed, kept original
        assert results[1]["status"] == "running"  # Second run processed normally

    def _create_mock_run(self, run_id: str, status: str, created_at: datetime) -> Mock:
        """Helper to create mock run objects."""
        mock_run = MagicMock(spec=Run)
        mock_run.id = run_id
        mock_run.status = status
        mock_run.prompt_id = "ps_test"
        mock_run.model_type = "inference"
        mock_run.execution_config = {}
        mock_run.outputs = (
            {} if status != "completed" else {"output_path": f"outputs/{run_id}/output.mp4"}
        )
        mock_run.run_metadata = {}
        mock_run.created_at = created_at
        mock_run.updated_at = created_at
        mock_run.log_path = None
        mock_run.completed_at = created_at if status == "completed" else None
        mock_run.error_message = "Test error" if status == "failed" else None
        return mock_run
