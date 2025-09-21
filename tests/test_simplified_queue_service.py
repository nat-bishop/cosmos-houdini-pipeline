"""Test suite for SimplifiedQueueService.

These tests verify the simplified queue implementation that uses database
transactions for atomicity instead of application-level locks.
"""

from unittest.mock import Mock

import pytest

from cosmos_workflow.database import DatabaseConnection
from cosmos_workflow.services.simple_queue_service import SimplifiedQueueService


class TestSimplifiedQueueService:
    """Test SimplifiedQueueService behavior."""

    @pytest.fixture
    def mock_cosmos_api(self):
        """Create a mock CosmosAPI instance."""
        mock_api = Mock()
        mock_api.get_active_containers = Mock(return_value=[])
        mock_api.quick_inference = Mock(
            return_value={
                "status": "completed",
                "output_path": "/outputs/result.mp4",
                "run_id": "run_test123",
            }
        )
        mock_api.batch_inference = Mock(
            return_value={
                "status": "completed",
                "output_mapping": {"ps_001": "/outputs/1.mp4", "ps_002": "/outputs/2.mp4"},
                "run_ids": ["run_batch1", "run_batch2"],
            }
        )
        mock_api.enhance_prompt = Mock(
            return_value={
                "status": "success",
                "enhanced_prompt": "Enhanced text",
                "prompt_id": "ps_enhanced",
            }
        )
        mock_api.upscale = Mock(
            return_value={
                "status": "completed",
                "output_path": "/outputs/upscaled.mp4",
                "run_id": "run_upscale123",
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
    def queue_service(self, mock_cosmos_api, test_db):
        """Create a SimplifiedQueueService instance for testing."""
        service = SimplifiedQueueService(cosmos_api=mock_cosmos_api, db_connection=test_db)
        return service

    # Test Basic Queue Operations

    def test_add_inference_job_to_queue(self, queue_service):
        """Test adding a single inference job to the queue."""
        job_id = queue_service.add_job(
            prompt_ids=["ps_test123"],
            job_type="inference",
            config={"weights": "model_v1", "num_steps": 30},
        )

        assert job_id.startswith("job_")

        # Verify job was added to database
        status = queue_service.get_job_status(job_id)
        assert status["id"] == job_id
        assert status["status"] == "queued"
        assert status["type"] == "inference"

    def test_add_batch_inference_job(self, queue_service):
        """Test adding a batch inference job with multiple prompts."""
        prompt_ids = ["ps_001", "ps_002", "ps_003"]
        job_id = queue_service.add_job(
            prompt_ids=prompt_ids,
            job_type="batch_inference",
            config={"weights": "model_v2"},
        )

        status = queue_service.get_job_status(job_id)
        assert status["type"] == "batch_inference"
        assert status["status"] == "queued"

    def test_add_enhancement_job(self, queue_service):
        """Test adding an enhancement job to the queue."""
        job_id = queue_service.add_job(
            prompt_ids=["ps_enhance"],
            job_type="enhancement",
            config={"model": "gpt-4", "create_new": True},
        )

        status = queue_service.get_job_status(job_id)
        assert status["type"] == "enhancement"
        assert status["status"] == "queued"

    def test_add_upscale_job(self, queue_service):
        """Test adding an upscale job to the queue."""
        job_id = queue_service.add_job(
            prompt_ids=[],  # Upscale doesn't need prompt IDs
            job_type="upscale",
            config={
                "video_source": "/inputs/video.mp4",
                "control_weight": 0.8,
                "prompt": "high quality",
            },
        )

        status = queue_service.get_job_status(job_id)
        assert status["type"] == "upscale"

    # Test Queue Position and Status

    def test_get_queue_position(self, queue_service):
        """Test getting a job's position in the queue."""
        # Add multiple jobs
        job1 = queue_service.add_job(["ps_001"], "inference", {})
        job2 = queue_service.add_job(["ps_002"], "inference", {})
        job3 = queue_service.add_job(["ps_003"], "inference", {})

        # Check positions
        assert queue_service.get_position(job1) == 1
        assert queue_service.get_position(job2) == 2
        assert queue_service.get_position(job3) == 3
        assert queue_service.get_position("nonexistent") is None

    def test_get_queue_status(self, queue_service):
        """Test getting overall queue status."""
        # Empty queue
        status = queue_service.get_queue_status()
        assert status["total_queued"] == 0
        assert status["running"] is None

        # Add some jobs
        job1 = queue_service.add_job(["ps_001"], "inference", {})
        queue_service.add_job(["ps_002"], "batch_inference", {})

        status = queue_service.get_queue_status()
        assert status["total_queued"] == 2
        assert len(status["queued"]) == 2
        assert status["queued"][0]["id"] == job1
        assert status["queued"][0]["position"] == 1

    # Test Job Processing

    def test_process_single_inference_job(self, queue_service, mock_cosmos_api):
        """Test processing a single inference job."""
        job_id = queue_service.add_job(
            ["ps_test"], "inference", {"weights": "model_v1", "num_steps": 25}
        )

        # Process the job
        result = queue_service.process_next_job()

        assert result["job_id"] == job_id
        assert result["status"] == "completed"
        assert mock_cosmos_api.quick_inference.called

        # Verify job was removed from queue after completion
        status = queue_service.get_job_status(job_id)
        assert status["status"] == "not_found"

    def test_process_batch_inference_job(self, queue_service, mock_cosmos_api):
        """Test processing a batch inference job."""
        prompt_ids = ["ps_001", "ps_002"]
        queue_service.add_job(prompt_ids, "batch_inference", {"weights": "model_v2"})

        result = queue_service.process_next_job()

        assert result["status"] == "completed"
        mock_cosmos_api.batch_inference.assert_called_once()

        # Check batch_size was passed
        call_args = mock_cosmos_api.batch_inference.call_args
        assert call_args.kwargs["batch_size"] == 4  # Default batch size

    def test_process_enhancement_job(self, queue_service, mock_cosmos_api):
        """Test processing an enhancement job."""
        queue_service.add_job(["ps_enhance"], "enhancement", {"create_new": True, "model": "gpt-4"})

        result = queue_service.process_next_job()

        assert result["status"] == "completed"
        mock_cosmos_api.enhance_prompt.assert_called_once_with(
            prompt_id="ps_enhance",
            create_new=True,
            enhancement_model="gpt-4",
        )

    def test_process_upscale_job(self, queue_service, mock_cosmos_api):
        """Test processing an upscale job."""
        queue_service.add_job(
            [], "upscale", {"video_source": "/inputs/video.mp4", "control_weight": 0.8}
        )

        result = queue_service.process_next_job()

        assert result["status"] == "completed"
        mock_cosmos_api.upscale.assert_called_once_with(
            video_source="/inputs/video.mp4",
            control_weight=0.8,
        )

    # Test Error Handling

    def test_job_failure_handling(self, queue_service, mock_cosmos_api):
        """Test that job failures are handled gracefully."""
        mock_cosmos_api.quick_inference.side_effect = Exception("GPU out of memory")

        job_id = queue_service.add_job(["ps_fail"], "inference", {})
        result = queue_service.process_next_job()

        assert result["status"] == "failed"
        assert "GPU out of memory" in result["error"]

        # Job should be marked as failed in database
        status = queue_service.get_job_status(job_id)
        assert status["status"] == "failed"  # Job kept as failed for visibility

    def test_invalid_job_type_handling(self, queue_service):
        """Test handling of invalid job types."""
        job_id = queue_service.add_job(["ps_test"], "invalid_type", {})
        result = queue_service.execute_job(job_id)

        assert result["status"] == "failed"
        assert "Unknown job type" in result["error"]

    # Test Job Cancellation

    def test_cancel_queued_job(self, queue_service):
        """Test cancelling a queued job."""
        job_id = queue_service.add_job(["ps_cancel"], "inference", {})

        # Cancel the job
        success = queue_service.cancel_job(job_id)
        assert success is True

        # Job should be marked as cancelled
        status = queue_service.get_job_status(job_id)
        assert status["status"] == "cancelled"

    def test_cannot_cancel_running_job(self, queue_service):
        """Test that running jobs cannot be cancelled."""
        job_id = queue_service.add_job(["ps_running"], "inference", {})

        # Claim the job (marks it as running)
        claimed_id = queue_service.claim_next_job()
        assert claimed_id == job_id

        # Try to cancel - should fail
        success = queue_service.cancel_job(job_id)
        assert success is False

    def test_cannot_cancel_nonexistent_job(self, queue_service):
        """Test cancelling a job that doesn't exist."""
        success = queue_service.cancel_job("nonexistent_job")
        assert success is False

    # Test Atomic Job Claiming

    def test_claim_next_job_atomic(self, queue_service):
        """Test that job claiming is atomic and follows FIFO order."""
        # Add jobs in order
        job1 = queue_service.add_job(["ps_001"], "inference", {})
        job2 = queue_service.add_job(["ps_002"], "inference", {})
        job3 = queue_service.add_job(["ps_003"], "inference", {})

        # Claim jobs - should be in FIFO order
        assert queue_service.claim_next_job() == job1
        assert queue_service.claim_next_job() == job2
        assert queue_service.claim_next_job() == job3
        assert queue_service.claim_next_job() is None  # Queue empty

    def test_claim_skips_when_container_running(self, queue_service, mock_cosmos_api):
        """Test that claiming is skipped when a container is already running."""
        # Simulate a running container
        mock_cosmos_api.get_active_containers.return_value = [
            {"container_id": "container_123", "status": "running"}
        ]

        job_id = queue_service.add_job(["ps_test"], "inference", {})

        # Should not claim the job
        claimed = queue_service.claim_next_job()
        assert claimed is None

        # Job should still be queued
        status = queue_service.get_job_status(job_id)
        assert status["status"] == "queued"

    # Test Batch Size Configuration

    def test_set_batch_size(self, queue_service):
        """Test updating the batch size for GPU processing."""
        # Default batch size
        assert queue_service.batch_size == 4

        # Update batch size
        queue_service.set_batch_size(8)
        assert queue_service.batch_size == 8

        # Test validation
        with pytest.raises(ValueError):
            queue_service.set_batch_size(0)

        # Large batch size should trigger warning but still set
        queue_service.set_batch_size(16)
        assert queue_service.batch_size == 16

    def test_batch_size_used_in_processing(self, queue_service, mock_cosmos_api):
        """Test that batch size is correctly passed to batch inference."""
        queue_service.set_batch_size(6)

        queue_service.add_job(["ps_001", "ps_002"], "batch_inference", {"weights": "model_v1"})

        queue_service.process_next_job()

        call_args = mock_cosmos_api.batch_inference.call_args
        assert call_args.kwargs["batch_size"] == 6

    # Test Database Session Management

    def test_fresh_database_sessions(self, queue_service):
        """Test that fresh database sessions are used to prevent stale data."""
        # Add a job
        queue_service.add_job(["ps_test"], "inference", {})

        # Get status multiple times - should always be fresh
        status1 = queue_service.get_queue_status()
        status2 = queue_service.get_queue_status()

        assert status1["total_queued"] == 1
        assert status2["total_queued"] == 1

    # Test Edge Cases

    def test_empty_prompt_ids_for_non_upscale(self, queue_service):
        """Test that non-upscale jobs require prompt IDs."""
        job_id = queue_service.add_job([], "inference", {})
        result = queue_service.execute_job(job_id)

        assert result["status"] == "failed"
        assert "No prompt IDs" in result["error"]

    def test_missing_video_source_for_upscale(self, queue_service):
        """Test that upscale jobs require video_source."""
        job_id = queue_service.add_job([], "upscale", {})
        result = queue_service.execute_job(job_id)

        assert result["status"] == "failed"
        assert "No video_source" in result["error"]

    def test_estimated_wait_time(self, queue_service):
        """Test wait time estimation for queued jobs."""
        # Add multiple jobs
        job1 = queue_service.add_job(["ps_001"], "inference", {})
        job2 = queue_service.add_job(["ps_002"], "inference", {})
        job3 = queue_service.add_job(["ps_003"], "inference", {})

        # Check estimated wait times (120 seconds per job)
        assert queue_service.get_estimated_wait_time(job1) == 120
        assert queue_service.get_estimated_wait_time(job2) == 240
        assert queue_service.get_estimated_wait_time(job3) == 360
        assert queue_service.get_estimated_wait_time("nonexistent") is None

    def test_process_with_no_jobs(self, queue_service):
        """Test processing when queue is empty."""
        result = queue_service.process_next_job()
        assert result is None

    def test_ensure_container_error_handling(self, queue_service, mock_cosmos_api):
        """Test container checking handles errors gracefully."""
        mock_cosmos_api.get_active_containers.side_effect = Exception("Connection failed")

        # Should handle error and return None
        container_id = queue_service.ensure_container()
        assert container_id is None

    # Test Concurrent Access (simulated)

    def test_simulated_concurrent_job_additions(self, queue_service):
        """Test that multiple jobs can be added without issues."""
        job_ids = []
        for i in range(10):
            job_id = queue_service.add_job([f"ps_{i:03d}"], "inference", {})
            job_ids.append(job_id)

        status = queue_service.get_queue_status()
        assert status["total_queued"] == 10

        # All jobs should be in queue in order
        for i, job_info in enumerate(status["queued"]):
            assert job_info["id"] == job_ids[i]
            assert job_info["position"] == i + 1

    def test_job_result_in_failed_state(self, queue_service, mock_cosmos_api):
        """Test that job results are stored when jobs fail."""
        mock_cosmos_api.quick_inference.side_effect = ValueError("Invalid parameters")

        job_id = queue_service.add_job(["ps_test"], "inference", {})

        # Before execution, job is queued
        status_before = queue_service.get_job_status(job_id)
        assert status_before["status"] == "queued"

        # Execute and fail
        result = queue_service.execute_job(job_id)
        assert result["status"] == "failed"
        assert "Invalid parameters" in result["error"]

    # Test SimplifiedQueueService specific features

    def test_no_background_threads(self, queue_service):
        """Test that SimplifiedQueueService doesn't use background threads."""
        # Unlike the old QueueService, there should be no processor thread
        assert not hasattr(queue_service, "_processor_thread")
        assert not hasattr(queue_service, "_stop_processor")
        assert not hasattr(queue_service, "_processor_lock")

    def test_database_transaction_atomicity(self, test_db):
        """Test that database operations are atomic."""
        service = SimplifiedQueueService(db_connection=test_db)

        # Add jobs
        job1 = service.add_job(["ps_001"], "inference", {})
        job2 = service.add_job(["ps_002"], "inference", {})

        # Claiming should be atomic - only one job claimed
        claimed1 = service.claim_next_job()
        assert claimed1 == job1

        # Job1 should now be running, job2 still queued
        status1 = service.get_job_status(job1)
        status2 = service.get_job_status(job2)
        assert status1["status"] == "running"
        assert status2["status"] == "queued"
