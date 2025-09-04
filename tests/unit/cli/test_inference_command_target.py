"""Behavioral tests for CLI inference command - TARGET BEHAVIOR.

These tests define the desired behavior of the inference command with WorkflowService.
Tests use run IDs from database, not JSON files.
Following TDD Gate 1: Write tests for desired behavior.
"""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner


class TestInferenceCommandTarget:
    """Test target behavior of 'cosmos inference' with database integration."""

    @pytest.fixture
    def runner(self):
        """Create a CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_service(self):
        """Create a mock WorkflowService with common responses."""
        service = MagicMock()

        # Default run response
        service.get_run.return_value = {
            "id": "rs_test_run_123",
            "prompt_id": "ps_test_prompt_456",
            "model_type": "transfer",
            "status": "pending",
            "execution_config": {
                "weights": {"vis": 0.25, "edge": 0.25, "depth": 0.25, "seg": 0.25},
                "num_steps": 35,
                "guidance": 7.0,
                "seed": 1,
            },
            "outputs": {},
            "metadata": {},
            "created_at": "2024-01-01T00:00:00",
        }

        # Default prompt response
        service.get_prompt.return_value = {
            "id": "ps_test_prompt_456",
            "model_type": "transfer",
            "prompt_text": "cyberpunk transformation",
            "negative_prompt": "low quality",
            "inputs": {
                "video": "/path/to/video.mp4",
                "depth": "/path/to/depth.mp4",
                "seg": "/path/to/seg.mp4",
            },
            "parameters": {"fps": 24, "resolution": "1920x1080"},
        }

        # Update run status returns updated run
        service.update_run_status.return_value = {"id": "rs_test_run_123", "status": "running"}

        return service

    @patch("cosmos_workflow.workflows.workflow_orchestrator.WorkflowOrchestrator")
    @patch("cosmos_workflow.cli.inference.WorkflowService")
    @patch("cosmos_workflow.cli.inference.init_database")
    def test_inference_with_run_id(
        self, mock_init_db, mock_service_class, mock_orchestrator_class, runner, mock_service
    ):
        """Test inference using a run ID from database."""
        # Setup mocks
        mock_db = MagicMock()
        mock_init_db.return_value = mock_db
        mock_service_class.return_value = mock_service

        mock_orchestrator = MagicMock()
        mock_orchestrator_class.return_value = mock_orchestrator
        mock_orchestrator.execute_run.return_value = {
            "status": "success",
            "output_path": "/outputs/result.mp4",
        }

        from cosmos_workflow.cli import cli

        result = runner.invoke(
            cli,
            [
                "inference",
                "rs_test_run_123",  # Run ID instead of JSON file
            ],
        )

        # Assertions
        assert result.exit_code == 0
        assert "success" in result.output.lower() or "completed" in result.output.lower()
        assert "rs_test_run_123" in result.output

        # Verify service interactions
        mock_service.get_run.assert_called_with("rs_test_run_123")
        mock_service.get_prompt.assert_called_with("ps_test_prompt_456")

        # Should update run status to running, then completed
        assert mock_service.update_run_status.call_count >= 1
        status_calls = [call[0][1] for call in mock_service.update_run_status.call_args_list]
        assert "running" in status_calls or "completed" in status_calls

    @patch("cosmos_workflow.cli.inference.WorkflowService")
    @patch("cosmos_workflow.cli.inference.init_database")
    def test_inference_dry_run_shows_full_details(
        self, mock_init_db, mock_service_class, runner, mock_service
    ):
        """Test --dry-run shows comprehensive information."""
        # Setup mocks
        mock_db = MagicMock()
        mock_init_db.return_value = mock_db
        mock_service_class.return_value = mock_service

        from cosmos_workflow.cli import cli

        result = runner.invoke(cli, ["inference", "rs_test_run_123", "--dry-run"])

        assert result.exit_code == 0

        # Should show all relevant information
        assert "dry" in result.output.lower() or "preview" in result.output.lower()
        assert "rs_test_run_123" in result.output
        assert "ps_test_prompt_456" in result.output
        assert "cyberpunk transformation" in result.output
        assert "/path/to/video.mp4" in result.output
        assert "pending" in result.output.lower()  # Current status

        # Should NOT execute
        mock_service.update_run_status.assert_not_called()

    @patch("cosmos_workflow.cli.inference.WorkflowService")
    @patch("cosmos_workflow.cli.inference.init_database")
    def test_inference_run_not_found(self, mock_init_db, mock_service_class, runner):
        """Test error when run ID doesn't exist."""
        # Setup mocks
        mock_db = MagicMock()
        mock_init_db.return_value = mock_db

        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        mock_service.get_run.return_value = None  # Run not found

        from cosmos_workflow.cli import cli

        result = runner.invoke(cli, ["inference", "rs_nonexistent"])

        assert result.exit_code != 0
        assert "not found" in result.output.lower() or "error" in result.output.lower()
        assert "rs_nonexistent" in result.output

    @patch("cosmos_workflow.cli.inference.WorkflowService")
    @patch("cosmos_workflow.cli.inference.init_database")
    def test_inference_already_running(self, mock_init_db, mock_service_class, runner):
        """Test handling when run is already in progress."""
        # Setup mocks
        mock_db = MagicMock()
        mock_init_db.return_value = mock_db

        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        mock_service.get_run.return_value = {
            "id": "rs_running",
            "status": "running",  # Already running
            "prompt_id": "ps_test",
        }

        from cosmos_workflow.cli import cli

        result = runner.invoke(cli, ["inference", "rs_running"])

        # Should either error or warn
        assert "already running" in result.output.lower() or "in progress" in result.output.lower()

    @patch("cosmos_workflow.cli.inference.WorkflowService")
    @patch("cosmos_workflow.cli.inference.init_database")
    def test_inference_completed_run(self, mock_init_db, mock_service_class, runner):
        """Test handling when run is already completed."""
        # Setup mocks
        mock_db = MagicMock()
        mock_init_db.return_value = mock_db

        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        mock_service.get_run.return_value = {
            "id": "rs_completed",
            "status": "completed",  # Already completed
            "prompt_id": "ps_test",
            "outputs": {"result_path": "/outputs/final.mp4"},
        }

        from cosmos_workflow.cli import cli

        result = runner.invoke(cli, ["inference", "rs_completed"])

        # Should inform user it's already done
        assert (
            "already completed" in result.output.lower() or "already done" in result.output.lower()
        )
        assert "/outputs/final.mp4" in result.output  # Show existing output

    @patch("cosmos_workflow.workflows.workflow_orchestrator.WorkflowOrchestrator")
    @patch("cosmos_workflow.cli.inference.WorkflowService")
    @patch("cosmos_workflow.cli.inference.init_database")
    def test_inference_with_upscaling(
        self, mock_init_db, mock_service_class, mock_orchestrator_class, runner
    ):
        """Test inference with upscaling options."""
        # Setup mocks
        mock_db = MagicMock()
        mock_init_db.return_value = mock_db

        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        mock_service.get_run.return_value = {
            "id": "rs_upscale",
            "prompt_id": "ps_test",
            "status": "pending",
            "execution_config": {"upscale": True, "upscale_weight": 0.5},
        }
        mock_service.get_prompt.return_value = {
            "id": "ps_test",
            "prompt_text": "test",
            "inputs": {},
        }

        mock_orchestrator = MagicMock()
        mock_orchestrator_class.return_value = mock_orchestrator

        from cosmos_workflow.cli import cli

        result = runner.invoke(
            cli, ["inference", "rs_upscale", "--upscale", "--upscale-weight", "0.7"]
        )

        assert result.exit_code == 0

        # Check orchestrator called with upscale options
        orchestrator_call = mock_orchestrator.execute_run.call_args
        assert orchestrator_call is not None
        # Exact args depend on implementation

    @patch("cosmos_workflow.workflows.workflow_orchestrator.WorkflowOrchestrator")
    @patch("cosmos_workflow.cli.inference.WorkflowService")
    @patch("cosmos_workflow.cli.inference.init_database")
    def test_inference_updates_database_on_failure(
        self, mock_init_db, mock_service_class, mock_orchestrator_class, runner
    ):
        """Test that failures update run status in database."""
        # Setup mocks
        mock_db = MagicMock()
        mock_init_db.return_value = mock_db

        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        mock_service.get_run.return_value = {
            "id": "rs_fail",
            "prompt_id": "ps_test",
            "status": "pending",
        }
        mock_service.get_prompt.return_value = {
            "id": "ps_test",
            "prompt_text": "test",
            "inputs": {},
        }

        mock_orchestrator = MagicMock()
        mock_orchestrator_class.return_value = mock_orchestrator
        mock_orchestrator.execute_run.side_effect = Exception("GPU out of memory")

        from cosmos_workflow.cli import cli

        result = runner.invoke(cli, ["inference", "rs_fail"])

        assert result.exit_code != 0
        assert "error" in result.output.lower() or "failed" in result.output.lower()

        # Should update status to failed
        status_updates = [call[0][1] for call in mock_service.update_run_status.call_args_list]
        assert "failed" in status_updates or "error" in status_updates


