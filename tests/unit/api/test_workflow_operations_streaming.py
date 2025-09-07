#!/usr/bin/env python3
"""Tests for WorkflowOperations.stream_run_logs API.

These tests verify behavior not implementation:
- Resolves run IDs correctly (including latest run)
- Handles tail_lines parameter
- Supports both sync and async (callback) streaming
- Handles edge cases (no runs, missing logs, etc.)
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from cosmos_workflow.api import WorkflowOperations


class TestStreamRunLogs:
    """Test the stream_run_logs API method."""

    def test_stream_run_logs_with_specific_run_id(self):
        """Test streaming logs for a specific run ID (behavior)."""
        with patch("cosmos_workflow.api.workflow_operations.ConfigManager") as mock_config_class:
            with patch("cosmos_workflow.api.workflow_operations.init_database") as mock_init_db:
                with patch(
                    "cosmos_workflow.api.workflow_operations.WorkflowService"
                ) as mock_service_class:
                    with patch(
                        "cosmos_workflow.api.workflow_operations.WorkflowOrchestrator"
                    ) as mock_orch_class:
                        # Setup mocks
                        mock_config = MagicMock()
                        mock_config_class.return_value = mock_config
                        mock_db = MagicMock()
                        mock_init_db.return_value = mock_db

                        mock_service = MagicMock()
                        mock_service_class.return_value = mock_service

                        mock_orchestrator = MagicMock()
                        mock_orch_class.return_value = mock_orchestrator

                        # Mock run and prompt data
                        mock_run = {
                            "id": "rn_123",
                            "prompt_id": "ps_456",
                            "log_path": "outputs/test/logs/run_rn_123.log",
                        }
                        mock_prompt = {"prompt_name": "test_prompt"}
                        mock_service.get_run.return_value = mock_run
                        mock_service.get_prompt.return_value = mock_prompt

                        # Mock remote config
                        mock_remote_config = Mock(remote_dir="/workspace")
                        mock_config.get_remote_config.return_value = mock_remote_config

                        # Create API instance
                        ops = WorkflowOperations(config=mock_config)

                        # Mock RemoteLogStreamer
                        with patch(
                            "cosmos_workflow.api.workflow_operations.RemoteLogStreamer"
                        ) as mock_streamer_class:
                            mock_streamer = MagicMock()
                            mock_streamer_class.return_value = mock_streamer
                            mock_streamer.tail_log.return_value = ""

                            # Test streaming with specific run ID
                            result = ops.stream_run_logs(run_id="rn_123", follow=False)

                            # Verify correct run was fetched
                            mock_service.get_run.assert_called_once_with("rn_123")

                            # Verify result structure
                            assert result["run_id"] == "rn_123"
                            assert "log_path" in result
                            assert result["status"] == "tailed"

    def test_stream_run_logs_uses_latest_when_no_id(self):
        """Test that stream_run_logs uses the latest run when no ID provided (behavior)."""
        with patch("cosmos_workflow.api.workflow_operations.ConfigManager") as mock_config_class:
            with patch("cosmos_workflow.api.workflow_operations.init_database") as mock_init_db:
                with patch(
                    "cosmos_workflow.api.workflow_operations.WorkflowService"
                ) as mock_service_class:
                    with patch(
                        "cosmos_workflow.api.workflow_operations.WorkflowOrchestrator"
                    ) as mock_orch_class:
                        # Setup mocks
                        mock_config = MagicMock()
                        mock_config_class.return_value = mock_config
                        mock_db = MagicMock()
                        mock_init_db.return_value = mock_db

                        mock_service = MagicMock()
                        mock_service_class.return_value = mock_service

                        mock_orchestrator = MagicMock()
                        mock_orch_class.return_value = mock_orchestrator

                        # Mock latest run
                        mock_latest_run = {
                            "id": "rn_latest",
                            "prompt_id": "ps_789",
                            "log_path": None,  # Test path construction
                        }
                        mock_service.list_runs.return_value = [mock_latest_run]
                        mock_service.get_prompt.return_value = {"prompt_name": "latest_prompt"}

                        # Mock remote config
                        mock_remote_config = Mock(remote_dir="/workspace")
                        mock_config.get_remote_config.return_value = mock_remote_config

                        # Create API instance
                        ops = WorkflowOperations(config=mock_config)

                        with patch(
                            "cosmos_workflow.api.workflow_operations.RemoteLogStreamer"
                        ) as mock_streamer_class:
                            mock_streamer = MagicMock()
                            mock_streamer_class.return_value = mock_streamer
                            mock_streamer.tail_log.return_value = ""

                            # Test without run ID
                            result = ops.stream_run_logs(run_id=None, follow=False)

                            # Verify latest run was fetched
                            mock_service.list_runs.assert_called_once_with(limit=1)

                            # Verify result uses latest run
                            assert result["run_id"] == "rn_latest"

    def test_stream_run_logs_with_tail_lines(self):
        """Test that tail_lines parameter causes tail output before streaming (behavior)."""
        with patch("cosmos_workflow.api.workflow_operations.ConfigManager") as mock_config_class:
            with patch("cosmos_workflow.api.workflow_operations.init_database") as mock_init_db:
                with patch(
                    "cosmos_workflow.api.workflow_operations.WorkflowService"
                ) as mock_service_class:
                    with patch(
                        "cosmos_workflow.api.workflow_operations.WorkflowOrchestrator"
                    ) as mock_orch_class:
                        # Setup standard mocks
                        mock_config = MagicMock()
                        mock_config_class.return_value = mock_config
                        mock_init_db.return_value = MagicMock()
                        mock_service = MagicMock()
                        mock_service_class.return_value = mock_service
                        mock_orchestrator = MagicMock()
                        mock_orch_class.return_value = mock_orchestrator

                        mock_run = {"id": "rn_123", "prompt_id": "ps_456"}
                        mock_service.get_run.return_value = mock_run
                        mock_service.get_prompt.return_value = {"prompt_name": "test"}
                        mock_config.get_remote_config.return_value = Mock(remote_dir="/workspace")

                        ops = WorkflowOperations(config=mock_config)

                        with patch(
                            "cosmos_workflow.api.workflow_operations.RemoteLogStreamer"
                        ) as mock_streamer_class:
                            mock_streamer = MagicMock()
                            mock_streamer_class.return_value = mock_streamer

                            # Mock tail output
                            tail_output = "line 1\nline 2\nline 3"
                            mock_streamer.tail_log.return_value = tail_output

                            # Test with tail_lines
                            with patch("builtins.print") as mock_print:
                                ops.stream_run_logs(run_id="rn_123", tail_lines=50, follow=False)

                                # Verify tail was called with correct lines
                                mock_streamer.tail_log.assert_called_once()
                                call_args = mock_streamer.tail_log.call_args
                                assert call_args[0][1] == 50  # lines parameter

                                # Verify output was printed
                                mock_print.assert_called_once_with(tail_output)

    def test_stream_run_logs_raises_when_no_runs(self):
        """Test that stream_run_logs raises ValueError when no runs exist (edge case)."""
        with patch("cosmos_workflow.api.workflow_operations.ConfigManager") as mock_config_class:
            with patch("cosmos_workflow.api.workflow_operations.init_database") as mock_init_db:
                with patch(
                    "cosmos_workflow.api.workflow_operations.WorkflowService"
                ) as mock_service_class:
                    with patch(
                        "cosmos_workflow.api.workflow_operations.WorkflowOrchestrator"
                    ) as mock_orch_class:
                        # Setup mocks
                        mock_config = MagicMock()
                        mock_config_class.return_value = mock_config
                        mock_init_db.return_value = MagicMock()
                        mock_service = MagicMock()
                        mock_service_class.return_value = mock_service
                        mock_orch_class.return_value = MagicMock()

                        # No runs exist
                        mock_service.list_runs.return_value = []

                        ops = WorkflowOperations(config=mock_config)

                        # Should raise ValueError
                        with pytest.raises(ValueError, match="No runs found"):
                            ops.stream_run_logs(run_id=None)

    def test_stream_run_logs_raises_when_run_not_found(self):
        """Test that stream_run_logs raises ValueError for non-existent run (edge case)."""
        with patch("cosmos_workflow.api.workflow_operations.ConfigManager") as mock_config_class:
            with patch("cosmos_workflow.api.workflow_operations.init_database") as mock_init_db:
                with patch(
                    "cosmos_workflow.api.workflow_operations.WorkflowService"
                ) as mock_service_class:
                    with patch(
                        "cosmos_workflow.api.workflow_operations.WorkflowOrchestrator"
                    ) as mock_orch_class:
                        # Setup mocks
                        mock_config = MagicMock()
                        mock_config_class.return_value = mock_config
                        mock_init_db.return_value = MagicMock()
                        mock_service = MagicMock()
                        mock_service_class.return_value = mock_service
                        mock_orch_class.return_value = MagicMock()

                        # Run doesn't exist
                        mock_service.get_run.return_value = None

                        ops = WorkflowOperations(config=mock_config)

                        # Should raise ValueError
                        with pytest.raises(ValueError, match="Run not found: rn_invalid"):
                            ops.stream_run_logs(run_id="rn_invalid")

    def test_stream_run_logs_with_callback_runs_async(self):
        """Test that providing a callback causes async streaming in thread (behavior)."""
        with patch("cosmos_workflow.api.workflow_operations.ConfigManager") as mock_config_class:
            with patch("cosmos_workflow.api.workflow_operations.init_database") as mock_init_db:
                with patch(
                    "cosmos_workflow.api.workflow_operations.WorkflowService"
                ) as mock_service_class:
                    with patch(
                        "cosmos_workflow.api.workflow_operations.WorkflowOrchestrator"
                    ) as mock_orch_class:
                        # Setup standard mocks
                        mock_config = MagicMock()
                        mock_config_class.return_value = mock_config
                        mock_init_db.return_value = MagicMock()
                        mock_service = MagicMock()
                        mock_service_class.return_value = mock_service
                        mock_orchestrator = MagicMock()
                        mock_orch_class.return_value = mock_orchestrator

                        mock_run = {"id": "rn_123", "prompt_id": "ps_456"}
                        mock_service.get_run.return_value = mock_run
                        mock_service.get_prompt.return_value = {"prompt_name": "test"}
                        mock_config.get_remote_config.return_value = Mock(remote_dir="/workspace")

                        ops = WorkflowOperations(config=mock_config)

                        with patch(
                            "cosmos_workflow.api.workflow_operations.RemoteLogStreamer"
                        ) as mock_streamer_class:
                            with patch(
                                "cosmos_workflow.api.workflow_operations.threading.Thread"
                            ) as mock_thread:
                                mock_streamer = MagicMock()
                                mock_streamer_class.return_value = mock_streamer
                                mock_streamer.tail_log.return_value = ""

                                # Mock thread
                                mock_thread_instance = MagicMock()
                                mock_thread.return_value = mock_thread_instance

                                # Test with callback
                                def test_callback(line):
                                    pass

                                ops.stream_run_logs(
                                    run_id="rn_123", callback=test_callback, follow=True
                                )

                                # Verify thread was created and started
                                mock_thread.assert_called_once()
                                assert mock_thread.call_args[1]["daemon"] is True
                                mock_thread_instance.start.assert_called_once()

    def test_get_latest_run_logs_wrapper(self):
        """Test that get_latest_run_logs is a proper wrapper around stream_run_logs (behavior)."""
        with patch("cosmos_workflow.api.workflow_operations.ConfigManager") as mock_config_class:
            with patch("cosmos_workflow.api.workflow_operations.init_database") as mock_init_db:
                with patch(
                    "cosmos_workflow.api.workflow_operations.WorkflowService"
                ) as mock_service_class:
                    with patch(
                        "cosmos_workflow.api.workflow_operations.WorkflowOrchestrator"
                    ) as mock_orch_class:
                        # Setup mocks
                        mock_config = MagicMock()
                        mock_config_class.return_value = mock_config
                        mock_init_db.return_value = MagicMock()
                        mock_service = MagicMock()
                        mock_service_class.return_value = mock_service
                        mock_orchestrator = MagicMock()
                        mock_orch_class.return_value = mock_orchestrator

                        # Mock run data
                        mock_run = {"id": "rn_latest", "prompt_id": "ps_789"}
                        mock_service.list_runs.return_value = [mock_run]
                        mock_service.get_prompt.return_value = {"prompt_name": "test"}
                        mock_config.get_remote_config.return_value = Mock(remote_dir="/workspace")

                        ops = WorkflowOperations(config=mock_config)

                        with patch(
                            "cosmos_workflow.api.workflow_operations.RemoteLogStreamer"
                        ) as mock_streamer_class:
                            mock_streamer = MagicMock()
                            mock_streamer_class.return_value = mock_streamer
                            mock_streamer.tail_log.return_value = "tail output"

                            # Test get_latest_run_logs
                            result = ops.get_latest_run_logs(tail_lines=200)

                            # Should have called stream_run_logs with follow=False
                            assert result["status"] == "tailed"
                            assert result["run_id"] == "rn_latest"

                            # Verify tail was called with correct lines
                            mock_streamer.tail_log.assert_called_once()
                            call_args = mock_streamer.tail_log.call_args
                            assert call_args[0][1] == 200
