"""Tests for CLI delete commands following TDD principles."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from cosmos_workflow.cli.delete import delete_group


class TestDeletePromptCommand:
    """Test delete prompt command."""

    @pytest.fixture
    def runner(self):
        """Create a CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_service(self):
        """Create a mock WorkflowService."""
        return MagicMock()

    @patch("cosmos_workflow.cli.delete.get_service")
    @patch("cosmos_workflow.cli.delete.click.confirm")
    def test_delete_prompt_with_confirmation(
        self, mock_confirm, mock_get_service, runner, mock_service
    ):
        """Test deleting a prompt with user confirmation."""
        # Arrange
        prompt_id = "ps_test123"
        mock_service.preview_prompt_deletion.return_value = {
            "prompt": {"id": prompt_id, "prompt_text": "Test prompt"},
            "runs": [{"id": "rs_001"}, {"id": "rs_002"}],
            "directories_to_delete": ["outputs/run_rs_001", "outputs/run_rs_002"],
        }
        mock_service.delete_prompt.return_value = {
            "success": True,
            "deleted": {
                "prompt_id": prompt_id,
                "run_ids": ["rs_001", "rs_002"],
                "directories": ["outputs/run_rs_001", "outputs/run_rs_002"],
            },
        }
        mock_get_service.return_value = mock_service
        mock_confirm.return_value = True

        # Act
        result = runner.invoke(delete_group, ["prompt", prompt_id])

        # Assert
        assert result.exit_code == 0
        assert "Preview of deletion" in result.output
        assert "Test prompt" in result.output
        assert "2 run(s)" in result.output
        assert "Successfully deleted" in result.output
        mock_service.preview_prompt_deletion.assert_called_once_with(prompt_id)
        mock_service.delete_prompt.assert_called_once_with(prompt_id)
        mock_confirm.assert_called_once()

    @patch("cosmos_workflow.cli.delete.get_service")
    @patch("cosmos_workflow.cli.delete.click.confirm")
    def test_delete_prompt_cancelled(self, mock_confirm, mock_get_service, runner, mock_service):
        """Test cancelling prompt deletion."""
        # Arrange
        prompt_id = "ps_test123"
        mock_service.preview_prompt_deletion.return_value = {
            "prompt": {"id": prompt_id, "prompt_text": "Test prompt"},
            "runs": [],
            "directories_to_delete": [],
        }
        mock_get_service.return_value = mock_service
        mock_confirm.return_value = False

        # Act
        result = runner.invoke(delete_group, ["prompt", prompt_id])

        # Assert
        assert result.exit_code == 0
        assert "Deletion cancelled" in result.output
        mock_service.preview_prompt_deletion.assert_called_once_with(prompt_id)
        mock_service.delete_prompt.assert_not_called()

    @patch("cosmos_workflow.cli.delete.get_service")
    def test_delete_prompt_with_force(self, mock_get_service, runner, mock_service):
        """Test deleting a prompt with --force flag."""
        # Arrange
        prompt_id = "ps_test123"
        mock_service.preview_prompt_deletion.return_value = {
            "prompt": {"id": prompt_id, "prompt_text": "Test prompt"},
            "runs": [],
            "directories_to_delete": [],
        }
        mock_service.delete_prompt.return_value = {
            "success": True,
            "deleted": {"prompt_id": prompt_id, "run_ids": [], "directories": []},
        }
        mock_get_service.return_value = mock_service

        # Act
        result = runner.invoke(delete_group, ["prompt", prompt_id, "--force"])

        # Assert
        assert result.exit_code == 0
        assert "Successfully deleted" in result.output
        mock_service.preview_prompt_deletion.assert_called_once_with(prompt_id)
        mock_service.delete_prompt.assert_called_once_with(prompt_id)

    @patch("cosmos_workflow.cli.delete.get_service")
    def test_delete_prompt_not_found(self, mock_get_service, runner, mock_service):
        """Test deleting a non-existent prompt."""
        # Arrange
        prompt_id = "ps_nonexistent"
        mock_service.preview_prompt_deletion.return_value = {
            "prompt": None,
            "runs": [],
            "directories_to_delete": [],
            "error": "Prompt not found",
        }
        mock_get_service.return_value = mock_service

        # Act
        result = runner.invoke(delete_group, ["prompt", prompt_id])

        # Assert
        assert result.exit_code == 1
        assert "Error: Prompt not found" in result.output
        mock_service.delete_prompt.assert_not_called()

    @patch("cosmos_workflow.cli.delete.get_service")
    @patch("cosmos_workflow.cli.delete.click.confirm")
    def test_delete_prompt_with_active_runs(
        self, mock_confirm, mock_get_service, runner, mock_service
    ):
        """Test that deletion fails if prompt has active runs."""
        # Arrange
        prompt_id = "ps_test123"
        mock_service.preview_prompt_deletion.return_value = {
            "prompt": {"id": prompt_id, "prompt_text": "Test prompt"},
            "runs": [{"id": "rs_001", "status": "running"}],
            "directories_to_delete": ["outputs/run_rs_001"],
        }
        mock_service.delete_prompt.return_value = {
            "success": False,
            "error": "Cannot delete prompt with active runs",
        }
        mock_get_service.return_value = mock_service
        mock_confirm.return_value = True

        # Act
        result = runner.invoke(delete_group, ["prompt", prompt_id])

        # Assert
        assert result.exit_code == 1
        assert "Error: Cannot delete prompt with active runs" in result.output
        mock_service.delete_prompt.assert_called_once_with(prompt_id)


