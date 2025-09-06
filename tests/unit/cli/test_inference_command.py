"""Behavioral tests for CLI inference command.

These tests define the CLI contract for the inference command.
Implementation-agnostic - tests behavior, not storage mechanism.
Updated for 2-step workflow: inference accepts prompt IDs directly.
"""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from cosmos_workflow.cli import cli


class TestInferenceCommand:
    """Test the 'cosmos inference' command behavior with prompt IDs."""

    @pytest.fixture
    def runner(self):
        """Create a CLI test runner."""
        return CliRunner()

    @patch("cosmos_workflow.cli.base.CLIContext.get_operations")
    def test_inference_basic(self, mock_get_ops, runner):
        """Test basic inference command execution with prompt ID."""
        # Setup mock operations
        mock_ops = MagicMock()
        mock_get_ops.return_value = mock_ops

        # Setup test data for quick_inference
        mock_ops.quick_inference.return_value = {
            "run_id": "rs_auto123",
            "status": "success",
            "output_path": "/output/test.mp4",
        }

        result = runner.invoke(cli, ["inference", "ps_test"])

        # Behavioral assertions
        assert result.exit_code == 0
        assert "completed" in result.output.lower() or "success" in result.output.lower()

        # Should have called quick_inference with prompt ID
        mock_ops.quick_inference.assert_called_once()
        call_kwargs = mock_ops.quick_inference.call_args[1]
        assert call_kwargs["prompt_id"] == "ps_test"  # Keyword arg prompt_id

    @patch("cosmos_workflow.cli.base.CLIContext.get_operations")
    def test_inference_no_upscale(self, mock_get_ops, runner):
        """Test inference without upscaling."""
        # Setup mock operations
        mock_ops = MagicMock()
        mock_get_ops.return_value = mock_ops

        # Setup test data
        mock_ops.quick_inference.return_value = {
            "run_id": "rs_auto123",
            "status": "success",
            "output_path": "/output/test.mp4",
        }

        result = runner.invoke(cli, ["inference", "ps_test", "--no-upscale"])

        assert result.exit_code == 0
        assert "completed" in result.output.lower() or "success" in result.output.lower()

        # Should call quick_inference with upscale=False
        mock_ops.quick_inference.assert_called_once()
        call_kwargs = mock_ops.quick_inference.call_args[1]
        assert call_kwargs.get("upscale") is False

    @patch("cosmos_workflow.cli.base.CLIContext.get_operations")
    def test_inference_dry_run(self, mock_get_ops, runner):
        """Test dry-run mode doesn't execute."""
        # Setup mock operations
        mock_ops = MagicMock()
        mock_get_ops.return_value = mock_ops

        # Mock get_prompt for dry-run preview
        mock_ops.get_prompt.return_value = {
            "id": "ps_test",
            "prompt_text": "cyberpunk transformation",
            "inputs": {"video": "/test/video.mp4"},
            "model_type": "transfer",
        }

        result = runner.invoke(cli, ["inference", "ps_test", "--dry-run"])

        assert result.exit_code == 0
        assert "dry run" in result.output.lower()
        assert "ps_test" in result.output

        # Should NOT call quick_inference in dry-run mode
        mock_ops.quick_inference.assert_not_called()
        # Should call get_prompt to show preview
        mock_ops.get_prompt.assert_called_once_with("ps_test")

    @patch("cosmos_workflow.cli.base.CLIContext.get_operations")
    def test_inference_dry_run_with_options(self, mock_get_ops, runner):
        """Test dry-run with various options."""
        # Setup mock operations
        mock_ops = MagicMock()
        mock_get_ops.return_value = mock_ops

        # Mock get_prompt for dry-run preview
        mock_ops.get_prompt.return_value = {
            "id": "ps_test",
            "prompt_text": "test prompt",
            "inputs": {"video": "/test/video.mp4"},
            "model_type": "transfer",
        }

        result = runner.invoke(
            cli,
            [
                "inference",
                "ps_test",
                "--dry-run",
                "--no-upscale",
                "--weights",
                "0.3",
                "0.3",
                "0.2",
                "0.2",
            ],
        )

        assert result.exit_code == 0
        assert "dry run" in result.output.lower()

        # Should NOT execute in dry-run mode
        mock_ops.quick_inference.assert_not_called()

    @patch("cosmos_workflow.cli.base.CLIContext.get_operations")
    def test_inference_missing_prompt(self, mock_get_ops, runner):
        """Test error when prompt doesn't exist."""
        # Setup mock operations
        mock_ops = MagicMock()
        mock_get_ops.return_value = mock_ops

        # Simulate prompt not found
        mock_ops.quick_inference.side_effect = ValueError("Prompt ps_missing not found")

        result = runner.invoke(cli, ["inference", "ps_missing"])

        assert result.exit_code != 0
        assert "not found" in result.output.lower() or "error" in result.output.lower()

    @patch("cosmos_workflow.cli.base.CLIContext.get_operations")
    def test_inference_invalid_prompt_data(self, mock_get_ops, runner):
        """Test error when prompt has invalid data."""
        # Setup mock operations
        mock_ops = MagicMock()
        mock_get_ops.return_value = mock_ops

        # Simulate invalid prompt data
        mock_ops.quick_inference.side_effect = ValueError("Invalid prompt data: missing inputs")

        result = runner.invoke(cli, ["inference", "ps_invalid"])

        assert result.exit_code != 0
        assert "invalid" in result.output.lower() or "error" in result.output.lower()

    @patch("cosmos_workflow.cli.base.CLIContext.get_operations")
    def test_inference_with_upscale_weight(self, mock_get_ops, runner):
        """Test inference with custom upscale weight."""
        # Setup mock operations
        mock_ops = MagicMock()
        mock_get_ops.return_value = mock_ops

        mock_ops.quick_inference.return_value = {
            "run_id": "rs_auto123",
            "status": "success",
            "output_path": "/output/test.mp4",
        }

        result = runner.invoke(cli, ["inference", "ps_test", "--upscale-weight", "0.7"])

        assert result.exit_code == 0

        # Should pass upscale_weight to quick_inference
        mock_ops.quick_inference.assert_called_once()
        call_kwargs = mock_ops.quick_inference.call_args[1]
        assert call_kwargs.get("upscale_weight") == 0.7

    @patch("cosmos_workflow.cli.base.CLIContext.get_operations")
    def test_inference_handles_orchestrator_error(self, mock_get_ops, runner):
        """Test graceful handling of execution errors."""
        # Setup mock operations
        mock_ops = MagicMock()
        mock_get_ops.return_value = mock_ops

        # Simulate execution error
        mock_ops.quick_inference.side_effect = RuntimeError("GPU connection failed")

        result = runner.invoke(cli, ["inference", "ps_test"])

        assert result.exit_code != 0
        assert "error" in result.output.lower() or "failed" in result.output.lower()

    @patch("cosmos_workflow.cli.base.CLIContext.get_operations")
    def test_batch_inference(self, mock_get_ops, runner):
        """Test batch inference with multiple prompt IDs."""
        # Setup mock operations
        mock_ops = MagicMock()
        mock_get_ops.return_value = mock_ops

        # Mock batch_inference return
        mock_ops.batch_inference.return_value = {
            "batch_id": "batch_123",
            "results": [
                {"prompt_id": "ps_001", "run_id": "rs_auto1", "status": "success"},
                {"prompt_id": "ps_002", "run_id": "rs_auto2", "status": "success"},
                {"prompt_id": "ps_003", "run_id": "rs_auto3", "status": "success"},
            ],
        }

        result = runner.invoke(cli, ["inference", "ps_001", "ps_002", "ps_003"])

        assert result.exit_code == 0
        assert "batch" in result.output.lower() or "completed" in result.output.lower()

        # Should call batch_inference for multiple prompts
        mock_ops.batch_inference.assert_called_once()
        call_kwargs = mock_ops.batch_inference.call_args[1]
        assert call_kwargs["prompt_ids"] == ["ps_001", "ps_002", "ps_003"]


