"""Tests for run action handlers in the UI."""

from unittest.mock import Mock, patch

import pytest

from cosmos_workflow.ui.tabs.runs.run_actions import execute_upscale


class TestExecuteUpscale:
    """Test the execute_upscale function."""

    @pytest.fixture
    def mock_queue_service(self):
        """Create a mock queue service."""
        queue_service = Mock()
        queue_service.add_job = Mock(return_value="job_123")
        queue_service.get_position = Mock(return_value=3)
        return queue_service

    def test_execute_upscale_success(self, mock_queue_service):
        """Test successful upscale job queueing."""
        # Call execute_upscale with valid parameters
        with patch("cosmos_workflow.ui.tabs.runs.run_actions.gr.Info") as mock_info:
            result = execute_upscale(
                run_id="rs_test123",
                control_weight=0.7,
                prompt_text="enhance quality",
                queue_service=mock_queue_service,
            )

        # Verify add_job was called with correct parameters
        mock_queue_service.add_job.assert_called_once_with(
            prompt_ids=[],
            job_type="upscale",
            config={
                "run_id": "rs_test123",
                "control_weight": 0.7,
                "prompt": "enhance quality",
            },
        )

        # Verify get_position was called
        mock_queue_service.get_position.assert_called_once_with("job_123")

        # Verify info message was shown
        mock_info.assert_called_once_with("✅ Upscaling queued at position #3")

        # Verify return values (dialog hidden, selection maintained)
        assert len(result) == 2
        # First return should hide dialog
        assert result[0]["visible"] is False

    def test_execute_upscale_no_run_id(self, mock_queue_service):
        """Test execute_upscale with missing run_id."""
        result = execute_upscale(
            run_id=None,
            control_weight=0.5,
            prompt_text="test",
            queue_service=mock_queue_service,
        )

        # Should not call add_job
        mock_queue_service.add_job.assert_not_called()

        # Should return updates to hide dialog
        assert len(result) == 2
        assert result[0]["visible"] is False

    def test_execute_upscale_with_error(self, mock_queue_service):
        """Test execute_upscale when queueing fails."""
        # Make add_job raise an exception
        mock_queue_service.add_job.side_effect = Exception("Queue full")

        with patch("cosmos_workflow.ui.tabs.runs.run_actions.gr.Warning") as mock_warning:
            result = execute_upscale(
                run_id="rs_test123",
                control_weight=0.5,
                prompt_text=None,
                queue_service=mock_queue_service,
            )

        # Verify warning was shown
        mock_warning.assert_called_once_with("Failed to queue upscaling: Queue full")

        # Should still return updates to hide dialog
        assert len(result) == 2
        assert result[0]["visible"] is False

    def test_execute_upscale_with_no_prompt(self, mock_queue_service):
        """Test execute_upscale without optional prompt text."""
        with patch("cosmos_workflow.ui.tabs.runs.run_actions.gr.Info"):
            result = execute_upscale(
                run_id="rs_test123",
                control_weight=0.5,
                prompt_text=None,  # No prompt provided
                queue_service=mock_queue_service,
            )

        # Verify add_job was called with None prompt
        mock_queue_service.add_job.assert_called_once_with(
            prompt_ids=[],
            job_type="upscale",
            config={
                "run_id": "rs_test123",
                "control_weight": 0.5,
                "prompt": None,
            },
        )

        assert len(result) == 2

    def test_execute_upscale_no_position_feedback(self, mock_queue_service):
        """Test execute_upscale when no queue position is returned."""
        # Make get_position return None
        mock_queue_service.get_position.return_value = None

        with patch("cosmos_workflow.ui.tabs.runs.run_actions.gr.Info") as mock_info:
            result = execute_upscale(
                run_id="rs_test123",
                control_weight=0.5,
                prompt_text="test",
                queue_service=mock_queue_service,
            )

        # Info should not be called when position is None
        mock_info.assert_not_called()

        # Should still return successful updates
        assert len(result) == 2
        assert result[0]["visible"] is False
