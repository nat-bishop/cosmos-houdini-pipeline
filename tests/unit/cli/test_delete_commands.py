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
    def mock_operations(self):
        """Create a mock WorkflowOperations."""
        return MagicMock()

    @patch("cosmos_workflow.cli.delete.get_operations")
    @patch("cosmos_workflow.cli.delete.click.confirm")
    def test_delete_prompt_with_confirmation(
        self, mock_confirm, mock_get_operations, runner, mock_operations
    ):
        """Test deleting a prompt with user confirmation."""
        # Arrange
        prompt_id = "ps_test123"
        mock_operations.preview_prompt_deletion.return_value = {
            "prompt": {"id": prompt_id, "prompt_text": "Test prompt"},
            "runs": [{"id": "rs_001"}, {"id": "rs_002"}],
            "directories_to_delete": ["outputs/run_rs_001", "outputs/run_rs_002"],
        }
        mock_operations.delete_prompt.return_value = {
            "success": True,
            "deleted": {
                "prompt_id": prompt_id,
                "run_ids": ["rs_001", "rs_002"],
                "directories": ["outputs/run_rs_001", "outputs/run_rs_002"],
            },
        }
        mock_get_operations.return_value = mock_operations
        mock_confirm.return_value = True

        # Act
        result = runner.invoke(delete_group, ["prompt", prompt_id])

        # Assert
        assert result.exit_code == 0
        assert "Preview of deletion" in result.output
        assert "Test prompt" in result.output
        assert "2 run(s)" in result.output
        assert "Successfully deleted" in result.output
        mock_operations.preview_prompt_deletion.assert_called_once_with(
            prompt_id, keep_outputs=True
        )
        mock_operations.delete_prompt.assert_called_once_with(prompt_id, keep_outputs=True)
        mock_confirm.assert_called_once()

    @patch("cosmos_workflow.cli.delete.get_operations")
    @patch("cosmos_workflow.cli.delete.click.confirm")
    def test_delete_prompt_cancelled(
        self, mock_confirm, mock_get_operations, runner, mock_operations
    ):
        """Test cancelling prompt deletion."""
        # Arrange
        prompt_id = "ps_test123"
        mock_operations.preview_prompt_deletion.return_value = {
            "prompt": {"id": prompt_id, "prompt_text": "Test prompt"},
            "runs": [],
            "directories_to_delete": [],
        }
        mock_get_operations.return_value = mock_operations
        mock_confirm.return_value = False

        # Act
        result = runner.invoke(delete_group, ["prompt", prompt_id])

        # Assert
        assert result.exit_code == 0
        assert "Deletion cancelled" in result.output
        mock_operations.preview_prompt_deletion.assert_called_once_with(
            prompt_id, keep_outputs=True
        )
        mock_operations.delete_prompt.assert_not_called()

    @patch("cosmos_workflow.cli.delete.get_operations")
    def test_delete_prompt_with_force(self, mock_get_operations, runner, mock_operations):
        """Test deleting a prompt with --force flag."""
        # Arrange
        prompt_id = "ps_test123"
        mock_operations.preview_prompt_deletion.return_value = {
            "prompt": {"id": prompt_id, "prompt_text": "Test prompt"},
            "runs": [],
            "directories_to_delete": [],
        }
        mock_operations.delete_prompt.return_value = {
            "success": True,
            "deleted": {"prompt_id": prompt_id, "run_ids": [], "directories": []},
        }
        mock_get_operations.return_value = mock_operations

        # Act
        result = runner.invoke(delete_group, ["prompt", prompt_id, "--force"])

        # Assert
        assert result.exit_code == 0
        assert "Successfully deleted" in result.output
        mock_operations.preview_prompt_deletion.assert_called_once_with(
            prompt_id, keep_outputs=True
        )
        mock_operations.delete_prompt.assert_called_once_with(prompt_id, keep_outputs=True)

    @patch("cosmos_workflow.cli.delete.get_operations")
    def test_delete_prompt_not_found(self, mock_get_operations, runner, mock_operations):
        """Test deleting a non-existent prompt."""
        # Arrange
        prompt_id = "ps_nonexistent"
        mock_operations.preview_prompt_deletion.return_value = {
            "prompt": None,
            "runs": [],
            "directories_to_delete": [],
            "error": "Prompt not found",
        }
        mock_get_operations.return_value = mock_operations

        # Act
        result = runner.invoke(delete_group, ["prompt", prompt_id])

        # Assert
        assert result.exit_code == 1
        assert "Error: Prompt not found" in result.output
        mock_operations.delete_prompt.assert_not_called()

    @patch("cosmos_workflow.cli.delete.get_operations")
    @patch("cosmos_workflow.cli.delete.click.confirm")
    def test_delete_prompt_with_active_runs(
        self, mock_confirm, mock_get_operations, runner, mock_operations
    ):
        """Test that deletion shows warning for active runs but proceeds."""
        # Arrange
        prompt_id = "ps_test123"
        mock_operations.preview_prompt_deletion.return_value = {
            "prompt": {"id": prompt_id, "prompt_text": "Test prompt"},
            "runs": [{"id": "rs_001", "status": "running"}],
            "directories_to_delete": ["outputs/run_rs_001"],
        }
        mock_operations.delete_prompt.return_value = {
            "success": True,
            "deleted": {
                "prompt_id": prompt_id,
                "run_ids": ["rs_001"],
                "directories": ["outputs/run_rs_001"],
            },
        }
        mock_get_operations.return_value = mock_operations
        mock_confirm.return_value = True

        # Act
        result = runner.invoke(delete_group, ["prompt", prompt_id])

        # Assert
        assert result.exit_code == 0
        assert "WARNING: 1 ACTIVE RUNS WILL BE DELETED!" in result.output
        assert "Successfully deleted" in result.output
        mock_operations.delete_prompt.assert_called_once_with(prompt_id, keep_outputs=True)


