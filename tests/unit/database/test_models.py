"""Test database models for cosmos workflow.

Tests follow TDD Gate 1: Write comprehensive tests before implementation.
These tests verify the flexible schema that supports multiple AI models.
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from cosmos_workflow.database.models import Base, Progress, Prompt, Run


class TestPromptModel:
    """Test Prompt model with flexible schema for multiple AI models."""

    @pytest.fixture
    def session(self):
        """Create in-memory database session."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        with Session(engine) as session:
            yield session

    def test_create_transfer_prompt(self, session: Session):
        """Test creating a prompt for cosmos transfer model."""
        prompt = Prompt(
            id="ps_20250104_120000_abc123",
            model_type="transfer",
            prompt_text="cyberpunk city at night",
            inputs={
                "video": "/inputs/videos/city.mp4",
                "depth": "/inputs/depth/city_depth.mp4",
            },
            parameters={"num_steps": 35, "cfg_scale": 7.5},
        )
        session.add(prompt)
        session.commit()

        retrieved = session.get(Prompt, prompt.id)
        assert retrieved is not None
        assert retrieved.model_type == "transfer"
        assert retrieved.prompt_text == "cyberpunk city at night"
        assert retrieved.inputs["video"] == "/inputs/videos/city.mp4"
        assert retrieved.parameters["num_steps"] == 35
        assert isinstance(retrieved.created_at, datetime)

    def test_create_reason_prompt(self, session: Session):
        """Test creating a prompt for future cosmos reason model."""
        prompt = Prompt(
            id="ps_20250104_130000_def456",
            model_type="reason",
            prompt_text="What happens next in this scene?",
            inputs={"video": "/outputs/result.mp4", "context": "urban environment"},
            parameters={"reasoning_depth": 3, "temperature": 0.7},
        )
        session.add(prompt)
        session.commit()

        retrieved = session.get(Prompt, prompt.id)
        assert retrieved.model_type == "reason"
        assert retrieved.inputs["context"] == "urban environment"
        assert retrieved.parameters["reasoning_depth"] == 3

    def test_create_predict_prompt(self, session: Session):
        """Test creating a prompt for future cosmos predict model."""
        prompt = Prompt(
            id="ps_20250104_140000_ghi789",
            model_type="predict",
            prompt_text="Continue this animation",
            inputs={
                "frames": ["frame1.png", "frame2.png", "frame3.png"],
                "motion_vectors": "/inputs/motion.json",
            },
            parameters={"prediction_length": 60, "fps": 30},
        )
        session.add(prompt)
        session.commit()

        retrieved = session.get(Prompt, prompt.id)
        assert retrieved.model_type == "predict"
        assert len(retrieved.inputs["frames"]) == 3
        assert retrieved.parameters["prediction_length"] == 60

    def test_prompt_json_columns_flexibility(self, session: Session):
        """Test that JSON columns can store arbitrary data structures."""
        complex_inputs = {
            "videos": ["/v1.mp4", "/v2.mp4"],
            "metadata": {"resolution": "1920x1080", "codec": "h264"},
            "nested": {"level1": {"level2": {"data": "value"}}},
        }

        complex_params = {
            "model_config": {"layers": 12, "attention_heads": 8},
            "sampling": {"method": "ddpm", "steps": 50},
            "array_param": [1, 2, 3, 4, 5],
        }

        prompt = Prompt(
            id="ps_complex",
            model_type="experimental",
            prompt_text="test",
            inputs=complex_inputs,
            parameters=complex_params,
        )
        session.add(prompt)
        session.commit()

        retrieved = session.get(Prompt, "ps_complex")
        assert retrieved.inputs["metadata"]["resolution"] == "1920x1080"
        assert retrieved.inputs["nested"]["level1"]["level2"]["data"] == "value"
        assert retrieved.parameters["model_config"]["layers"] == 12
        assert retrieved.parameters["array_param"][2] == 3

    def test_prompt_required_fields(self, session: Session):
        """Test that required fields are enforced."""
        with pytest.raises(TypeError):  # Should fail without required fields
            prompt = Prompt(id="ps_invalid")
            session.add(prompt)
            session.commit()

    def test_query_prompts_by_model_type(self, session: Session):
        """Test filtering prompts by model type."""
        prompt1 = Prompt(
            id="ps_1",
            model_type="transfer",
            prompt_text="test1",
            inputs={},
            parameters={},
        )
        prompt2 = Prompt(
            id="ps_2",
            model_type="reason",
            prompt_text="test2",
            inputs={},
            parameters={},
        )
        prompt3 = Prompt(
            id="ps_3",
            model_type="transfer",
            prompt_text="test3",
            inputs={},
            parameters={},
        )
        session.add_all([prompt1, prompt2, prompt3])
        session.commit()

        transfer_prompts = session.scalars(
            select(Prompt).where(Prompt.model_type == "transfer")
        ).all()
        assert len(transfer_prompts) == 2
        assert all(p.model_type == "transfer" for p in transfer_prompts)

    def test_prompt_timestamp_auto_set(self, session: Session):
        """Test that created_at is automatically set."""
        before = datetime.now(timezone.utc)
        prompt = Prompt(
            id="ps_time",
            model_type="transfer",
            prompt_text="test",
            inputs={},
            parameters={},
        )
        session.add(prompt)
        session.commit()
        after = datetime.now(timezone.utc)

        assert before <= prompt.created_at <= after


