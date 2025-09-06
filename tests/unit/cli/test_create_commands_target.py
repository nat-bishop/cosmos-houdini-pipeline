"""Behavioral tests for CLI create commands - TARGET BEHAVIOR.

These tests define the desired CLI behavior using WorkflowOperations.
Updated for 2-step workflow: removed create run command tests.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner


class TestCreatePromptCommandTarget:
    """Test the target behavior of 'cosmos create prompt' with WorkflowOperations."""

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

    @patch("cosmos_workflow.cli.base.CLIContext.get_operations")
    def test_create_prompt_uses_operations(self, mock_get_ops, runner, test_video_dir):
        """Test that create prompt uses WorkflowOperations and returns database ID."""
        # Setup mock operations
        mock_ops = MagicMock()
        mock_get_ops.return_value = mock_ops
        mock_ops.create_prompt.return_value = {
            "id": "ps_database_id_123",
            "model_type": "transfer",
            "prompt_text": "cyberpunk city at night",
            "inputs": {
                "video": str(test_video_dir / "color.mp4"),
                "depth": str(test_video_dir / "depth.mp4"),
                "segmentation": str(test_video_dir / "segmentation.mp4"),
            },
            "name": "cyberpunk_city",
            "created_at": "2024-01-01T00:00:00",
        }

        from cosmos_workflow.cli import cli

        result = runner.invoke(
            cli,
            [
                "create",
                "prompt",
                "cyberpunk city at night",
                str(test_video_dir),
            ],
        )

        assert result.exit_code == 0
        assert "Prompt created successfully!" in result.output or "Prompt created" in result.output
        assert "ps_database_id_123" in result.output  # Database ID is shown
        assert "cyberpunk_city" in result.output  # Name shown

        # Verify operations call
        mock_ops.create_prompt.assert_called_once()
        call_kwargs = mock_ops.create_prompt.call_args[1]
        assert call_kwargs["prompt_text"] == "cyberpunk city at night"
        assert str(test_video_dir) in str(call_kwargs["video_dir"])

    @patch("cosmos_workflow.cli.base.CLIContext.get_operations")
    def test_create_prompt_validates_files(self, mock_get_ops, runner):
        """Test that create prompt validates required video files."""
        # Setup mock operations
        mock_ops = MagicMock()
        mock_get_ops.return_value = mock_ops

        # Create dir without required color.mp4
        with tempfile.TemporaryDirectory() as tmpdir:
            video_dir = Path(tmpdir) / "invalid_videos"
            video_dir.mkdir()
            # Only create depth, missing color
            (video_dir / "depth.mp4").write_text("mock depth")

            from cosmos_workflow.cli import cli

            result = runner.invoke(
                cli,
                ["create", "prompt", "test prompt", str(video_dir)],
            )

            # Should fail validation
            assert result.exit_code != 0
            assert "color.mp4" in result.output.lower() or "not found" in result.output.lower()

    @patch("cosmos_workflow.cli.base.CLIContext.get_operations")
    def test_create_prompt_handles_db_error(self, mock_get_ops, runner, test_video_dir):
        """Test handling database errors from operations."""
        # Setup mock operations
        mock_ops = MagicMock()
        mock_get_ops.return_value = mock_ops
        mock_ops.create_prompt.side_effect = RuntimeError("Database connection failed")

        from cosmos_workflow.cli import cli

        result = runner.invoke(
            cli,
            ["create", "prompt", "test prompt", str(test_video_dir)],
        )

        assert result.exit_code != 0
        assert "error" in result.output.lower() or "failed" in result.output.lower()
        # Clear error message, no silent failure
        assert "database" in result.output.lower()


class TestInferenceCommandTarget:
    """Test the target behavior of 'cosmos inference' with WorkflowOperations."""

    @pytest.fixture
    def runner(self):
        """Create a CLI test runner."""
        return CliRunner()

    @patch("cosmos_workflow.cli.base.CLIContext.get_operations")
    def test_inference_with_prompt_id(self, mock_get_ops, runner):
        """Test inference accepts prompt ID directly."""
        # Setup mock operations
        mock_ops = MagicMock()
        mock_get_ops.return_value = mock_ops

        # Mock quick_inference result
        mock_ops.quick_inference.return_value = {
            "run_id": "rs_auto123",
            "prompt_id": "ps_test123",
            "status": "success",
            "output_path": "/outputs/run_rs_auto123/output.mp4",
            "duration_seconds": 120,
        }

        from cosmos_workflow.cli import cli

        result = runner.invoke(
            cli,
            ["inference", "ps_test123"],
        )

        assert result.exit_code == 0
        assert "completed" in result.output.lower() or "success" in result.output.lower()
        assert "output.mp4" in result.output or "rs_auto123" in result.output

        # Verify operations call
        mock_ops.quick_inference.assert_called_once()
        call_kwargs = mock_ops.quick_inference.call_args[1]
        assert call_kwargs["prompt_id"] == "ps_test123"

    @patch("cosmos_workflow.cli.base.CLIContext.get_operations")
    def test_inference_dry_run_shows_full_details(self, mock_get_ops, runner):
        """Test dry-run mode shows execution plan without running."""
        # Setup mock operations
        mock_ops = MagicMock()
        mock_get_ops.return_value = mock_ops

        # Mock get_prompt for dry-run preview
        mock_ops.get_prompt.return_value = {
            "id": "ps_test123",
            "prompt_text": "A futuristic city",
            "inputs": {
                "video": "/inputs/scene1/color.mp4",
                "depth": "/inputs/scene1/depth.mp4",
            },
            "parameters": {"negative_prompt": "blurry"},
        }

        from cosmos_workflow.cli import cli

        result = runner.invoke(
            cli,
            ["inference", "ps_test123", "--dry-run"],
        )

        assert result.exit_code == 0
        assert "dry run" in result.output.lower()
        assert "ps_test123" in result.output
        assert "futuristic city" in result.output.lower()

        # Should NOT call quick_inference in dry-run
        mock_ops.quick_inference.assert_not_called()
        # Should call get_prompt for preview
        mock_ops.get_prompt.assert_called_once_with("ps_test123")

    @patch("cosmos_workflow.cli.base.CLIContext.get_operations")
    def test_inference_prompt_not_found(self, mock_get_ops, runner):
        """Test error when prompt doesn't exist."""
        # Setup mock operations
        mock_ops = MagicMock()
        mock_get_ops.return_value = mock_ops
        mock_ops.quick_inference.side_effect = ValueError("Prompt ps_missing not found")

        from cosmos_workflow.cli import cli

        result = runner.invoke(
            cli,
            ["inference", "ps_missing"],
        )

        assert result.exit_code != 0
        assert "not found" in result.output.lower() or "error" in result.output.lower()
        assert "ps_missing" in result.output

    @patch("cosmos_workflow.cli.base.CLIContext.get_operations")
    def test_inference_already_running(self, mock_get_ops, runner):
        """Test handling of already running inference."""
        # Setup mock operations
        mock_ops = MagicMock()
        mock_get_ops.return_value = mock_ops
        mock_ops.quick_inference.side_effect = RuntimeError(
            "Prompt ps_test123 already has a running job"
        )

        from cosmos_workflow.cli import cli

        result = runner.invoke(
            cli,
            ["inference", "ps_test123"],
        )

        assert result.exit_code != 0
        assert "already" in result.output.lower() or "running" in result.output.lower()

    @patch("cosmos_workflow.cli.base.CLIContext.get_operations")
    def test_inference_with_upscaling(self, mock_get_ops, runner):
        """Test inference with upscaling options."""
        # Setup mock operations
        mock_ops = MagicMock()
        mock_get_ops.return_value = mock_ops

        mock_ops.quick_inference.return_value = {
            "run_id": "rs_auto123",
            "status": "success",
            "output_path": "/outputs/run_rs_auto123/output.mp4",
            "upscaled": True,
        }

        from cosmos_workflow.cli import cli

        result = runner.invoke(
            cli,
            ["inference", "ps_test123", "--upscale-weight", "0.8"],
        )

        assert result.exit_code == 0

        # Verify upscale weight passed
        mock_ops.quick_inference.assert_called_once()
        call_kwargs = mock_ops.quick_inference.call_args[1]
        assert call_kwargs.get("upscale_weight") == 0.8

    @patch("cosmos_workflow.cli.base.CLIContext.get_operations")
    def test_inference_updates_database_on_failure(self, mock_get_ops, runner):
        """Test that database is updated even when execution fails."""
        # Setup mock operations
        mock_ops = MagicMock()
        mock_get_ops.return_value = mock_ops
        mock_ops.quick_inference.side_effect = RuntimeError("GPU execution failed")

        from cosmos_workflow.cli import cli

        result = runner.invoke(
            cli,
            ["inference", "ps_test123"],
        )

        assert result.exit_code != 0
        assert "failed" in result.output.lower() or "error" in result.output.lower()