class TestDeleteRunCommand:
    """Test delete run command."""

    @pytest.fixture
    def runner(self):
        """Create a CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_operations(self):
        """Create a mock WorkflowOperations."""
        return MagicMock()

    @patch("cosmos_workflow.cli.delete.get_operations")
    @patch("cosmos_workflow.cli.delete.click.confirm")
    def test_delete_run_with_confirmation(
        self, mock_confirm, mock_get_operations, runner, mock_operations
    ):
        """Test deleting a run with user confirmation."""
        # Arrange
        run_id = "rs_test123"
        mock_operations.preview_run_deletion.return_value = {
            "run": {"id": run_id, "status": "completed", "prompt_id": "ps_001"},
            "directory_to_delete": "outputs/run_rs_test123",
        }
        mock_operations.delete_run.return_value = {
            "success": True,
            "deleted": {"run_id": run_id, "directory": "outputs/run_rs_test123"},
        }
        mock_get_operations.return_value = mock_operations
        mock_confirm.return_value = True

        # Act
        result = runner.invoke(delete_group, ["run", run_id])

        # Assert
        assert result.exit_code == 0
        assert "Preview of deletion" in result.output
        assert run_id in result.output
        assert "Successfully deleted" in result.output
        mock_operations.preview_run_deletion.assert_called_once_with(run_id, keep_outputs=True)
        mock_operations.delete_run.assert_called_once_with(run_id, keep_outputs=True)
        mock_confirm.assert_called_once()

    @patch("cosmos_workflow.cli.delete.get_operations")
    @patch("cosmos_workflow.cli.delete.click.confirm")
    def test_delete_run_cancelled(self, mock_confirm, mock_get_operations, runner, mock_operations):
        """Test cancelling run deletion."""
        # Arrange
        run_id = "rs_test123"
        mock_operations.preview_run_deletion.return_value = {
            "run": {"id": run_id, "status": "completed"},
            "directory_to_delete": "outputs/run_rs_test123",
        }
        mock_get_operations.return_value = mock_operations
        mock_confirm.return_value = False

        # Act
        result = runner.invoke(delete_group, ["run", run_id])

        # Assert
        assert result.exit_code == 0
        assert "Deletion cancelled" in result.output
        mock_operations.preview_run_deletion.assert_called_once_with(run_id, keep_outputs=True)
        mock_operations.delete_run.assert_not_called()

    @patch("cosmos_workflow.cli.delete.get_operations")
    def test_delete_run_with_force(self, mock_get_operations, runner, mock_operations):
        """Test deleting a run with --force flag."""
        # Arrange
        run_id = "rs_test123"
        mock_operations.preview_run_deletion.return_value = {
            "run": {"id": run_id, "status": "completed"},
            "directory_to_delete": "outputs/run_rs_test123",
        }
        mock_operations.delete_run.return_value = {
            "success": True,
            "deleted": {"run_id": run_id, "directory": "outputs/run_rs_test123"},
        }
        mock_get_operations.return_value = mock_operations

        # Act
        result = runner.invoke(delete_group, ["run", run_id, "--force"])

        # Assert
        assert result.exit_code == 0
        assert "Successfully deleted" in result.output
        mock_operations.preview_run_deletion.assert_called_once_with(run_id, keep_outputs=True)
        mock_operations.delete_run.assert_called_once_with(run_id, keep_outputs=True)

    @patch("cosmos_workflow.cli.delete.get_operations")
    def test_delete_run_not_found(self, mock_get_operations, runner, mock_operations):
        """Test deleting a non-existent run."""
        # Arrange
        run_id = "rs_nonexistent"
        mock_operations.preview_run_deletion.return_value = {
            "run": None,
            "directory_to_delete": None,
            "error": "Run not found",
        }
        mock_get_operations.return_value = mock_operations

        # Act
        result = runner.invoke(delete_group, ["run", run_id])

        # Assert
        assert result.exit_code == 1
        assert "Error: Run not found" in result.output
        mock_operations.delete_run.assert_not_called()

    @patch("cosmos_workflow.cli.delete.get_operations")
    @patch("cosmos_workflow.cli.delete.click.confirm")
    def test_delete_run_with_active_status(
        self, mock_confirm, mock_get_operations, runner, mock_operations
    ):
        """Test that deletion shows warning for active run but proceeds."""
        # Arrange
        run_id = "rs_test123"
        mock_operations.preview_run_deletion.return_value = {
            "run": {"id": run_id, "status": "running"},
            "directory_to_delete": "outputs/run_rs_test123",
        }
        mock_operations.delete_run.return_value = {
            "success": True,
            "deleted": {"run_id": run_id, "directory": "outputs/run_rs_test123"},
        }
        mock_get_operations.return_value = mock_operations
        mock_confirm.return_value = True

        # Act
        result = runner.invoke(delete_group, ["run", run_id])

        # Assert
        assert result.exit_code == 0
        assert "WARNING: THIS RUN IS CURRENTLY ACTIVE!" in result.output
        assert "Successfully deleted" in result.output
        mock_operations.delete_run.assert_called_once_with(run_id, keep_outputs=True)

    @patch("cosmos_workflow.cli.delete.get_operations")
    @patch("cosmos_workflow.cli.delete.click.confirm")
    def test_delete_run_with_warnings(
        self, mock_confirm, mock_get_operations, runner, mock_operations
    ):
        """Test deletion that succeeds with warnings."""
        # Arrange
        run_id = "rs_test123"
        mock_operations.preview_run_deletion.return_value = {
            "run": {"id": run_id, "status": "completed"},
            "directory_to_delete": "outputs/run_rs_test123",
        }
        mock_operations.delete_run.return_value = {
            "success": True,
            "deleted": {"run_id": run_id, "directory": "outputs/run_rs_test123"},
            "warnings": ["Could not delete directory due to permission error"],
        }
        mock_get_operations.return_value = mock_operations
        mock_confirm.return_value = True

        # Act
        result = runner.invoke(delete_group, ["run", run_id])

        # Assert
        assert result.exit_code == 0
        assert "Successfully deleted" in result.output
        assert "Warning:" in result.output
        assert "permission error" in result.output


class TestDeletePromptWithKeepOutputs:
    """Test delete prompt command with --keep-outputs flag."""

    @pytest.fixture
    def runner(self):
        """Create a CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_operations(self):
        """Create a mock WorkflowOperations."""
        return MagicMock()

    @patch("cosmos_workflow.cli.delete.get_operations")
    def test_delete_prompt_keeps_outputs_by_default(
        self, mock_get_operations, runner, mock_operations
    ):
        """Test that outputs are kept by default when deleting a prompt."""
        # Arrange
        prompt_id = "ps_test123"
        mock_operations.preview_prompt_deletion.return_value = {
            "prompt": {"id": prompt_id, "prompt_text": "Test prompt"},
            "runs": [{"id": "rs_001"}, {"id": "rs_002"}],
            "directories_to_delete": [],  # No directories to delete when keeping outputs
            "keep_outputs": True,
        }
        mock_operations.delete_prompt.return_value = {
            "success": True,
            "deleted": {
                "prompt_id": prompt_id,
                "run_ids": ["rs_001", "rs_002"],
                "directories": [],  # No directories deleted
            },
        }
        mock_get_operations.return_value = mock_operations

        # Act
        result = runner.invoke(delete_group, ["prompt", prompt_id, "--force"])

        # Assert
        assert result.exit_code == 0
        assert "Output files: KEPT" in result.output
        assert "Successfully deleted" in result.output
        # Should call delete_prompt with keep_outputs=True (default)
        mock_operations.delete_prompt.assert_called_once_with(prompt_id, keep_outputs=True)

    @patch("cosmos_workflow.cli.delete.get_operations")
    def test_delete_prompt_with_delete_outputs(self, mock_get_operations, runner, mock_operations):
        """Test deleting a prompt with --delete-outputs flag."""
        # Arrange
        prompt_id = "ps_test123"
        mock_operations.preview_prompt_deletion.return_value = {
            "prompt": {"id": prompt_id, "prompt_text": "Test prompt"},
            "runs": [{"id": "rs_001"}, {"id": "rs_002"}],
            "directories_to_delete": ["outputs/run_rs_001", "outputs/run_rs_002"],
            "keep_outputs": False,
        }
        mock_operations.delete_prompt.return_value = {
            "success": True,
            "deleted": {
                "prompt_id": prompt_id,
                "run_ids": ["rs_001", "rs_002"],
                "directories": ["outputs/run_rs_001", "outputs/run_rs_002"],
            },
        }
        mock_get_operations.return_value = mock_operations

        # Act
        result = runner.invoke(delete_group, ["prompt", prompt_id, "--delete-outputs", "--force"])

        # Assert
        assert result.exit_code == 0
        assert "Output directories to delete:" in result.output
        assert "outputs/run_rs_001" in result.output
        assert "Successfully deleted" in result.output
        mock_operations.delete_prompt.assert_called_once_with(prompt_id, keep_outputs=False)


