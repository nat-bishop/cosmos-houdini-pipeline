"""Integration tests for complete database workflow.

These tests verify the full flow from prompt creation through execution,
using actual database operations but mocked GPU execution.
"""

import pytest

from cosmos_workflow.config.config_manager import ConfigManager
from cosmos_workflow.database import DatabaseConnection
from cosmos_workflow.execution.gpu_executor import GPUExecutor
from cosmos_workflow.services import DataRepository


class TestDatabaseWorkflow:
    """Test the complete database-driven workflow."""

    @pytest.fixture
    def test_db(self):
        """Create an in-memory test database."""
        db = DatabaseConnection(":memory:")
        db.create_tables()
        return db

    @pytest.fixture
    def test_service(self, test_db):
        """Create a test WorkflowService with in-memory database."""
        config = ConfigManager()
        return DataRepository(test_db, config)

    @pytest.fixture
    def test_orchestrator(self):
        """Create a WorkflowOrchestrator for testing."""
        return GPUExecutor()

    @pytest.fixture
    def sample_video_files(self, tmp_path):
        """Create sample video files for testing."""
        video_dir = tmp_path / "videos"
        video_dir.mkdir()

        video_file = video_dir / "test_video.mp4"
        video_file.write_bytes(b"fake video content")

        depth_file = video_dir / "test_depth.mp4"
        depth_file.write_bytes(b"fake depth content")

        seg_file = video_dir / "test_seg.mp4"
        seg_file.write_bytes(b"fake seg content")

        return {"video": str(video_file), "depth": str(depth_file), "seg": str(seg_file)}

    def test_create_prompt_workflow(self, test_service, sample_video_files):
        """Test creating a prompt through the service layer."""
        # Create prompt
        prompt = test_service.create_prompt(
            model_type="transfer",
            prompt_text="A beautiful sunset over mountains",
            inputs=sample_video_files,
            parameters={"negative_prompt": "blurry, dark", "fps": 24},
        )

        # Verify prompt created
        assert prompt["id"] is not None
        assert prompt["model_type"] == "transfer"
        assert prompt["prompt_text"] == "A beautiful sunset over mountains"
        assert prompt["inputs"]["video"] == sample_video_files["video"]
        assert prompt["parameters"]["fps"] == 24

        # Query prompt back
        retrieved = test_service.get_prompt(prompt["id"])
        assert retrieved["id"] == prompt["id"]
        assert retrieved["prompt_text"] == prompt["prompt_text"]

    def test_create_run_workflow(self, test_service, sample_video_files):
        """Test creating and executing a run through the service layer."""
        # Create prompt first
        prompt = test_service.create_prompt(
            model_type="transfer",
            prompt_text="Ocean waves crashing on shore",
            inputs=sample_video_files,
            parameters={"negative_prompt": "static"},
        )

        # Create run for the prompt
        run = test_service.create_run(
            prompt_id=prompt["id"],
            execution_config={
                "weights": {"vis": 0.25, "edge": 0.25, "depth": 0.25, "seg": 0.25},
                "num_steps": 35,
                "guidance": 8.0,
                "seed": 42,
            },
            metadata={"test_run": True},
        )

        # Verify run created
        assert run["id"] is not None
        assert run["prompt_id"] == prompt["id"]
        assert run["status"] == "pending"
        assert run["execution_config"]["seed"] == 42

        # Update run status
        test_service.update_run_status(run["id"], "running")
        retrieved = test_service.get_run(run["id"])
        assert retrieved["status"] == "running"

        # Complete run with output
        test_service.update_run(run["id"], outputs={"frames": ["frame1.png", "frame2.png"]})
        test_service.update_run_status(run["id"], "completed")

        final_run = test_service.get_run(run["id"])
        assert final_run["status"] == "completed"
        assert final_run["outputs"]["frames"] == ["frame1.png", "frame2.png"]

    def test_query_workflow(self, test_service, sample_video_files):
        """Test querying prompts and runs through the service layer."""
        # Create multiple prompts
        prompt1 = test_service.create_prompt(
            model_type="transfer",
            prompt_text="First prompt",
            inputs=sample_video_files,
            parameters={},
        )

        prompt2 = test_service.create_prompt(
            model_type="reason",
            prompt_text="Second prompt",
            inputs=sample_video_files,
            parameters={},
        )

        # Create multiple runs for first prompt
        run1 = test_service.create_run(prompt_id=prompt1["id"], execution_config={"seed": 1})
        test_service.update_run_status(run1["id"], "completed")

        run2 = test_service.create_run(prompt_id=prompt1["id"], execution_config={"seed": 2})
        test_service.update_run_status(run2["id"], "failed")

        test_service.create_run(prompt_id=prompt2["id"], execution_config={"seed": 3})

        # Query all prompts
        all_prompts = test_service.list_prompts()
        assert len(all_prompts) == 2

        # Query runs for first prompt
        prompt1_runs = test_service.list_runs(prompt_id=prompt1["id"])
        assert len(prompt1_runs) == 2

        # Query by status
        completed_runs = test_service.list_runs(status="completed")
        assert len(completed_runs) == 1
        assert completed_runs[0]["id"] == run1["id"]

        failed_runs = test_service.list_runs(status="failed")
        assert len(failed_runs) == 1
        assert failed_runs[0]["id"] == run2["id"]

    def test_enhancement_workflow(self, test_service):
        """Test the prompt enhancement workflow."""
        # Create base prompt
        prompt = test_service.create_prompt(
            model_type="enhancement",
            prompt_text="A simple scene",
            inputs={"base_prompt": "A simple scene"},
            parameters={},
        )

        # Create enhancement run
        enhancement_run = test_service.create_run(
            prompt_id=prompt["id"],
            execution_config={"operation": "enhance", "model": "pixtral", "temperature": 0.7},
            metadata={"type": "enhancement"},
        )

        # Simulate enhancement completion
        enhanced_text = "A breathtaking scene with dramatic lighting and intricate details"
        test_service.update_run(enhancement_run["id"], outputs={"enhanced_prompt": enhanced_text})
        test_service.update_run_status(enhancement_run["id"], "completed")

        # Create new prompt from enhanced text
        enhanced_prompt = test_service.create_prompt(
            model_type="enhancement",
            prompt_text=enhanced_text,
            inputs={"base_prompt": "A simple scene"},
            parameters={"parent_prompt_id": prompt["id"]},
        )

        # Verify enhancement chain
        assert enhanced_prompt["prompt_text"] == enhanced_text
        assert enhanced_prompt["parameters"]["parent_prompt_id"] == prompt["id"]

        # Query enhancement history
        enhancement_runs = test_service.list_runs(prompt_id=prompt["id"])
        # Filter client-side for test purposes
        enhancement_runs = [
            r for r in enhancement_runs if r.get("metadata", {}).get("type") == "enhancement"
        ]
        assert len(enhancement_runs) > 0

    def test_batch_operations(self, test_service, sample_video_files):
        """Test batch operations on prompts and runs."""
        # Create batch of prompts
        prompts = []
        for i in range(5):
            prompt = test_service.create_prompt(
                model_type="transfer",
                prompt_text=f"Batch prompt {i}",
                inputs=sample_video_files,
                parameters={"batch_id": "test_batch"},
            )
            prompts.append(prompt)

        # Create runs for each prompt
        runs = []
        for prompt in prompts[:3]:  # Only create runs for first 3
            run = test_service.create_run(
                prompt_id=prompt["id"], execution_config={"seed": prompt["id"]}
            )
            runs.append(run)

        # Query batch - we can't filter by parameters, so just check all prompts
        all_prompts = test_service.list_prompts()
        # Filter client-side for test purposes
        batch_prompts = [
            p for p in all_prompts if p.get("parameters", {}).get("batch_id") == "test_batch"
        ]
        assert len(batch_prompts) == 5

        # Update batch status
        for run in runs:
            test_service.update_run_status(run["id"], "completed")

        # Query completed runs
        completed = test_service.list_runs(status="completed")
        assert len(completed) == 3

    def test_error_recovery(self, test_service, sample_video_files):
        """Test error recovery and retry logic."""
        # Create prompt
        prompt = test_service.create_prompt(
            model_type="transfer",
            prompt_text="Error test prompt",
            inputs=sample_video_files,
            parameters={},
        )

        # Create failing run
        run = test_service.create_run(prompt_id=prompt["id"], execution_config={"will_fail": True})

        # Fail the run
        test_service.update_run(run["id"], outputs={"error": "GPU out of memory"})
        test_service.update_run_status(run["id"], "failed")

        # Verify failure recorded
        failed_run = test_service.get_run(run["id"])
        assert failed_run["status"] == "failed"
        assert "GPU out of memory" in failed_run["outputs"]["error"]

        # Create retry run
        retry_run = test_service.create_run(
            prompt_id=prompt["id"],
            execution_config={"retry_of": run["id"], "reduced_batch": True},
            metadata={"retry_attempt": 1},
        )

        # Complete retry successfully
        test_service.update_run_status(retry_run["id"], "completed")

        # Query run history
        all_runs = test_service.list_runs(prompt_id=prompt["id"])
        assert len(all_runs) == 2
        assert sum(1 for r in all_runs if r["status"] == "completed") == 1
        assert sum(1 for r in all_runs if r["status"] == "failed") == 1

    def test_concurrent_operations(self, test_service, sample_video_files):
        """Test multiple database operations in sequence."""
        # Create multiple prompts and runs sequentially
        # (SQLite in-memory doesn't work well with threading)
        results = []

        for index in range(10):
            prompt = test_service.create_prompt(
                model_type="transfer",
                prompt_text=f"Concurrent prompt {index}",
                inputs=sample_video_files,
                parameters={},
            )

            run = test_service.create_run(
                prompt_id=prompt["id"], execution_config={"thread_index": index}
            )

            test_service.update_run_status(run["id"], "completed")
            results.append((prompt["id"], run["id"]))

        # Verify all operations succeeded
        assert len(results) == 10
        all_prompts = test_service.list_prompts()
        assert len(all_prompts) == 10

        completed_runs = test_service.list_runs(status="completed")
        assert len(completed_runs) == 10
