"""Tests for WorkflowService query methods following TDD principles."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import SQLAlchemyError

from cosmos_workflow.services.data_repository import DataRepository


class TestWorkflowServiceQueries:
    """Test query methods for WorkflowService."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        session = MagicMock()
        return session

    @pytest.fixture
    def mock_db_connection(self, mock_session):
        """Create a mock database connection."""
        connection = MagicMock()
        connection.get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        connection.get_session.return_value.__exit__ = MagicMock(return_value=None)
        return connection

    @pytest.fixture
    def mock_config_manager(self):
        """Create a mock config manager."""
        config = MagicMock()
        config.get.return_value = {
            "inputs_directory": "/test/inputs",
            "outputs_directory": "/test/outputs",
        }
        return config

    @pytest.fixture
    def service(self, mock_db_connection, mock_config_manager):
        """Create WorkflowService instance with mocks."""
        return DataRepository(db_connection=mock_db_connection, config_manager=mock_config_manager)

    # Test list_prompts method
    def test_list_prompts_default(self, service, mock_session):
        """Test listing prompts with default parameters."""
        # Arrange
        mock_prompts = [
            MagicMock(
                id="ps_001",
                prompt_text="Test prompt 1",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                inputs={"video": "test.mp4"},
                parameters={"num_steps": 35},
                model_config={},
            ),
            MagicMock(
                id="ps_002",
                prompt_text="Test prompt 2",
                created_at=datetime.now() - timedelta(hours=1),
                updated_at=datetime.now() - timedelta(hours=1),
                inputs={"video": "test2.mp4"},
                parameters={"num_steps": 25},
                model_config={},
            ),
        ]

        mock_query = MagicMock()
        mock_query.order_by.return_value.limit.return_value.offset.return_value.all.return_value = (
            mock_prompts
        )
        mock_session.query.return_value = mock_query

        # Act
        result = service.list_prompts()

        # Assert
        assert len(result) == 2
        assert result[0]["id"] == "ps_001"
        # model_type no longer returned for prompts
        assert result[1]["id"] == "ps_002"
        mock_query.order_by.assert_called_once()
        mock_query.order_by().limit.assert_called_with(50)
        mock_query.order_by().limit().offset.assert_called_with(0)

    # Model filter test removed - prompts no longer have model_type filter

    def test_list_prompts_with_pagination(self, service, mock_session):
        """Test listing prompts with pagination."""
        # Arrange
        mock_prompts = []
        mock_query = MagicMock()
        mock_query.order_by.return_value.limit.return_value.offset.return_value.all.return_value = (
            mock_prompts
        )
        mock_session.query.return_value = mock_query

        # Act
        result = service.list_prompts(limit=10, offset=20)

        # Assert
        assert result == []
        mock_query.order_by().limit.assert_called_with(10)
        mock_query.order_by().limit().offset.assert_called_with(20)

    def test_list_prompts_database_error(self, service, mock_session):
        """Test list_prompts handles database errors gracefully."""
        # Arrange
        mock_session.query.side_effect = SQLAlchemyError("Database error")

        # Act
        result = service.list_prompts()

        # Assert
        assert result == []

    # Test list_runs method
    def test_list_runs_default(self, service, mock_session):
        """Test listing runs with default parameters."""
        # Arrange
        mock_runs = [
            MagicMock(
                id="rs_001",
                prompt_id="ps_001",
                status="completed",
                created_at=datetime.now(),
                started_at=datetime.now() - timedelta(minutes=10),
                completed_at=datetime.now(),
                execution_config={"weights": {}},
                outputs={"video_path": "output.mp4"},
                metadata={},
            ),
            MagicMock(
                id="rs_002",
                prompt_id="ps_002",
                status="running",
                created_at=datetime.now() - timedelta(hours=1),
                started_at=datetime.now() - timedelta(hours=1),
                completed_at=None,
                execution_config={},
                outputs={},
                metadata={},
            ),
        ]

        mock_query = MagicMock()
        mock_query.order_by.return_value.limit.return_value.offset.return_value.all.return_value = (
            mock_runs
        )
        mock_session.query.return_value = mock_query

        # Act
        result = service.list_runs()

        # Assert
        assert len(result) == 2
        assert result[0]["id"] == "rs_001"
        assert result[0]["status"] == "completed"
        assert result[1]["id"] == "rs_002"
        assert result[1]["status"] == "running"

    def test_list_runs_with_status_filter(self, service, mock_session):
        """Test listing runs filtered by status."""
        # Arrange
        mock_runs = [
            MagicMock(
                id="rs_001",
                prompt_id="ps_001",
                status="completed",
                created_at=datetime.now(),
                started_at=datetime.now(),
                completed_at=datetime.now(),
                execution_config={},
                outputs={"video_path": "output.mp4"},
                metadata={},
            )
        ]

        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_query.filter.return_value = mock_filter
        mock_filter.order_by.return_value.limit.return_value.offset.return_value.all.return_value = mock_runs
        mock_session.query.return_value = mock_query

        # Act
        result = service.list_runs(status="completed")

        # Assert
        assert len(result) == 1
        assert result[0]["status"] == "completed"
        mock_query.filter.assert_called_once()

    def test_list_runs_with_prompt_filter(self, service, mock_session):
        """Test listing runs filtered by prompt_id."""
        # Arrange
        mock_runs = [
            MagicMock(
                id="rs_001",
                prompt_id="ps_specific",
                status="completed",
                created_at=datetime.now(),
                started_at=datetime.now(),
                completed_at=datetime.now(),
                execution_config={},
                outputs={},
                metadata={},
            )
        ]

        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_query.filter.return_value = mock_filter
        mock_filter.order_by.return_value.limit.return_value.offset.return_value.all.return_value = mock_runs
        mock_session.query.return_value = mock_query

        # Act
        result = service.list_runs(prompt_id="ps_specific")

        # Assert
        assert len(result) == 1
        assert result[0]["prompt_id"] == "ps_specific"

    def test_list_runs_with_multiple_filters(self, service, mock_session):
        """Test listing runs with both status and prompt_id filters."""
        # Arrange
        mock_runs = []
        mock_query = MagicMock()
        mock_filter1 = MagicMock()
        mock_filter2 = MagicMock()
        mock_query.filter.return_value = mock_filter1
        mock_filter1.filter.return_value = mock_filter2
        mock_filter2.order_by.return_value.limit.return_value.offset.return_value.all.return_value = mock_runs
        mock_session.query.return_value = mock_query

        # Act
        result = service.list_runs(status="failed", prompt_id="ps_001")

        # Assert
        assert result == []
        assert mock_query.filter.called
        assert mock_filter1.filter.called

    # Test search_prompts method
    def test_search_prompts_finds_matches(self, service, mock_session):
        """Test searching prompts with matching query."""
        # Arrange
        mock_prompts = [
            MagicMock(
                id="ps_001",
                prompt_text="cyberpunk city transformation",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                inputs={"video": "city.mp4"},
                parameters={},
                model_config={},
            ),
            MagicMock(
                id="ps_002",
                prompt_text="futuristic cyberpunk scene",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                inputs={},
                parameters={},
                model_config={},
            ),
        ]

        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_query.filter.return_value = mock_filter
        mock_filter.order_by.return_value.limit.return_value.all.return_value = mock_prompts
        mock_session.query.return_value = mock_query

        # Act
        result = service.search_prompts("cyberpunk")

        # Assert
        assert len(result) == 2
        assert "cyberpunk" in result[0]["prompt_text"].lower()
        assert "cyberpunk" in result[1]["prompt_text"].lower()

    def test_search_prompts_no_matches(self, service, mock_session):
        """Test searching prompts with no matches."""
        # Arrange
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_query.filter.return_value = mock_filter
        mock_filter.order_by.return_value.limit.return_value.all.return_value = []
        mock_session.query.return_value = mock_query

        # Act
        result = service.search_prompts("nonexistent")

        # Assert
        assert result == []

    def test_search_prompts_empty_query(self, service, mock_session):
        """Test search_prompts with empty query returns empty list."""
        # Act
        result = service.search_prompts("")

        # Assert
        assert result == []
        mock_session.query.assert_not_called()

    def test_search_prompts_case_insensitive(self, service, mock_session):
        """Test search is case-insensitive."""
        # Arrange
        mock_prompts = [
            MagicMock(
                id="ps_001",
                prompt_text="CYBERPUNK CITY",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                inputs={},
                parameters={},
                model_config={},
            )
        ]

        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_query.filter.return_value = mock_filter
        mock_filter.order_by.return_value.limit.return_value.all.return_value = mock_prompts
        mock_session.query.return_value = mock_query

        # Act
        result = service.search_prompts("cyberpunk")

        # Assert
        assert len(result) == 1

    # Test get_prompt_with_runs method
    def test_get_prompt_with_runs_found(self, service, mock_session):
        """Test getting prompt with associated runs."""
        # Arrange
        mock_runs = [
            MagicMock(
                id="rs_001",
                prompt_id="ps_001",
                status="completed",
                created_at=datetime.now(),
                started_at=datetime.now(),
                completed_at=datetime.now(),
                execution_config={},
                outputs={"video_path": "output.mp4"},
                metadata={},
            ),
            MagicMock(
                id="rs_002",
                prompt_id="ps_001",
                status="failed",
                created_at=datetime.now() - timedelta(hours=1),
                started_at=datetime.now() - timedelta(hours=1),
                completed_at=datetime.now() - timedelta(minutes=50),
                execution_config={},
                outputs={},
                metadata={"error": "GPU OOM"},
            ),
        ]

        mock_prompt = MagicMock(
            id="ps_001",
            prompt_text="Test prompt",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            inputs={"video": "test.mp4"},
            parameters={},
            model_config={},
            runs=mock_runs,
        )

        mock_query = MagicMock()
        mock_options = MagicMock()
        mock_query.options.return_value = mock_options
        mock_options.filter.return_value.first.return_value = mock_prompt
        mock_session.query.return_value = mock_query

        # Act
        result = service.get_prompt_with_runs("ps_001")

        # Assert
        assert result is not None
        assert result["id"] == "ps_001"
        assert "runs" in result
        assert len(result["runs"]) == 2
        assert result["runs"][0]["id"] == "rs_001"
        assert result["runs"][0]["status"] == "completed"
        assert result["runs"][1]["id"] == "rs_002"
        assert result["runs"][1]["status"] == "failed"

    def test_get_prompt_with_runs_not_found(self, service, mock_session):
        """Test getting prompt that doesn't exist."""
        # Arrange
        mock_query = MagicMock()
        mock_options = MagicMock()
        mock_query.options.return_value = mock_options
        mock_options.filter.return_value.first.return_value = None
        mock_session.query.return_value = mock_query

        # Act
        result = service.get_prompt_with_runs("ps_nonexistent")

        # Assert
        assert result is None

    def test_get_prompt_with_runs_no_runs(self, service, mock_session):
        """Test getting prompt with no associated runs."""
        # Arrange
        mock_prompt = MagicMock(
            id="ps_001",
            prompt_text="Test prompt",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            inputs={},
            parameters={},
            model_config={},
            runs=[],
        )

        mock_query = MagicMock()
        mock_options = MagicMock()
        mock_query.options.return_value = mock_options
        mock_options.filter.return_value.first.return_value = mock_prompt
        mock_session.query.return_value = mock_query

        # Act
        result = service.get_prompt_with_runs("ps_001")

        # Assert
        assert result is not None
        assert result["id"] == "ps_001"
        assert "runs" in result
        assert result["runs"] == []

    def test_get_prompt_with_runs_database_error(self, service, mock_session):
        """Test get_prompt_with_runs handles database errors."""
        # Arrange
        mock_session.query.side_effect = SQLAlchemyError("Database error")

        # Act
        result = service.get_prompt_with_runs("ps_001")

        # Assert
        assert result is None
