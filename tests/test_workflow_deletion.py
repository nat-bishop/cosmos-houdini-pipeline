"""Tests for workflow deletion functionality.

Tests preview and deletion operations for prompts and runs,
including cascade behavior and file cleanup.
"""

from unittest.mock import patch

import pytest

from cosmos_workflow.config.config_manager import ConfigManager
from cosmos_workflow.database import DatabaseConnection
from cosmos_workflow.services.data_repository import DataRepository


@pytest.fixture
def temp_db():
    """Create an in-memory test database."""
    db = DatabaseConnection(":memory:")
    db.create_tables()
    return db


@pytest.fixture
def config_manager():
    """Create a real configuration manager for testing."""
    return ConfigManager()


@pytest.fixture
def workflow_service(temp_db, config_manager):
    """Create a workflow service instance for testing."""
    return DataRepository(temp_db, config_manager)


@pytest.fixture
def sample_prompt_data():
    """Sample prompt data for testing."""
    return {
        "model_type": "transfer",
        "prompt_text": "Test prompt for deletion",
        "inputs": {"video_path": "/test/video.mp4"},
        "parameters": {"num_steps": 30, "cfg_scale": 7.5},
    }


@pytest.fixture
def sample_run_data():
    """Sample run data for testing."""
    return {
        "execution_config": {"gpu_node": "test-node", "docker_image": "test:latest"},
        "metadata": {"user": "test_user", "session": "test_session"},
    }


class TestPromptDeletion:
    """Test prompt deletion functionality."""

    def test_preview_prompt_deletion_shows_associated_runs(
        self, workflow_service, sample_prompt_data, sample_run_data
    ):
        """Test that preview shows all runs that will be deleted."""
        # Create prompt and multiple runs
        prompt = workflow_service.create_prompt(**sample_prompt_data)
        prompt_id = prompt["id"]

        run1 = workflow_service.create_run(prompt_id, **sample_run_data)
        run2 = workflow_service.create_run(prompt_id, **sample_run_data)

        # Preview deletion
        preview = workflow_service.preview_prompt_deletion(prompt_id)

        # Check preview contains correct information
        assert preview["prompt"]["id"] == prompt_id
        assert preview["prompt"]["prompt_text"] == sample_prompt_data["prompt_text"]
        assert len(preview["runs"]) == 2
        assert {run["id"] for run in preview["runs"]} == {run1["id"], run2["id"]}
        assert len(preview["directories_to_delete"]) == 2

    def test_preview_prompt_deletion_nonexistent_prompt(self, workflow_service):
        """Test preview with non-existent prompt ID."""
        preview = workflow_service.preview_prompt_deletion("ps_nonexistent")

        assert preview["error"] == "Prompt not found"
        assert preview["prompt"] is None
        assert preview["runs"] == []
        assert preview["directories_to_delete"] == []

    def test_delete_prompt_removes_from_database(
        self, workflow_service, sample_prompt_data, sample_run_data
    ):
        """Test that deleting prompt removes it and all runs from database."""
        # Create prompt and runs
        prompt = workflow_service.create_prompt(**sample_prompt_data)
        prompt_id = prompt["id"]

        run1 = workflow_service.create_run(prompt_id, **sample_run_data)
        run2 = workflow_service.create_run(prompt_id, **sample_run_data)

        # Delete prompt
        result = workflow_service.delete_prompt(prompt_id)

        # Verify deletion
        assert result["success"] is True
        assert result["deleted"]["prompt_id"] == prompt_id
        assert len(result["deleted"]["run_ids"]) == 2

        # Verify prompt and runs are gone
        assert workflow_service.get_prompt(prompt_id) is None
        assert workflow_service.get_run(run1["id"]) is None
        assert workflow_service.get_run(run2["id"]) is None

    def test_delete_prompt_removes_output_directories(
        self, workflow_service, sample_prompt_data, sample_run_data, tmp_path
    ):
        """Test that deleting prompt removes all output directories."""
        # Create prompt and runs
        prompt = workflow_service.create_prompt(**sample_prompt_data)
        prompt_id = prompt["id"]

        run1 = workflow_service.create_run(prompt_id, **sample_run_data)
        run2 = workflow_service.create_run(prompt_id, **sample_run_data)

        # Create mock output directories
        output_dir1 = tmp_path / "outputs" / f"run_{run1['id']}"
        output_dir2 = tmp_path / "outputs" / f"run_{run2['id']}"
        output_dir1.mkdir(parents=True)
        output_dir2.mkdir(parents=True)

        # Get the actual outputs directory from config
        outputs_dir = workflow_service.config.get_local_config().outputs_dir

        # Delete prompt
        result = workflow_service.delete_prompt(prompt_id)

        # Verify directories were attempted to be removed
        # Note: Using actual outputs directory from config
        expected_dirs = [
            str(outputs_dir / f"run_{run1['id']}"),
            str(outputs_dir / f"run_{run2['id']}"),
        ]
        assert set(result["deleted"]["directories"]) == set(expected_dirs)

    def test_delete_prompt_nonexistent(self, workflow_service):
        """Test deleting non-existent prompt."""
        result = workflow_service.delete_prompt("ps_nonexistent")

        assert result["success"] is False
        assert result["error"] == "Prompt not found"

    def test_delete_prompt_with_running_run_fails(
        self, workflow_service, sample_prompt_data, sample_run_data
    ):
        """Test that deleting prompt with running run fails by default."""
        # Create prompt and running run
        prompt = workflow_service.create_prompt(**sample_prompt_data)
        prompt_id = prompt["id"]

        run = workflow_service.create_run(prompt_id, **sample_run_data)
        workflow_service.update_run_status(run["id"], "running")

        # Attempt deletion
        result = workflow_service.delete_prompt(prompt_id)

        assert result["success"] is False
        assert "running" in result["error"].lower()

        # Verify nothing was deleted
        assert workflow_service.get_prompt(prompt_id) is not None
        assert workflow_service.get_run(run["id"]) is not None


