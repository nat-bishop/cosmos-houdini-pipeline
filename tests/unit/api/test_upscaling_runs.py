"""Tests for upscaling with database run integration (Phase 3)."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from cosmos_workflow.api import CosmosAPI


class TestUpscalingRuns:
    """Test upscaling creates proper database runs."""

    @pytest.fixture
    def mock_service(self):
        """Create mock data service."""
        service = MagicMock()

        # Mock parent run data (completed inference run)
        service.get_run.return_value = {
            "id": "rs_inference123",
            "prompt_id": "ps_test123",
            "model_type": "transfer",
            "status": "completed",
            "execution_config": {
                "weights": {"vis": 0.25, "edge": 0.25, "depth": 0.25, "seg": 0.25}
            },
            "outputs": {
                "output_path": "outputs/run_rs_inference123/output.mp4",
                "duration_seconds": 120,
            },
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # Mock prompt data
        service.get_prompt.return_value = {
            "id": "ps_test123",
            "model_type": "transfer",
            "prompt_text": "Original prompt text",
            "inputs": {"video": "/path/to/video.mp4"},
            "parameters": {"name": "test_prompt"},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # Mock run creation - should return run with model_type="upscale"
        service.create_run.return_value = {
            "id": "rs_upscale456",
            "prompt_id": "ps_test123",
            "model_type": "upscale",  # This should be "upscale" not "transfer"
            "status": "pending",
            "execution_config": {},
            "outputs": {},
            "metadata": {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        return service

    @pytest.fixture
    def mock_orchestrator(self):
        """Create mock orchestrator."""
        orchestrator = MagicMock()
        # Upscaling now completes synchronously with a status field
        orchestrator.execute_upscaling_run.return_value = {
            "status": "completed",  # Required for synchronous completion
            "output_path": "outputs/run_rs_upscale456/output_4k.mp4",
            "parent_run_id": "rs_inference123",
            "duration_seconds": 180.5,
            "log_path": "outputs/run_rs_upscale456/logs/upscaling.log",
        }
        return orchestrator

    @pytest.fixture
    def api(self, mock_service, mock_orchestrator):
        """Create API instance with mocks."""
        with patch("cosmos_workflow.api.cosmos_api.init_database"):
            with patch("cosmos_workflow.api.cosmos_api.DataRepository") as MockRepo:
                with patch("cosmos_workflow.api.cosmos_api.GPUExecutor") as MockOrch:
                    MockRepo.return_value = mock_service
                    MockOrch.return_value = mock_orchestrator

                    api = CosmosAPI()
                    api.service = mock_service
                    api.orchestrator = mock_orchestrator
                    return api

    def test_upscale_creates_database_run(self, api, mock_service):
        """Test that upscale creates a proper database run."""
        # Act
        result = api.upscale(
            run_id="rs_inference123",
            control_weight=0.7,
        )

        # Assert - should create an upscaling run
        mock_service.create_run.assert_called_once()
        call_args = mock_service.create_run.call_args

        # Check that a run was created with proper model_type
        assert call_args[1]["prompt_id"] == "ps_test123"

        # Check execution config contains upscaling parameters
        exec_config = call_args[1]["execution_config"]
        assert exec_config["source_run_id"] == "rs_inference123"  # Changed from parent_run_id
        assert exec_config["control_weight"] == 0.7
        assert "input_video_source" in exec_config  # Changed from input_video

        # Result should include upscale_run_id and success status
        assert "upscale_run_id" in result
        assert result["upscale_run_id"] == "rs_upscale456"
        assert result["status"] == "success"  # Synchronous completion
        assert "output_path" in result

    def test_upscale_validates_parent_run_exists(self, api, mock_service):
        """Test that upscale validates the parent run exists."""
        # Setup - parent run not found
        mock_service.get_run.return_value = None

        # Act & Assert
        with pytest.raises(ValueError, match="Run not found: rs_missing"):
            api.upscale(run_id="rs_missing", control_weight=0.5)

    def test_upscale_validates_parent_run_completed(self, api, mock_service):
        """Test that upscale validates the parent run is completed."""
        # Setup - parent run not completed
        mock_service.get_run.return_value = {
            "id": "rs_running123",
            "prompt_id": "ps_test123",
            "status": "running",  # Not completed
            "outputs": {},
        }

        # Act & Assert
        with pytest.raises(ValueError, match="must be completed before upscaling"):
            api.upscale(run_id="rs_running123", control_weight=0.5)

    def test_upscale_handles_execution_failure(self, api, mock_service, mock_orchestrator):
        """Test that upscale handles execution failures gracefully."""
        # Setup - orchestrator raises error
        mock_orchestrator.execute_upscaling_run.side_effect = RuntimeError("GPU error")

        # Act
        result = api.upscale(
            run_id="rs_inference123",
            control_weight=0.5,
        )

        # Assert - should update status to failed
        assert result["status"] == "failed"
        assert "error" in result
        assert "GPU error" in result["error"]

        # Check run status was updated
        mock_service.update_run_status.assert_any_call("rs_upscale456", "running")
        mock_service.update_run_status.assert_any_call("rs_upscale456", "failed")

    def test_upscale_updates_run_status_lifecycle(self, api, mock_service):
        """Test that upscale properly updates run status throughout lifecycle."""
        # Act
        api.upscale(run_id="rs_inference123", control_weight=0.5)

        # Assert - check status updates
        status_calls = mock_service.update_run_status.call_args_list
        assert len(status_calls) == 2

        # First call: set to running
        assert status_calls[0][0] == ("rs_upscale456", "running")

        # Second call: set to completed
        assert status_calls[1][0] == ("rs_upscale456", "completed")

    def test_upscale_passes_correct_parameters_to_orchestrator(
        self, api, mock_service, mock_orchestrator
    ):
        """Test that upscale passes all required parameters to orchestrator."""
        # Act
        api.upscale(run_id="rs_inference123", control_weight=0.8)

        # Assert - check orchestrator was called correctly
        mock_orchestrator.execute_upscaling_run.assert_called_once()
        call_args = mock_orchestrator.execute_upscaling_run.call_args

        # Check positional arguments
        upscale_run = call_args[0][0]
        assert upscale_run["id"] == "rs_upscale456"

        # Check keyword arguments (new signature uses video_path and prompt_text)
        assert "video_path" in call_args[1]
        assert call_args[1]["video_path"] == "outputs/run_rs_inference123/output.mp4"
        assert call_args[1].get("prompt_text") is None  # No prompt provided

    def test_upscale_with_default_control_weight(self, api, mock_service):
        """Test that upscale uses default control weight if not specified."""
        # Act
        api.upscale(run_id="rs_inference123")

        # Assert - should use default weight of 0.5
        call_args = mock_service.create_run.call_args
        exec_config = call_args[1]["execution_config"]
        assert exec_config["control_weight"] == 0.5

    def test_upscale_validates_control_weight_range(self, api):
        """Test that upscale validates control weight is in valid range."""
        # Test invalid weights
        with pytest.raises(ValueError, match="Control weight must be between"):
            api.upscale(run_id="rs_inference123", control_weight=-0.1)

        with pytest.raises(ValueError, match="Control weight must be between"):
            api.upscale(run_id="rs_inference123", control_weight=1.1)

    def test_upscale_stores_outputs_in_database(self, api, mock_service):
        """Test that upscale stores the outputs in the database."""
        # Act
        api.upscale(run_id="rs_inference123", control_weight=0.5)

        # Assert - check that outputs were stored
        mock_service.update_run.assert_called_once()
        call_args = mock_service.update_run.call_args

        assert call_args[0][0] == "rs_upscale456"  # run_id
        outputs = call_args[1]["outputs"]
        assert "output_path" in outputs
        assert "parent_run_id" in outputs
        assert "duration_seconds" in outputs
        assert "log_path" in outputs