class TestDeleteRunCommand:
    """Test delete run command."""

    @pytest.fixture
    def runner(self):
        """Create a CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_service(self):
        """Create a mock WorkflowService."""
        return MagicMock()

    @patch("cosmos_workflow.cli.delete.get_service")
    @patch("cosmos_workflow.cli.delete.click.confirm")
    def test_delete_run_with_confirmation(
        self, mock_confirm, mock_get_service, runner, mock_service
    ):
        """Test deleting a run with user confirmation."""
        # Arrange
        run_id = "rs_test123"
        mock_service.preview_run_deletion.return_value = {
            "run": {"id": run_id, "status": "completed", "prompt_id": "ps_001"},
            "directory_to_delete": "outputs/run_rs_test123",
        }
        mock_service.delete_run.return_value = {
            "success": True,
            "deleted": {"run_id": run_id, "directory": "outputs/run_rs_test123"},
        }
        mock_get_service.return_value = mock_service
        mock_confirm.return_value = True

        # Act
        result = runner.invoke(delete_group, ["run", run_id])

        # Assert
        assert result.exit_code == 0
        assert "Preview of deletion" in result.output
        assert run_id in result.output
        assert "Successfully deleted" in result.output
        mock_service.preview_run_deletion.assert_called_once_with(run_id)
        mock_service.delete_run.assert_called_once_with(run_id)
        mock_confirm.assert_called_once()

    @patch("cosmos_workflow.cli.delete.get_service")
    @patch("cosmos_workflow.cli.delete.click.confirm")
    def test_delete_run_cancelled(self, mock_confirm, mock_get_service, runner, mock_service):
        """Test cancelling run deletion."""
        # Arrange
        run_id = "rs_test123"
        mock_service.preview_run_deletion.return_value = {
            "run": {"id": run_id, "status": "completed"},
            "directory_to_delete": "outputs/run_rs_test123",
        }
        mock_get_service.return_value = mock_service
        mock_confirm.return_value = False

        # Act
        result = runner.invoke(delete_group, ["run", run_id])

        # Assert
        assert result.exit_code == 0
        assert "Deletion cancelled" in result.output
        mock_service.preview_run_deletion.assert_called_once_with(run_id)
        mock_service.delete_run.assert_not_called()

    @patch("cosmos_workflow.cli.delete.get_service")
    def test_delete_run_with_force(self, mock_get_service, runner, mock_service):
        """Test deleting a run with --force flag."""
        # Arrange
        run_id = "rs_test123"
        mock_service.preview_run_deletion.return_value = {
            "run": {"id": run_id, "status": "completed"},
            "directory_to_delete": "outputs/run_rs_test123",
        }
        mock_service.delete_run.return_value = {
            "success": True,
            "deleted": {"run_id": run_id, "directory": "outputs/run_rs_test123"},
        }
        mock_get_service.return_value = mock_service

        # Act
        result = runner.invoke(delete_group, ["run", run_id, "--force"])

        # Assert
        assert result.exit_code == 0
        assert "Successfully deleted" in result.output
        mock_service.preview_run_deletion.assert_called_once_with(run_id)
        mock_service.delete_run.assert_called_once_with(run_id)

    @patch("cosmos_workflow.cli.delete.get_service")
    def test_delete_run_not_found(self, mock_get_service, runner, mock_service):
        """Test deleting a non-existent run."""
        # Arrange
        run_id = "rs_nonexistent"
        mock_service.preview_run_deletion.return_value = {
            "run": None,
            "directory_to_delete": None,
            "error": "Run not found",
        }
        mock_get_service.return_value = mock_service

        # Act
        result = runner.invoke(delete_group, ["run", run_id])

        # Assert
        assert result.exit_code == 1
        assert "Error: Run not found" in result.output
        mock_service.delete_run.assert_not_called()

    @patch("cosmos_workflow.cli.delete.get_service")
    @patch("cosmos_workflow.cli.delete.click.confirm")
    def test_delete_run_with_active_status(
        self, mock_confirm, mock_get_service, runner, mock_service
    ):
        """Test that deletion fails if run is active."""
        # Arrange
        run_id = "rs_test123"
        mock_service.preview_run_deletion.return_value = {
            "run": {"id": run_id, "status": "running"},
            "directory_to_delete": "outputs/run_rs_test123",
        }
        mock_service.delete_run.return_value = {
            "success": False,
            "error": "Cannot delete run with status 'running'",
        }
        mock_get_service.return_value = mock_service
        mock_confirm.return_value = True

        # Act
        result = runner.invoke(delete_group, ["run", run_id])

        # Assert
        assert result.exit_code == 1
        assert "Error: Cannot delete run with status 'running'" in result.output
        mock_service.delete_run.assert_called_once_with(run_id)

    @patch("cosmos_workflow.cli.delete.get_service")
    @patch("cosmos_workflow.cli.delete.click.confirm")
    def test_delete_run_with_warnings(self, mock_confirm, mock_get_service, runner, mock_service):
        """Test deletion that succeeds with warnings."""
        # Arrange
        run_id = "rs_test123"
        mock_service.preview_run_deletion.return_value = {
            "run": {"id": run_id, "status": "completed"},
            "directory_to_delete": "outputs/run_rs_test123",
        }
        mock_service.delete_run.return_value = {
            "success": True,
            "deleted": {"run_id": run_id, "directory": "outputs/run_rs_test123"},
            "warnings": ["Could not delete directory due to permission error"],
        }
        mock_get_service.return_value = mock_service
        mock_confirm.return_value = True

        # Act
        result = runner.invoke(delete_group, ["run", run_id])

        # Assert
        assert result.exit_code == 0
        assert "Successfully deleted" in result.output
        assert "Warning:" in result.output
        assert "permission error" in result.output