class TestRunDeletion:
    """Test run deletion functionality."""

    def test_preview_run_deletion_shows_details(
        self, workflow_service, sample_prompt_data, sample_run_data
    ):
        """Test that preview shows run details and output directory."""
        # Create prompt and run
        prompt = workflow_service.create_prompt(**sample_prompt_data)
        run = workflow_service.create_run(prompt["id"], **sample_run_data)
        run_id = run["id"]

        # Preview deletion
        preview = workflow_service.preview_run_deletion(run_id)

        # Check preview contains correct information
        assert preview["run"]["id"] == run_id
        assert preview["run"]["prompt_id"] == prompt["id"]
        # Use Path to handle OS-specific separators
        from pathlib import Path

        expected_dir = str(Path("outputs") / f"run_{run_id}")
        assert preview["directory_to_delete"] == expected_dir

    def test_preview_run_deletion_nonexistent(self, workflow_service):
        """Test preview with non-existent run ID."""
        preview = workflow_service.preview_run_deletion("rs_nonexistent")

        assert preview["error"] == "Run not found"
        assert preview["run"] is None
        assert preview["directory_to_delete"] is None

    def test_delete_run_removes_from_database(
        self, workflow_service, sample_prompt_data, sample_run_data
    ):
        """Test that deleting run removes it but keeps prompt."""
        # Create prompt and run
        prompt = workflow_service.create_prompt(**sample_prompt_data)
        prompt_id = prompt["id"]
        run = workflow_service.create_run(prompt_id, **sample_run_data)
        run_id = run["id"]

        # Delete run
        result = workflow_service.delete_run(run_id)

        # Verify deletion
        assert result["success"] is True
        assert result["deleted"]["run_id"] == run_id

        # Verify run is gone but prompt remains
        assert workflow_service.get_run(run_id) is None
        assert workflow_service.get_prompt(prompt_id) is not None

    def test_delete_run_removes_output_directory(
        self, workflow_service, sample_prompt_data, sample_run_data, tmp_path
    ):
        """Test that deleting run removes its output directory."""
        # Create prompt and run
        prompt = workflow_service.create_prompt(**sample_prompt_data)
        run = workflow_service.create_run(prompt["id"], **sample_run_data)
        run_id = run["id"]

        # Create mock output directory
        output_dir = tmp_path / "outputs" / f"run_{run_id}"
        output_dir.mkdir(parents=True)

        # Get the actual outputs directory from config
        outputs_dir = workflow_service.config.get_local_config().outputs_dir

        # Delete run
        result = workflow_service.delete_run(run_id)

        # Verify directory was removed
        assert result["deleted"]["directory"] == str(outputs_dir / f"run_{run_id}")

    def test_delete_run_nonexistent(self, workflow_service):
        """Test deleting non-existent run."""
        result = workflow_service.delete_run("rs_nonexistent")

        assert result["success"] is False
        assert result["error"] == "Run not found"

    def test_delete_run_with_running_status_fails(
        self, workflow_service, sample_prompt_data, sample_run_data
    ):
        """Test that deleting running run fails by default."""
        # Create prompt and run
        prompt = workflow_service.create_prompt(**sample_prompt_data)
        run = workflow_service.create_run(prompt["id"], **sample_run_data)
        workflow_service.update_run_status(run["id"], "running")

        # Attempt deletion
        result = workflow_service.delete_run(run["id"])

        assert result["success"] is False
        assert "running" in result["error"].lower()

        # Verify run still exists
        assert workflow_service.get_run(run["id"]) is not None

    def test_delete_multiple_runs_independently(
        self, workflow_service, sample_prompt_data, sample_run_data
    ):
        """Test deleting one run doesn't affect others."""
        # Create prompt and multiple runs
        prompt = workflow_service.create_prompt(**sample_prompt_data)
        prompt_id = prompt["id"]

        run1 = workflow_service.create_run(prompt_id, **sample_run_data)
        run2 = workflow_service.create_run(prompt_id, **sample_run_data)
        run3 = workflow_service.create_run(prompt_id, **sample_run_data)

        # Delete only run2
        result = workflow_service.delete_run(run2["id"])

        assert result["success"] is True

        # Verify run2 is gone but others remain
        assert workflow_service.get_run(run1["id"]) is not None
        assert workflow_service.get_run(run2["id"]) is None
        assert workflow_service.get_run(run3["id"]) is not None
        assert workflow_service.get_prompt(prompt_id) is not None


