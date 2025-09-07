#!/usr/bin/env python3
"""Tests for cosmos stream CLI command.

These tests verify behavior:
- Streams logs for specific run ID
- Streams latest run when no ID provided
- Shows tail before streaming
- Handles --no-follow flag
- Handles errors gracefully
"""

from unittest.mock import MagicMock, patch

import click.testing

from cosmos_workflow.cli.stream import stream


class TestStreamCommand:
    """Test the cosmos stream CLI command."""

    def test_stream_with_run_id(self):
        """Test streaming logs for a specific run ID (behavior)."""
        runner = click.testing.CliRunner()

        with patch("cosmos_workflow.cli.stream.CLIContext") as mock_ctx_class:
            mock_ctx = MagicMock()
            mock_ctx_class.return_value = mock_ctx

            mock_ops = MagicMock()
            mock_ctx.get_operations.return_value = mock_ops

            # Mock successful streaming
            mock_ops.stream_run_logs.return_value = {
                "run_id": "rn_123",
                "log_path": "outputs/test/logs/run_rn_123.log",
                "status": "streaming",
            }

            # Run command with specific run ID
            result = runner.invoke(stream, ["rn_123"], obj=mock_ctx)

            # Verify operations called correctly
            mock_ops.stream_run_logs.assert_called_once_with(
                run_id="rn_123",
                tail_lines=100,  # default
                follow=True,  # default
            )

            # Verify output shows streaming message
            assert "Streaming logs" in result.output
            assert "showing last 100 lines" in result.output

    def test_stream_without_run_id_uses_latest(self):
        """Test streaming latest run when no ID provided (behavior)."""
        runner = click.testing.CliRunner()

        with patch("cosmos_workflow.cli.stream.CLIContext") as mock_ctx_class:
            mock_ctx = MagicMock()
            mock_ctx_class.return_value = mock_ctx

            mock_ops = MagicMock()
            mock_ctx.get_operations.return_value = mock_ops

            # Mock successful streaming
            mock_ops.stream_run_logs.return_value = {
                "run_id": "rn_latest",
                "log_path": "outputs/test/logs/run_rn_latest.log",
                "status": "streaming",
            }

            # Run command without run ID
            result = runner.invoke(stream, [], obj=mock_ctx)

            # Verify operations called with None for run_id
            mock_ops.stream_run_logs.assert_called_once_with(
                run_id=None,  # Should use latest
                tail_lines=100,
                follow=True,
            )

            assert result.exit_code == 0

    def test_stream_with_custom_tail_lines(self):
        """Test that --tail-lines parameter is passed correctly (behavior)."""
        runner = click.testing.CliRunner()

        with patch("cosmos_workflow.cli.stream.CLIContext") as mock_ctx_class:
            mock_ctx = MagicMock()
            mock_ctx_class.return_value = mock_ctx

            mock_ops = MagicMock()
            mock_ctx.get_operations.return_value = mock_ops

            mock_ops.stream_run_logs.return_value = {
                "run_id": "rn_123",
                "log_path": "outputs/test/logs/run_rn_123.log",
                "status": "streaming",
            }

            # Run with custom tail lines
            result = runner.invoke(stream, ["--tail-lines", "50", "rn_123"], obj=mock_ctx)

            # Verify tail_lines parameter passed
            mock_ops.stream_run_logs.assert_called_once_with(
                run_id="rn_123",
                tail_lines=50,  # Custom value
                follow=True,
            )

            assert "showing last 50 lines" in result.output

    def test_stream_no_follow_just_shows_tail(self):
        """Test that --no-follow only shows tail without streaming (behavior)."""
        runner = click.testing.CliRunner()

        with patch("cosmos_workflow.cli.stream.CLIContext") as mock_ctx_class:
            mock_ctx = MagicMock()
            mock_ctx_class.return_value = mock_ctx

            mock_ops = MagicMock()
            mock_ctx.get_operations.return_value = mock_ops

            mock_ops.stream_run_logs.return_value = {
                "run_id": "rn_123",
                "log_path": "outputs/test/logs/run_rn_123.log",
                "status": "tailed",
            }

            # Run with --no-follow
            result = runner.invoke(stream, ["--no-follow", "-t", "200", "rn_123"], obj=mock_ctx)

            # Verify follow=False passed
            mock_ops.stream_run_logs.assert_called_once_with(
                run_id="rn_123",
                tail_lines=200,
                follow=False,  # No streaming
            )

            assert "Showing last 200 lines" in result.output
            assert "Streaming" not in result.output

    def test_stream_handles_no_runs_error(self):
        """Test graceful handling when no runs exist (edge case)."""
        runner = click.testing.CliRunner()

        with patch("cosmos_workflow.cli.stream.CLIContext") as mock_ctx_class:
            mock_ctx = MagicMock()
            mock_ctx_class.return_value = mock_ctx

            mock_ops = MagicMock()
            mock_ctx.get_operations.return_value = mock_ops

            # Mock ValueError for no runs
            mock_ops.stream_run_logs.side_effect = ValueError("No runs found")

            # Run command
            result = runner.invoke(stream, [], obj=mock_ctx)

            # Should show error message
            assert "No runs found" in result.output
            assert "cosmos list runs" in result.output  # Helpful tip

    def test_stream_handles_run_not_found(self):
        """Test graceful handling when run doesn't exist (edge case)."""
        runner = click.testing.CliRunner()

        with patch("cosmos_workflow.cli.stream.CLIContext") as mock_ctx_class:
            mock_ctx = MagicMock()
            mock_ctx_class.return_value = mock_ctx

            mock_ops = MagicMock()
            mock_ctx.get_operations.return_value = mock_ops

            # Mock ValueError for run not found
            mock_ops.stream_run_logs.side_effect = ValueError("Run not found: rn_invalid")

            # Run command
            result = runner.invoke(stream, ["rn_invalid"], obj=mock_ctx)

            # Should show error message
            assert "Run not found: rn_invalid" in result.output
            assert "cosmos list runs" in result.output

    def test_stream_handles_keyboard_interrupt(self):
        """Test graceful handling of Ctrl+C (behavior)."""
        runner = click.testing.CliRunner()

        with patch("cosmos_workflow.cli.stream.CLIContext") as mock_ctx_class:
            mock_ctx = MagicMock()
            mock_ctx_class.return_value = mock_ctx

            mock_ops = MagicMock()
            mock_ctx.get_operations.return_value = mock_ops

            # Mock KeyboardInterrupt
            mock_ops.stream_run_logs.side_effect = KeyboardInterrupt()

            # Run command
            result = runner.invoke(stream, ["rn_123"], obj=mock_ctx)

            # Should show clean exit message
            assert "Stopped streaming logs" in result.output

    def test_stream_handles_unexpected_errors(self):
        """Test handling of unexpected errors (edge case)."""
        runner = click.testing.CliRunner()

        with patch("cosmos_workflow.cli.stream.CLIContext") as mock_ctx_class:
            mock_ctx = MagicMock()
            mock_ctx_class.return_value = mock_ctx

            mock_ops = MagicMock()
            mock_ctx.get_operations.return_value = mock_ops

            # Mock unexpected error
            mock_ops.stream_run_logs.side_effect = RuntimeError("SSH connection lost")

            # Run command
            result = runner.invoke(stream, ["rn_123"], obj=mock_ctx)

            # Should show error
            assert "SSH connection lost" in result.output