class TestInferenceIntegration:
    """Integration tests for inference command."""

    @pytest.fixture
    def runner(self):
        """Create a CLI test runner."""
        return CliRunner()

    @patch("cosmos_workflow.cli.base.CLIContext.get_operations")
    def test_inference_dry_run_shows_correct_info(self, mock_get_ops, runner):
        """Test dry-run displays all relevant information."""
        # Setup mock operations
        mock_ops = MagicMock()
        mock_get_ops.return_value = mock_ops

        # Setup detailed prompt data
        mock_ops.get_prompt.return_value = {
            "id": "ps_test",
            "prompt_text": "A futuristic city",
            "inputs": {
                "video": "/inputs/scene1/color.mp4",
                "depth": "/inputs/scene1/depth.mp4",
            },
            "model_type": "transfer",
            "parameters": {"negative_prompt": "blurry, low quality"},
        }

        result = runner.invoke(cli, ["inference", "ps_test", "--dry-run"])

        assert result.exit_code == 0
        # Should show prompt ID and text
        assert "ps_test" in result.output
        assert "futuristic city" in result.output.lower()
        # Should indicate dry-run mode
        assert "dry run" in result.output.lower()

    @patch("cosmos_workflow.cli.base.CLIContext.get_operations")
    def test_verbose_mode_shows_details(self, mock_get_ops, runner):
        """Test verbose mode provides detailed output."""
        # Setup mock operations
        mock_ops = MagicMock()
        mock_get_ops.return_value = mock_ops

        mock_ops.quick_inference.return_value = {
            "run_id": "rs_auto123",
            "status": "success",
            "output_path": "/outputs/run_rs_auto123/output.mp4",
            "duration_seconds": 120,
        }

        result = runner.invoke(cli, ["-v", "inference", "ps_test"])

        assert result.exit_code == 0
        # Verbose mode should show more details
        assert "rs_auto123" in result.output or "output" in result.output

    @patch("cosmos_workflow.cli.base.CLIContext.get_operations")
    def test_inference_with_weights(self, mock_get_ops, runner):
        """Test inference with custom control weights."""
        # Setup mock operations
        mock_ops = MagicMock()
        mock_get_ops.return_value = mock_ops

        mock_ops.quick_inference.return_value = {
            "run_id": "rs_auto123",
            "status": "success",
            "output_path": "/output/test.mp4",
        }

        result = runner.invoke(
            cli,
            ["inference", "ps_test", "--weights", "0.3", "0.3", "0.2", "0.2"],
        )

        assert result.exit_code == 0

        # Should pass weights to quick_inference
        mock_ops.quick_inference.assert_called_once()
        call_kwargs = mock_ops.quick_inference.call_args[1]
        expected_weights = {"vis": 0.3, "edge": 0.3, "depth": 0.2, "seg": 0.2}
        assert call_kwargs.get("weights") == expected_weights