class TestDeleteRunWithKeepOutputs:
    """Test delete run command with --keep-outputs flag."""

    @pytest.fixture
    def runner(self):
        """Create a CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_operations(self):
        """Create a mock WorkflowOperations."""
        return MagicMock()

    @patch("cosmos_workflow.cli.delete.get_operations")
    def test_delete_run_keeps_outputs_by_default(
        self, mock_get_operations, runner, mock_operations
    ):
        """Test that outputs are kept by default when deleting a run."""
        # Arrange
        run_id = "rs_test123"
        mock_operations.preview_run_deletion.return_value = {
            "run": {"id": run_id, "status": "completed", "prompt_id": "ps_001"},
            "directory_to_delete": None,  # No directory to delete when keeping outputs
            "keep_outputs": True,
        }
        mock_operations.delete_run.return_value = {
            "success": True,
            "deleted": {"run_id": run_id, "directory": None},
        }
        mock_get_operations.return_value = mock_operations

        # Act
        result = runner.invoke(delete_group, ["run", run_id, "--force"])

        # Assert
        assert result.exit_code == 0
        assert "Output files: KEPT" in result.output
        assert "Successfully deleted" in result.output
        mock_operations.delete_run.assert_called_once_with(run_id, keep_outputs=True)

    @patch("cosmos_workflow.cli.delete.get_operations")
    def test_delete_run_with_delete_outputs(self, mock_get_operations, runner, mock_operations):
        """Test deleting a run with --delete-outputs flag."""
        # Arrange
        run_id = "rs_test123"
        mock_operations.preview_run_deletion.return_value = {
            "run": {"id": run_id, "status": "completed", "prompt_id": "ps_001"},
            "directory_to_delete": "outputs/run_rs_test123",
            "keep_outputs": False,
        }
        mock_operations.delete_run.return_value = {
            "success": True,
            "deleted": {"run_id": run_id, "directory": "outputs/run_rs_test123"},
        }
        mock_get_operations.return_value = mock_operations

        # Act
        result = runner.invoke(delete_group, ["run", run_id, "--delete-outputs", "--force"])

        # Assert
        assert result.exit_code == 0
        assert "Output directory to delete:" in result.output
        assert "outputs/run_rs_test123" in result.output
        assert "Successfully deleted" in result.output
        mock_operations.delete_run.assert_called_once_with(run_id, keep_outputs=False)


class TestBulkDeletion:
    """Test bulk deletion with --all flag."""

    @pytest.fixture
    def runner(self):
        """Create a CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_operations(self):
        """Create a mock WorkflowOperations."""
        return MagicMock()

    @patch("cosmos_workflow.cli.delete.get_operations")
    @patch("cosmos_workflow.cli.delete.click.prompt")
    def test_delete_all_runs(self, mock_prompt, mock_get_operations, runner, mock_operations):
        """Test deleting all runs with --all flag."""
        # Arrange
        mock_operations.preview_all_runs_deletion.return_value = {
            "runs": [
                {"id": "rs_001", "status": "completed"},
                {"id": "rs_002", "status": "failed"},
                {"id": "rs_003", "status": "completed"},
            ],
            "total_count": 3,
            "total_size": "1.5 GB",
            "directories_to_delete": [
                "outputs/run_rs_001",
                "outputs/run_rs_002",
                "outputs/run_rs_003",
            ],
        }
        mock_operations.delete_all_runs.return_value = {
            "success": True,
            "deleted": {
                "run_ids": ["rs_001", "rs_002", "rs_003"],
                "directories": ["outputs/run_rs_001", "outputs/run_rs_002", "outputs/run_rs_003"],
            },
        }
        mock_get_operations.return_value = mock_operations
        mock_prompt.return_value = "DELETE ALL"

        # Act
        result = runner.invoke(delete_group, ["run", "--all"])

        # Assert
        assert result.exit_code == 0
        assert "This will delete ALL 3 runs" in result.output
        assert "Total output size: 1.5 GB" in result.output
        assert "Successfully deleted 3 run(s)" in result.output
        mock_operations.preview_all_runs_deletion.assert_called_once()
        mock_operations.delete_all_runs.assert_called_once_with(keep_outputs=True)
        mock_prompt.assert_called_once_with("Type 'DELETE ALL' to confirm")

    @patch("cosmos_workflow.cli.delete.get_operations")
    def test_delete_all_runs_with_force(self, mock_get_operations, runner, mock_operations):
        """Test deleting all runs with --all --force flags."""
        # Arrange
        mock_operations.preview_all_runs_deletion.return_value = {
            "runs": [{"id": "rs_001"}, {"id": "rs_002"}],
            "total_count": 2,
            "total_size": "500 MB",
            "directories_to_delete": [],
        }
        mock_operations.delete_all_runs.return_value = {
            "success": True,
            "deleted": {"run_ids": ["rs_001", "rs_002"], "directories": []},
        }
        mock_get_operations.return_value = mock_operations

        # Act
        result = runner.invoke(delete_group, ["run", "--all", "--force"])

        # Assert
        assert result.exit_code == 0
        assert "Successfully deleted 2 run(s)" in result.output
        mock_operations.delete_all_runs.assert_called_once_with(keep_outputs=True)

    @patch("cosmos_workflow.cli.delete.get_operations")
    @patch("cosmos_workflow.cli.delete.click.prompt")
    def test_delete_all_runs_cancelled(
        self, mock_prompt, mock_get_operations, runner, mock_operations
    ):
        """Test cancelling bulk deletion when confirmation doesn't match."""
        # Arrange
        mock_operations.preview_all_runs_deletion.return_value = {
            "runs": [{"id": "rs_001"}],
            "total_count": 1,
            "total_size": "100 MB",
        }
        mock_get_operations.return_value = mock_operations
        mock_prompt.return_value = "no"  # Wrong confirmation

        # Act
        result = runner.invoke(delete_group, ["run", "--all"])

        # Assert
        assert result.exit_code == 0
        assert "Deletion cancelled" in result.output
        mock_operations.delete_all_runs.assert_not_called()

    @patch("cosmos_workflow.cli.delete.get_operations")
    def test_delete_all_runs_empty(self, mock_get_operations, runner, mock_operations):
        """Test deleting all runs when there are none."""
        # Arrange
        mock_operations.preview_all_runs_deletion.return_value = {
            "runs": [],
            "total_count": 0,
            "error": "No runs found",
        }
        mock_get_operations.return_value = mock_operations

        # Act
        result = runner.invoke(delete_group, ["run", "--all"])

        # Assert
        assert result.exit_code == 0
        assert "No runs found to delete" in result.output
        mock_operations.delete_all_runs.assert_not_called()

    @patch("cosmos_workflow.cli.delete.get_operations")
    @patch("cosmos_workflow.cli.delete.click.prompt")
    def test_delete_all_prompts(self, mock_prompt, mock_get_operations, runner, mock_operations):
        """Test deleting all prompts with --all flag."""
        # Arrange
        mock_operations.preview_all_prompts_deletion.return_value = {
            "prompts": [
                {"id": "ps_001", "prompt_text": "Prompt 1"},
                {"id": "ps_002", "prompt_text": "Prompt 2"},
            ],
            "total_prompt_count": 2,
            "total_run_count": 5,
            "total_size": "2.5 GB",
        }
        mock_operations.delete_all_prompts.return_value = {
            "success": True,
            "deleted": {
                "prompt_ids": ["ps_001", "ps_002"],
                "run_ids": ["rs_001", "rs_002", "rs_003", "rs_004", "rs_005"],
                "directories": [],
            },
        }
        mock_get_operations.return_value = mock_operations
        mock_prompt.return_value = "DELETE ALL"

        # Act
        result = runner.invoke(delete_group, ["prompt", "--all"])

        # Assert
        assert result.exit_code == 0
        assert "This will delete ALL 2 prompts" in result.output
        assert "and 5 associated runs" in result.output
        assert "Successfully deleted 2 prompt(s)" in result.output
        mock_operations.preview_all_prompts_deletion.assert_called_once()
        mock_operations.delete_all_prompts.assert_called_once_with(keep_outputs=True)

    @patch("cosmos_workflow.cli.delete.get_operations")
    def test_cannot_use_all_with_id(self, mock_get_operations, runner, mock_operations):
        """Test that --all and ID are mutually exclusive."""
        # Act
        result = runner.invoke(delete_group, ["run", "rs_123", "--all"])

        # Assert
        assert result.exit_code == 2
        assert "Cannot specify both a run ID and --all" in result.output