class TestRunModel:
    """Test Run model for tracking executions."""

    @pytest.fixture
    def session(self):
        """Create in-memory database session."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        with Session(engine) as session:
            yield session

    @pytest.fixture
    def sample_prompt(self, session: Session) -> Prompt:
        """Create a sample prompt for run tests."""
        prompt = Prompt(
            id="ps_test",
            model_type="transfer",
            prompt_text="test prompt",
            inputs={"video": "/test.mp4"},
            parameters={"num_steps": 35},
        )
        session.add(prompt)
        session.commit()
        return prompt

    def test_create_run_for_prompt(self, session: Session, sample_prompt: Prompt):
        """Test creating a run associated with a prompt."""
        run = Run(
            id="rs_20250104_120000_abc123",
            prompt_id=sample_prompt.id,
            model_type="transfer",
            status="pending",
            execution_config={
                "gpu_node": "gpu-001",
                "docker_image": "cosmos:latest",
                "weights": "/weights/cosmos_transfer.ckpt",
            },
            outputs={},
            metadata={"user": "NAT", "priority": "high"},
        )
        session.add(run)
        session.commit()

        retrieved = session.get(Run, run.id)
        assert retrieved is not None
        assert retrieved.prompt_id == sample_prompt.id
        assert retrieved.status == "pending"
        assert retrieved.execution_config["gpu_node"] == "gpu-001"
        assert retrieved.metadata["user"] == "NAT"

    def test_run_status_transitions(self, session: Session, sample_prompt: Prompt):
        """Test updating run status through lifecycle."""
        run = Run(
            id="rs_status",
            prompt_id=sample_prompt.id,
            model_type="transfer",
            status="pending",
            execution_config={},
            outputs={},
            metadata={},
        )
        session.add(run)
        session.commit()

        statuses = ["pending", "uploading", "running", "downloading", "completed"]
        for status in statuses:
            run.status = status
            session.commit()
            retrieved = session.get(Run, run.id)
            assert retrieved.status == status

    def test_run_outputs_storage(self, session: Session, sample_prompt: Prompt):
        """Test storing outputs in flexible JSON format."""
        run = Run(
            id="rs_outputs",
            prompt_id=sample_prompt.id,
            model_type="transfer",
            status="completed",
            execution_config={},
            outputs={
                "result_video": "/outputs/result.mp4",
                "metrics": {
                    "inference_time": 45.3,
                    "gpu_memory_used": "12GB",
                    "frames_processed": 120,
                },
                "logs": ["Step 1: Upload", "Step 2: Inference", "Step 3: Download"],
            },
            metadata={},
        )
        session.add(run)
        session.commit()

        retrieved = session.get(Run, run.id)
        assert retrieved.outputs["result_video"] == "/outputs/result.mp4"
        assert retrieved.outputs["metrics"]["inference_time"] == 45.3
        assert len(retrieved.outputs["logs"]) == 3

    def test_run_timestamps(self, session: Session, sample_prompt: Prompt):
        """Test automatic timestamp management."""
        run = Run(
            id="rs_time",
            prompt_id=sample_prompt.id,
            model_type="transfer",
            status="pending",
            execution_config={},
            outputs={},
            metadata={},
        )
        session.add(run)
        session.commit()

        assert isinstance(run.created_at, datetime)
        assert isinstance(run.updated_at, datetime)
        assert run.started_at is None
        assert run.completed_at is None

        # Update to running
        run.status = "running"
        run.started_at = datetime.now(timezone.utc)
        session.commit()
        assert run.started_at is not None

        # Update to completed
        run.status = "completed"
        run.completed_at = datetime.now(timezone.utc)
        session.commit()
        assert run.completed_at is not None
        assert run.updated_at > run.created_at

    def test_query_runs_by_status(self, session: Session, sample_prompt: Prompt):
        """Test filtering runs by status."""
        runs = [
            Run(
                id=f"rs_{i}",
                prompt_id=sample_prompt.id,
                model_type="transfer",
                status=status,
                execution_config={},
                outputs={},
                metadata={},
            )
            for i, status in enumerate(["pending", "running", "completed", "failed", "completed"])
        ]
        session.add_all(runs)
        session.commit()

        completed_runs = session.scalars(select(Run).where(Run.status == "completed")).all()
        assert len(completed_runs) == 2

        active_runs = session.scalars(
            select(Run).where(Run.status.in_(["pending", "running"]))
        ).all()
        assert len(active_runs) == 2

    def test_run_prompt_relationship(self, session: Session):
        """Test relationship between Run and Prompt."""
        prompt = Prompt(
            id="ps_rel",
            model_type="transfer",
            prompt_text="test",
            inputs={},
            parameters={},
        )
        session.add(prompt)
        session.commit()

        runs = [
            Run(
                id=f"rs_rel_{i}",
                prompt_id=prompt.id,
                model_type="transfer",
                status="pending",
                execution_config={},
                outputs={},
                metadata={},
            )
            for i in range(3)
        ]
        session.add_all(runs)
        session.commit()

        # Test accessing runs through prompt
        prompt_runs = prompt.runs
        assert len(prompt_runs) == 3
        assert all(r.prompt_id == prompt.id for r in prompt_runs)

        # Test accessing prompt through run
        run = runs[0]
        assert run.prompt.id == prompt.id
        assert run.prompt.prompt_text == "test"


class TestProgressModel:
    """Test Progress model for real-time tracking."""

    @pytest.fixture
    def session(self):
        """Create in-memory database session."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        with Session(engine) as session:
            yield session

    @pytest.fixture
    def sample_run(self, session: Session) -> Run:
        """Create a sample run for progress tests."""
        prompt = Prompt(
            id="ps_prog",
            model_type="transfer",
            prompt_text="test",
            inputs={},
            parameters={},
        )
        session.add(prompt)

        run = Run(
            id="rs_prog",
            prompt_id=prompt.id,
            model_type="transfer",
            status="running",
            execution_config={},
            outputs={},
            metadata={},
        )
        session.add(run)
        session.commit()
        return run

    def test_create_progress_entry(self, session: Session, sample_run: Run):
        """Test creating progress tracking entries."""
        progress = Progress(
            run_id=sample_run.id,
            stage="uploading",
            percentage=45.5,
            message="Uploading depth video to GPU node...",
        )
        session.add(progress)
        session.commit()

        assert progress.id is not None
        assert progress.run_id == sample_run.id
        assert progress.stage == "uploading"
        assert progress.percentage == 45.5
        assert "depth video" in progress.message
        assert isinstance(progress.timestamp, datetime)

    def test_progress_stages(self, session: Session, sample_run: Run):
        """Test tracking different execution stages."""
        stages = [
            ("uploading", 0.0, "Starting upload"),
            ("uploading", 50.0, "Uploading video"),
            ("uploading", 100.0, "Upload complete"),
            ("inference", 0.0, "Starting inference"),
            ("inference", 25.0, "Processing frame 30/120"),
            ("inference", 50.0, "Processing frame 60/120"),
            ("inference", 75.0, "Processing frame 90/120"),
            ("inference", 100.0, "Inference complete"),
            ("downloading", 0.0, "Starting download"),
            ("downloading", 100.0, "Download complete"),
        ]

        for stage, percentage, message in stages:
            progress = Progress(
                run_id=sample_run.id,
                stage=stage,
                percentage=percentage,
                message=message,
            )
            session.add(progress)
        session.commit()

        # Query progress by stage
        upload_progress = session.scalars(
            select(Progress).where(
                (Progress.run_id == sample_run.id) & (Progress.stage == "uploading")
            )
        ).all()
        assert len(upload_progress) == 3

        # Query latest progress
        latest = session.scalars(
            select(Progress)
            .where(Progress.run_id == sample_run.id)
            .order_by(Progress.timestamp.desc())
            .limit(1)
        ).first()
        assert latest.stage == "downloading"
        assert latest.percentage == 100.0

    def test_progress_run_relationship(self, session: Session, sample_run: Run):
        """Test relationship between Progress and Run."""
        progress_entries = [
            Progress(
                run_id=sample_run.id,
                stage="uploading",
                percentage=float(i * 20),
                message=f"Progress {i}",
            )
            for i in range(5)
        ]
        session.add_all(progress_entries)
        session.commit()

        # Access progress through run
        run_progress = sample_run.progress
        assert len(run_progress) == 5
        assert all(p.run_id == sample_run.id for p in run_progress)

        # Access run through progress
        progress = progress_entries[0]
        assert progress.run.id == sample_run.id

    def test_progress_chronological_order(self, session: Session, sample_run: Run):
        """Test that progress entries maintain chronological order."""
        import time

        progress1 = Progress(
            run_id=sample_run.id,
            stage="uploading",
            percentage=0.0,
            message="Start",
        )
        session.add(progress1)
        session.commit()

        time.sleep(0.01)  # Small delay to ensure different timestamps

        progress2 = Progress(
            run_id=sample_run.id,
            stage="uploading",
            percentage=50.0,
            message="Middle",
        )
        session.add(progress2)
        session.commit()

        time.sleep(0.01)

        progress3 = Progress(
            run_id=sample_run.id,
            stage="uploading",
            percentage=100.0,
            message="End",
        )
        session.add(progress3)
        session.commit()

        # Query in chronological order
        ordered_progress = session.scalars(
            select(Progress).where(Progress.run_id == sample_run.id).order_by(Progress.timestamp)
        ).all()

        assert len(ordered_progress) == 3
        assert ordered_progress[0].percentage == 0.0
        assert ordered_progress[1].percentage == 50.0
        assert ordered_progress[2].percentage == 100.0
        assert ordered_progress[0].timestamp < ordered_progress[1].timestamp
        assert ordered_progress[1].timestamp < ordered_progress[2].timestamp


