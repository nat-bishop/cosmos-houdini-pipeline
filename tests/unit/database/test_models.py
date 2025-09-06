"""Test database models for cosmos workflow.

Tests follow TDD Gate 1: Write comprehensive tests before implementation.
These tests verify the flexible schema that supports multiple AI models.
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from cosmos_workflow.database.models import Base, Prompt, Run


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
        from sqlalchemy.exc import IntegrityError

        with pytest.raises(IntegrityError):  # Should fail without required fields
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
        before = datetime.now(timezone.utc).replace(tzinfo=None)
        prompt = Prompt(
            id="ps_time",
            model_type="transfer",
            prompt_text="test",
            inputs={},
            parameters={},
        )
        session.add(prompt)
        session.commit()
        after = datetime.now(timezone.utc).replace(tzinfo=None)

        assert isinstance(prompt.created_at, datetime)
        # SQLite doesn't preserve timezone info, but timestamp should be in range
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
            run_metadata={"user": "NAT", "priority": "high"},
        )
        session.add(run)
        session.commit()

        retrieved = session.get(Run, run.id)
        assert retrieved is not None
        assert retrieved.prompt_id == sample_prompt.id
        assert retrieved.status == "pending"
        assert retrieved.execution_config["gpu_node"] == "gpu-001"
        assert retrieved.run_metadata["user"] == "NAT"

    def test_run_status_transitions(self, session: Session, sample_prompt: Prompt):
        """Test updating run status through lifecycle."""
        run = Run(
            id="rs_status",
            prompt_id=sample_prompt.id,
            model_type="transfer",
            status="pending",
            execution_config={},
            outputs={},
            run_metadata={},
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
            run_metadata={},
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
            run_metadata={},
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
                run_metadata={},
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
                run_metadata={},
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


class TestModelValidation:
    """Test model validation rules."""

    def test_prompt_rejects_none_json_fields(self):
        """Test that Prompt rejects None for JSON fields."""
        with pytest.raises(ValueError, match="inputs cannot be None"):
            Prompt(
                id="ps_invalid",
                model_type="transfer",
                prompt_text="test",
                inputs=None,
                parameters={},
            )

        with pytest.raises(ValueError, match="parameters cannot be None"):
            Prompt(
                id="ps_invalid",
                model_type="transfer",
                prompt_text="test",
                inputs={},
                parameters=None,
            )

    def test_prompt_rejects_empty_required_fields(self):
        """Test that Prompt rejects empty required fields."""
        with pytest.raises(ValueError, match="model_type cannot be None or empty"):
            Prompt(id="ps_invalid", model_type="", prompt_text="test", inputs={}, parameters={})

        with pytest.raises(ValueError, match="prompt_text cannot be None or empty"):
            Prompt(
                id="ps_invalid", model_type="transfer", prompt_text="   ", inputs={}, parameters={}
            )

    def test_run_validates_required_fields(self):
        """Test that Run validates required fields."""
        with pytest.raises(ValueError, match="execution_config cannot be None"):
            Run(
                id="rs_invalid",
                prompt_id="ps_test",
                model_type="transfer",
                status="pending",
                execution_config=None,
                outputs={},
                run_metadata={},
            )

        with pytest.raises(ValueError, match="status cannot be None or empty"):
            Run(
                id="rs_invalid",
                prompt_id="ps_test",
                model_type="transfer",
                status="",
                execution_config={},
                outputs={},
                run_metadata={},
            )


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
        """Test complete workflow from prompt to completion."""
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
            run_metadata={"session": "test"},
        )
        session.add(run)
        session.commit()

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
                run_metadata={},
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
            run_metadata={},
        )

        session.add(prompt)
        session.add(run)
        session.commit()

        # Verify all objects exist
        assert session.get(Prompt, prompt.id) is not None
        assert session.get(Run, run.id) is not None

        # Test that deleting prompt cascades to runs
        session.delete(prompt)
        session.commit()

        assert session.get(Prompt, prompt.id) is None
        assert session.get(Run, run.id) is None
