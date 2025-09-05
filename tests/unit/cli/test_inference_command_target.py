"""Behavioral tests for CLI inference command - TARGET BEHAVIOR.

These tests define the desired behavior of inference with WorkflowService.
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
            },
            "outputs": {},
            "metadata": {},
            "created_at": "2024-01-01T00:00:00",
        }

        # Default prompt response
        service.get_prompt.return_value = {
            "id": "ps_test_prompt_456",
            "model_type": "transfer",
            "prompt_text": "cyberpunk city at night",
            "inputs": {
                "video": "/path/to/video.mp4",
                "depth": "/path/to/depth.mp4",
                "seg": "/path/to/seg.mp4",
            },
            "parameters": {"name": "test_prompt", "negative_prompt": "bad quality"},
        }

        # Update run status response
        service.update_run_status.return_value = {"id": "rs_test_run_123", "status": "running"}

        return service

    @patch("cosmos_workflow.cli.base.CLIContext.get_orchestrator")
    @patch("cosmos_workflow.cli.base.CLIContext.get_workflow_service")
    def test_inference_with_run_id(
        self, mock_get_service, mock_get_orchestrator, runner, mock_service
    ):
        """Test inference using a run ID from database."""
        # Setup mocks
        mock_get_service.return_value = mock_service

        mock_orchestrator = MagicMock()
        mock_get_orchestrator.return_value = mock_orchestrator
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
        assert "completed" in result.output.lower() or "success" in result.output.lower()
        assert "rs_test_run_123" in result.output  # Run ID shown

        # Verify service interactions
        mock_service.get_run.assert_called_with("rs_test_run_123")
        mock_service.get_prompt.assert_called_with("ps_test_prompt_456")

        # Should update run status
        assert mock_service.update_run_status.call_count >= 1
        status_calls = [call[0][1] for call in mock_service.update_run_status.call_args_list]
        assert "running" in status_calls or "completed" in status_calls

    @patch("cosmos_workflow.cli.base.CLIContext.get_workflow_service")
    def test_inference_dry_run_shows_full_details(self, mock_get_service, runner, mock_service):
        """Test that --dry-run shows comprehensive information without executing."""
        mock_get_service.return_value = mock_service

        from cosmos_workflow.cli import cli

        result = runner.invoke(
            cli,
            [
                "inference",
                "rs_test_run_123",
                "--dry-run",
            ],
        )

        # Assertions
        assert result.exit_code == 0
        assert "dry" in result.output.lower() or "preview" in result.output.lower()
        assert "rs_test_run_123" in result.output
        assert "ps_test_prompt_4" in result.output  # May be truncated in output
        assert "cyberpunk city" in result.output.lower()  # Prompt text shown
        assert "pending" in result.output.lower()  # Status shown

        # Should NOT execute
        mock_service.update_run_status.assert_not_called()

    @patch("cosmos_workflow.cli.base.CLIContext.get_workflow_service")
    def test_inference_run_not_found(self, mock_get_service, runner):
        """Test error when run ID doesn't exist."""
        # Setup mocks
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.get_run.return_value = None  # Run not found

        from cosmos_workflow.cli import cli

        result = runner.invoke(cli, ["inference", "rs_nonexistent"])

        assert result.exit_code != 0
        assert "not found" in result.output.lower() or "error" in result.output.lower()
        assert "rs_nonexistent" in result.output

    @patch("cosmos_workflow.cli.base.CLIContext.get_workflow_service")
    def test_inference_already_running(self, mock_get_service, runner):
        """Test handling when run is already in progress."""
        # Setup mocks
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        # Run already in "running" state
        mock_service.get_run.return_value = {
            "id": "rs_test_run_123",
            "prompt_id": "ps_test_prompt_456",
            "status": "running",  # Already running
        }
        mock_service.get_prompt.return_value = {"id": "ps_test_prompt_456", "prompt_text": "test"}

        from cosmos_workflow.cli import cli

        # Implementation should either:
        # 1. Continue/resume the run
        # 2. Show appropriate message
        # The test just verifies it handles the situation gracefully
        result = runner.invoke(cli, ["inference", "rs_test_run_123"])

        # Should not crash, should handle gracefully
        assert "running" in result.output.lower() or "progress" in result.output.lower()

    @patch("cosmos_workflow.cli.base.CLIContext.get_orchestrator")
    @patch("cosmos_workflow.cli.base.CLIContext.get_workflow_service")
    def test_inference_completed_run(self, mock_get_service, mock_get_orchestrator, runner):
        """Test handling when run is already completed."""
        # Setup mocks
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        mock_orchestrator = MagicMock()
        mock_get_orchestrator.return_value = mock_orchestrator

        # Run already completed
        mock_service.get_run.return_value = {
            "id": "rs_test_run_123",
            "prompt_id": "ps_test_prompt_456",
            "status": "completed",
            "outputs": {"video_path": "/existing/output.mp4"},
        }
        mock_service.get_prompt.return_value = {"id": "ps_test_prompt_456", "prompt_text": "test"}

        from cosmos_workflow.cli import cli

        result = runner.invoke(cli, ["inference", "rs_test_run_123"])

        # Should handle completed run appropriately
        # Either re-run or show existing results
        assert result.exit_code == 0
        assert "rs_test_run_123" in result.output

    @patch("cosmos_workflow.cli.base.CLIContext.get_orchestrator")
    @patch("cosmos_workflow.cli.base.CLIContext.get_workflow_service")
    def test_inference_with_upscaling(
        self, mock_get_service, mock_get_orchestrator, runner, mock_service
    ):
        """Test inference with upscaling option."""
        mock_get_service.return_value = mock_service

        mock_orchestrator = MagicMock()
        mock_get_orchestrator.return_value = mock_orchestrator
        mock_orchestrator.execute_run.return_value = {
            "status": "success",
            "output_path": "/outputs/upscaled.mp4",
        }

        from cosmos_workflow.cli import cli

        result = runner.invoke(
            cli,
            [
                "inference",
                "rs_test_run_123",
                "--upscale-weight",
                "0.7",
            ],
        )

        assert result.exit_code == 0

        # Check that upscaling was applied
        orchestrator_call = mock_orchestrator.execute_run.call_args
        assert orchestrator_call.kwargs.get("upscale") is True
        assert orchestrator_call.kwargs.get("upscale_weight") == 0.7

        # Run outputs should be updated
        mock_service.update_run.assert_called()
        update_call = mock_service.update_run.call_args
        outputs = update_call.kwargs.get("outputs", {})
        assert outputs.get("upscaled") is True

    @patch("cosmos_workflow.cli.base.CLIContext.get_orchestrator")
    @patch("cosmos_workflow.cli.base.CLIContext.get_workflow_service")
    def test_inference_updates_database_on_failure(
        self, mock_get_service, mock_get_orchestrator, runner, mock_service
    ):
        """Test that database is updated when inference fails."""
        mock_get_service.return_value = mock_service

        mock_orchestrator = MagicMock()
        mock_get_orchestrator.return_value = mock_orchestrator
        mock_orchestrator.execute_run.side_effect = Exception("GPU memory error")

        from cosmos_workflow.cli import cli

        result = runner.invoke(cli, ["inference", "rs_test_run_123"])

        assert result.exit_code != 0
        assert "error" in result.output.lower()

        # Should update status to failed
        status_updates = [call[0][1] for call in mock_service.update_run_status.call_args_list]
        assert "failed" in status_updates

        # Should store error in outputs
        if mock_service.update_run.called:
            update_call = mock_service.update_run.call_args
            outputs = update_call.kwargs.get("outputs", {})
            assert "error" in outputs