class TestDatabaseIntegration:
    """Integration tests for all models working together."""

    @pytest.fixture
    def session(self):
        """Create in-memory database session."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        with Session(engine) as session:
            yield session

    def test_full_workflow_lifecycle(self, session: Session):
        """Test complete workflow from prompt to completion with progress."""
        # Create prompt
        prompt = Prompt(
            id="ps_workflow",
            model_type="transfer",
            prompt_text="futuristic landscape",
            inputs={
                "video": "/inputs/landscape.mp4",
                "depth": "/inputs/landscape_depth.mp4",
            },
            parameters={"num_steps": 50},
        )
        session.add(prompt)
        session.commit()

        # Create run
        run = Run(
            id="rs_workflow",
            prompt_id=prompt.id,
            model_type="transfer",
            status="pending",
            execution_config={
                "gpu_node": "gpu-002",
                "docker_image": "cosmos:latest",
            },
            outputs={},
            metadata={"session": "test"},
        )
        session.add(run)
        session.commit()

        # Add progress entries
        progress_entries = [
            Progress(run_id=run.id, stage="uploading", percentage=0.0, message="Starting"),
            Progress(
                run_id=run.id,
                stage="uploading",
                percentage=100.0,
                message="Upload complete",
            ),
            Progress(
                run_id=run.id,
                stage="inference",
                percentage=50.0,
                message="Processing",
            ),
            Progress(
                run_id=run.id,
                stage="inference",
                percentage=100.0,
                message="Inference done",
            ),
            Progress(
                run_id=run.id,
                stage="downloading",
                percentage=100.0,
                message="Complete",
            ),
        ]
        session.add_all(progress_entries)

        # Update run to completed
        run.status = "completed"
        run.outputs = {
            "result": "/outputs/landscape_futuristic.mp4",
            "metrics": {"time": 67.8},
        }
        session.commit()

        # Verify full workflow
        retrieved_prompt = session.get(Prompt, prompt.id)
        assert len(retrieved_prompt.runs) == 1

        retrieved_run = retrieved_prompt.runs[0]
        assert retrieved_run.status == "completed"
        assert retrieved_run.outputs["result"] == "/outputs/landscape_futuristic.mp4"
        assert len(retrieved_run.progress) == 5

        last_progress = retrieved_run.progress[-1]
        assert last_progress.stage == "downloading"
        assert last_progress.percentage == 100.0

    def test_multiple_runs_per_prompt(self, session: Session):
        """Test handling multiple runs for the same prompt."""
        prompt = Prompt(
            id="ps_multi",
            model_type="transfer",
            prompt_text="test",
            inputs={},
            parameters={},
        )
        session.add(prompt)

        # Create multiple runs with different statuses
        runs = []
        for i, status in enumerate(["failed", "completed", "running"]):
            run = Run(
                id=f"rs_multi_{i}",
                prompt_id=prompt.id,
                model_type="transfer",
                status=status,
                execution_config={"attempt": i + 1},
                outputs={},
                metadata={},
            )
            runs.append(run)
        session.add_all(runs)
        session.commit()

        # Verify all runs are associated
        retrieved_prompt = session.get(Prompt, prompt.id)
        assert len(retrieved_prompt.runs) == 3

        # Find successful run
        successful_runs = [r for r in retrieved_prompt.runs if r.status == "completed"]
        assert len(successful_runs) == 1
        assert successful_runs[0].execution_config["attempt"] == 2

    def test_cascade_operations(self, session: Session):
        """Test that cascade operations work correctly."""
        prompt = Prompt(
            id="ps_cascade",
            model_type="transfer",
            prompt_text="test",
            inputs={},
            parameters={},
        )
        run = Run(
            id="rs_cascade",
            prompt_id=prompt.id,
            model_type="transfer",
            status="running",
            execution_config={},
            outputs={},
            metadata={},
        )
        progress = Progress(
            run_id=run.id,
            stage="uploading",
            percentage=50.0,
            message="In progress",
        )

        session.add(prompt)
        session.add(run)
        session.add(progress)
        session.commit()

        # Verify all objects exist
        assert session.get(Prompt, prompt.id) is not None
        assert session.get(Run, run.id) is not None
        assert session.get(Progress, progress.id) is not None

        # Test that deleting prompt cascades to runs and progress
        session.delete(prompt)
        session.commit()

        assert session.get(Prompt, prompt.id) is None
        assert session.get(Run, run.id) is None
        assert session.get(Progress, progress.id) is None