class TestInferenceProgress:
    """Test progress tracking during inference."""

    @pytest.fixture
    def runner(self):
        """Create a CLI test runner."""
        return CliRunner()

    @patch("cosmos_workflow.workflows.workflow_orchestrator.WorkflowOrchestrator")
    @patch("cosmos_workflow.cli.inference.WorkflowService")
    @patch("cosmos_workflow.cli.inference.init_database")
    def test_inference_tracks_progress(
        self, mock_init_db, mock_service_class, mock_orchestrator_class, runner
    ):
        """Test that inference tracks progress in database."""
        # Setup mocks
        mock_db = MagicMock()
        mock_init_db.return_value = mock_db

        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        mock_service.get_run.return_value = {
            "id": "rs_progress",
            "prompt_id": "ps_test",
            "status": "pending",
        }
        mock_service.get_prompt.return_value = {
            "id": "ps_test",
            "prompt_text": "test",
            "inputs": {},
        }

        # Mock orchestrator with progress callback
        mock_orchestrator = MagicMock()
        mock_orchestrator_class.return_value = mock_orchestrator

        def execute_with_progress(*args, **kwargs):
            # Simulate progress updates
            progress_callback = kwargs.get("progress_callback")
            if progress_callback:
                progress_callback("uploading", 0.25, "Uploading videos")
                progress_callback("inference", 0.50, "Running inference")
                progress_callback("downloading", 0.90, "Downloading results")
            return {"status": "success"}

        mock_orchestrator.execute_run.side_effect = execute_with_progress

        from cosmos_workflow.cli import cli

        result = runner.invoke(
            cli,
            [
                "inference",
                "rs_progress",
                "--verbose",  # Verbose might show progress
            ],
        )

        assert result.exit_code == 0

        # Check progress updates were recorded
        # This depends on implementation - might use update_run_progress method
        # or create Progress entries
