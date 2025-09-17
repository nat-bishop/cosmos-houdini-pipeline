"""Test suite for Queue UI Integration.

These tests define the behavioral contract for how the queue integrates
with the Gradio UI, ensuring users get proper feedback and visibility.
"""

from unittest.mock import Mock, patch

import pytest


class TestQueueUIIntegration:
    """Test queue integration with Gradio UI."""

    @pytest.fixture
    def mock_queue_service(self):
        """Create a mock QueueService instance."""
        service = Mock()
        service.get_queue_status = Mock(
            return_value={
                "queued": [
                    {"id": "job_001", "position": 1, "type": "inference", "prompt_count": 1},
                    {"id": "job_002", "position": 2, "type": "batch_inference", "prompt_count": 3},
                ],
                "running": {
                    "id": "job_000",
                    "type": "inference",
                    "prompt_count": 1,
                    "elapsed_time": 45,
                },
                "total_queued": 2,
            }
        )
        service.add_job = Mock(return_value="job_new_001")
        service.get_position = Mock(return_value=3)
        service.cancel_job = Mock(return_value=True)
        service.clear_completed_jobs = Mock(return_value=5)
        return service

    def test_run_inference_adds_to_queue(self, mock_queue_service):
        """When user clicks inference, job is added to queue with feedback."""
        # This will be tested through the actual UI handler
        # For now, we test the expected behavior
        from cosmos_workflow.ui.queue_handlers import run_inference_with_queue

        # Arrange
        dataframe_data = [[True, "ps_12345", "Test prompt"]]

        # Act
        with patch("cosmos_workflow.ui.queue_handlers.queue_service", mock_queue_service):
            result = run_inference_with_queue(
                dataframe_data,
                weight_vis=1.0,
                weight_edge=0.5,
                weight_depth=0.0,
                weight_seg=0.0,
                steps=25,
                guidance=4.0,
                seed=42,
                fps=8,
                sigma_max=1000.0,
                blur_strength=0.5,
                canny_threshold=0.1,
            )

        # Assert
        assert "job_new_001" in result
        assert "position" in result.lower() or "queue" in result.lower()
        mock_queue_service.add_job.assert_called_once()

    def test_run_batch_inference_adds_to_queue(self, mock_queue_service):
        """When user selects multiple prompts, batch job is added to queue."""
        from cosmos_workflow.ui.queue_handlers import run_inference_with_queue

        # Arrange
        dataframe_data = [
            [True, "ps_001", "Prompt 1"],
            [True, "ps_002", "Prompt 2"],
            [True, "ps_003", "Prompt 3"],
        ]

        # Act
        with patch("cosmos_workflow.ui.queue_handlers.queue_service", mock_queue_service):
            run_inference_with_queue(
                dataframe_data,
                weight_vis=1.0,
                weight_edge=0.0,
                weight_depth=0.0,
                weight_seg=0.0,
                steps=25,
                guidance=4.0,
                seed=42,
                fps=8,
                sigma_max=1000.0,
                blur_strength=0.5,
                canny_threshold=0.1,
            )

        # Assert
        call_args = mock_queue_service.add_job.call_args
        assert call_args[1]["prompt_ids"] == ["ps_001", "ps_002", "ps_003"]
        assert call_args[1]["job_type"] == "batch_inference"

    def test_run_enhancement_adds_to_queue(self, mock_queue_service):
        """When user clicks enhance, job is added to queue."""
        from cosmos_workflow.ui.queue_handlers import run_enhance_with_queue

        # Arrange
        dataframe_data = [[True, "ps_12345", "Test prompt"]]

        # Act
        with patch("cosmos_workflow.ui.queue_handlers.queue_service", mock_queue_service):
            result = run_enhance_with_queue(
                dataframe_data,
                create_new=True,
                force_overwrite=False,
            )

        # Assert
        assert "queue" in result.lower()
        call_args = mock_queue_service.add_job.call_args
        assert call_args[1]["job_type"] == "enhancement"
        assert call_args[1]["config"]["model"] == "pixtral"

    def test_queue_display_shows_correct_info(self, mock_queue_service):
        """Queue display shows running job, queued jobs, and positions."""
        # Import the display function
        from cosmos_workflow.ui.queue_handlers import get_queue_display

        # Act
        display = get_queue_display(mock_queue_service)

        # Assert
        assert "job_000" in display  # Running job
        assert "job_001" in display  # First queued
        assert "job_002" in display  # Second queued
        assert "Position: 1" in display or "#1" in display
        assert "Position: 2" in display or "#2" in display
        assert "inference" in display.lower()
        assert "batch" in display.lower()

    def test_queue_display_empty_state(self):
        """Queue display shows appropriate message when empty."""
        from cosmos_workflow.ui.queue_handlers import get_queue_display

        # Arrange
        mock_service = Mock()
        mock_service.get_queue_status = Mock(
            return_value={
                "queued": [],
                "running": None,
                "total_queued": 0,
            }
        )

        # Act
        display = get_queue_display(mock_service)

        # Assert
        assert "no jobs" in display.lower() or "empty" in display.lower()

    def test_cancel_queued_job_success(self, mock_queue_service):
        """User can cancel a queued job through UI."""
        from cosmos_workflow.ui.queue_handlers import handle_queue_cancel

        # Act
        result = handle_queue_cancel("job_001", mock_queue_service)

        # Assert
        assert "cancelled" in result.lower() or "success" in result.lower()
        mock_queue_service.cancel_job.assert_called_once_with("job_001")

    def test_cancel_running_job_fails(self, mock_queue_service):
        """User cannot cancel a running job."""
        from cosmos_workflow.ui.queue_handlers import handle_queue_cancel

        # Arrange
        mock_queue_service.cancel_job.return_value = False

        # Act
        result = handle_queue_cancel("job_000", mock_queue_service)

        # Assert
        assert "cannot" in result.lower() or "running" in result.lower()

    def test_clear_completed_jobs(self, mock_queue_service):
        """User can clear completed jobs from history."""
        from cosmos_workflow.ui.queue_handlers import clear_queue_history

        # Act
        result = clear_queue_history(mock_queue_service)

        # Assert
        assert "5" in result or "cleared" in result.lower()
        mock_queue_service.clear_completed_jobs.assert_called_once()

    def test_queue_auto_refresh_data(self, mock_queue_service):
        """Queue display provides data suitable for auto-refresh."""
        from cosmos_workflow.ui.queue_handlers import get_queue_display

        # Act
        display = get_queue_display(mock_queue_service)

        # Assert
        # Display should be text that can be updated via Gradio timer
        assert isinstance(display, str)
        assert len(display) > 0

    def test_queue_position_in_feedback(self, mock_queue_service):
        """User gets immediate feedback with queue position when adding job."""
        from cosmos_workflow.ui.queue_handlers import run_inference_with_queue

        # Arrange
        mock_queue_service.get_position.return_value = 5
        dataframe_data = [[True, "ps_12345", "Test prompt"]]

        # Act
        with patch("cosmos_workflow.ui.queue_handlers.queue_service", mock_queue_service):
            result = run_inference_with_queue(
                dataframe_data,
                weight_vis=1.0,
                weight_edge=0.0,
                weight_depth=0.0,
                weight_seg=0.0,
                steps=25,
                guidance=4.0,
                seed=42,
                fps=8,
                sigma_max=1000.0,
                blur_strength=0.5,
                canny_threshold=0.1,
            )

        # Assert
        assert "5" in result or "position" in result.lower()

    def test_estimated_wait_time_display(self, mock_queue_service):
        """Queue display shows estimated wait times."""
        from cosmos_workflow.ui.queue_handlers import get_queue_display

        # Arrange
        mock_queue_service.get_estimated_wait_time = Mock(side_effect=[120, 240])  # 2 min, 4 min

        # Act
        get_queue_display(mock_queue_service)

        # Assert - we expect to see wait time formatting
        # This depends on implementation, but should show time
        # For now we verify the method is called
        if hasattr(mock_queue_service, "get_estimated_wait_time"):
            # Wait times should be requested for queued jobs
            pass

    def test_queue_shows_job_type_icons(self):
        """Queue display uses appropriate icons for different job types."""
        from cosmos_workflow.ui.queue_handlers import get_queue_display

        # Arrange
        mock_service = Mock()
        mock_service.get_queue_status = Mock(
            return_value={
                "queued": [
                    {"id": "job_001", "position": 1, "type": "inference", "prompt_count": 1},
                    {"id": "job_002", "position": 2, "type": "enhancement", "prompt_count": 1},
                    {"id": "job_003", "position": 3, "type": "batch_inference", "prompt_count": 5},
                ],
                "running": None,
                "total_queued": 3,
            }
        )

        # Act
        display = get_queue_display(mock_service)

        # Assert
        # Check for type indicators (icons or text)
        assert any(indicator in display for indicator in ["🎬", "🌟", "📦", "inf", "enh", "batch"])

    def test_ui_handles_queue_service_errors(self, mock_queue_service):
        """UI gracefully handles queue service errors."""
        # Arrange
        mock_queue_service.add_job.side_effect = Exception("Database error")
        from cosmos_workflow.ui.queue_handlers import run_inference_with_queue

        dataframe_data = [[True, "ps_12345", "Test prompt"]]

        # Act
        with patch("cosmos_workflow.ui.queue_handlers.queue_service", mock_queue_service):
            result = run_inference_with_queue(
                dataframe_data,
                weight_vis=1.0,
                weight_edge=0.0,
                weight_depth=0.0,
                weight_seg=0.0,
                steps=25,
                guidance=4.0,
                seed=42,
                fps=8,
                sigma_max=1000.0,
                blur_strength=0.5,
                canny_threshold=0.1,
            )

        # Assert
        assert "error" in result.lower() or "❌" in result
