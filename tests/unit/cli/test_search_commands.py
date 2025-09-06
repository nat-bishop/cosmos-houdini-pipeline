"""Tests for CLI search and show commands following TDD principles."""

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from cosmos_workflow.cli.search import search_command
from cosmos_workflow.cli.show import show_command


class TestSearchCommand:
    """Test search command for CLI."""

    @pytest.fixture
    def runner(self):
        """Create a CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_operations(self):
        """Create a mock WorkflowOperations."""
        return MagicMock()

    @patch("cosmos_workflow.cli.search.get_operations")
    def test_search_with_results(self, mock_get_operations, runner, mock_operations):
        """Test searching prompts with matching results."""
        # Arrange
        mock_prompts = [
            {
                "id": "ps_001",
                "model_type": "transfer",
                "prompt_text": "A cyberpunk city at night",
                "created_at": "2024-01-01T00:00:00",
                "inputs": {"video": "test.mp4"},
            },
            {
                "id": "ps_002",
                "model_type": "transfer",
                "prompt_text": "Futuristic cyberpunk scene",
                "created_at": "2024-01-01T01:00:00",
                "inputs": {"video": "test2.mp4"},
            },
        ]
        mock_operations.search_prompts.return_value = mock_prompts
        mock_get_operations.return_value = mock_operations

        # Act
        result = runner.invoke(search_command, ["cyberpunk"])

        # Assert
        assert result.exit_code == 0
        assert "ps_001" in result.output
        assert "ps_002" in result.output
        assert "cyberpunk" in result.output.lower()
        mock_operations.search_prompts.assert_called_once_with("cyberpunk", limit=50)

    @patch("cosmos_workflow.cli.search.get_operations")
    def test_search_no_results(self, mock_get_operations, runner, mock_operations):
        """Test searching prompts with no matches."""
        # Arrange
        mock_operations.search_prompts.return_value = []
        mock_get_operations.return_value = mock_operations

        # Act
        result = runner.invoke(search_command, ["nonexistent"])

        # Assert
        assert result.exit_code == 0
        assert "No prompts found" in result.output
        mock_operations.search_prompts.assert_called_once_with("nonexistent", limit=50)

    @patch("cosmos_workflow.cli.search.get_operations")
    def test_search_with_limit(self, mock_get_operations, runner, mock_operations):
        """Test searching prompts with custom limit."""
        # Arrange
        mock_operations.search_prompts.return_value = []
        mock_get_operations.return_value = mock_operations

        # Act
        result = runner.invoke(search_command, ["test", "--limit", "10"])

        # Assert
        assert result.exit_code == 0
        mock_operations.search_prompts.assert_called_once_with("test", limit=10)

    @patch("cosmos_workflow.cli.search.get_operations")
    def test_search_empty_query(self, mock_get_operations, runner, mock_operations):
        """Test search with empty query."""
        # Act
        result = runner.invoke(search_command, [""])

        # Assert
        assert result.exit_code != 0
        assert "Search query cannot be empty" in result.output

    @patch("cosmos_workflow.cli.search.get_operations")
    def test_search_json_output(self, mock_get_operations, runner, mock_operations):
        """Test search with JSON output format."""
        # Arrange
        mock_prompts = [
            {
                "id": "ps_001",
                "model_type": "transfer",
                "prompt_text": "Test prompt",
                "created_at": "2024-01-01T00:00:00",
                "inputs": {"video": "test.mp4"},
            }
        ]
        mock_operations.search_prompts.return_value = mock_prompts
        mock_get_operations.return_value = mock_operations

        # Act
        result = runner.invoke(search_command, ["test", "--json"])

        # Assert
        assert result.exit_code == 0
        output_data = json.loads(result.output)
        assert len(output_data) == 1
        assert output_data[0]["id"] == "ps_001"


class TestShowCommand:
    """Test show command for CLI."""

    @pytest.fixture
    def runner(self):
        """Create a CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_operations(self):
        """Create a mock WorkflowOperations."""
        return MagicMock()

    @patch("cosmos_workflow.cli.show.get_operations")
    def test_show_prompt_with_runs(self, mock_get_operations, runner, mock_operations):
        """Test showing prompt with associated runs."""
        # Arrange
        mock_prompt_data = {
            "id": "ps_001",
            "model_type": "transfer",
            "prompt_text": "Test prompt",
            "created_at": "2024-01-01T00:00:00",
            "inputs": {"video": "test.mp4"},
            "parameters": {"num_steps": 35},
            "runs": [
                {
                    "id": "rs_001",
                    "status": "completed",
                    "created_at": "2024-01-01T01:00:00",
                    "outputs": {"video_path": "output.mp4"},
                },
                {
                    "id": "rs_002",
                    "status": "failed",
                    "created_at": "2024-01-01T02:00:00",
                    "outputs": {},
                },
            ],
        }
        mock_operations.get_prompt_with_runs.return_value = mock_prompt_data
        mock_get_operations.return_value = mock_operations

        # Act
        result = runner.invoke(show_command, ["ps_001"])

        # Assert
        assert result.exit_code == 0
        assert "ps_001" in result.output
        assert "Test prompt" in result.output
        assert "rs_001" in result.output
        assert "rs_002" in result.output
        assert "completed" in result.output
        assert "failed" in result.output
        mock_operations.get_prompt_with_runs.assert_called_once_with("ps_001")

    @patch("cosmos_workflow.cli.show.get_operations")
    def test_show_prompt_no_runs(self, mock_get_operations, runner, mock_operations):
        """Test showing prompt with no runs."""
        # Arrange
        mock_prompt_data = {
            "id": "ps_001",
            "model_type": "transfer",
            "prompt_text": "Test prompt",
            "created_at": "2024-01-01T00:00:00",
            "inputs": {"video": "test.mp4"},
            "parameters": {"num_steps": 35},
            "runs": [],
        }
        mock_operations.get_prompt_with_runs.return_value = mock_prompt_data
        mock_get_operations.return_value = mock_operations

        # Act
        result = runner.invoke(show_command, ["ps_001"])

        # Assert
        assert result.exit_code == 0
        assert "ps_001" in result.output
        assert "Test prompt" in result.output
        assert "No runs" in result.output or "0 runs" in result.output

    @patch("cosmos_workflow.cli.show.get_operations")
    def test_show_prompt_not_found(self, mock_get_operations, runner, mock_operations):
        """Test showing non-existent prompt."""
        # Arrange
        mock_operations.get_prompt_with_runs.return_value = None
        mock_get_operations.return_value = mock_operations

        # Act
        result = runner.invoke(show_command, ["ps_nonexistent"])

        # Assert
        assert result.exit_code == 0
        assert "Prompt not found" in result.output
        mock_operations.get_prompt_with_runs.assert_called_once_with("ps_nonexistent")

    @patch("cosmos_workflow.cli.show.get_operations")
    def test_show_json_output(self, mock_get_operations, runner, mock_operations):
        """Test show with JSON output format."""
        # Arrange
        mock_prompt_data = {
            "id": "ps_001",
            "model_type": "transfer",
            "prompt_text": "Test prompt",
            "created_at": "2024-01-01T00:00:00",
            "inputs": {"video": "test.mp4"},
            "parameters": {"num_steps": 35},
            "runs": [
                {
                    "id": "rs_001",
                    "status": "completed",
                    "created_at": "2024-01-01T01:00:00",
                    "outputs": {"video_path": "output.mp4"},
                }
            ],
        }
        mock_operations.get_prompt_with_runs.return_value = mock_prompt_data
        mock_get_operations.return_value = mock_operations

        # Act
        result = runner.invoke(show_command, ["ps_001", "--json"])

        # Assert
        assert result.exit_code == 0
        output_data = json.loads(result.output)
        assert output_data["id"] == "ps_001"
        assert len(output_data["runs"]) == 1
        assert output_data["runs"][0]["id"] == "rs_001"
