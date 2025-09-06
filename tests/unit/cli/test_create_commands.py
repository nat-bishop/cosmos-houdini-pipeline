"""Behavioral tests for CLI create commands - TARGET BEHAVIOR.

These tests define the desired CLI behavior using WorkflowService and database.
They test the target state, not the current JSON-based implementation.
Following TDD Gate 1: Write tests for desired behavior.
These tests will initially FAIL until we implement the service integration.
"""

import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from cosmos_workflow.cli import cli


class TestCreatePromptCommand:
    """Test the 'cosmos create prompt' command behavior."""

    @pytest.fixture
    def runner(self):
        """Create a CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def test_video_dir(self):
        """Create a temporary directory with test video files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            video_dir = Path(tmpdir) / "test_videos"
            video_dir.mkdir()

            # Create mock video files
            (video_dir / "color.mp4").write_text("mock video content")
            (video_dir / "depth.mp4").write_text("mock depth content")
            (video_dir / "segmentation.mp4").write_text("mock segmentation content")

            yield video_dir

    def test_create_prompt_basic(self, runner, test_video_dir):
        """Test creating a basic prompt succeeds."""
        result = runner.invoke(
            cli, ["create", "prompt", "cyberpunk city at night", str(test_video_dir)]
        )

        # Test behavioral contract
        assert result.exit_code == 0
        assert "Prompt created successfully!" in result.output
        # Name is auto-generated from prompt
        assert "cyberpunk" in result.output.lower()
        # Should display the video path used
        assert str(test_video_dir) in result.output or "color.mp4" in result.output

    def test_create_prompt_with_name(self, runner, test_video_dir):
        """Test creating a prompt with custom name."""
        result = runner.invoke(
            cli,
            [
                "create",
                "prompt",
                "futuristic scene",
                str(test_video_dir),
                "--name",
                "my_custom_prompt",
            ],
        )

        assert result.exit_code == 0
        assert "Prompt created successfully!" in result.output
        assert "my_custom_prompt" in result.output

    def test_create_prompt_with_negative(self, runner, test_video_dir):
        """Test creating a prompt with custom negative prompt."""
        custom_negative = "low quality, blurry, artifacts"
        result = runner.invoke(
            cli,
            [
                "create",
                "prompt",
                "beautiful landscape",
                str(test_video_dir),
                "--negative",
                custom_negative,
            ],
        )

        assert result.exit_code == 0
        assert "Prompt created successfully!" in result.output
        # The negative prompt should be stored (though not necessarily displayed)

    def test_create_prompt_missing_video_dir(self, runner):
        """Test that missing video directory causes error."""
        result = runner.invoke(cli, ["create", "prompt", "test prompt", "/nonexistent/directory"])

        assert result.exit_code != 0
        # Should have an error message
        assert "error" in result.output.lower() or "not found" in result.output.lower()

    def test_create_prompt_missing_video_files(self, runner):
        """Test that missing required color.mp4 file causes error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            video_dir = Path(tmpdir) / "incomplete_videos"
            video_dir.mkdir()
            # Don't create color.mp4 - this should cause an error

            result = runner.invoke(cli, ["create", "prompt", "test prompt", str(video_dir)])

            # Should fail when color.mp4 is missing
            assert result.exit_code != 0
            assert "color.mp4" in result.output.lower() or "not found" in result.output.lower()

    def test_create_prompt_with_color_only(self, runner):
        """Test that prompt creation works with only color.mp4 (depth and segmentation optional)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            video_dir = Path(tmpdir) / "color_only_videos"
            video_dir.mkdir()
            # Only create color.mp4 - depth and segmentation are optional
            (video_dir / "color.mp4").write_text("mock content")

            result = runner.invoke(cli, ["create", "prompt", "test prompt", str(video_dir)])

            # Should succeed with only color.mp4
            assert result.exit_code == 0
            assert "successfully" in result.output.lower()

    def test_create_prompt_auto_generates_name(self, runner, test_video_dir):
        """Test that name is auto-generated when not provided."""
        result = runner.invoke(
            cli, ["create", "prompt", "epic cyberpunk transformation scene", str(test_video_dir)]
        )

        assert result.exit_code == 0
        assert "Prompt created successfully!" in result.output
        # Should show some generated name (not the full prompt text)
        # Name generation might truncate or simplify the prompt


class TestCLIIntegration:
    """Test integration between CLI commands."""

    @pytest.fixture
    def runner(self):
        """Create a CLI test runner."""
        return CliRunner()

    def test_cli_help_works(self, runner):
        """Test that help command works."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "cosmos" in result.output.lower()

    def test_create_help_works(self, runner):
        """Test that create help works."""
        result = runner.invoke(cli, ["create", "--help"])
        assert result.exit_code == 0
        assert "create" in result.output.lower()
        assert "prompt" in result.output.lower()

    def test_create_prompt_help_works(self, runner):
        """Test that create prompt help works."""
        result = runner.invoke(cli, ["create", "prompt", "--help"])
        assert result.exit_code == 0
        assert "prompt_text" in result.output.lower() or "prompt" in result.output.lower()
        assert "video" in result.output.lower()

    def test_verbose_flag_increases_output(self, runner):
        """Test that verbose flag provides more output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            video_dir = Path(tmpdir) / "videos"
            video_dir.mkdir()
            (video_dir / "color.mp4").write_text("mock")
            (video_dir / "depth.mp4").write_text("mock")
            (video_dir / "segmentation.mp4").write_text("mock")

            # Run without verbose
            result_normal = runner.invoke(cli, ["create", "prompt", "test", str(video_dir)])

            # Run with verbose
            result_verbose = runner.invoke(
                cli, ["--verbose", "create", "prompt", "test", str(video_dir)]
            )

            # Verbose should have more output (or at least not less)
            assert len(result_verbose.output) >= len(result_normal.output)
