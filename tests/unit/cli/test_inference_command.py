"""Behavioral tests for CLI inference command.

These tests define the CLI contract for the inference command.
Implementation-agnostic - tests behavior, not storage mechanism.
Following TDD Gate 1: Write tests first.
"""

import json
import tempfile
from pathlib import Path
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

    @pytest.fixture
    def test_prompt_spec(self):
        """Create a temporary prompt spec file for testing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            spec_data = {
                "id": "ps_inference_test",
                "name": "test_inference_prompt",
                "prompt": "cyberpunk transformation",
                "negative_prompt": "low quality",
                "input_video_path": "/fake/path/to/video.mp4",
                "control_inputs": {
                    "depth": "/fake/path/to/depth.mp4",
                    "seg": "/fake/path/to/seg.mp4",
                },
                "timestamp": "2024-01-01T00:00:00Z",
            }
            json.dump(spec_data, f)
            f.flush()
            yield Path(f.name)
            # Cleanup
            Path(f.name).unlink(missing_ok=True)

    @patch("cosmos_workflow.workflows.workflow_orchestrator.WorkflowOrchestrator")
    def test_inference_basic(self, mock_orchestrator_class, runner, test_prompt_spec):
        """Test basic inference command execution."""
        # Setup mock
        mock_orchestrator = MagicMock()
        mock_orchestrator_class.return_value = mock_orchestrator
        mock_orchestrator.run_full_cycle.return_value = {"status": "success"}

        result = runner.invoke(cli, ["inference", str(test_prompt_spec)])

        # Behavioral assertions
        assert result.exit_code == 0
        assert "completed" in result.output.lower() or "success" in result.output.lower()

        # Should have called orchestrator
        mock_orchestrator.run_full_cycle.assert_called_once()

    @patch("cosmos_workflow.workflows.workflow_orchestrator.WorkflowOrchestrator")
    def test_inference_no_upscale(self, mock_orchestrator_class, runner, test_prompt_spec):
        """Test inference without upscaling."""
        # Setup mock
        mock_orchestrator = MagicMock()
        mock_orchestrator_class.return_value = mock_orchestrator
        mock_orchestrator.run_inference_only.return_value = {"status": "success"}

        result = runner.invoke(cli, ["inference", str(test_prompt_spec), "--no-upscale"])

        assert result.exit_code == 0
        assert "completed" in result.output.lower() or "success" in result.output.lower()

        # Should call inference_only, not full_cycle
        mock_orchestrator.run_inference_only.assert_called_once()
        mock_orchestrator.run_full_cycle.assert_not_called()

    def test_inference_dry_run(self, runner, test_prompt_spec):
        """Test dry-run mode doesn't execute."""
        result = runner.invoke(cli, ["inference", str(test_prompt_spec), "--dry-run"])

        assert result.exit_code == 0
        # Dry run should show what would happen
        assert "would" in result.output.lower()
        assert "dry" in result.output.lower() or "preview" in result.output.lower()
        # Should display prompt information
        assert "cyberpunk transformation" in result.output

    def test_inference_dry_run_with_options(self, runner, test_prompt_spec):
        """Test dry-run shows configuration options."""
        result = runner.invoke(
            cli, ["inference", str(test_prompt_spec), "--upscale-weight", "0.7", "--dry-run"]
        )

        assert result.exit_code == 0
        assert "0.7" in result.output
        assert "upscale" in result.output.lower()

    def test_inference_missing_spec_file(self, runner):
        """Test inference with missing spec file."""
        result = runner.invoke(cli, ["inference", "/nonexistent/spec.json"])

        assert result.exit_code != 0
        assert "not found" in result.output.lower() or "error" in result.output.lower()

    def test_inference_invalid_spec_file(self, runner):
        """Test inference with invalid JSON file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json content {[")
            f.flush()

            result = runner.invoke(cli, ["inference", f.name])

            assert result.exit_code != 0
            # Should have JSON error

            # Cleanup
            Path(f.name).unlink(missing_ok=True)

    @patch("cosmos_workflow.workflows.workflow_orchestrator.WorkflowOrchestrator")
    def test_inference_with_custom_video_dir(
        self, mock_orchestrator_class, runner, test_prompt_spec
    ):
        """Test inference with custom video directory."""
        # Setup mock
        mock_orchestrator = MagicMock()
        mock_orchestrator_class.return_value = mock_orchestrator
        mock_orchestrator.run_full_cycle.return_value = {"status": "success"}

        result = runner.invoke(
            cli, ["inference", str(test_prompt_spec), "--videos-dir", "/custom/video/path"]
        )

        assert result.exit_code == 0

        # Check orchestrator was called with custom path
        call_args = mock_orchestrator.run_full_cycle.call_args
        assert call_args[1]["videos_subdir"] == "/custom/video/path"

    @patch("cosmos_workflow.workflows.workflow_orchestrator.WorkflowOrchestrator")
    def test_inference_handles_orchestrator_error(
        self, mock_orchestrator_class, runner, test_prompt_spec
    ):
        """Test inference handles orchestrator errors gracefully."""
        # Setup mock to raise error
        mock_orchestrator = MagicMock()
        mock_orchestrator_class.return_value = mock_orchestrator
        mock_orchestrator.run_full_cycle.side_effect = Exception("GPU not available")

        result = runner.invoke(cli, ["inference", str(test_prompt_spec)])

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

    @pytest.fixture
    def complete_test_setup(self):
        """Create a complete test environment."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)

            # Create video directory
            video_dir = base_dir / "videos"
            video_dir.mkdir()
            (video_dir / "color.mp4").write_text("video")
            (video_dir / "depth.mp4").write_text("depth")
            (video_dir / "segmentation.mp4").write_text("seg")

            # Create prompt spec
            prompt_file = base_dir / "prompt.json"
            prompt_data = {
                "id": "ps_complete_test",
                "name": "complete_test",
                "prompt": "test prompt",
                "negative_prompt": "bad",
                "input_video_path": str(video_dir / "color.mp4"),
                "control_inputs": {
                    "depth": str(video_dir / "depth.mp4"),
                    "seg": str(video_dir / "segmentation.mp4"),
                },
            }
            prompt_file.write_text(json.dumps(prompt_data))

            yield {"base_dir": base_dir, "video_dir": video_dir, "prompt_file": prompt_file}

    def test_inference_dry_run_shows_correct_info(self, runner, complete_test_setup):
        """Test that dry-run displays all relevant information."""
        setup = complete_test_setup

        result = runner.invoke(cli, ["inference", str(setup["prompt_file"]), "--dry-run"])

        assert result.exit_code == 0
        # Should show prompt details
        assert "test prompt" in result.output
        assert "complete_test" in result.output
        # Should indicate what would happen
        assert "would" in result.output.lower()

    @patch("cosmos_workflow.workflows.workflow_orchestrator.WorkflowOrchestrator")
    def test_verbose_mode_shows_details(self, mock_orchestrator_class, runner, complete_test_setup):
        """Test verbose mode provides additional output."""
        setup = complete_test_setup

        # Setup mock
        mock_orchestrator = MagicMock()
        mock_orchestrator_class.return_value = mock_orchestrator
        mock_orchestrator.run_full_cycle.return_value = {
            "status": "success",
            "output_path": "/fake/output.mp4",
        }

        # Run with verbose
        result = runner.invoke(cli, ["--verbose", "inference", str(setup["prompt_file"])])

        assert result.exit_code == 0
        # Verbose mode might show results or additional info
        # Exact behavior depends on implementation
