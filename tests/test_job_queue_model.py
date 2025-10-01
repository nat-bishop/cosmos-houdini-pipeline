"""Test suite for JobQueue database model.

These tests define the behavioral contract for the job queue persistence layer.
Tests focus on user-observable behaviors: creating jobs, querying status,
and tracking execution lifecycle.
"""

from datetime import datetime, timezone

import pytest

from cosmos_workflow.database import DatabaseConnection
from cosmos_workflow.database.models import JobQueue


class TestJobQueueModel:
    """Test JobQueue model behavior."""

    @pytest.fixture
    def test_db(self):
        """Create an in-memory test database following existing pattern."""
        db = DatabaseConnection(":memory:")
        db.create_tables()
        return db

    @pytest.fixture
    def db_session(self, test_db):
        """Get database session from test database."""
        with test_db.get_session() as session:
            yield session

    def test_create_job_with_required_fields(self, db_session):
        """User can create a job with all required fields."""
        # Arrange
        job_data = {
            "id": "job_test_001",
            "prompt_ids": ["ps_12345"],
            "job_type": "inference",
            "status": "queued",
            "config": {"weights": {"vis": 1.0}, "num_steps": 25},
        }

        # Act
        job = JobQueue(**job_data)
        db_session.add(job)
        db_session.commit()

        # Assert
        retrieved = db_session.query(JobQueue).filter_by(id="job_test_001").first()
        assert retrieved is not None
        assert retrieved.prompt_ids == ["ps_12345"]
        assert retrieved.job_type == "inference"
        assert retrieved.status == "queued"
        assert retrieved.config["weights"]["vis"] == 1.0
        assert retrieved.created_at is not None

    def test_job_supports_multiple_prompt_ids(self, db_session):
        """User can create batch jobs with multiple prompt IDs."""
        # Arrange
        job_data = {
            "id": "job_batch_001",
            "prompt_ids": ["ps_001", "ps_002", "ps_003"],
            "job_type": "batch_inference",
            "status": "queued",
            "config": {"weights": {"vis": 1.0}},
        }

        # Act
        job = JobQueue(**job_data)
        db_session.add(job)
        db_session.commit()

        # Assert
        retrieved = db_session.query(JobQueue).filter_by(id="job_batch_001").first()
        assert len(retrieved.prompt_ids) == 3
        assert "ps_002" in retrieved.prompt_ids

    def test_job_status_transitions(self, db_session):
        """User can track job status through its lifecycle."""
        # Arrange
        job = JobQueue(
            id="job_status_001",
            prompt_ids=["ps_12345"],
            job_type="inference",
            status="queued",
            config={},
        )
        db_session.add(job)
        db_session.commit()

        # Act - Transition through statuses
        job.status = "running"
        job.started_at = datetime.now(timezone.utc)
        db_session.commit()

        retrieved = db_session.query(JobQueue).filter_by(id="job_status_001").first()
        assert retrieved.status == "running"
        assert retrieved.started_at is not None

        job.status = "completed"
        job.completed_at = datetime.now(timezone.utc)
        job.result = {"output_path": "/outputs/result.mp4"}
        db_session.commit()

        # Assert
        final = db_session.query(JobQueue).filter_by(id="job_status_001").first()
        assert final.status == "completed"
        assert final.completed_at is not None
        assert final.result["output_path"] == "/outputs/result.mp4"

    def test_query_jobs_by_status(self, db_session):
        """User can query jobs filtered by status."""
        # Arrange
        jobs = [
            JobQueue(
                id=f"job_{i}",
                prompt_ids=[f"ps_{i}"],
                job_type="inference",
                status=status,
                config={},
            )
            for i, status in enumerate(["queued", "queued", "running", "completed"])
        ]
        db_session.add_all(jobs)
        db_session.commit()

        # Act
        queued_jobs = db_session.query(JobQueue).filter_by(status="queued").all()
        running_jobs = db_session.query(JobQueue).filter_by(status="running").all()

        # Assert
        assert len(queued_jobs) == 2
        assert len(running_jobs) == 1
        assert all(j.status == "queued" for j in queued_jobs)

    def test_get_queue_position(self, db_session):
        """User can determine a job's position in the queue."""
        # Arrange
        from datetime import timedelta

        base_time = datetime.now(timezone.utc)

        for i in range(5):
            job = JobQueue(
                id=f"job_{i:03d}",
                prompt_ids=[f"ps_{i}"],
                job_type="inference",
                status="queued" if i > 0 else "running",
                config={},
            )
            # Override created_at to ensure order
            db_session.add(job)
            db_session.flush()
            job.created_at = base_time + timedelta(seconds=i)

        db_session.commit()

        # Act - Get position of job_003
        # In a real implementation, this would be a method or query
        queued = (
            db_session.query(JobQueue)
            .filter_by(status="queued")
            .order_by(JobQueue.created_at)
            .all()
        )

        position = next((i for i, j in enumerate(queued, 1) if j.id == "job_003"), None)

        # Assert
        assert position == 3  # It's the 3rd queued job (job_001, job_002, job_003 are queued)

    def test_job_error_tracking(self, db_session):
        """User can see why a job failed."""
        # Arrange
        job = JobQueue(
            id="job_error_001",
            prompt_ids=["ps_12345"],
            job_type="inference",
            status="running",
            config={},
        )
        db_session.add(job)
        db_session.commit()

        # Act - Mark job as failed with error in result
        job.status = "failed"
        job.completed_at = datetime.now(timezone.utc)
        job.result = {"error": "GPU out of memory", "details": "CUDA OOM: Allocation failed"}
        db_session.commit()

        # Assert
        retrieved = db_session.query(JobQueue).filter_by(id="job_error_001").first()
        assert retrieved.status == "failed"
        assert "out of memory" in retrieved.result["error"]
        assert "CUDA OOM" in retrieved.result["details"]

    def test_job_config_flexibility(self, db_session):
        """User can store various configuration types for different job types."""
        # Arrange
        inference_job = JobQueue(
            id="job_inf_001",
            prompt_ids=["ps_001"],
            job_type="inference",
            status="queued",
            config={
                "weights": {"vis": 1.0, "edge": 0.5},
                "num_steps": 25,
                "guidance_scale": 4.0,
                "seed": 42,
            },
        )

        enhance_job = JobQueue(
            id="job_enh_001",
            prompt_ids=["ps_002"],
            job_type="enhancement",
            status="queued",
            config={
                "model": "pixtral",
                "create_new": True,
                "force_overwrite": False,
            },
        )

        # Act
        db_session.add_all([inference_job, enhance_job])
        db_session.commit()

        # Assert
        inf = db_session.query(JobQueue).filter_by(id="job_inf_001").first()
        enh = db_session.query(JobQueue).filter_by(id="job_enh_001").first()

        assert inf.config["weights"]["edge"] == 0.5
        assert inf.config["seed"] == 42
        assert enh.config["model"] == "pixtral"
        assert enh.config["create_new"] is True

    def test_fifo_queue_ordering(self, db_session):
        """Jobs are processed in FIFO order based on created_at."""
        # Arrange
        from datetime import timedelta

        base_time = datetime.now(timezone.utc)

        # Create jobs with specific creation times
        jobs = []
        for i in range(5):
            job = JobQueue(
                id=f"fifo_{i:03d}",
                prompt_ids=[f"ps_{i}"],
                job_type="inference",
                status="queued",
                config={},
            )
            db_session.add(job)
            db_session.flush()
            # Set specific created_at to ensure order
            job.created_at = base_time + timedelta(seconds=i * 10)
            jobs.append(job)

        db_session.commit()

        # Act - Query jobs in queue order
        queued_jobs = (
            db_session.query(JobQueue)
            .filter_by(status="queued")
            .order_by(JobQueue.created_at)
            .all()
        )

        # Assert - Jobs are in FIFO order
        for i, job in enumerate(queued_jobs):
            assert job.id == f"fifo_{i:03d}"
            if i > 0:
                assert job.created_at > queued_jobs[i - 1].created_at

    def test_job_priority_field_optional(self, db_session):
        """Priority field is optional with default value."""
        # Arrange
        job = JobQueue(
            id="job_priority_001",
            prompt_ids=["ps_001"],
            job_type="inference",
            status="queued",
            config={},
            # Not setting priority - should use default
        )

        # Act
        db_session.add(job)
        db_session.commit()

        # Assert
        retrieved = db_session.query(JobQueue).filter_by(id="job_priority_001").first()
        # Priority should have a default value (e.g., 50 or None)
        assert hasattr(retrieved, "priority")

    def test_cancelled_job_status(self, db_session):
        """User can cancel a queued job."""
        # Arrange
        job = JobQueue(
            id="job_cancel_001",
            prompt_ids=["ps_001"],
            job_type="inference",
            status="queued",
            config={},
        )
        db_session.add(job)
        db_session.commit()

        # Act
        job.status = "cancelled"
        job.completed_at = datetime.now(timezone.utc)
        job.result = {"reason": "User cancelled"}
        db_session.commit()

        # Assert
        retrieved = db_session.query(JobQueue).filter_by(id="job_cancel_001").first()
        assert retrieved.status == "cancelled"
        assert retrieved.result["reason"] == "User cancelled"

    def test_job_validates_required_fields(self, db_session):
        """System prevents creating jobs without required fields."""
        from sqlalchemy.exc import IntegrityError

        # Act & Assert - Test missing required JSON fields
        with pytest.raises(IntegrityError):  # SQLAlchemy raises IntegrityError for NOT NULL
            job = JobQueue(id="job_invalid_001")  # Missing required fields
            db_session.add(job)
            db_session.flush()  # This will trigger validation

        # Need to rollback after the error
        db_session.rollback()

        # Test that we can create job without id but it fails on commit
        job = JobQueue(
            prompt_ids=["ps_001"],  # Missing id
            job_type="inference",
            status="queued",
            config={},
        )
        db_session.add(job)
        with pytest.raises(IntegrityError):  # Should fail when trying to commit without primary key
            db_session.commit()
