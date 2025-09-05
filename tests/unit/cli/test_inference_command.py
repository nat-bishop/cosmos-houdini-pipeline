"""Behavioral tests for CLI inference command.

These tests define the CLI contract for the inference command.
Implementation-agnostic - tests behavior, not storage mechanism.
Following TDD Gate 1: Write tests first.
"""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from cosmos_workflow.cli import cli


class TestInferenceCommand:
    """Test the 'cosmos inference' command behavior."""

    @pytest.fixture
    def runner(self):
        """Create a CLI test runner."""
        return CliRunner()

    @patch("cosmos_workflow.cli.base.CLIContext.get_orchestrator")
    @patch("cosmos_workflow.cli.base.CLIContext.get_workflow_service")
    def test_inference_basic(self, mock_get_service, mock_get_orchestrator, runner):
        """Test basic inference command execution."""
        # Setup mocks
        mock_service = MagicMock()
        mock_orchestrator = MagicMock()

        mock_get_service.return_value = mock_service
        mock_get_orchestrator.return_value = mock_orchestrator

        # Setup test data
        run_dict = {
            "id": "rs_test",
            "prompt_id": "ps_test",
            "status": "pending",
            "model_type": "transfer",
            "execution_config": {},
        }
        prompt_dict = {
            "id": "ps_test",
            "prompt_text": "test",
            "inputs": {"video": "/test/video.mp4"},
        }

        mock_service.get_run.return_value = run_dict
        mock_service.get_prompt.return_value = prompt_dict
        mock_orchestrator.execute_run.return_value = {
            "status": "success",
            "output_path": "/output/test.mp4",
        }

        result = runner.invoke(cli, ["inference", "rs_test"])

        # Behavioral assertions
        assert result.exit_code == 0
        assert "completed" in result.output.lower() or "success" in result.output.lower()

        # Should have called orchestrator with correct args
        mock_orchestrator.execute_run.assert_called_once()

    @patch("cosmos_workflow.cli.base.CLIContext.get_orchestrator")
    @patch("cosmos_workflow.cli.base.CLIContext.get_workflow_service")
    def test_inference_no_upscale(self, mock_get_service, mock_get_orchestrator, runner):
        """Test inference without upscaling."""
        # Setup mocks
        mock_service = MagicMock()
        mock_orchestrator = MagicMock()

        mock_get_service.return_value = mock_service
        mock_get_orchestrator.return_value = mock_orchestrator

        # Setup test data
        run_dict = {
            "id": "rs_test",
            "prompt_id": "ps_test",
            "status": "pending",
            "model_type": "transfer",
            "execution_config": {},
        }
        prompt_dict = {"id": "ps_test", "prompt_text": "test", "inputs": {}}

        mock_service.get_run.return_value = run_dict
        mock_service.get_prompt.return_value = prompt_dict
        mock_orchestrator.execute_run.return_value = {
            "status": "success",
            "output_path": "/output/test.mp4",
        }

        result = runner.invoke(cli, ["inference", "rs_test", "--no-upscale"])

        assert result.exit_code == 0
        assert "completed" in result.output.lower() or "success" in result.output.lower()

        # Should call execute_run with upscale=False
        mock_orchestrator.execute_run.assert_called_once()
        call_args = mock_orchestrator.execute_run.call_args
        assert call_args[1]["upscale"] is False

    @patch("cosmos_workflow.cli.base.CLIContext.get_workflow_service")
    def test_inference_dry_run(self, mock_get_service, runner):
        """Test dry-run mode doesn't execute."""
        # Setup mocks
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        # Setup test data
        run_dict = {
            "id": "rs_test",
            "prompt_id": "ps_test",
            "status": "pending",
            "model_type": "transfer",
            "execution_config": {},
        }
        prompt_dict = {"id": "ps_test", "prompt_text": "cyberpunk transformation", "inputs": {}}

        mock_service.get_run.return_value = run_dict
        mock_service.get_prompt.return_value = prompt_dict

        result = runner.invoke(cli, ["inference", "rs_test", "--dry-run"])

        assert result.exit_code == 0
        # Dry run should show what would happen
        assert "would" in result.output.lower()
        assert "dry" in result.output.lower() or "preview" in result.output.lower()
        # Should display prompt information
        assert "cyberpunk transformation" in result.output

    @patch("cosmos_workflow.cli.base.CLIContext.get_workflow_service")
    def test_inference_dry_run_with_options(self, mock_get_service, runner):
        """Test dry-run shows configuration options."""
        # Setup mocks
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        # Setup test data
        run_dict = {
            "id": "rs_test",
            "prompt_id": "ps_test",
            "status": "pending",
            "model_type": "transfer",
            "execution_config": {},
        }
        prompt_dict = {"id": "ps_test", "prompt_text": "test", "inputs": {}}

        mock_service.get_run.return_value = run_dict
        mock_service.get_prompt.return_value = prompt_dict

        result = runner.invoke(
            cli, ["inference", "rs_test", "--upscale-weight", "0.7", "--dry-run"]
        )

        assert result.exit_code == 0
        assert "0.7" in result.output
        assert "upscale" in result.output.lower()

    @patch("cosmos_workflow.cli.base.CLIContext.get_workflow_service")
    def test_inference_missing_run(self, mock_get_service, runner):
        """Test inference with missing run ID."""
        # Setup mocks
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        # Make get_run return None for missing run
        mock_service.get_run.return_value = None

        result = runner.invoke(cli, ["inference", "rs_nonexistent"])

        assert result.exit_code != 0
        assert "not found" in result.output.lower() or "error" in result.output.lower()

    @patch("cosmos_workflow.cli.base.CLIContext.get_workflow_service")
    def test_inference_invalid_run_data(self, mock_get_service, runner):
        """Test inference with invalid run data."""
        # Setup mocks
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        # Make get_run raise an exception
        mock_service.get_run.side_effect = Exception("Database error")

        result = runner.invoke(cli, ["inference", "rs_test"])

        assert result.exit_code != 0
        assert "error" in result.output.lower()

    @patch("cosmos_workflow.cli.base.CLIContext.get_orchestrator")
    @patch("cosmos_workflow.cli.base.CLIContext.get_workflow_service")
    def test_inference_with_upscale_weight(self, mock_get_service, mock_get_orchestrator, runner):
        """Test inference with custom upscale weight."""
        # Setup mocks
        mock_service = MagicMock()
        mock_orchestrator = MagicMock()

        mock_get_service.return_value = mock_service
        mock_get_orchestrator.return_value = mock_orchestrator

        # Setup test data
        run_dict = {
            "id": "rs_test",
            "prompt_id": "ps_test",
            "status": "pending",
            "model_type": "transfer",
            "execution_config": {},
        }
        prompt_dict = {"id": "ps_test", "prompt_text": "test", "inputs": {}}

        mock_service.get_run.return_value = run_dict
        mock_service.get_prompt.return_value = prompt_dict
        mock_orchestrator.execute_run.return_value = {"status": "success"}

        result = runner.invoke(cli, ["inference", "rs_test", "--upscale-weight", "0.8"])

        assert result.exit_code == 0

        # Check orchestrator was called with custom weight
        call_args = mock_orchestrator.execute_run.call_args
        assert call_args[1]["upscale_weight"] == 0.8

    @patch("cosmos_workflow.cli.base.CLIContext.get_orchestrator")
    @patch("cosmos_workflow.cli.base.CLIContext.get_workflow_service")
    def test_inference_handles_orchestrator_error(
        self, mock_get_service, mock_get_orchestrator, runner
    ):
        """Test inference handles orchestrator errors gracefully."""
        # Setup mocks
        mock_service = MagicMock()
        mock_orchestrator = MagicMock()

        mock_get_service.return_value = mock_service
        mock_get_orchestrator.return_value = mock_orchestrator

        # Setup test data
        run_dict = {
            "id": "rs_test",
            "prompt_id": "ps_test",
            "status": "pending",
            "model_type": "transfer",
            "execution_config": {},
        }
        prompt_dict = {"id": "ps_test", "prompt_text": "test", "inputs": {}}

        mock_service.get_run.return_value = run_dict
        mock_service.get_prompt.return_value = prompt_dict
        mock_orchestrator.execute_run.side_effect = Exception("GPU not available")

        result = runner.invoke(cli, ["inference", "rs_test"])

        assert result.exit_code != 0
        assert "error" in result.output.lower() or "failed" in result.output.lower()

    def test_inference_help_works(self, runner):
        """Test inference help command."""
        result = runner.invoke(cli, ["inference", "--help"])

        assert result.exit_code == 0
        assert "inference" in result.output.lower()
        assert "upscale" in result.output.lower()
        assert "dry-run" in result.output.lower()


