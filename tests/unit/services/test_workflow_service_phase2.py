"""Tests for Phase 2 WorkflowService update methods - log and error tracking."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock

import pytest

from cosmos_workflow.database.models import Run
from cosmos_workflow.services.data_repository import DataRepository


class TestWorkflowServicePhase2Updates:
    """Test the new update_run_with_log and update_run_error methods."""

    @pytest.fixture
    def mock_db_connection(self):
        """Create a mock database connection."""
        mock_db = Mock()
        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__ = Mock(return_value=mock_session)
        mock_db.get_session.return_value.__exit__ = Mock(return_value=None)
        return mock_db, mock_session

    @pytest.fixture
    def mock_config_manager(self):
        """Create a mock config manager."""
        mock_config = Mock()
        return mock_config

    @pytest.fixture
    def workflow_service(self, mock_db_connection, mock_config_manager):
        """Create WorkflowService instance with mocks."""
        mock_db, _ = mock_db_connection
        return DataRepository(mock_db, mock_config_manager)

    def test_update_run_with_log_method_exists(self, workflow_service):
        """Test that update_run_with_log method exists."""
        assert hasattr(workflow_service, "update_run_with_log"), (
            "WorkflowService should have update_run_with_log method"
        )

    def test_update_run_error_method_exists(self, workflow_service):
        """Test that update_run_error method exists."""
        assert hasattr(workflow_service, "update_run_error"), (
            "WorkflowService should have update_run_error method"
        )

    def test_update_run_with_log_success(self, workflow_service, mock_db_connection):
        """Test successful update of run with log path."""
        mock_db, mock_session = mock_db_connection

        # Create mock run
        mock_run = Mock(spec=Run)
        mock_run.id = "rs_test123"
        mock_run.prompt_id = "ps_test456"
        mock_run.model_type = "transfer"
        mock_run.status = "completed"
        mock_run.execution_config = {"gpu": "A100"}
        mock_run.outputs = {"video": "/output/video.mp4"}
        mock_run.run_metadata = {}
        mock_run.created_at = datetime.now(timezone.utc)
        mock_run.updated_at = datetime.now(timezone.utc)
        mock_run.started_at = datetime.now(timezone.utc)
        mock_run.completed_at = datetime.now(timezone.utc)
        mock_run.log_path = None  # Initially no log path

        # Mock the query
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_run

        # Call the method
        log_path = "outputs/run_rs_test123/logs/run.log"
        result = workflow_service.update_run_with_log("rs_test123", log_path)

        # Verify
        assert mock_run.log_path == log_path
        mock_session.commit.assert_called_once()
        assert result["id"] == "rs_test123"
        assert result["log_path"] == log_path

    def test_update_run_with_log_run_not_found(self, workflow_service, mock_db_connection):
        """Test update_run_with_log when run doesn't exist."""
        mock_db, mock_session = mock_db_connection

        # Mock query returns None
        mock_session.query.return_value.filter_by.return_value.first.return_value = None

        # Call the method
        result = workflow_service.update_run_with_log("rs_nonexistent", "some/path.log")

        # Verify
        assert result is None
        mock_session.commit.assert_not_called()

    def test_update_run_error_success(self, workflow_service, mock_db_connection):
        """Test successful update of run with error message."""
        mock_db, mock_session = mock_db_connection

        # Create mock run
        mock_run = Mock(spec=Run)
        mock_run.id = "rs_test789"
        mock_run.prompt_id = "ps_test456"
        mock_run.model_type = "transfer"
        mock_run.status = "running"
        mock_run.execution_config = {"gpu": "A100"}
        mock_run.outputs = {}
        mock_run.run_metadata = {}
        mock_run.created_at = datetime.now(timezone.utc)
        mock_run.updated_at = datetime.now(timezone.utc)
        mock_run.started_at = datetime.now(timezone.utc)
        mock_run.completed_at = None
        mock_run.error_message = None  # Initially no error

        # Mock the query
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_run

        # Call the method
        error_msg = "Docker container failed to start: insufficient GPU memory"
        result = workflow_service.update_run_error("rs_test789", error_msg)

        # Verify
        assert mock_run.status == "failed"
        assert mock_run.error_message == error_msg
        mock_session.commit.assert_called_once()
        assert result["id"] == "rs_test789"
        assert result["status"] == "failed"
        assert result["error_message"] == error_msg

    def test_update_run_error_truncates_long_message(self, workflow_service, mock_db_connection):
        """Test that update_run_error truncates very long error messages."""
        mock_db, mock_session = mock_db_connection

        # Create mock run
        mock_run = Mock(spec=Run)
        mock_run.id = "rs_long_error"
        mock_run.prompt_id = "ps_test456"
        mock_run.model_type = "transfer"
        mock_run.status = "running"
        mock_run.execution_config = {"gpu": "A100"}
        mock_run.outputs = {}
        mock_run.run_metadata = {}
        mock_run.created_at = datetime.now(timezone.utc)
        mock_run.updated_at = datetime.now(timezone.utc)
        mock_run.started_at = datetime.now(timezone.utc)
        mock_run.completed_at = None
        mock_run.error_message = None

        # Mock the query
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_run

        # Call with very long error message
        long_error = "Error: " + "x" * 2000  # 2000+ character error
        workflow_service.update_run_error("rs_long_error", long_error)

        # Verify truncation to 1000 characters
        assert len(mock_run.error_message) == 1000
        assert mock_run.error_message == long_error[:1000]
        assert mock_run.status == "failed"
        mock_session.commit.assert_called_once()

    def test_update_run_error_run_not_found(self, workflow_service, mock_db_connection):
        """Test update_run_error when run doesn't exist."""
        mock_db, mock_session = mock_db_connection

        # Mock query returns None
        mock_session.query.return_value.filter_by.return_value.first.return_value = None

        # Call the method
        result = workflow_service.update_run_error("rs_nonexistent", "Some error")

        # Verify
        assert result is None
        mock_session.commit.assert_not_called()

    def test_update_run_with_log_validates_run_id(self, workflow_service):
        """Test that update_run_with_log validates run_id."""
        # Test with None
        with pytest.raises(ValueError, match="run_id is required"):
            workflow_service.update_run_with_log(None, "some/path.log")

        # Test with empty string
        with pytest.raises(ValueError, match="run_id cannot be empty"):
            workflow_service.update_run_with_log("", "some/path.log")

        # Test with whitespace
        with pytest.raises(ValueError, match="run_id cannot be empty"):
            workflow_service.update_run_with_log("   ", "some/path.log")

    def test_update_run_error_validates_run_id(self, workflow_service):
        """Test that update_run_error validates run_id."""
        # Test with None
        with pytest.raises(ValueError, match="run_id is required"):
            workflow_service.update_run_error(None, "Some error")

        # Test with empty string
        with pytest.raises(ValueError, match="run_id cannot be empty"):
            workflow_service.update_run_error("", "Some error")

        # Test with whitespace
        with pytest.raises(ValueError, match="run_id cannot be empty"):
            workflow_service.update_run_error("   ", "Some error")

    def test_update_run_with_log_preserves_existing_data(
        self, workflow_service, mock_db_connection
    ):
        """Test that update_run_with_log doesn't modify other fields."""
        mock_db, mock_session = mock_db_connection

        # Create mock run with existing data
        mock_run = Mock(spec=Run)
        mock_run.id = "rs_preserve"
        mock_run.prompt_id = "ps_test456"
        mock_run.model_type = "transfer"
        mock_run.status = "completed"
        mock_run.execution_config = {"gpu": "A100", "memory": "40GB"}
        mock_run.outputs = {"video": "/output/video.mp4", "frames": 100}
        mock_run.run_metadata = {"user": "test", "priority": "high"}
        mock_run.created_at = datetime.now(timezone.utc)
        mock_run.updated_at = datetime.now(timezone.utc)
        mock_run.started_at = datetime.now(timezone.utc)
        mock_run.completed_at = datetime.now(timezone.utc)
        mock_run.log_path = None
        mock_run.error_message = "Previous error"  # Existing error

        # Store original values
        original_status = mock_run.status
        original_config = mock_run.execution_config.copy()
        original_outputs = mock_run.outputs.copy()
        original_metadata = mock_run.run_metadata.copy()
        original_error = mock_run.error_message

        # Mock the query
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_run

        # Call the method
        log_path = "outputs/run_rs_preserve/logs/run.log"
        workflow_service.update_run_with_log("rs_preserve", log_path)

        # Verify only log_path changed
        assert mock_run.log_path == log_path
        assert mock_run.status == original_status
        assert mock_run.execution_config == original_config
        assert mock_run.outputs == original_outputs
        assert mock_run.run_metadata == original_metadata
        assert mock_run.error_message == original_error  # Error message preserved

    def test_update_run_error_preserves_log_path(self, workflow_service, mock_db_connection):
        """Test that update_run_error preserves existing log_path."""
        mock_db, mock_session = mock_db_connection

        # Create mock run with existing log path
        mock_run = Mock(spec=Run)
        mock_run.id = "rs_preserve_log"
        mock_run.prompt_id = "ps_test456"
        mock_run.model_type = "transfer"
        mock_run.status = "running"
        mock_run.execution_config = {"gpu": "A100"}
        mock_run.outputs = {}
        mock_run.run_metadata = {}
        mock_run.created_at = datetime.now(timezone.utc)
        mock_run.updated_at = datetime.now(timezone.utc)
        mock_run.started_at = datetime.now(timezone.utc)
        mock_run.completed_at = None
        mock_run.log_path = "outputs/run_rs_preserve_log/logs/run.log"  # Existing log
        mock_run.error_message = None

        original_log_path = mock_run.log_path

        # Mock the query
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_run

        # Call the method
        error_msg = "Process failed"
        workflow_service.update_run_error("rs_preserve_log", error_msg)

        # Verify log_path preserved
        assert mock_run.log_path == original_log_path
        assert mock_run.error_message == error_msg
        assert mock_run.status == "failed"

    def test_both_methods_can_be_called_sequentially(self, workflow_service, mock_db_connection):
        """Test that both update methods can be called on the same run."""
        mock_db, mock_session = mock_db_connection

        # Create mock run
        mock_run = Mock(spec=Run)
        mock_run.id = "rs_sequential"
        mock_run.prompt_id = "ps_test456"
        mock_run.model_type = "transfer"
        mock_run.status = "running"
        mock_run.execution_config = {"gpu": "A100"}
        mock_run.outputs = {}
        mock_run.run_metadata = {}
        mock_run.created_at = datetime.now(timezone.utc)
        mock_run.updated_at = datetime.now(timezone.utc)
        mock_run.started_at = datetime.now(timezone.utc)
        mock_run.completed_at = None
        mock_run.log_path = None
        mock_run.error_message = None

        # Mock the query to return the same run
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_run

        # First, update with log path
        log_path = "outputs/run_rs_sequential/logs/run.log"
        workflow_service.update_run_with_log("rs_sequential", log_path)
        assert mock_run.log_path == log_path

        # Then, update with error (simulating a failure after logging started)
        error_msg = "Process terminated unexpectedly"
        workflow_service.update_run_error("rs_sequential", error_msg)

        # Verify both fields are set
        assert mock_run.log_path == log_path
        assert mock_run.error_message == error_msg
        assert mock_run.status == "failed"
