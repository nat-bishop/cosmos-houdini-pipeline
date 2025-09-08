"""Behavioral tests for CLI upscale command (Phase 3).

These tests define the CLI contract for the upscale command.
Implementation-agnostic - tests behavior, not storage mechanism.
Upscaling operates on completed inference runs as separate operations.
"""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from cosmos_workflow.cli import cli


class TestUpscaleCommand:
    """Test the 'cosmos upscale' command behavior with run IDs."""

    @pytest.fixture
    def runner(self):
        """Create a CLI test runner."""
        return CliRunner()

    @patch("cosmos_workflow.cli.base.CLIContext.get_operations")
    def test_upscale_basic(self, mock_get_ops, runner):
        """Test basic upscale command execution with run ID."""
        # Setup mock operations
        mock_ops = MagicMock()
        mock_get_ops.return_value = mock_ops

        # Setup test data for upscale_run
        mock_ops.upscale_run.return_value = {
            "upscale_run_id": "rs_upscale456",
            "status": "success",
            "output_path": "/output/test_4k.mp4",
        }

        result = runner.invoke(cli, ["upscale", "rs_inference123"])

        # Behavioral assertions
        assert result.exit_code == 0
        assert "upscaling started" in result.output.lower() or "success" in result.output.lower()

        # Should have called upscale_run with run ID
        mock_ops.upscale_run.assert_called_once()
        call_kwargs = mock_ops.upscale_run.call_args[1]
        assert call_kwargs["run_id"] == "rs_inference123"

    @patch("cosmos_workflow.cli.base.CLIContext.get_operations")
    def test_upscale_with_custom_weight(self, mock_get_ops, runner):
        """Test upscale command with custom control weight."""
        # Setup mock operations
        mock_ops = MagicMock()
        mock_get_ops.return_value = mock_ops

        # Setup test data
        mock_ops.upscale_run.return_value = {
            "upscale_run_id": "rs_upscale456",
            "status": "success",
            "output_path": "/output/test_4k.mp4",
        }

        result = runner.invoke(cli, ["upscale", "rs_inference123", "--weight", "0.8"])

        assert result.exit_code == 0
        assert "upscaling started" in result.output.lower() or "success" in result.output.lower()

        # Should call upscale_run with custom weight
        mock_ops.upscale_run.assert_called_once()
        call_kwargs = mock_ops.upscale_run.call_args[1]
        assert call_kwargs["run_id"] == "rs_inference123"
        assert call_kwargs["control_weight"] == 0.8

    @patch("cosmos_workflow.cli.base.CLIContext.get_operations")
    def test_upscale_with_weight_shorthand(self, mock_get_ops, runner):
        """Test upscale command with -w shorthand for weight."""
        # Setup mock operations
        mock_ops = MagicMock()
        mock_get_ops.return_value = mock_ops

        # Setup test data
        mock_ops.upscale_run.return_value = {
            "upscale_run_id": "rs_upscale456",
            "status": "success",
            "output_path": "/output/test_4k.mp4",
        }

        result = runner.invoke(cli, ["upscale", "rs_inference123", "-w", "0.3"])

        assert result.exit_code == 0

        # Should call upscale_run with custom weight
        mock_ops.upscale_run.assert_called_once()
        call_kwargs = mock_ops.upscale_run.call_args[1]
        assert call_kwargs["control_weight"] == 0.3

    @patch("cosmos_workflow.cli.base.CLIContext.get_operations")
    def test_upscale_invalid_weight_range(self, mock_get_ops, runner):
        """Test upscale command validates weight range."""
        # Setup mock operations
        mock_ops = MagicMock()
        mock_get_ops.return_value = mock_ops

        # Test weight too low
        result = runner.invoke(cli, ["upscale", "rs_inference123", "--weight", "-0.1"])
        assert result.exit_code != 0
        assert "invalid" in result.output.lower() or "error" in result.output.lower()

        # Test weight too high
        result = runner.invoke(cli, ["upscale", "rs_inference123", "--weight", "1.5"])
        assert result.exit_code != 0
        assert "invalid" in result.output.lower() or "error" in result.output.lower()

    @patch("cosmos_workflow.cli.base.CLIContext.get_operations")
    def test_upscale_handles_failure(self, mock_get_ops, runner):
        """Test upscale command handles operation failure."""
        # Setup mock operations
        mock_ops = MagicMock()
        mock_get_ops.return_value = mock_ops

        # Setup failure response
        mock_ops.upscale_run.return_value = {
            "upscale_run_id": "rs_upscale456",
            "status": "failed",
            "error": "Run not found",
        }

        result = runner.invoke(cli, ["upscale", "rs_missing"])

        # Should show error message
        assert result.exit_code != 0 or "failed" in result.output.lower()
        assert "failed" in result.output.lower() or "error" in result.output.lower()

    @patch("cosmos_workflow.cli.base.CLIContext.get_operations")
    def test_upscale_shows_monitoring_instructions(self, mock_get_ops, runner):
        """Test upscale command shows monitoring instructions."""
        # Setup mock operations
        mock_ops = MagicMock()
        mock_get_ops.return_value = mock_ops

        # Setup test data
        mock_ops.upscale_run.return_value = {
            "upscale_run_id": "rs_upscale456",
            "status": "success",
            "output_path": "/output/test_4k.mp4",
        }

        result = runner.invoke(cli, ["upscale", "rs_inference123"])

        assert result.exit_code == 0
        # Should show monitoring instructions
        assert "cosmos status" in result.output or "monitor" in result.output.lower()

    @patch("cosmos_workflow.cli.base.CLIContext.get_operations")
    def test_upscale_displays_run_id(self, mock_get_ops, runner):
        """Test upscale command displays the new upscale run ID."""
        # Setup mock operations
        mock_ops = MagicMock()
        mock_get_ops.return_value = mock_ops

        # Setup test data
        mock_ops.upscale_run.return_value = {
            "upscale_run_id": "rs_upscale456",
            "status": "success",
            "output_path": "/output/test_4k.mp4",
        }

        result = runner.invoke(cli, ["upscale", "rs_inference123"])

        assert result.exit_code == 0
        # Should display the upscale run ID
        assert "rs_upscale456" in result.output

    @patch("cosmos_workflow.cli.base.CLIContext.get_operations")
    def test_upscale_dry_run(self, mock_get_ops, runner):
        """Test dry-run mode shows preview without executing."""
        # Setup mock operations
        mock_ops = MagicMock()
        mock_get_ops.return_value = mock_ops

        # Mock get_run for dry-run preview
        mock_ops.get_run.return_value = {
            "id": "rs_inference123",
            "status": "completed",
            "outputs": {"output_path": "/output/test.mp4"},
        }

        result = runner.invoke(cli, ["upscale", "rs_inference123", "--dry-run"])

        # Should not execute
        mock_ops.upscale_run.assert_not_called()

        # Should show preview info
        assert result.exit_code == 0
        assert "dry" in result.output.lower() or "preview" in result.output.lower()
        assert "rs_inference123" in result.output

    @patch("cosmos_workflow.cli.base.CLIContext.get_operations")
    def test_upscale_validates_run_id_format(self, mock_get_ops, runner):
        """Test upscale command validates run ID format."""
        # Setup mock operations
        mock_ops = MagicMock()
        mock_get_ops.return_value = mock_ops

        # Test invalid run ID format
        result = runner.invoke(cli, ["upscale", "invalid-id"])

        # Should show error for invalid format
        assert result.exit_code != 0 or "invalid" in result.output.lower()

    @patch("cosmos_workflow.cli.base.CLIContext.get_operations")
    def test_upscale_without_arguments_shows_help(self, mock_get_ops, runner):
        """Test upscale command without arguments shows help."""
        result = runner.invoke(cli, ["upscale"])

        # Should show help or error
        assert result.exit_code != 0
        assert "usage" in result.output.lower() or "error" in result.output.lower()
