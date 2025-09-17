"""Test suite for QueueService.

These tests define the behavioral contract for the queue service layer.
Tests focus on user-observable behaviors: adding jobs to queue, processing them,
and providing queue visibility.
"""

import threading
import time
from unittest.mock import Mock

import pytest

from cosmos_workflow.database import DatabaseConnection
from cosmos_workflow.services.queue_service import QueueService


class TestQueueService:
    """Test QueueService behavior."""

    @pytest.fixture
    def mock_cosmos_api(self):
        """Create a mock CosmosAPI instance."""
        mock_api = Mock()
        mock_api.quick_inference = Mock(
            return_value={
                "status": "completed",
                "output_path": "/outputs/result.mp4",
            }
        )
        mock_api.batch_inference = Mock(
            return_value={
                "status": "completed",
                "output_mapping": {"ps_001": "/outputs/1.mp4", "ps_002": "/outputs/2.mp4"},
            }
        )
        mock_api.enhance_prompt = Mock(
            return_value={
                "status": "success",
                "enhanced_prompt": "Enhanced text",
            }
        )
        return mock_api

    @pytest.fixture
    def test_db(self):
        """Create an in-memory test database."""
        db = DatabaseConnection(":memory:")
        db.create_tables()
        return db

    @pytest.fixture
    def db_session(self, test_db):
        """Get database session from test database."""
        with test_db.get_session() as session:
            yield session

    @pytest.fixture
    def queue_service(self, mock_cosmos_api, db_session):
        """Create QueueService instance with real database and mock API."""
        service = QueueService(cosmos_api=mock_cosmos_api, db_session=db_session)
        return service

    def test_add_inference_job_to_queue(self, queue_service):
        """User can add an inference job to the queue."""
        # Arrange
        job_config = {
            "prompt_ids": ["ps_12345"],
            "job_type": "inference",
            "config": {
                "weights": {"vis": 1.0, "edge": 0.5},
                "num_steps": 25,
                "guidance_scale": 4.0,
            },
        }

        # Act
        job_id = queue_service.add_job(**job_config)

        # Assert
        assert job_id is not None
        assert job_id.startswith("job_")
        assert len(queue_service.get_queue_status()["queued"]) > 0

    def test_add_batch_inference_job(self, queue_service):
        """User can add a batch inference job with multiple prompts."""
        # Arrange
        job_config = {
            "prompt_ids": ["ps_001", "ps_002", "ps_003"],
            "job_type": "batch_inference",
            "config": {
                "weights": {"vis": 1.0},
                "num_steps": 25,
            },
        }

        # Act
        job_id = queue_service.add_job(**job_config)

        # Assert
        assert job_id is not None
        status = queue_service.get_queue_status()
        assert any(j["prompt_count"] == 3 for j in status["queued"])

    def test_add_enhancement_job(self, queue_service):
        """User can add an enhancement job to the queue."""
        # Arrange
        job_config = {
            "prompt_ids": ["ps_12345"],
            "job_type": "enhancement",
            "config": {
                "model": "pixtral",
                "create_new": True,
                "force_overwrite": False,
            },
        }

        # Act
        job_id = queue_service.add_job(**job_config)

        # Assert
        assert job_id is not None
        assert queue_service.get_position(job_id) == 1

    def test_get_queue_position(self, queue_service):
        """User can check their job's position in the queue."""
        # Arrange
        queue_service.add_job(
            prompt_ids=["ps_001"],
            job_type="inference",
            config={},
        )
        job2 = queue_service.add_job(
            prompt_ids=["ps_002"],
            job_type="inference",
            config={},
        )
        job3 = queue_service.add_job(
            prompt_ids=["ps_003"],
            job_type="inference",
            config={},
        )

        # Act
        position2 = queue_service.get_position(job2)
        position3 = queue_service.get_position(job3)

        # Assert
        assert position2 == 2
        assert position3 == 3

    def test_get_queue_status(self, queue_service):
        """User can view the current queue status."""
        # Arrange
        for i in range(3):
            queue_service.add_job(
                prompt_ids=[f"ps_{i:03d}"],
                job_type="inference",
                config={},
            )

        # Act
        status = queue_service.get_queue_status()

        # Assert
        assert "queued" in status
        assert "running" in status
        assert "total_queued" in status
        assert status["total_queued"] == 3
        assert len(status["queued"]) == 3
        assert all("position" in job for job in status["queued"])

    def test_process_single_job(self, queue_service, mock_cosmos_api):
        """System processes a single queued job."""
        # Arrange
        job_id = queue_service.add_job(
            prompt_ids=["ps_12345"],
            job_type="inference",
            config={
                "weights": {"vis": 1.0},
                "num_steps": 25,
            },
        )

        # Act
        result = queue_service.process_next_job()

        # Assert
        assert result is not None
        assert result["job_id"] == job_id
        assert result["status"] == "completed"
        mock_cosmos_api.quick_inference.assert_called_once()

    def test_process_batch_job(self, queue_service, mock_cosmos_api):
        """System processes batch inference jobs correctly."""
        # Arrange
        queue_service.add_job(
            prompt_ids=["ps_001", "ps_002"],
            job_type="batch_inference",
            config={
                "weights": {"vis": 1.0},
                "num_steps": 25,
            },
        )

        # Act
        result = queue_service.process_next_job()

        # Assert
        assert result["status"] == "completed"
        mock_cosmos_api.batch_inference.assert_called_once_with(
            prompt_ids=["ps_001", "ps_002"],
            shared_weights={"vis": 1.0},
            num_steps=25,
        )

    def test_process_enhancement_job(self, queue_service, mock_cosmos_api):
        """System processes enhancement jobs correctly."""
        # Arrange
        queue_service.add_job(
            prompt_ids=["ps_12345"],
            job_type="enhancement",
            config={
                "model": "pixtral",
                "create_new": True,
            },
        )

        # Act
        result = queue_service.process_next_job()

        # Assert
        assert result["status"] == "completed"
        mock_cosmos_api.enhance_prompt.assert_called_once_with(
            prompt_id="ps_12345",
            enhancement_model="pixtral",
            create_new=True,
        )

    def test_process_upscale_job_from_run(self, queue_service, mock_cosmos_api):
        """System processes upscale jobs from run ID correctly."""
        # Arrange
        queue_service.add_job(
            prompt_ids=[],  # Upscale doesn't need prompt IDs
            job_type="upscale",
            config={
                "video_source": "rs_abc123",
                "control_weight": 0.7,
                "prompt": "cinematic quality",
            },
        )

        # Configure mock
        mock_cosmos_api.upscale.return_value = {
            "status": "success",
            "upscale_run_id": "rs_upscale_456",
            "output_path": "/outputs/upscaled_4k.mp4",
        }

        # Act
        result = queue_service.process_next_job()

        # Assert
        assert result["status"] == "completed"
        mock_cosmos_api.upscale.assert_called_once_with(
            video_source="rs_abc123",
            control_weight=0.7,
            prompt="cinematic quality",
        )

    def test_process_upscale_job_from_video(self, queue_service, mock_cosmos_api):
        """System processes upscale jobs from video file correctly."""
        # Arrange
        queue_service.add_job(
            prompt_ids=[],  # Upscale doesn't need prompt IDs
            job_type="upscale",
            config={
                "video_source": "/path/to/video.mp4",
                "control_weight": 0.5,
                # No prompt this time
            },
        )

        # Configure mock
        mock_cosmos_api.upscale.return_value = {
            "status": "success",
            "upscale_run_id": "rs_upscale_789",
            "output_path": "/outputs/upscaled_4k.mp4",
        }

        # Act
        result = queue_service.process_next_job()

        # Assert
        assert result["status"] == "completed"
        mock_cosmos_api.upscale.assert_called_once_with(
            video_source="/path/to/video.mp4",
            control_weight=0.5,
        )

    def test_add_upscale_job_to_queue(self, queue_service):
        """User can add an upscale job to the queue."""
        # Arrange & Act
        job_id = queue_service.add_job(
            prompt_ids=[],  # Empty list for upscale
            job_type="upscale",
            config={
                "video_source": "rs_test123",
                "control_weight": 0.8,
            },
        )

        # Assert
        assert job_id.startswith("job_")
        job_status = queue_service.get_job_status(job_id)
        assert job_status["status"] == "queued"
        assert job_status["type"] == "upscale"

    def test_job_failure_handling(self, queue_service, mock_cosmos_api):
        """System handles job failures gracefully."""
        # Arrange
        mock_cosmos_api.quick_inference.side_effect = Exception("GPU out of memory")
        queue_service.add_job(
            prompt_ids=["ps_12345"],
            job_type="inference",
            config={},
        )

        # Act
        result = queue_service.process_next_job()

        # Assert
        assert result["status"] == "failed"
        assert "GPU out of memory" in result["error"]

    def test_cancel_queued_job(self, queue_service):
        """User can cancel a queued job."""
        # Arrange
        job_id = queue_service.add_job(
            prompt_ids=["ps_12345"],
            job_type="inference",
            config={},
        )

        # Act
        success = queue_service.cancel_job(job_id)

        # Assert
        assert success is True
        assert queue_service.get_position(job_id) is None
        status = queue_service.get_job_status(job_id)
        assert status["status"] == "cancelled"

    def test_cannot_cancel_running_job(self, queue_service):
        """User cannot cancel a job that's already running."""
        # Arrange
        job_id = queue_service.add_job(
            prompt_ids=["ps_12345"],
            job_type="inference",
            config={},
        )
        # Simulate job starting by processing it
        queue_service.process_next_job()  # This should mark it as running

        # Act
        success = queue_service.cancel_job(job_id)

        # Assert
        assert success is False

    @pytest.mark.skip(reason="SQLite concurrency limitations in test environment")
    def test_background_processor(self, mock_cosmos_api, test_db):
        """Background processor automatically processes queued jobs."""
        # Arrange - use db_connection for background thread
        queue_service = QueueService(cosmos_api=mock_cosmos_api, db_connection=test_db)
        job_ids = []
        for i in range(3):
            job_id = queue_service.add_job(
                prompt_ids=[f"ps_{i:03d}"],
                job_type="inference",
                config={},
            )
            job_ids.append(job_id)

        # Configure mock to simulate processing time
        mock_cosmos_api.quick_inference.return_value = {
            "status": "completed",
            "output_path": "/outputs/result.mp4",
        }

        # Act
        queue_service.start_background_processor()
        time.sleep(1.0)  # Give processor time to work
        queue_service.stop_background_processor()

        # Assert
        # At least one job should have been processed
        assert mock_cosmos_api.quick_inference.call_count > 0

    def test_processor_handles_mixed_job_types(self, queue_service, mock_cosmos_api):
        """Background processor handles different job types in sequence."""
        # Arrange
        queue_service.add_job(
            prompt_ids=["ps_001"],
            job_type="inference",
            config={"weights": {"vis": 1.0}},
        )
        queue_service.add_job(
            prompt_ids=["ps_002"],
            job_type="enhancement",
            config={"model": "pixtral"},
        )
        queue_service.add_job(
            prompt_ids=["ps_003", "ps_004"],
            job_type="batch_inference",
            config={"weights": {"vis": 0.5}},
        )
        queue_service.add_job(
            prompt_ids=[],
            job_type="upscale",
            config={"video_source": "rs_005", "control_weight": 0.6},
        )

        # Configure mock for upscale
        mock_cosmos_api.upscale.return_value = {
            "status": "success",
            "upscale_run_id": "rs_upscale_test",
            "output_path": "/outputs/upscaled.mp4",
        }

        # Act
        queue_service.process_next_job()  # Process inference
        queue_service.process_next_job()  # Process enhancement
        queue_service.process_next_job()  # Process batch
        queue_service.process_next_job()  # Process upscale

        # Assert
        mock_cosmos_api.quick_inference.assert_called_once()
        mock_cosmos_api.enhance_prompt.assert_called_once()
        mock_cosmos_api.batch_inference.assert_called_once()
        mock_cosmos_api.upscale.assert_called_once()

    def test_get_estimated_wait_time(self, queue_service):
        """User can get estimated wait time for their job."""
        # Arrange
        # Add some jobs with known processing times
        for i in range(5):
            queue_service.add_job(
                prompt_ids=[f"ps_{i:03d}"],
                job_type="inference",
                config={},
            )

        job_id = queue_service.add_job(
            prompt_ids=["ps_target"],
            job_type="inference",
            config={},
        )

        # Act
        wait_time = queue_service.get_estimated_wait_time(job_id)

        # Assert
        assert wait_time is not None
        assert wait_time > 0  # Should have some wait time with 5 jobs ahead

    def test_clear_completed_jobs(self, queue_service, mock_cosmos_api):
        """User can clear completed jobs from history."""
        # Arrange
        queue_service.add_job(
            prompt_ids=["ps_001"],
            job_type="inference",
            config={},
        )
        queue_service.add_job(
            prompt_ids=["ps_002"],
            job_type="inference",
            config={},
        )

        # Process jobs to completion
        queue_service.process_next_job()
        queue_service.process_next_job()

        # Act
        cleared = queue_service.clear_completed_jobs()

        # Assert
        assert cleared == 2
        status = queue_service.get_queue_status()
        assert status["total_queued"] == 0

    def test_job_result_persistence(self, queue_service, mock_cosmos_api):
        """Job results are persisted and retrievable."""
        # Arrange
        mock_cosmos_api.quick_inference.return_value = {
            "status": "completed",
            "output_path": "/outputs/video.mp4",
            "duration": 180,
        }

        job_id = queue_service.add_job(
            prompt_ids=["ps_12345"],
            job_type="inference",
            config={},
        )

        # Act
        queue_service.process_next_job()
        job_status = queue_service.get_job_status(job_id)

        # Assert
        assert job_status["status"] == "completed"
        assert job_status["result"]["output_path"] == "/outputs/video.mp4"
        assert job_status["result"]["duration"] == 180

    @pytest.mark.skip(reason="SQLite concurrency limitations in test environment")
    def test_concurrent_job_additions(self, mock_cosmos_api, test_db):
        """Multiple threads can safely add jobs concurrently."""
        # Arrange - use db_connection for thread safety
        queue_service = QueueService(cosmos_api=mock_cosmos_api, db_connection=test_db)
        job_ids = []
        lock = threading.Lock()

        def add_job(i):
            job_id = queue_service.add_job(
                prompt_ids=[f"ps_{i:03d}"],
                job_type="inference",
                config={},
            )
            with lock:
                job_ids.append(job_id)

        # Act
        threads = [threading.Thread(target=add_job, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Assert
        assert len(job_ids) == 10
        assert len(set(job_ids)) == 10  # All IDs unique
        status = queue_service.get_queue_status()
        assert status["total_queued"] == 10

    def test_fifo_processing_order(self, queue_service, mock_cosmos_api):
        """Jobs are processed in FIFO order."""
        # Arrange
        job_ids = []
        for i in range(5):
            job_id = queue_service.add_job(
                prompt_ids=[f"ps_{i:03d}"],
                job_type="inference",
                config={"index": i},  # Track order
            )
            job_ids.append(job_id)

        # Track processing order
        processed_order = []

        def track_inference(*args, **kwargs):
            processed_order.append(kwargs.get("prompt_id"))
            return {"status": "completed"}

        mock_cosmos_api.quick_inference.side_effect = track_inference

        # Act - Process all jobs
        for _ in range(5):
            queue_service.process_next_job()

        # Assert - Jobs processed in order added
        assert processed_order == [f"ps_{i:03d}" for i in range(5)]

    @pytest.mark.skip(reason="SQLite concurrency limitations in test environment")
    def test_processor_lifecycle(self, mock_cosmos_api, test_db):
        """Background processor can be started and stopped safely."""
        # Arrange - use db_connection for background thread
        queue_service = QueueService(cosmos_api=mock_cosmos_api, db_connection=test_db)
        for i in range(3):
            queue_service.add_job(
                prompt_ids=[f"ps_{i:03d}"],
                job_type="inference",
                config={},
            )

        # Act - Start and stop processor multiple times
        queue_service.start_background_processor()
        assert queue_service.is_processor_running()

        time.sleep(0.2)  # Let it process
        queue_service.stop_background_processor()
        assert not queue_service.is_processor_running()

        # Restart
        queue_service.start_background_processor()
        assert queue_service.is_processor_running()

        time.sleep(0.2)
        queue_service.stop_background_processor()
        assert not queue_service.is_processor_running()

        # Assert - Some jobs should have been processed
        assert mock_cosmos_api.quick_inference.call_count > 0

    def test_processor_crash_recovery(self, queue_service, mock_cosmos_api):
        """System recovers from processor crashes gracefully."""
        # Arrange
        queue_service.add_job(
            prompt_ids=["ps_crash"],
            job_type="inference",
            config={},
        )

        # Make first call crash
        mock_cosmos_api.quick_inference.side_effect = [
            Exception("Simulated crash"),
            {"status": "completed"},  # Second attempt succeeds
        ]

        # Act - Process with crash
        result1 = queue_service.process_next_job()

        # Add another job and process
        queue_service.add_job(
            prompt_ids=["ps_after_crash"],
            job_type="inference",
            config={},
        )
        result2 = queue_service.process_next_job()

        # Assert
        assert result1["status"] == "failed"
        assert "Simulated crash" in result1["error"]
        assert result2["status"] == "completed"