class TestInferenceProgress:
    """Test progress tracking during inference."""

    @pytest.fixture
    def runner(self):
        """Create a CLI test runner."""
        return CliRunner()

    @patch("cosmos_workflow.cli.base.CLIContext.get_orchestrator")
    @patch("cosmos_workflow.cli.base.CLIContext.get_workflow_service")
    def test_inference_tracks_progress(self, mock_get_service, mock_get_orchestrator, runner):
        """Test that inference shows progress to user."""
        # Setup mocks
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        mock_orchestrator = MagicMock()
        mock_get_orchestrator.return_value = mock_orchestrator

        mock_service.get_run.return_value = {
            "id": "rs_test_run_123",
            "prompt_id": "ps_test_prompt_456",
            "status": "pending",
        }
        mock_service.get_prompt.return_value = {"id": "ps_test_prompt_456", "prompt_text": "test"}

        mock_orchestrator.execute_run.return_value = {
            "status": "success",
            "output_path": "/output.mp4",
        }

        from cosmos_workflow.cli import cli

        result = runner.invoke(cli, ["inference", "rs_test_run_123"])

        assert result.exit_code == 0

        # Should show progress indicators
        assert (
            "running" in result.output.lower()
            or "progress" in result.output.lower()
            or "processing" in result.output.lower()
        )

        # This depends on implementation - might use update_run_progress method
        # or just update status to show progress
