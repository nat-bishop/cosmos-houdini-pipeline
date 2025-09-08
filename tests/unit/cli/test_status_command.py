"""Tests for the status command with unified status tracking."""

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from cosmos_workflow.cli.status import status


class TestStatusCommand:
    """Test status command with enhanced functionality."""

    @patch("cosmos_workflow.cli.status.CLIContext")
    def test_status_displays_active_operations(self, mock_ctx_class):
        """Test that status command displays active operations."""
        # Setup mocks
        mock_ctx = MagicMock()
        mock_ctx_class.return_value = mock_ctx
        mock_ops = MagicMock()
        mock_ctx.get_operations.return_value = mock_ops

        # Mock status with active operations
        status_info = {
            "ssh_status": "connected",
            "docker_status": {"docker_running": True},
            "gpu_info": {"name": "NVIDIA A100", "memory_total": "40GB"},
            "active_operations": [
                {
                    "id": "run_abc123",
                    "model_type": "transfer",
                    "status": "running",
                    "prompt_id": "ps_12345",
                    "container": {"id": "container_111", "name": "cosmos_transfer_abc123"},
                },
                {
                    "id": "run_def456",
                    "model_type": "upscale",
                    "status": "running",
                    "prompt_id": "ps_12345",
                    "container": {"id": "container_222", "name": "cosmos_upscale_def456"},
                },
            ],
        }
        mock_ops.check_status.return_value = status_info

        runner = CliRunner()
        result = runner.invoke(status)

        # Check output includes active operations
        assert "transfer" in result.output
        assert "upscale" in result.output
        assert "abc123" in result.output or "run_abc123" in result.output
        assert "def456" in result.output or "run_def456" in result.output

    @patch("cosmos_workflow.cli.status.CLIContext")
    def test_status_shows_no_operations_message(self, mock_ctx_class):
        """Test status shows helpful message when no operations running."""
        mock_ctx = MagicMock()
        mock_ctx_class.return_value = mock_ctx
        mock_ops = MagicMock()
        mock_ctx.get_operations.return_value = mock_ops

        # No active operations
        status_info = {
            "ssh_status": "connected",
            "docker_status": {"docker_running": True},
            "gpu_info": {"name": "NVIDIA A100"},
            "active_operations": [],
        }
        mock_ops.check_status.return_value = status_info

        runner = CliRunner()
        result = runner.invoke(status)

        # Should indicate no operations
        assert "No active" in result.output or "None" in result.output

    @patch("cosmos_workflow.cli.status.CLIContext")
    def test_status_shows_issues(self, mock_ctx_class):
        """Test that status displays issues when detected."""
        mock_ctx = MagicMock()
        mock_ctx_class.return_value = mock_ctx
        mock_ops = MagicMock()
        mock_ctx.get_operations.return_value = mock_ops

        # Status with issues
        status_info = {
            "ssh_status": "connected",
            "docker_status": {"docker_running": True},
            "active_operations": [
                {
                    "id": "run_zombie",
                    "model_type": "transfer",
                    "status": "running",
                    "container": None,  # Zombie run
                }
            ],
            "issues": ["Zombie run detected: run_zombie has no container"],
        }
        mock_ops.check_status.return_value = status_info

        runner = CliRunner()
        result = runner.invoke(status)

        # Should show issues
        assert "zombie" in result.output.lower() or "issue" in result.output.lower()

    @patch("cosmos_workflow.cli.status.CLIContext")
    def test_status_handles_all_model_types(self, mock_ctx_class):
        """Test that all model types are displayed correctly."""
        mock_ctx = MagicMock()
        mock_ctx_class.return_value = mock_ctx
        mock_ops = MagicMock()
        mock_ctx.get_operations.return_value = mock_ops

        # All three model types
        status_info = {
            "ssh_status": "connected",
            "docker_status": {"docker_running": True},
            "active_operations": [
                {"id": "run_1", "model_type": "transfer", "status": "running"},
                {"id": "run_2", "model_type": "upscale", "status": "running"},
                {"id": "run_3", "model_type": "enhance", "status": "running"},
            ],
        }
        mock_ops.check_status.return_value = status_info

        runner = CliRunner()
        result = runner.invoke(status)

        # All model types should be shown
        assert "transfer" in result.output
        assert "upscale" in result.output
        assert "enhance" in result.output

    @patch("cosmos_workflow.cli.status.CLIContext")
    def test_status_without_active_operations_key(self, mock_ctx_class):
        """Test backward compatibility when active_operations not present."""
        mock_ctx = MagicMock()
        mock_ctx_class.return_value = mock_ctx
        mock_ops = MagicMock()
        mock_ctx.get_operations.return_value = mock_ops

        # Old-style status without active_operations
        status_info = {
            "ssh_status": "connected",
            "docker_status": {"docker_running": True},
            "gpu_info": {"name": "NVIDIA A100"},
            "container": {
                "id": "container_old",
                "name": "cosmos_container",
                "status": "Up 10 minutes",
            },
        }
        mock_ops.check_status.return_value = status_info

        runner = CliRunner()
        result = runner.invoke(status)

        # Should still work and show container info
        assert result.exit_code == 0
        assert "cosmos_container" in result.output or "container" in result.output.lower()

    @patch("cosmos_workflow.cli.status.CLIContext")
    def test_status_formats_run_ids(self, mock_ctx_class):
        """Test that run IDs are formatted nicely (shortened)."""
        mock_ctx = MagicMock()
        mock_ctx_class.return_value = mock_ctx
        mock_ops = MagicMock()
        mock_ctx.get_operations.return_value = mock_ops

        status_info = {
            "ssh_status": "connected",
            "docker_status": {"docker_running": True},
            "active_operations": [
                {
                    "id": "run_verylongidthatshouldbeshortened",
                    "model_type": "transfer",
                    "status": "running",
                }
            ],
        }
        mock_ops.check_status.return_value = status_info

        runner = CliRunner()
        result = runner.invoke(status)

        # Should show shortened ID (first 8 chars typically)
        assert "verylong" in result.output or result.exit_code == 0
        # Should not show the entire long ID
        assert "verylongidthatshouldbeshortened" not in result.output
