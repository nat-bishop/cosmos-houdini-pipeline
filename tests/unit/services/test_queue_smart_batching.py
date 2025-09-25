"""Unit tests for smart batching extensions to SimplifiedQueueService.

Tests the queue analysis and execution methods for smart batching.
Focus on behavioral testing of the service layer integration.
"""

from unittest.mock import Mock

import pytest

from cosmos_workflow.database.models import JobQueue
from cosmos_workflow.services.simple_queue_service import SimplifiedQueueService


class TestQueueSmartBatching:
    """Test smart batching methods in SimplifiedQueueService."""

    @pytest.fixture
    def queue_service(self):
        """Create a SimplifiedQueueService instance with mocks."""
        cosmos_api = Mock()
        db_connection = Mock()
        service = SimplifiedQueueService(cosmos_api, db_connection)
        return service

    @pytest.fixture
    def mock_jobs(self):
        """Create mock job queue entries for testing."""
        jobs = []
        for i in range(6):
            job = Mock(spec=JobQueue)
            job.id = f"job_{i}"
            job.job_type = "inference"
            job.status = "queued"
            job.prompt_ids = [f"ps_{i}"]
            job.config = {"weights": {"edge": 0.5} if i % 2 == 0 else {"depth": 0.5}}
            jobs.append(job)
        return jobs

    def test_analyze_queue_for_smart_batching_strict_mode(self, queue_service, mock_jobs):
        """Analyze queue in strict mode should group identical controls only."""
        # Setup mock database session
        mock_session = Mock()
        mock_session.query().filter_by().all.return_value = mock_jobs
        queue_service.db_connection.get_session.return_value.__enter__ = Mock(
            return_value=mock_session
        )
        queue_service.db_connection.get_session.return_value.__exit__ = Mock()

        # Analyze queue in strict mode
        analysis = queue_service.analyze_queue_for_smart_batching(mix_controls=False)

        assert analysis is not None
        assert "batches" in analysis
        assert "efficiency" in analysis
        assert "preview" in analysis
        assert analysis["efficiency"]["job_count_before"] == 6
        # Should create 2 batches (edge jobs and depth jobs)
        assert len(analysis["batches"]) == 2

    def test_analyze_queue_for_smart_batching_mixed_mode(self, queue_service, mock_jobs):
        """Analyze queue in mixed mode should optimize control overhead."""
        mock_session = Mock()
        mock_session.query().filter_by().all.return_value = mock_jobs
        queue_service.db_connection.get_session.return_value.__enter__ = Mock(
            return_value=mock_session
        )
        queue_service.db_connection.get_session.return_value.__exit__ = Mock()

        # Analyze queue in mixed mode
        analysis = queue_service.analyze_queue_for_smart_batching(mix_controls=True)

        assert analysis is not None
        assert "batches" in analysis
        assert "efficiency" in analysis
        # Mixed mode may create fewer batches by using master controls
        assert analysis["efficiency"]["estimated_speedup"] > 1.0

    def test_analyze_queue_empty(self, queue_service):
        """Empty queue should return None analysis."""
        mock_session = Mock()
        mock_session.query().filter_by().all.return_value = []
        queue_service.db_connection.get_session.return_value.__enter__ = Mock(
            return_value=mock_session
        )
        queue_service.db_connection.get_session.return_value.__exit__ = Mock()

        analysis = queue_service.analyze_queue_for_smart_batching()

        assert analysis is None

    def test_analyze_queue_filters_non_batchable(self, queue_service):
        """Analysis should exclude non-batchable job types."""
        # Create mix of batchable and non-batchable jobs
        jobs = [
            self._create_mock_job("job_1", "inference"),
            self._create_mock_job("job_2", "enhancement"),
            self._create_mock_job("job_3", "batch_inference"),
            self._create_mock_job("job_4", "upscale"),
        ]

        mock_session = Mock()
        mock_session.query().filter_by().all.return_value = jobs
        queue_service.db_connection.get_session.return_value.__enter__ = Mock(
            return_value=mock_session
        )
        queue_service.db_connection.get_session.return_value.__exit__ = Mock()

        analysis = queue_service.analyze_queue_for_smart_batching()

        # Should only analyze batchable jobs
        assert analysis is not None
        assert analysis["efficiency"]["job_count_before"] == 2  # Only inference and batch_inference

    def test_execute_smart_batches_success(self, queue_service, mock_jobs):
        """Execute smart batches should process stored analysis."""
        # Setup stored analysis
        queue_service._smart_batch_analysis = {
            "batches": [
                {"jobs": mock_jobs[:3], "signature": ("edge",)},
                {"jobs": mock_jobs[3:], "signature": ("depth",)},
            ],
            "efficiency": {
                "job_count_before": 6,
                "job_count_after": 2,
                "estimated_speedup": 3.0,
            },
        }
        queue_service._analysis_queue_size = 6

        # Mock database session
        mock_session = Mock()
        mock_session.query().filter_by().all.return_value = mock_jobs
        queue_service.db_connection.get_session.return_value.__enter__ = Mock(
            return_value=mock_session
        )
        queue_service.db_connection.get_session.return_value.__exit__ = Mock()

        # Mock batch execution
        queue_service.cosmos_api.batch_inference.return_value = {"status": "success"}

        results = queue_service.execute_smart_batches()

        assert results is not None
        assert results["jobs_executed"] == 6
        assert results["batches_created"] == 2
        assert results["speedup"] == 3.0
        assert queue_service.cosmos_api.batch_inference.call_count == 2

    def test_execute_smart_batches_stale_analysis(self, queue_service, mock_jobs):
        """Execute should fail if queue changed since analysis."""
        # Setup stored analysis with different queue size
        queue_service._smart_batch_analysis = {"batches": [], "efficiency": {}}
        queue_service._analysis_queue_size = 10  # Different from current queue

        mock_session = Mock()
        mock_session.query().filter_by().all.return_value = mock_jobs  # 6 jobs
        queue_service.db_connection.get_session.return_value.__enter__ = Mock(
            return_value=mock_session
        )
        queue_service.db_connection.get_session.return_value.__exit__ = Mock()

        results = queue_service.execute_smart_batches()

        assert results is not None
        assert "error" in results
        assert "stale" in results["error"].lower()

    def test_execute_smart_batches_no_analysis(self, queue_service):
        """Execute should fail gracefully if no analysis exists."""
        queue_service._smart_batch_analysis = None

        results = queue_service.execute_smart_batches()

        assert results is not None
        assert "error" in results
        assert "no analysis" in results["error"].lower()

    def test_get_smart_batch_preview(self, queue_service):
        """Preview should return human-readable analysis summary."""
        queue_service._smart_batch_analysis = {
            "preview": "Smart Batching Analysis:\n- 6 jobs → 2 batches\n- Estimated speedup: 3.0x",
            "efficiency": {"estimated_speedup": 3.0},
        }
        queue_service._analysis_queue_size = 6

        # Mock current queue size check
        mock_session = Mock()
        mock_session.query().filter_by().all.return_value = [Mock()] * 6
        queue_service.db_connection.get_session.return_value.__enter__ = Mock(
            return_value=mock_session
        )
        queue_service.db_connection.get_session.return_value.__exit__ = Mock()

        preview = queue_service.get_smart_batch_preview()

        assert preview is not None
        assert "6 jobs → 2 batches" in preview
        assert "3.0x" in preview

    def test_get_smart_batch_preview_stale(self, queue_service):
        """Preview should return empty string if analysis is stale."""
        queue_service._smart_batch_analysis = {"preview": "Old analysis"}
        queue_service._analysis_queue_size = 10

        mock_session = Mock()
        mock_session.query().filter_by().all.return_value = [Mock()] * 5  # Different size
        queue_service.db_connection.get_session.return_value.__enter__ = Mock(
            return_value=mock_session
        )
        queue_service.db_connection.get_session.return_value.__exit__ = Mock()

        preview = queue_service.get_smart_batch_preview()

        assert preview == ""

    def test_analysis_invalidation_on_queue_change(self, queue_service):
        """Analysis should be invalidated when queue changes."""
        # Set up initial analysis
        queue_service._smart_batch_analysis = {"batches": [], "efficiency": {}}
        queue_service._analysis_queue_size = 5

        # Add a new job (simulating queue change)
        queue_service.add_job(["ps_123"], "inference", {"weights": {"edge": 0.5}})

        # Analysis should be cleared when queue changes
        # This would be triggered by checking queue size mismatch
        mock_session = Mock()
        mock_session.query().filter_by().all.return_value = [Mock()] * 6
        queue_service.db_connection.get_session.return_value.__enter__ = Mock(
            return_value=mock_session
        )
        queue_service.db_connection.get_session.return_value.__exit__ = Mock()

        preview = queue_service.get_smart_batch_preview()
        assert preview == ""  # Stale analysis returns empty

    def test_batch_with_job_failure(self, queue_service):
        """Batch execution should handle individual job failures gracefully."""
        queue_service._smart_batch_analysis = {
            "batches": [{"jobs": [Mock(id="job_1"), Mock(id="job_2")], "signature": ("edge",)}],
            "efficiency": {"job_count_before": 2, "job_count_after": 1, "estimated_speedup": 2.0},
        }
        queue_service._analysis_queue_size = 2

        mock_session = Mock()
        mock_session.query().filter_by().all.return_value = [Mock(), Mock()]
        queue_service.db_connection.get_session.return_value.__enter__ = Mock(
            return_value=mock_session
        )
        queue_service.db_connection.get_session.return_value.__exit__ = Mock()

        # Simulate batch execution failure
        queue_service.cosmos_api.batch_inference.side_effect = Exception("GPU memory error")

        results = queue_service.execute_smart_batches()

        assert results is not None
        assert "error" in results or results.get("batches_failed", 0) > 0

    def _create_mock_job(self, job_id, job_type):
        """Helper to create mock job objects."""
        job = Mock(spec=JobQueue)
        job.id = job_id
        job.job_type = job_type
        job.status = "queued"
        job.prompt_ids = ["ps_test"]
        job.config = {"weights": {"edge": 0.5}}
        return job
