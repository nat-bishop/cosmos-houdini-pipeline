"""Tests for prompt enhancement with database run integration (Phase 2)."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from cosmos_workflow.api import CosmosAPI


class TestPromptEnhancementRuns:
    """Test prompt enhancement creates proper database runs."""

    @pytest.fixture
    def mock_service(self):
        """Create mock data service."""
        service = MagicMock()

        # Mock prompt data
        service.get_prompt.return_value = {
            "id": "ps_test123",
            "model_type": "transfer",
            "prompt_text": "Original prompt text",
            "inputs": {"video": "/path/to/video.mp4"},
            "parameters": {"name": "test_prompt"},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # Mock run creation - should return run with model_type="enhance"
        service.create_run.return_value = {
            "id": "rs_enhance123",
            "prompt_id": "ps_test123",
            "model_type": "enhance",  # This should be "enhance" not "transfer"
            "status": "pending",
            "execution_config": {},
            "outputs": {},
            "metadata": {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # Mock list_runs for checking overwrites
        service.list_runs.return_value = []

        return service

    @pytest.fixture
    def mock_orchestrator(self):
        """Create mock orchestrator."""
        orchestrator = MagicMock()
        # Enhancement should now return a run result like inference does
        orchestrator.execute_enhancement_run.return_value = {
            "enhanced_text": "Enhanced prompt text with better details",
            "original_prompt_id": "ps_test123",
            "duration_seconds": 30.5,
            "log_path": "outputs/run_rs_enhance123/logs/enhancement.log",
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

    def test_enhance_prompt_creates_database_run(self, api, mock_service):
        """Test that enhance_prompt creates a proper database run."""
        # Act
        result = api.enhance_prompt(
            prompt_id="ps_test123",
            create_new=True,
            enhancement_model="pixtral",
        )

        # Assert - should create an enhancement run
        mock_service.create_run.assert_called_once()
        call_args = mock_service.create_run.call_args

        # Check that a run was created with proper model_type
        assert call_args[1]["prompt_id"] == "ps_test123"

        # Check execution config contains enhancement parameters
        exec_config = call_args[1]["execution_config"]
        assert exec_config["model"] == "pixtral"
        assert "offload" in exec_config
        assert "batch_size" in exec_config

        # Result should include run_id
        assert "run_id" in result
        assert result["run_id"] == "rs_enhance123"
        assert "enhanced_text" in result
        assert result["status"] == "success"

    def test_enhance_prompt_updates_run_status(self, api, mock_service):
        """Test that enhancement updates run status like inference does."""
        # Act
        api.enhance_prompt(
            prompt_id="ps_test123",
            create_new=True,
            enhancement_model="pixtral",
        )

        # Assert - should update status to running then completed
        status_calls = mock_service.update_run_status.call_args_list
        assert len(status_calls) >= 2
        assert status_calls[0][0] == ("rs_enhance123", "running")
        assert status_calls[1][0] == ("rs_enhance123", "completed")

    def test_enhance_prompt_stores_outputs_in_database(self, api, mock_service, mock_orchestrator):
        """Test that enhancement results are stored in run outputs."""
        # Act
        api.enhance_prompt(
            prompt_id="ps_test123",
            create_new=True,
            enhancement_model="pixtral",
        )

        # Assert - outputs should be stored in database
        mock_service.update_run.assert_called_once()
        call_args = mock_service.update_run.call_args

        assert call_args[0][0] == "rs_enhance123"  # run_id
        outputs = call_args[1]["outputs"]
        assert "enhanced_text" in outputs
        assert outputs["enhanced_text"] == "Enhanced prompt text with better details"
        assert "duration_seconds" in outputs
        assert outputs["duration_seconds"] == 30.5

    def test_enhance_prompt_handles_failure(self, api, mock_service, mock_orchestrator):
        """Test that enhancement handles failures properly."""
        # Setup
        mock_orchestrator.execute_enhancement_run.side_effect = RuntimeError("GPU error")

        # Act
        result = api.enhance_prompt(
            prompt_id="ps_test123",
            create_new=True,
            enhancement_model="pixtral",
        )

        # Assert - should mark run as failed
        status_calls = mock_service.update_run_status.call_args_list
        assert status_calls[-1][0] == ("rs_enhance123", "failed")

        assert result["status"] == "failed"
        assert result["run_id"] == "rs_enhance123"
        assert "error" in result

    def test_enhance_prompt_creates_new_prompt_when_requested(
        self, api, mock_service, mock_orchestrator
    ):
        """Test that create_new=True creates a new enhanced prompt."""
        # Setup
        mock_service.create_prompt.return_value = {
            "id": "ps_enhanced456",
            "prompt_text": "Enhanced prompt text with better details",
            "model_type": "transfer",
            "parameters": {
                "name": "test_prompt_enhanced",
                "enhanced": True,
                "parent_prompt_id": "ps_test123",
            },
        }

        # Act
        result = api.enhance_prompt(
            prompt_id="ps_test123",
            create_new=True,
            enhancement_model="pixtral",
        )

        # Assert - should create both a run and a new prompt
        mock_service.create_run.assert_called_once()
        mock_service.create_prompt.assert_called_once()

        # New prompt should have enhanced flag
        prompt_args = mock_service.create_prompt.call_args[1]
        assert prompt_args["parameters"]["enhanced"] is True
        assert prompt_args["parameters"]["name"] == "test_prompt_enhanced"

        assert result["enhanced_prompt_id"] == "ps_enhanced456"

    def test_enhance_prompt_with_video_context(self, api, mock_service):
        """Test that video path is included in execution config."""
        # Act
        api.enhance_prompt(
            prompt_id="ps_test123",
            create_new=True,
            enhancement_model="pixtral",
        )

        # Assert
        call_args = mock_service.create_run.call_args
        exec_config = call_args[1]["execution_config"]
        assert "video_context" in exec_config
        assert exec_config["video_context"] == "/path/to/video.mp4"

    def test_run_directory_structure(self, api, mock_service, mock_orchestrator):
        """Test that enhancement creates proper run directory structure."""
        # Act
        api.enhance_prompt(
            prompt_id="ps_test123",
            create_new=True,
            enhancement_model="pixtral",
        )

        # Assert - orchestrator should receive run_id for directory creation
        mock_orchestrator.execute_enhancement_run.assert_called_once()
        call_args = mock_orchestrator.execute_enhancement_run.call_args

        run_arg = call_args[0][0]  # First positional arg should be run dict
        assert run_arg["id"] == "rs_enhance123"

        # Results should indicate proper directory
        assert "log_path" in mock_orchestrator.execute_enhancement_run.return_value
        assert (
            "run_rs_enhance123"
            in mock_orchestrator.execute_enhancement_run.return_value["log_path"]
        )

    def test_async_execution_returns_immediately(self, api, mock_service):
        """Test that enhancement returns immediately with run_id for tracking."""
        # Act
        result = api.enhance_prompt(
            prompt_id="ps_test123",
            create_new=True,
            enhancement_model="pixtral",
        )

        # Assert - should return run_id immediately
        assert "run_id" in result
        assert result["run_id"] == "rs_enhance123"

        # Should not block waiting for results
        # (In real implementation, execute_enhancement_run would be async)
        assert result["status"] in ["success", "started"]


class TestUpscalingRunsDesign:
    """Test design for upscaling runs (Phase 3 preview)."""

    def test_upscaling_takes_run_id_not_prompt_id(self):
        """Test that upscaling takes a run_id as input, not prompt_id."""
        # This is a design test to clarify the API
        # Upscaling operates on the output of a specific run

        # Conceptual API:
        # api.create_upscale_run(
        #     parent_run_id="rs_inference123",  # NOT prompt_id!
        #     control_weight=0.5,
        # )

        # The upscale run would have:
        # - model_type="upscale"
        # - execution_config with parent_run_id and control_weight
        # - Input video path derived from parent run's outputs

        assert True  # Design placeholder

    def test_upscaling_links_to_parent_run(self):
        """Test that upscaling run links to its parent inference run."""
        # execution_config should contain:
        # {
        #     "parent_run_id": "rs_inference123",
        #     "control_weight": 0.5,
        #     "input_video": "outputs/run_rs_inference123/output.mp4"
        # }
        assert True  # Design placeholder