class TestEnhancedFilePreview:
    """Test enhanced file preview functionality."""

    @pytest.fixture
    def runner(self):
        """Create a CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_operations(self):
        """Create a mock WorkflowOperations."""
        return MagicMock()

    @patch("cosmos_workflow.cli.delete.get_operations")
    @patch("cosmos_workflow.cli.delete.click.confirm")
    def test_enhanced_file_preview_for_run(
        self, mock_confirm, mock_get_operations, runner, mock_operations
    ):
        """Test that file preview shows detailed file information."""
        # Arrange
        run_id = "rs_test123"
        mock_operations.preview_run_deletion.return_value = {
            "run": {"id": run_id, "status": "completed", "prompt_id": "ps_001"},
            "directory_to_delete": "outputs/run_rs_test123",
            "keep_outputs": False,
            "files": {
                "video": {
                    "count": 3,
                    "total_size": "1.2 GB",
                    "files": [
                        {"name": "output_0001.mp4", "size": "400 MB"},
                        {"name": "output_0002.mp4", "size": "410 MB"},
                        {"name": "output_0003.mp4", "size": "390 MB"},
                    ],
                },
                "json": {
                    "count": 2,
                    "total_size": "15 KB",
                    "files": [
                        {"name": "metadata.json", "size": "10 KB"},
                        {"name": "config.json", "size": "5 KB"},
                    ],
                },
            },
            "total_files": 5,
            "total_size": "1.2 GB",
        }
        mock_operations.delete_run.return_value = {
            "success": True,
            "deleted": {"run_id": run_id, "directory": "outputs/run_rs_test123"},
        }
        mock_get_operations.return_value = mock_operations
        mock_confirm.return_value = True

        # Act
        result = runner.invoke(delete_group, ["run", run_id, "--delete-outputs"])

        # Assert
        assert result.exit_code == 0
        assert "Output directory: outputs/run_rs_test123" in result.output
        assert "3 video files (1.2 GB)" in result.output
        assert "output_0001.mp4 (400 MB)" in result.output
        assert "2 json files (15 KB)" in result.output
        assert "Total: 5 files (1.2 GB)" in result.output

    @patch("cosmos_workflow.cli.delete.get_operations")
    @patch("cosmos_workflow.cli.delete.click.confirm")
    def test_enhanced_file_preview_for_prompt(
        self, mock_confirm, mock_get_operations, runner, mock_operations
    ):
        """Test that file preview works for prompt deletion."""
        # Arrange
        prompt_id = "ps_test123"
        mock_operations.preview_prompt_deletion.return_value = {
            "prompt": {"id": prompt_id, "prompt_text": "Test prompt"},
            "runs": [{"id": "rs_001"}, {"id": "rs_002"}],
            "directories_to_delete": ["outputs/run_rs_001", "outputs/run_rs_002"],
            "keep_outputs": False,
            "files_summary": {
                "total_files": 10,
                "total_size": "2.5 GB",
                "by_type": {
                    "video": {"count": 6, "size": "2.4 GB"},
                    "json": {"count": 4, "size": "100 MB"},
                },
            },
        }
        mock_operations.delete_prompt.return_value = {
            "success": True,
            "deleted": {
                "prompt_id": prompt_id,
                "run_ids": ["rs_001", "rs_002"],
                "directories": ["outputs/run_rs_001", "outputs/run_rs_002"],
            },
        }
        mock_get_operations.return_value = mock_operations
        mock_confirm.return_value = True

        # Act
        result = runner.invoke(delete_group, ["prompt", prompt_id, "--delete-outputs"])

        # Assert
        assert result.exit_code == 0
        assert "Total files to delete: 10 files (2.5 GB)" in result.output
        assert "6 video files (2.4 GB)" in result.output
        assert "4 json files (100 MB)" in result.output
