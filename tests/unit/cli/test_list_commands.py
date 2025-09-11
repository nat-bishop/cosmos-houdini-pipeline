"""Tests for CLI list commands following TDD principles."""

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from cosmos_workflow.cli.base import CLIContext
from cosmos_workflow.cli.list_commands import list_group


class TestListCommands:
    """Test list commands for CLI."""

    @pytest.fixture
    def runner(self):
        """Create a CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_operations(self):
        """Create a mock WorkflowOperations."""
        return MagicMock()

    @pytest.fixture
    def mock_context(self, mock_operations):
        """Create a mock context with service."""
        context = MagicMock()
        context.obj = {"service": mock_operations}
        return context

    # Test list prompts command
    @patch("cosmos_workflow.cli.base.CLIContext.get_operations")
    def test_list_prompts_default(self, mock_get_operations, runner, mock_operations):
        """Test listing prompts with default parameters."""
        # Arrange
        mock_prompts = [
            {
                "id": "ps_001",
                "prompt_text": "Test prompt 1",
                "created_at": "2024-01-01T00:00:00",
                "inputs": {"video": "test.mp4"},
            },
            {
                "id": "ps_002",
                "prompt_text": "Test prompt 2",
                "created_at": "2024-01-01T01:00:00",
                "inputs": {},
            },
        ]
        mock_operations.list_prompts.return_value = mock_prompts
        mock_get_operations.return_value = mock_operations

        # Act
        result = runner.invoke(list_group, ["prompts"], obj=CLIContext())

        # Assert
        assert result.exit_code == 0
        assert "ps_001" in result.output
        assert "ps_002" in result.output
        # Model type no longer displayed for prompts
        mock_operations.list_prompts.assert_called_once_with(limit=50)

    # Model filter removed - prompts no longer have model_type

    @patch("cosmos_workflow.cli.base.CLIContext.get_operations")
    def test_list_prompts_with_limit(self, mock_get_operations, runner, mock_operations):
        """Test listing prompts with custom limit."""
        # Arrange
        mock_operations.list_prompts.return_value = []
        mock_get_operations.return_value = mock_operations

        # Act
        result = runner.invoke(list_group, ["prompts", "--limit", "10"], obj=CLIContext())

        # Assert
        assert result.exit_code == 0
        mock_operations.list_prompts.assert_called_once_with(limit=10)

    @patch("cosmos_workflow.cli.base.CLIContext.get_operations")
    def test_list_prompts_empty_result(self, mock_get_operations, runner, mock_operations):
        """Test listing prompts with no results."""
        # Arrange
        mock_operations.list_prompts.return_value = []
        mock_get_operations.return_value = mock_operations

        # Act
        result = runner.invoke(list_group, ["prompts"], obj=CLIContext())

        # Assert
        assert result.exit_code == 0
        assert "No prompts found" in result.output

    @patch("cosmos_workflow.cli.base.CLIContext.get_operations")
    def test_list_prompts_json_output(self, mock_get_operations, runner, mock_operations):
        """Test listing prompts with JSON output format."""
        # Arrange
        mock_prompts = [
            {
                "id": "ps_001",
                "prompt_text": "Test prompt",
                "created_at": "2024-01-01T00:00:00",
                "inputs": {"video": "test.mp4"},
            }
        ]
        mock_operations.list_prompts.return_value = mock_prompts
        mock_get_operations.return_value = mock_operations

        # Act
        result = runner.invoke(list_group, ["prompts", "--json"], obj=CLIContext())

        # Assert
        assert result.exit_code == 0
        output_data = json.loads(result.output)
        assert len(output_data) == 1
        assert output_data[0]["id"] == "ps_001"

    # Test list runs command
    @patch("cosmos_workflow.cli.base.CLIContext.get_operations")
    def test_list_runs_default(self, mock_get_operations, runner, mock_operations):
        """Test listing runs with default parameters."""
        # Arrange
        mock_runs = [
            {
                "id": "rs_001",
                "prompt_id": "ps_001",
                "model_type": "transfer",
                "status": "completed",
                "created_at": "2024-01-01T00:00:00",
                "outputs": {"video_path": "output.mp4"},
            },
            {
                "id": "rs_002",
                "prompt_id": "ps_002",
                "model_type": "enhance",
                "status": "running",
                "created_at": "2024-01-01T01:00:00",
                "outputs": {},
            },
        ]
        mock_operations.list_runs.return_value = mock_runs
        mock_get_operations.return_value = mock_operations

        # Act
        result = runner.invoke(list_group, ["runs"], obj=CLIContext())

        # Assert
        assert result.exit_code == 0
        assert "rs_001" in result.output
        assert "rs_002" in result.output
        assert "completed" in result.output
        assert "running" in result.output
        mock_operations.list_runs.assert_called_once_with(status=None, prompt_id=None, limit=50)

    @patch("cosmos_workflow.cli.base.CLIContext.get_operations")
    def test_list_runs_with_status_filter(self, mock_get_operations, runner, mock_operations):
        """Test listing runs filtered by status."""
        # Arrange
        mock_runs = [
            {
                "id": "rs_001",
                "model_type": "transfer",
                "prompt_id": "ps_001",
                "status": "completed",
                "created_at": "2024-01-01T00:00:00",
                "outputs": {"video_path": "output.mp4"},
            }
        ]
        mock_operations.list_runs.return_value = mock_runs
        mock_get_operations.return_value = mock_operations

        # Act
        result = runner.invoke(list_group, ["runs", "--status", "completed"], obj=CLIContext())

        # Assert
        assert result.exit_code == 0
        assert "rs_001" in result.output
        assert "completed" in result.output
        mock_operations.list_runs.assert_called_once_with(
            status="completed", prompt_id=None, limit=50
        )

    @patch("cosmos_workflow.cli.base.CLIContext.get_operations")
    def test_list_runs_with_prompt_filter(self, mock_get_operations, runner, mock_operations):
        """Test listing runs filtered by prompt ID."""
        # Arrange
        mock_runs = [
            {
                "id": "rs_001",
                "model_type": "transfer",
                "prompt_id": "ps_specific",
                "status": "completed",
                "created_at": "2024-01-01T00:00:00",
                "outputs": {},
            }
        ]
        mock_operations.list_runs.return_value = mock_runs
        mock_get_operations.return_value = mock_operations

        # Act
        result = runner.invoke(list_group, ["runs", "--prompt", "ps_specific"], obj=CLIContext())

        # Assert
        assert result.exit_code == 0
        assert "rs_001" in result.output
        assert "ps_specific" in result.output
        mock_operations.list_runs.assert_called_once_with(
            status=None, prompt_id="ps_specific", limit=50
        )

    @patch("cosmos_workflow.cli.base.CLIContext.get_operations")
    def test_list_runs_with_multiple_filters(self, mock_get_operations, runner, mock_operations):
        """Test listing runs with both status and prompt filters."""
        # Arrange
        mock_operations.list_runs.return_value = []
        mock_get_operations.return_value = mock_operations

        # Act
        result = runner.invoke(
            list_group, ["runs", "--status", "failed", "--prompt", "ps_001"], obj=CLIContext()
        )

        # Assert
        assert result.exit_code == 0
        mock_operations.list_runs.assert_called_once_with(
            status="failed", prompt_id="ps_001", limit=50
        )

    @patch("cosmos_workflow.cli.base.CLIContext.get_operations")
    def test_list_runs_empty_result(self, mock_get_operations, runner, mock_operations):
        """Test listing runs with no results."""
        # Arrange
        mock_operations.list_runs.return_value = []
        mock_get_operations.return_value = mock_operations

        # Act
        result = runner.invoke(list_group, ["runs"], obj=CLIContext())

        # Assert
        assert result.exit_code == 0
        assert "No runs found" in result.output

    @patch("cosmos_workflow.cli.base.CLIContext.get_operations")
    def test_list_runs_invalid_status(self, mock_get_operations, runner, mock_operations):
        """Test listing runs with invalid status filter."""
        # Arrange
        mock_get_operations.return_value = mock_operations

        # Act
        result = runner.invoke(list_group, ["runs", "--status", "invalid"], obj=CLIContext())

        # Assert
        assert result.exit_code != 0
        assert "Invalid value for '--status'" in result.output

    @patch("cosmos_workflow.cli.base.CLIContext.get_operations")
    def test_list_runs_json_output(self, mock_get_operations, runner, mock_operations):
        """Test listing runs with JSON output format."""
        # Arrange
        mock_runs = [
            {
                "id": "rs_001",
                "model_type": "transfer",
                "prompt_id": "ps_001",
                "status": "completed",
                "created_at": "2024-01-01T00:00:00",
                "outputs": {"video_path": "output.mp4"},
            }
        ]
        mock_operations.list_runs.return_value = mock_runs
        mock_get_operations.return_value = mock_operations

        # Act
        result = runner.invoke(list_group, ["runs", "--json"], obj=CLIContext())

        # Assert
        assert result.exit_code == 0
        output_data = json.loads(result.output)
        assert len(output_data) == 1
        assert output_data[0]["id"] == "rs_001"
        assert output_data[0]["status"] == "completed"
