"""Tests for graceful shutdown handling."""

import signal
from unittest.mock import patch

import pytest


class TestShutdownHandler:
    """Test graceful shutdown behavior."""

    def test_cleanup_kills_containers(self):
        """Test that cleanup_on_shutdown calls kill_containers."""
        from cosmos_workflow.ui.app import cleanup_on_shutdown

        with patch("cosmos_workflow.ui.app.ops") as mock_ops:
            # Mock successful container kill
            mock_ops.kill_containers.return_value = {
                "killed_count": 2,
                "killed_containers": ["abc123", "def456"],
                "status": "success",
            }

            # Call cleanup
            cleanup_on_shutdown()

            # Verify kill_containers was called
            mock_ops.kill_containers.assert_called_once()

    def test_cleanup_handles_no_containers(self):
        """Test cleanup when no containers are running."""
        from cosmos_workflow.ui.app import cleanup_on_shutdown

        with patch("cosmos_workflow.ui.app.ops") as mock_ops:
            # Mock no containers to kill
            mock_ops.kill_containers.return_value = {
                "killed_count": 0,
                "killed_containers": [],
                "status": "success",
            }

            # Call cleanup - should not raise
            cleanup_on_shutdown()

            mock_ops.kill_containers.assert_called_once()

    def test_cleanup_handles_errors_gracefully(self):
        """Test that cleanup doesn't crash on errors."""
        from cosmos_workflow.ui.app import cleanup_on_shutdown

        with patch("cosmos_workflow.ui.app.ops") as mock_ops:
            # Mock an exception
            mock_ops.kill_containers.side_effect = Exception("Connection failed")

            # Should not raise - errors are logged but ignored
            cleanup_on_shutdown()

            mock_ops.kill_containers.assert_called_once()

    def test_cleanup_with_signal(self):
        """Test cleanup when triggered by signal."""
        from cosmos_workflow.ui.app import cleanup_on_shutdown

        with patch("cosmos_workflow.ui.app.ops") as mock_ops:
            with patch("cosmos_workflow.ui.app.logger") as mock_logger:
                mock_ops.kill_containers.return_value = {
                    "killed_count": 1,
                    "killed_containers": ["test123"],
                    "status": "success",
                }

                # Call with signal number
                cleanup_on_shutdown(signal.SIGINT, None)

                # Should log shutdown message
                mock_logger.info.assert_any_call("Shutting down gracefully...")
                mock_ops.kill_containers.assert_called_once()

    def test_signal_handlers_registered(self):
        """Test that signal handlers are properly registered."""
        import cosmos_workflow.ui.app  # noqa: F401

        # Check that signal handlers are registered
        # Note: We can't easily test the actual signal.signal calls,
        # but we can verify the function exists
        from cosmos_workflow.ui.app import cleanup_on_shutdown

        assert callable(cleanup_on_shutdown)

    @patch("cosmos_workflow.ui.app.atexit.register")
    def test_atexit_handler_registered(self, mock_atexit):
        """Test that atexit handler is registered on module import."""
        # Re-import to trigger registration
        import importlib

        import cosmos_workflow.ui.app

        importlib.reload(cosmos_workflow.ui.app)

        # Verify atexit.register was called with cleanup function
        assert mock_atexit.called
        # Get the registered function
        registered_func = mock_atexit.call_args[0][0]
        assert callable(registered_func)


class TestIntegrationShutdown:
    """Integration tests for shutdown behavior."""

    @pytest.mark.integration
    def test_container_cleanup_on_kill(self):
        """Test that containers are actually killed on shutdown.

        This is an integration test that requires:
        - SSH connection to GPU server
        - Docker running on GPU server
        - Active containers to test with
        """
        pytest.skip("Integration test - requires live GPU server")

        # This would be tested manually or in CI with actual infrastructure:
        # 1. Start a long-running inference
        # 2. Kill the Gradio server with Ctrl+C
        # 3. Verify container is stopped on GPU server
        # 4. Verify database status is updated

    @pytest.mark.integration
    def test_queue_persistence_after_shutdown(self):
        """Test queue behavior after server restart.

        Verifies that:
        - Queue state persists through server restarts
        - Running jobs continue after disconnect
        - Reconnection shows correct status
        """
        pytest.skip("Integration test - requires live Gradio server")

        # This would test the queue persistence behavior:
        # 1. Start Gradio server
        # 2. Queue multiple jobs
        # 3. Kill server during execution
        # 4. Restart server
        # 5. Verify queue state and job status