class TestInferenceProgress:
    """Test inference progress tracking."""

    @pytest.fixture
    def runner(self):
        """Create a CLI test runner."""
        return CliRunner()

    @patch("cosmos_workflow.cli.base.CLIContext.get_operations")
    def test_inference_tracks_progress(self, mock_get_ops, runner):
        """Test that inference shows progress updates."""
        # Setup mock operations
        mock_ops = MagicMock()
        mock_get_ops.return_value = mock_ops

        # Mock successful execution
        mock_ops.quick_inference.return_value = {
            "run_id": "rs_auto123",
            "status": "success",
            "output_path": "/outputs/run_rs_auto123/output.mp4",
        }

        from cosmos_workflow.cli import cli

        result = runner.invoke(
            cli,
            ["inference", "ps_test123"],
        )

        assert result.exit_code == 0
        # Should show some kind of progress/status
        assert any(
            word in result.output.lower()
            for word in ["processing", "running", "executing", "completed", "success"]
        )


class TestCLIOperationsIntegration:
    """Test CLI integration with WorkflowOperations."""

    @pytest.fixture
    def runner(self):
        """Create a CLI test runner."""
        return CliRunner()

    @patch("cosmos_workflow.api.workflow_operations.init_database")
    @patch("cosmos_workflow.cli.base.CLIContext.get_operations")
    def test_database_initialized_once_per_invocation(self, mock_get_ops, mock_init_db, runner):
        """Test that database is initialized once per CLI invocation."""
        # Setup mock operations
        mock_ops = MagicMock()
        mock_get_ops.return_value = mock_ops

        # Mock list operations
        mock_ops.list_prompts.return_value = []

        from cosmos_workflow.cli import cli

        # Single invocation
        result = runner.invoke(cli, ["list", "prompts"])
        assert result.exit_code == 0

        # Verify get_operations was called (which initializes database internally)
        mock_get_ops.assert_called()

    @patch("cosmos_workflow.cli.base.CLIContext.get_operations")
    def test_database_error_shows_clear_message(self, mock_get_ops, runner):
        """Test that database errors show clear messages."""
        # Simulate database initialization error
        mock_get_ops.side_effect = RuntimeError("Failed to connect to database")

        from cosmos_workflow.cli import cli

        result = runner.invoke(cli, ["list", "prompts"])

        assert result.exit_code != 0
        assert "database" in result.output.lower() or "failed" in result.output.lower()