class TestDeletionEdgeCases:
    """Test edge cases and error handling in deletion."""

    def test_delete_prompt_with_no_runs(self, workflow_service, sample_prompt_data):
        """Test deleting prompt that has no runs."""
        prompt = workflow_service.create_prompt(**sample_prompt_data)
        prompt_id = prompt["id"]

        result = workflow_service.delete_prompt(prompt_id)

        assert result["success"] is True
        assert result["deleted"]["run_ids"] == []
        assert result["deleted"]["directories"] == []
        assert workflow_service.get_prompt(prompt_id) is None

    def test_delete_run_when_directory_missing(
        self, workflow_service, sample_prompt_data, sample_run_data
    ):
        """Test deleting run when output directory doesn't exist."""
        # Create prompt and run
        prompt = workflow_service.create_prompt(**sample_prompt_data)
        run = workflow_service.create_run(prompt["id"], **sample_run_data)

        # Delete run (directory doesn't exist)
        result = workflow_service.delete_run(run["id"])

        # Should succeed even if directory doesn't exist
        assert result["success"] is True
        assert workflow_service.get_run(run["id"]) is None

    @patch("shutil.rmtree")
    def test_delete_run_handles_permission_error(
        self, mock_rmtree, workflow_service, sample_prompt_data, sample_run_data
    ):
        """Test handling permission errors when deleting directories."""
        # Create prompt and run
        prompt = workflow_service.create_prompt(**sample_prompt_data)
        run = workflow_service.create_run(prompt["id"], **sample_run_data)
        run_id = run["id"]

        # Create the directory so it exists for deletion
        outputs_dir = workflow_service.config.get_local_config().outputs_dir
        run_dir = outputs_dir / f"run_{run_id}"
        run_dir.mkdir(parents=True, exist_ok=True)

        # Mock permission error
        mock_rmtree.side_effect = PermissionError("Access denied")

        # Delete run
        result = workflow_service.delete_run(run_id)

        # Database deletion should succeed, but note directory error
        assert result["success"] is True
        assert "warnings" in result
        assert "permission" in result["warnings"][0].lower()
        assert workflow_service.get_run(run_id) is None