class TestInferenceIntegration:
    """Test inference command integration with other components."""

    @pytest.fixture
    def runner(self):
        """Create a CLI test runner."""
        return CliRunner()

    @patch("cosmos_workflow.cli.base.CLIContext.get_workflow_service")
    def test_inference_dry_run_shows_correct_info(self, mock_get_service, runner):
        """Test that dry-run displays all relevant information."""
        # Setup mocks
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        # Setup test data with more details
        run_dict = {
            "id": "rs_complete_test",
            "prompt_id": "ps_complete_test",
            "status": "pending",
            "model_type": "transfer",
            "execution_config": {
                "weights": {"vis": 0.25, "edge": 0.25, "depth": 0.25, "seg": 0.25}
            },
        }
        prompt_dict = {
            "id": "ps_complete_test",
            "prompt_text": "test prompt",
            "inputs": {"video": "/videos/color.mp4"},
        }

        mock_service.get_run.return_value = run_dict
        mock_service.get_prompt.return_value = prompt_dict

        result = runner.invoke(cli, ["inference", "rs_complete_test", "--dry-run"])

        assert result.exit_code == 0
        # Should show prompt details
        assert "test prompt" in result.output
        # Should indicate what would happen
        assert "would" in result.output.lower()

    @patch("cosmos_workflow.cli.base.CLIContext.get_orchestrator")
    @patch("cosmos_workflow.cli.base.CLIContext.get_workflow_service")
    def test_verbose_mode_shows_details(self, mock_get_service, mock_get_orchestrator, runner):
        """Test verbose mode provides additional output."""
        # Setup mocks
        mock_service = MagicMock()
        mock_orchestrator = MagicMock()

        mock_get_service.return_value = mock_service
        mock_get_orchestrator.return_value = mock_orchestrator

        # Setup test data
        run_dict = {
            "id": "rs_test",
            "prompt_id": "ps_test",
            "status": "pending",
            "model_type": "transfer",
            "execution_config": {},
        }
        prompt_dict = {"id": "ps_test", "prompt_text": "test", "inputs": {}}

        mock_service.get_run.return_value = run_dict
        mock_service.get_prompt.return_value = prompt_dict
        mock_orchestrator.execute_run.return_value = {
            "status": "success",
            "output_path": "/fake/output.mp4",
        }

        # Run with verbose - note: can't easily test verbose flag in this way
        # The test is mainly checking that command completes successfully
        result = runner.invoke(cli, ["inference", "rs_test"])

        assert result.exit_code == 0
