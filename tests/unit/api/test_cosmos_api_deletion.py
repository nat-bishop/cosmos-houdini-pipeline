"""Tests for CosmosAPI deletion methods.

Following TDD principles to test the deletion and preview deletion
methods in the CosmosAPI facade.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cosmos_workflow.api.cosmos_api import CosmosAPI
from cosmos_workflow.config.config_manager import ConfigManager


class TestCosmosAPIDeletionMethods:
    """Test deletion-related methods in CosmosAPI."""

    @pytest.fixture
    def mock_config(self):
        """Create mock config manager."""
        config = MagicMock(spec=ConfigManager)
        config.get_local_config.return_value = MagicMock(outputs_dir=Path("/tmp/outputs"))
        return config

    @pytest.fixture
    def mock_service(self):
        """Create mock DataRepository."""
        service = MagicMock()
        return service

    @pytest.fixture
    def mock_orchestrator(self):
        """Create mock GPUExecutor."""
        orchestrator = MagicMock()
        return orchestrator

    @pytest.fixture
    def api(self, mock_config, mock_service, mock_orchestrator):
        """Create CosmosAPI instance with mocked dependencies."""
        with patch("cosmos_workflow.api.cosmos_api.init_database"):
            with patch("cosmos_workflow.api.cosmos_api.DataRepository", return_value=mock_service):
                with patch(
                    "cosmos_workflow.api.cosmos_api.GPUExecutor",
                    return_value=mock_orchestrator,
                ):
                    api = CosmosAPI(mock_config)
                    api.service = mock_service
                    api.orchestrator = mock_orchestrator
                    return api

    def test_preview_run_deletion_delegates_to_service(self, api, mock_service):
        """Test that preview_run_deletion delegates to DataRepository."""
        # Setup mock response
        expected_preview = {
            "run": {
                "id": "rs_test123",
                "status": "completed",
                "prompt_id": "ps_abc456",
            },
            "directory_to_delete": "/tmp/outputs/run_rs_test123",
        }
        mock_service.preview_run_deletion.return_value = expected_preview

        # Call the method
        result = api.preview_run_deletion("rs_test123")

        # Verify delegation
        mock_service.preview_run_deletion.assert_called_once_with("rs_test123")
        assert result == expected_preview

    def test_preview_run_deletion_with_nonexistent_run(self, api, mock_service):
        """Test preview_run_deletion with non-existent run."""
        # Setup mock response for non-existent run
        expected_preview = {
            "run": None,
            "directory_to_delete": None,
            "error": "Run not found",
        }
        mock_service.preview_run_deletion.return_value = expected_preview

        # Call the method
        result = api.preview_run_deletion("rs_nonexistent")

        # Verify delegation and response
        mock_service.preview_run_deletion.assert_called_once_with("rs_nonexistent")
        assert result == expected_preview
        assert result["error"] == "Run not found"

    def test_preview_run_deletion_with_active_run(self, api, mock_service):
        """Test preview_run_deletion with an active (running) run."""
        # Setup mock response for active run
        expected_preview = {
            "run": {
                "id": "rs_active123",
                "status": "running",
                "prompt_id": "ps_xyz789",
            },
            "directory_to_delete": "/tmp/outputs/run_rs_active123",
        }
        mock_service.preview_run_deletion.return_value = expected_preview

        # Call the method
        result = api.preview_run_deletion("rs_active123")

        # Verify delegation
        mock_service.preview_run_deletion.assert_called_once_with("rs_active123")
        assert result == expected_preview
        assert result["run"]["status"] == "running"

    def test_delete_run_delegates_to_service(self, api, mock_service):
        """Test that delete_run delegates to DataRepository."""
        # Setup mock response
        expected_result = {
            "success": True,
            "deleted": {
                "run_id": "rs_test123",
                "directory": "/tmp/outputs/run_rs_test123",
            },
        }
        mock_service.delete_run.return_value = expected_result

        # Call the method
        result = api.delete_run("rs_test123")

        # Verify delegation
        mock_service.delete_run.assert_called_once_with("rs_test123")
        assert result == expected_result

    def test_preview_prompt_deletion_returns_prompt_and_runs(self, api, mock_service):
        """Test that preview_prompt_deletion returns prompt info and associated runs."""
        # Setup mock prompt
        mock_prompt = {
            "id": "ps_test123",
            "prompt_text": "Test prompt",
        }
        mock_service.get_prompt.return_value = mock_prompt

        # Setup mock runs
        mock_runs = [
            {"id": "rs_001", "status": "completed"},
            {"id": "rs_002", "status": "failed"},
        ]
        mock_service.list_runs.return_value = mock_runs

        # Call the method
        result = api.preview_prompt_deletion("ps_test123")

        # Verify it calls the right service methods
        mock_service.get_prompt.assert_called_once_with("ps_test123")
        mock_service.list_runs.assert_called_once_with(prompt_id="ps_test123", limit=100)

        # Verify the result structure
        assert result["prompt"] == mock_prompt
        assert result["runs"] == mock_runs
        assert result["run_count"] == 2
        assert "warnings" in result

    def test_preview_prompt_deletion_with_nonexistent_prompt(self, api, mock_service):
        """Test preview_prompt_deletion with non-existent prompt."""
        # Setup mock for non-existent prompt
        mock_service.get_prompt.return_value = None

        # Call the method
        result = api.preview_prompt_deletion("ps_nonexistent")

        # Verify it returns an error
        assert "error" in result
        assert "Prompt not found" in result["error"]
        mock_service.get_prompt.assert_called_once_with("ps_nonexistent")
        # Should not call list_runs if prompt doesn't exist
        mock_service.list_runs.assert_not_called()

    def test_delete_prompt_delegates_to_service(self, api, mock_service):
        """Test that delete_prompt delegates to DataRepository."""
        # Setup mock response
        expected_result = {
            "success": True,
            "deleted": {
                "prompt_id": "ps_test123",
                "run_ids": ["rs_001", "rs_002"],
                "directories": [
                    "/tmp/outputs/run_rs_001",
                    "/tmp/outputs/run_rs_002",
                ],
            },
        }
        mock_service.delete_prompt.return_value = expected_result

        # Call the method
        result = api.delete_prompt("ps_test123")

        # Verify delegation
        mock_service.delete_prompt.assert_called_once_with("ps_test123")
        assert result == expected_result


class TestCosmosAPIDeletionIntegration:
    """Test integration between deletion methods and other CosmosAPI functionality."""

    @pytest.fixture
    def mock_config(self):
        """Create mock config manager."""
        config = MagicMock(spec=ConfigManager)
        config.get_local_config.return_value = MagicMock(outputs_dir=Path("/tmp/outputs"))
        return config

    @pytest.fixture
    def mock_service(self):
        """Create mock DataRepository."""
        service = MagicMock()
        return service

    @pytest.fixture
    def mock_orchestrator(self):
        """Create mock GPUExecutor."""
        orchestrator = MagicMock()
        return orchestrator

    @pytest.fixture
    def api(self, mock_config, mock_service, mock_orchestrator):
        """Create CosmosAPI instance with mocked dependencies."""
        with patch("cosmos_workflow.api.cosmos_api.init_database"):
            with patch("cosmos_workflow.api.cosmos_api.DataRepository", return_value=mock_service):
                with patch(
                    "cosmos_workflow.api.cosmos_api.GPUExecutor",
                    return_value=mock_orchestrator,
                ):
                    api = CosmosAPI(mock_config)
                    api.service = mock_service
                    api.orchestrator = mock_orchestrator
                    return api

    def test_preview_and_delete_run_workflow(self, api, mock_service):
        """Test the complete workflow of previewing and then deleting a run."""
        run_id = "rs_workflow123"

        # Step 1: Preview the deletion
        preview_response = {
            "run": {
                "id": run_id,
                "status": "completed",
                "prompt_id": "ps_test456",
            },
            "directory_to_delete": f"/tmp/outputs/run_{run_id}",
        }
        mock_service.preview_run_deletion.return_value = preview_response

        preview = api.preview_run_deletion(run_id)
        assert preview["run"]["id"] == run_id

        # Step 2: Actually delete the run
        delete_response = {
            "success": True,
            "deleted": {
                "run_id": run_id,
                "directory": f"/tmp/outputs/run_{run_id}",
            },
        }
        mock_service.delete_run.return_value = delete_response

        result = api.delete_run(run_id)
        assert result["success"] is True
        assert result["deleted"]["run_id"] == run_id

        # Verify both methods were called
        mock_service.preview_run_deletion.assert_called_once_with(run_id)
        mock_service.delete_run.assert_called_once_with(run_id)

    def test_preview_shows_warnings_for_active_runs(self, api, mock_service):
        """Test that preview correctly identifies active runs that shouldn't be deleted."""
        # Setup active run preview
        preview_response = {
            "run": {
                "id": "rs_active",
                "status": "running",
                "prompt_id": "ps_test",
            },
            "directory_to_delete": "/tmp/outputs/run_rs_active",
            "warnings": ["Run is currently active"],
        }
        mock_service.preview_run_deletion.return_value = preview_response

        preview = api.preview_run_deletion("rs_active")

        # Verify warning is present
        assert "warnings" in preview
        assert preview["run"]["status"] == "running"
        mock_service.preview_run_deletion.assert_called_once_with("rs_active")
