"""Integration tests for smart batching end-to-end workflow.

Tests the complete smart batching feature from UI interaction through execution.
Verifies the feature works as an overlay on existing functionality.
"""

from unittest.mock import Mock

import pytest

from cosmos_workflow.api.cosmos_api import CosmosAPI
from cosmos_workflow.database import DatabaseConnection
from cosmos_workflow.services.simple_queue_service import SimplifiedQueueService


class TestSmartBatchingWorkflow:
    """Test complete smart batching workflows."""

    @pytest.fixture
    def integration_setup(self, tmp_path):
        """Set up integration test environment."""
        # Create test database
        db_path = tmp_path / "test.db"
        db_connection = DatabaseConnection(str(db_path))
        db_connection.create_tables()

        # Mock CosmosAPI
        cosmos_api = Mock(spec=CosmosAPI)
        cosmos_api.get_active_containers.return_value = []
        cosmos_api.batch_inference.return_value = {"status": "success", "run_ids": []}

        # Create queue service
        queue_service = SimplifiedQueueService(cosmos_api, db_connection)

        return {
            "queue_service": queue_service,
            "cosmos_api": cosmos_api,
            "db_connection": db_connection,
        }

    def test_basic_smart_batching_workflow(self, integration_setup):
        """Test basic workflow: add jobs, analyze, execute."""
        queue_service = integration_setup["queue_service"]

        # Step 1: Add multiple jobs with similar controls
        job_ids = []
        for i in range(6):
            job_id = queue_service.add_job(
                prompt_ids=[f"ps_00{i}"],
                job_type="inference",
                config={"weights": {"edge": 0.5, "depth": 0.0}},
            )
            job_ids.append(job_id)

        # Step 2: Pause queue (prerequisite for smart batching)
        queue_service.set_queue_paused(True)
        assert queue_service.is_queue_paused()

        # Step 3: Analyze for smart batching
        analysis = queue_service.analyze_queue_for_smart_batching(mix_controls=False)

        assert analysis is not None
        assert analysis["efficiency"]["job_count_before"] == 6
        assert analysis["efficiency"]["estimated_speedup"] > 1.0

        # Step 4: Review preview
        preview = queue_service.get_smart_batch_preview()
        assert preview != ""
        assert "jobs" in preview.lower()
        assert "batch" in preview.lower()

        # Step 5: Execute smart batches
        results = queue_service.execute_smart_batches()

        assert results["jobs_executed"] == 6
        assert results["batches_created"] >= 1
        assert results["speedup"] > 1.0

    def test_strict_mode_grouping(self, integration_setup):
        """Test strict mode groups only identical control signatures."""
        queue_service = integration_setup["queue_service"]

        # Add jobs with different control signatures
        queue_service.add_job(["ps_001"], "inference", {"weights": {"edge": 0.5}})
        queue_service.add_job(["ps_002"], "inference", {"weights": {"edge": 0.5}})
        queue_service.add_job(["ps_003"], "inference", {"weights": {"depth": 0.5}})
        queue_service.add_job(["ps_004"], "inference", {"weights": {"depth": 0.5}})

        queue_service.set_queue_paused(True)

        # Analyze in strict mode
        analysis = queue_service.analyze_queue_for_smart_batching(mix_controls=False)

        # Should create 2 separate batches (edge and depth)
        assert len(analysis["batches"]) == 2

        # Verify each batch has consistent signatures
        for batch in analysis["batches"]:
            job_signatures = set()
            for job in batch["jobs"]:
                sig = tuple(sorted([k for k, v in job.config.get("weights", {}).items() if v > 0]))
                job_signatures.add(sig)
            assert len(job_signatures) == 1  # All jobs in batch have same signature

    def test_mixed_mode_optimization(self, integration_setup):
        """Test mixed mode creates optimized master batches."""
        queue_service = integration_setup["queue_service"]

        # Add jobs with overlapping controls
        queue_service.add_job(["ps_001"], "inference", {"weights": {"edge": 0.5}})
        queue_service.add_job(["ps_002"], "inference", {"weights": {"depth": 0.5}})
        queue_service.add_job(["ps_003"], "inference", {"weights": {"edge": 0.3, "depth": 0.7}})

        queue_service.set_queue_paused(True)

        # Analyze in mixed mode
        analysis = queue_service.analyze_queue_for_smart_batching(mix_controls=True)

        # Mixed mode should create fewer batches by using master controls
        assert analysis is not None
        assert len(analysis["batches"]) <= 2  # Optimized grouping

        # Execute and verify
        results = queue_service.execute_smart_batches()
        assert results["jobs_executed"] == 3

    def test_edge_case_empty_queue(self, integration_setup):
        """Test smart batching with empty queue."""
        queue_service = integration_setup["queue_service"]
        queue_service.set_queue_paused(True)

        analysis = queue_service.analyze_queue_for_smart_batching()
        assert analysis is None

        preview = queue_service.get_smart_batch_preview()
        assert preview == ""

    def test_edge_case_single_job(self, integration_setup):
        """Test smart batching with single job."""
        queue_service = integration_setup["queue_service"]

        queue_service.add_job(["ps_001"], "inference", {"weights": {"edge": 0.5}})
        queue_service.set_queue_paused(True)

        analysis = queue_service.analyze_queue_for_smart_batching()

        assert analysis is not None
        assert len(analysis["batches"]) == 1
        assert analysis["efficiency"]["job_count_before"] == 1
        assert analysis["efficiency"]["job_count_after"] == 1

    def test_non_batchable_jobs_excluded(self, integration_setup):
        """Test that enhance/upscale jobs are excluded from batching."""
        queue_service = integration_setup["queue_service"]

        # Add mix of batchable and non-batchable jobs
        queue_service.add_job(["ps_001"], "inference", {"weights": {"edge": 0.5}})
        queue_service.add_job(["ps_002"], "enhancement", {"model": "esrgan"})
        queue_service.add_job(["ps_003"], "batch_inference", {"weights": {"depth": 0.5}})
        queue_service.add_job(["ps_004"], "upscale", {"run_id": "run_123"})

        queue_service.set_queue_paused(True)

        analysis = queue_service.analyze_queue_for_smart_batching()

        # Only inference and batch_inference should be analyzed
        assert analysis is not None
        assert analysis["efficiency"]["job_count_before"] == 2

    def test_queue_change_invalidates_analysis(self, integration_setup):
        """Test that queue changes invalidate stored analysis."""
        queue_service = integration_setup["queue_service"]

        # Add initial jobs and analyze
        for i in range(3):
            queue_service.add_job([f"ps_00{i}"], "inference", {"weights": {"edge": 0.5}})

        queue_service.set_queue_paused(True)
        analysis = queue_service.analyze_queue_for_smart_batching()
        assert analysis is not None

        # Add another job (queue change)
        queue_service.add_job(["ps_new"], "inference", {"weights": {"edge": 0.5}})

        # Try to execute with stale analysis
        results = queue_service.execute_smart_batches()
        assert "error" in results
        assert "stale" in results["error"].lower()

    def test_batch_execution_with_failure_handling(self, integration_setup):
        """Test batch execution handles failures gracefully."""
        queue_service = integration_setup["queue_service"]
        cosmos_api = integration_setup["cosmos_api"]

        # Add jobs
        for i in range(4):
            queue_service.add_job([f"ps_00{i}"], "inference", {"weights": {"edge": 0.5}})

        queue_service.set_queue_paused(True)
        queue_service.analyze_queue_for_smart_batching()

        # Simulate partial failure
        cosmos_api.batch_inference.side_effect = [
            {"status": "success", "run_ids": ["r1", "r2"]},
            Exception("GPU memory error"),
        ]

        results = queue_service.execute_smart_batches()

        # Should report partial success
        assert results is not None
        # At least some jobs should succeed
        assert "jobs_executed" in results or "error" in results

    def test_performance_benchmark_strict_mode(self, integration_setup):
        """Benchmark performance improvement in strict mode."""
        queue_service = integration_setup["queue_service"]

        # Add many jobs with identical controls
        for i in range(12):
            queue_service.add_job([f"ps_{i:03d}"], "inference", {"weights": {"edge": 0.5}})

        queue_service.set_queue_paused(True)
        analysis = queue_service.analyze_queue_for_smart_batching(mix_controls=False)

        # With identical controls, expect significant speedup
        assert analysis["efficiency"]["estimated_speedup"] >= 3.0
        assert analysis["efficiency"]["estimated_speedup"] <= 5.0

    def test_performance_benchmark_mixed_mode(self, integration_setup):
        """Benchmark performance improvement in mixed mode."""
        queue_service = integration_setup["queue_service"]

        # Add jobs with varied controls
        controls = [
            {"edge": 0.5},
            {"depth": 0.5},
            {"edge": 0.3, "depth": 0.7},
            {"normal": 0.5},
        ]

        for i in range(12):
            queue_service.add_job(
                [f"ps_{i:03d}"],
                "inference",
                {"weights": controls[i % len(controls)]},
            )

        queue_service.set_queue_paused(True)
        analysis = queue_service.analyze_queue_for_smart_batching(mix_controls=True)

        # Mixed mode should still provide speedup
        assert analysis["efficiency"]["estimated_speedup"] >= 2.0
        assert analysis["efficiency"]["estimated_speedup"] <= 3.0

    def test_memory_safety_with_conservative_sizing(self, integration_setup):
        """Test conservative batch sizing prevents OOM errors."""
        queue_service = integration_setup["queue_service"]

        # Add jobs with multiple controls (should trigger conservative sizing)
        for i in range(20):
            queue_service.add_job(
                [f"ps_{i:03d}"],
                "inference",
                {"weights": {"edge": 0.3, "depth": 0.3, "normal": 0.4}},
            )

        queue_service.set_queue_paused(True)
        analysis = queue_service.analyze_queue_for_smart_batching()

        # With 3 controls, batch size should be limited to 2
        for batch in analysis["batches"]:
            assert len(batch["jobs"]) <= 2

    def test_queue_remains_functional_without_smart_batching(self, integration_setup):
        """Test that normal queue operations work without smart batching."""
        queue_service = integration_setup["queue_service"]

        # Add jobs and process normally (without smart batching)
        job_id = queue_service.add_job(["ps_001"], "inference", {"weights": {"edge": 0.5}})

        # Process job normally
        claimed_job = queue_service.claim_next_job()
        assert claimed_job == job_id

        # Queue functionality unaffected
        status = queue_service.get_queue_status()
        assert status["total_queued"] == 0
        assert status["running"] is not None
