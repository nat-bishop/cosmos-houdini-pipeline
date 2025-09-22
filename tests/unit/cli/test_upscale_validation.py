"""Tests for upscale CLI command validation and edge cases."""

from unittest.mock import Mock

import pytest
from click.testing import CliRunner

from cosmos_workflow.cli.base import CLIContext
from cosmos_workflow.cli.upscale import upscale


class TestUpscaleCLIValidation:
    """Test CLI validation for upscale command."""

    @pytest.fixture
    def runner(self):
        """Create a CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_context(self):
        """Create a mock CLI context."""
        ctx = Mock(spec=CLIContext)
        mock_ops = Mock()
        ctx.get_operations = Mock(return_value=mock_ops)
        return ctx

    def test_no_run_id_provided_error(self, runner):
        """Test that error is shown when no run ID is provided."""
        # Create a mock context
        mock_ctx = Mock(spec=CLIContext)
        mock_ops = Mock()
        mock_ctx.get_operations = Mock(return_value=mock_ops)

        # Run command with no arguments
        result = runner.invoke(upscale, [], obj=mock_ctx)

        # Should fail with exit code 2 (missing required argument)
        assert result.exit_code == 2
        assert "Missing argument 'RUN_ID'" in result.output

    def test_invalid_run_id_format(self, runner):
        """Test that invalid run ID format is rejected."""
        # Create a mock context
        mock_ctx = Mock(spec=CLIContext)
        mock_ops = Mock()
        mock_ctx.get_operations = Mock(return_value=mock_ops)

        # Invalid format (doesn't start with rs_ or run_)
        result = runner.invoke(upscale, ["invalid_id"], obj=mock_ctx)

        assert result.exit_code == 1
        assert "Invalid run ID format" in result.output

    def test_valid_run_id_formats(self, runner):
        """Test that valid run ID formats are accepted."""
        # Create a mock context
        mock_ctx = Mock(spec=CLIContext)
        mock_ops = Mock()
        # Mock a successful upscale operation
        mock_ops.upscale = Mock(
            return_value={"status": "started", "upscale_run_id": "rs_upscale123"}
        )
        mock_ctx.get_operations = Mock(return_value=mock_ops)

        # Test with rs_ prefix
        runner.invoke(upscale, ["rs_inference123"], obj=mock_ctx)
        # Should call the upscale method (may fail for other reasons, but syntax is valid)
        assert mock_ops.upscale.called
        assert mock_ops.upscale.call_args[1]["run_id"] == "rs_inference123"

        # Reset mock
        mock_ops.upscale.reset_mock()

        # Test with run_ prefix
        runner.invoke(upscale, ["run_inference123"], obj=mock_ctx)
        assert mock_ops.upscale.called
        assert mock_ops.upscale.call_args[1]["run_id"] == "run_inference123"

    def test_video_file_path_rejected(self, runner):
        """Test that video file paths are properly rejected with helpful message."""
        # Create a mock context
        mock_ctx = Mock(spec=CLIContext)
        mock_ops = Mock()
        mock_ctx.get_operations = Mock(return_value=mock_ops)

        # Try with a video file path
        result = runner.invoke(upscale, ["/path/to/video.mp4"], obj=mock_ctx)

        assert result.exit_code == 1
        assert "Invalid run ID format" in result.output
        assert "To upscale external video files" in result.output

    def test_weight_out_of_range(self, runner):
        """Test that weight values outside 0-1 range are rejected."""
        # Create a mock context
        mock_ctx = Mock(spec=CLIContext)
        mock_ops = Mock()
        mock_ctx.get_operations = Mock(return_value=mock_ops)

        # Test weight > 1
        result = runner.invoke(upscale, ["rs_123", "--weight", "1.5"], obj=mock_ctx)
        assert result.exit_code == 2  # Click validation error

        # Test weight < 0
        result = runner.invoke(upscale, ["rs_123", "--weight", "-0.5"], obj=mock_ctx)
        assert result.exit_code == 2  # Click validation error

    def test_valid_weight_values(self, runner):
        """Test that valid weight values are accepted."""
        # Create a mock context
        mock_ctx = Mock(spec=CLIContext)
        mock_ops = Mock()
        mock_ops.upscale = Mock(return_value={"status": "started", "upscale_run_id": "rs_123"})
        mock_ctx.get_operations = Mock(return_value=mock_ops)

        # Test various valid weights
        for weight in [0.0, 0.5, 1.0]:
            mock_ops.upscale.reset_mock()
            runner.invoke(upscale, ["rs_123", "--weight", str(weight)], obj=mock_ctx)
            assert mock_ops.upscale.called
            assert mock_ops.upscale.call_args[1]["control_weight"] == weight

    def test_prompt_with_run_id(self, runner):
        """Test that prompt works with run ID."""
        # Create a mock context
        mock_ctx = Mock(spec=CLIContext)
        mock_ops = Mock()
        mock_ops.upscale = Mock(return_value={"status": "started", "upscale_run_id": "rs_456"})
        mock_ctx.get_operations = Mock(return_value=mock_ops)

        runner.invoke(upscale, ["rs_123", "--prompt", "cinematic quality"], obj=mock_ctx)

        # Should call upscale with prompt
        assert mock_ops.upscale.called
        assert mock_ops.upscale.call_args[1]["prompt"] == "cinematic quality"

    def test_dry_run_with_run_id(self, runner):
        """Test dry-run mode with run ID."""
        # Create a mock context
        mock_ctx = Mock(spec=CLIContext)
        mock_ops = Mock()
        mock_run = {"id": "rs_123", "status": "completed", "outputs": {"output_path": "test.mp4"}}
        mock_ops.get_run = Mock(return_value=mock_run)
        mock_ops.upscale = Mock()  # Should NOT be called in dry-run
        mock_ctx.get_operations = Mock(return_value=mock_ops)

        result = runner.invoke(upscale, ["rs_123", "--dry-run"], obj=mock_ctx)

        # Should show preview and NOT execute
        assert "Dry-run mode" in result.output
        assert "Would upscale from run" in result.output
        assert not mock_ops.upscale.called  # Should not execute in dry-run

    def test_run_not_found_in_dry_run(self, runner):
        """Test dry-run mode when run doesn't exist."""
        # Create a mock context
        mock_ctx = Mock(spec=CLIContext)
        mock_ops = Mock()
        mock_ops.get_run = Mock(return_value=None)  # Run not found
        mock_ctx.get_operations = Mock(return_value=mock_ops)

        result = runner.invoke(upscale, ["rs_nonexistent", "--dry-run"], obj=mock_ctx)

        # Should show error
        assert result.exit_code == 1
        assert "Run not found" in result.output
