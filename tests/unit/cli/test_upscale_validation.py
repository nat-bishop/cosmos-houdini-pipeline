"""Tests for upscale CLI command validation and edge cases."""

from pathlib import Path
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
        ctx = Mock()
        ctx.get_operations = Mock()
        return ctx

    def test_no_source_provided_error(self, runner):
        """Test that error is shown when neither --from-run nor --video is provided."""
        # Create a mock context that will be passed to the command
        mock_ctx = Mock(spec=CLIContext)
        mock_ops = Mock()
        mock_ctx.get_operations = Mock(return_value=mock_ops)

        # Run command with no source
        result = runner.invoke(upscale, [], obj=mock_ctx)

        # Should fail with exit code 1
        assert result.exit_code == 1
        assert "You must specify either --from-run or --video" in result.output

    def test_both_sources_provided_error(self, runner):
        """Test that error is shown when both --from-run and --video are provided."""
        with runner.isolated_filesystem():
            # Create a dummy video file
            Path("test.mp4").touch()

            # Create a mock context
            mock_ctx = Mock(spec=CLIContext)
            mock_ops = Mock()
            mock_ctx.get_operations = Mock(return_value=mock_ops)

            # Run command with both sources
            result = runner.invoke(
                upscale, ["--from-run", "rs_123", "--video", "test.mp4"], obj=mock_ctx
            )

            # Should fail with exit code 1
            assert result.exit_code == 1
            assert "Cannot specify both --from-run and --video" in result.output

    def test_invalid_run_id_format(self, runner):
        """Test that invalid run ID format is rejected."""
        # Create a mock context
        mock_ctx = Mock(spec=CLIContext)
        mock_ops = Mock()
        mock_ctx.get_operations = Mock(return_value=mock_ops)

        # Invalid format (doesn't start with rs_ or run_)
        result = runner.invoke(upscale, ["--from-run", "invalid_id"], obj=mock_ctx)

        assert result.exit_code == 1
        assert "Invalid run ID format" in result.output

    def test_valid_run_id_formats(self, runner):
        """Test that valid run ID formats are accepted."""
        # Create a mock context
        mock_ctx = Mock(spec=CLIContext)
        mock_ops = Mock()
        mock_ops.get_run = Mock(return_value=None)  # Run not found
        mock_ops.upscale = Mock(side_effect=ValueError("Run not found: rs_123"))
        mock_ctx.get_operations = Mock(return_value=mock_ops)

        # Test rs_ prefix
        result = runner.invoke(upscale, ["--from-run", "rs_123"], obj=mock_ctx)
        # Will fail because run not found, but should pass ID format validation
        assert result.exit_code == 1
        # The error should be about run not found, not invalid format
        assert "Invalid run ID format" not in result.output

        # Test run_ prefix
        result = runner.invoke(upscale, ["--from-run", "run_456"], obj=mock_ctx)
        # Will fail because run not found, but should pass ID format validation
        assert result.exit_code == 1
        assert "Invalid run ID format" not in result.output

    def test_video_file_not_exists(self, runner):
        """Test that non-existent video file is rejected."""
        result = runner.invoke(upscale, ["--video", "nonexistent.mp4"])

        # Click validates the path exists
        assert result.exit_code == 2  # Click's exit code for invalid option
        assert "does not exist" in result.output.lower() or "invalid" in result.output.lower()

    def test_weight_out_of_range(self, runner):
        """Test that weight values outside 0.0-1.0 are rejected."""
        with runner.isolated_filesystem():
            Path("test.mp4").touch()

            # Test weight > 1.0
            result = runner.invoke(upscale, ["--video", "test.mp4", "--weight", "1.5"])
            assert result.exit_code == 2  # Click validation error

            # Test weight < 0.0
            result = runner.invoke(upscale, ["--video", "test.mp4", "--weight", "-0.5"])
            assert result.exit_code == 2  # Click validation error

    def test_valid_weight_values(self, runner):
        """Test that valid weight values are accepted."""
        with runner.isolated_filesystem():
            Path("test.mp4").touch()

            # Create a mock context
            mock_ctx = Mock(spec=CLIContext)
            mock_ops = Mock()
            mock_ops.upscale = Mock(return_value={"status": "started", "upscale_run_id": "rs_123"})
            mock_ctx.get_operations = Mock(return_value=mock_ops)

            # Test weight = 0.0
            result = runner.invoke(
                upscale, ["--video", "test.mp4", "--weight", "0.0"], obj=mock_ctx
            )
            # Should proceed to execution
            assert result.exit_code == 0
            assert mock_ops.upscale.called

            # Test weight = 1.0
            mock_ops.reset_mock()
            result = runner.invoke(
                upscale, ["--video", "test.mp4", "--weight", "1.0"], obj=mock_ctx
            )
            # Should proceed to execution
            assert result.exit_code == 0
            assert mock_ops.upscale.called

            # Test weight = 0.5 (default)
            mock_ops.reset_mock()
            result = runner.invoke(upscale, ["--video", "test.mp4"], obj=mock_ctx)
            # Should proceed to execution with default weight
            assert result.exit_code == 0
            assert mock_ops.upscale.called

    def test_prompt_with_from_run(self, runner):
        """Test that prompt works with --from-run."""
        # Create a mock context
        mock_ctx = Mock(spec=CLIContext)
        mock_ops = Mock()
        mock_run = {"id": "rs_123", "status": "completed", "outputs": {"output_path": "test.mp4"}}
        mock_ops.get_run = Mock(return_value=mock_run)
        mock_ops.upscale = Mock(return_value={"status": "started", "upscale_run_id": "rs_456"})
        mock_ctx.get_operations = Mock(return_value=mock_ops)

        runner.invoke(
            upscale, ["--from-run", "rs_123", "--prompt", "enhance quality"], obj=mock_ctx
        )

        # Should call upscale with prompt
        assert mock_ops.upscale.called
        call_kwargs = mock_ops.upscale.call_args.kwargs
        assert call_kwargs.get("prompt") == "enhance quality"

    def test_prompt_with_video(self, runner):
        """Test that prompt works with --video."""
        with runner.isolated_filesystem():
            Path("test.mp4").touch()

            # Create a mock context
            mock_ctx = Mock(spec=CLIContext)
            mock_ops = Mock()
            mock_ops.upscale = Mock(return_value={"status": "started", "upscale_run_id": "rs_456"})
            mock_ctx.get_operations = Mock(return_value=mock_ops)

            runner.invoke(
                upscale, ["--video", "test.mp4", "--prompt", "cinematic 8K"], obj=mock_ctx
            )

            # Should call upscale with prompt
            assert mock_ops.upscale.called
            call_kwargs = mock_ops.upscale.call_args.kwargs
            assert call_kwargs.get("prompt") == "cinematic 8K"

    def test_dry_run_with_from_run(self, runner):
        """Test dry-run mode with --from-run."""
        # Create a mock context
        mock_ctx = Mock(spec=CLIContext)
        mock_ops = Mock()
        mock_run = {"id": "rs_123", "status": "completed", "outputs": {"output_path": "test.mp4"}}
        mock_ops.get_run = Mock(return_value=mock_run)
        mock_ops.upscale = Mock()  # Should NOT be called in dry-run
        mock_ctx.get_operations = Mock(return_value=mock_ops)

        result = runner.invoke(upscale, ["--from-run", "rs_123", "--dry-run"], obj=mock_ctx)

        # Should show preview and NOT execute
        assert "Dry-run mode" in result.output
        assert "No changes made" in result.output
        assert not mock_ops.upscale.called

    def test_dry_run_with_video(self, runner):
        """Test dry-run mode with --video."""
        with runner.isolated_filesystem():
            # Create a test video file with some size
            test_file = Path("test.mp4")
            test_file.write_bytes(b"dummy video content")

            # Create a mock context
            mock_ctx = Mock(spec=CLIContext)
            mock_ops = Mock()
            mock_ops.upscale = Mock()  # Should NOT be called in dry-run
            mock_ctx.get_operations = Mock(return_value=mock_ops)

            result = runner.invoke(upscale, ["--video", "test.mp4", "--dry-run"], obj=mock_ctx)

            # Should show preview and NOT execute
            assert "Dry-run mode" in result.output
            assert "Would upscale video" in result.output
            assert "File size" in result.output
            assert "No changes made" in result.output
            assert not mock_ops.upscale.called
