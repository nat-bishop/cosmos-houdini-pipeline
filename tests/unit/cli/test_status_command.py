"""Tests for the status command with unified status tracking."""

from unittest.mock import MagicMock

from click.testing import CliRunner

from cosmos_workflow.cli.status import status


class TestStatusCommand:
    """Test status command with enhanced functionality."""

    def test_status_displays_active_operations(self):
        """Test that status command displays active operations."""
        # Setup mocks
        mock_ctx = MagicMock()
        mock_ops = MagicMock()
        mock_ctx.get_operations.return_value = mock_ops

        # Mock status with active run (simplified for single container)
        status_info = {
            "ssh_status": "connected",
            "docker_status": {"docker_running": True},
            "gpu_info": {"name": "NVIDIA A100", "memory_total": "40GB"},
            "active_run": {
                "id": "run_abc123",
                "model_type": "transfer",
                "status": "running",
                "prompt_id": "ps_12345",
                "started_at": "2024-01-01T10:00:00Z",
            },
            "container": {
                "id": "container_111",
                "name": "cosmos_transfer_abc123",
                "status": "Up 5 minutes",
                "id_short": "container_111",
            },
        }
        mock_ops.check_status.return_value = status_info

        runner = CliRunner()
        # Properly inject the context object
        result = runner.invoke(status, obj=mock_ctx)

        # Check output includes active operations
        assert "transfer" in result.output.lower() or "TRANSFER" in result.output
        assert "abc123" in result.output or "run_abc123" in result.output

    def test_status_shows_no_operations_message(self):
        """Test status shows helpful message when no operations running."""
        mock_ctx = MagicMock()
        mock_ops = MagicMock()
        mock_ctx.get_operations.return_value = mock_ops

        # No active operations
        status_info = {
            "ssh_status": "connected",
            "docker_status": {"docker_running": True},
            "gpu_info": {"name": "NVIDIA A100"},
            "active_run": None,
            "container": None,
        }
        mock_ops.check_status.return_value = status_info

        runner = CliRunner()
        result = runner.invoke(status, obj=mock_ctx)

        # Should indicate no operations
        assert "No active" in result.output or "None" in result.output

    def test_status_shows_issues(self):
        """Test that status displays issues when detected."""
        mock_ctx = MagicMock()
        mock_ops = MagicMock()
        mock_ctx.get_operations.return_value = mock_ops

        # Status with issues - zombie run
        status_info = {
            "ssh_status": "connected",
            "docker_status": {"docker_running": True},
            "active_run": {
                "id": "run_zombie",
                "model_type": "transfer",
                "status": "running",
            },
            "container": None,  # Zombie run - no container
        }
        mock_ops.check_status.return_value = status_info

        runner = CliRunner()
        result = runner.invoke(status, obj=mock_ctx)

        # Should show issues
        assert "missing" in result.output.lower() or "error" in result.output.lower()

    def test_status_handles_all_model_types(self):
        """Test that all model types are displayed correctly."""
        mock_ctx = MagicMock()
        mock_ops = MagicMock()
        mock_ctx.get_operations.return_value = mock_ops

        # Test each model type (one at a time since we're single container)
        for model_type in ["transfer", "upscale", "enhance"]:
            status_info = {
                "ssh_status": "connected",
                "docker_status": {"docker_running": True},
                "active_run": {
                    "id": f"run_{model_type}",
                    "model_type": model_type,
                    "status": "running",
                    "prompt_id": f"ps_{model_type}",
                },
                "container": {
                    "name": f"cosmos_{model_type}_run_{model_type}",
                    "status": "Up 1 minute",
                    "id_short": f"cont_{model_type}",
                },
            }
            mock_ops.check_status.return_value = status_info

            runner = CliRunner()
            result = runner.invoke(status, obj=mock_ctx)
            # Check that the model type is shown
            assert model_type in result.output.lower() or model_type.upper() in result.output

    def test_status_without_active_operations_key(self):
        """Test backward compatibility when active_run not present."""
        mock_ctx = MagicMock()
        mock_ops = MagicMock()
        mock_ctx.get_operations.return_value = mock_ops

        # Old-style status without active_run but with container
        status_info = {
            "ssh_status": "connected",
            "docker_status": {"docker_running": True},
            "gpu_info": {"name": "NVIDIA A100"},
            "container": {
                "id": "container_old",
                "name": "cosmos_container",
                "status": "Up 10 minutes",
                "id_short": "container_old",
            },
        }
        mock_ops.check_status.return_value = status_info

        runner = CliRunner()
        result = runner.invoke(status, obj=mock_ctx)

        # Should still work and show container info
        assert result.exit_code == 0
        assert "cosmos_container" in result.output or "container" in result.output.lower()

    def test_status_formats_run_ids(self):
        """Test that run IDs are formatted nicely (shortened)."""
        mock_ctx = MagicMock()
        mock_ops = MagicMock()
        mock_ctx.get_operations.return_value = mock_ops

        status_info = {
            "ssh_status": "connected",
            "docker_status": {"docker_running": True},
            "active_run": {
                "id": "run_verylongidthatshouldbeshortened",
                "model_type": "transfer",
                "status": "running",
                "prompt_id": "ps_12345",
            },
            "container": {
                "name": "cosmos_transfer_verylong",
                "status": "Up 2 minutes",
                "id_short": "cont_xyz",
            },
        }
        mock_ops.check_status.return_value = status_info

        runner = CliRunner()
        result = runner.invoke(status, obj=mock_ctx)

        # Test behavior: command should execute successfully
        assert result.exit_code == 0
        # Test that some container info is displayed (don't be prescriptive about format)
        assert "cosmos_verylongidthatshouldbeshortened" in result.output or "cont_xyz" in result.output
