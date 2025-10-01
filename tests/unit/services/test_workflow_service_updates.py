"""Tests for WorkflowService update methods.

These tests cover update_run_status and update_run methods.
Following TDD principles - testing behavior with real database, not mocks.
"""

import pytest

from cosmos_workflow.config.config_manager import ConfigManager
from cosmos_workflow.database import DatabaseConnection
from cosmos_workflow.services.data_repository import DataRepository


class TestWorkflowServiceUpdateRunStatus:
    """Test update_run_status method with real database."""

    @pytest.fixture
    def service(self):
        """Create a WorkflowService instance with in-memory database."""
        db_connection = DatabaseConnection(":memory:")
        db_connection.create_tables()
        config_manager = ConfigManager()
        return DataRepository(db_connection, config_manager)

    @pytest.fixture
    def sample_prompt(self, service):
        """Create a sample prompt for testing."""
        return service.create_prompt(
            prompt_text="test prompt",
            inputs={"video": "test.mp4"},
            parameters={"fps": 24},
        )

    @pytest.fixture
    def sample_run(self, service, sample_prompt):
        """Create a sample run for testing."""
        return service.create_run(
            prompt_id=sample_prompt["id"],
            model_type="transfer",
            execution_config={"weights": {"vis": 0.25}},
            metadata={"test": True},
        )

    def test_update_run_status_to_running(self, service, sample_run):
        """Test updating run status to running sets started_at."""
        # Initial status should be pending
        run = service.get_run(sample_run["id"])
        assert run["status"] == "pending"
        assert "started_at" not in run

        # Update to running
        updated = service.update_run_status(sample_run["id"], "running")

        assert updated is not None
        assert updated["status"] == "running"
        assert "started_at" in updated
        assert updated["started_at"] is not None

        # Verify persisted
        run = service.get_run(sample_run["id"])
        assert run["status"] == "running"
        assert "started_at" in run

    def test_update_run_status_to_completed(self, service, sample_run):
        """Test updating run status to completed sets completed_at."""
        # First set to running
        service.update_run_status(sample_run["id"], "running")

        # Then complete
        updated = service.update_run_status(sample_run["id"], "completed")

        assert updated is not None
        assert updated["status"] == "completed"
        assert "completed_at" in updated
        assert updated["completed_at"] is not None

        # Verify persisted
        run = service.get_run(sample_run["id"])
        assert run["status"] == "completed"
        assert "completed_at" in run

    def test_update_run_status_to_failed(self, service, sample_run):
        """Test updating run status to failed sets completed_at."""
        # First set to running
        service.update_run_status(sample_run["id"], "running")

        # Then fail
        updated = service.update_run_status(sample_run["id"], "failed")

        assert updated is not None
        assert updated["status"] == "failed"
        assert "completed_at" in updated
        assert updated["completed_at"] is not None

    def test_update_run_status_invalid_status(self, service, sample_run):
        """Test that invalid status raises ValueError."""
        with pytest.raises(ValueError, match="Invalid status"):
            service.update_run_status(sample_run["id"], "invalid_status")

    def test_update_run_status_none_run_id(self, service):
        """Test that None run_id raises ValueError."""
        with pytest.raises(ValueError, match="run_id is required"):
            service.update_run_status(None, "running")

    def test_update_run_status_empty_run_id(self, service):
        """Test that empty run_id raises ValueError."""
        with pytest.raises(ValueError, match="run_id cannot be empty"):
            service.update_run_status("", "running")

    def test_update_run_status_run_not_found(self, service):
        """Test that non-existent run returns None."""
        result = service.update_run_status("rs_nonexistent", "running")
        assert result is None

    def test_update_run_status_preserves_timestamps(self, service, sample_run):
        """Test that status updates preserve existing timestamps."""
        # Set to running (sets started_at)
        service.update_run_status(sample_run["id"], "running")
        run1 = service.get_run(sample_run["id"])
        started_at_1 = run1["started_at"]

        # Update status again - started_at should not change
        service.update_run_status(sample_run["id"], "running")
        run2 = service.get_run(sample_run["id"])
        assert run2["started_at"] == started_at_1


class TestWorkflowServiceUpdateRun:
    """Test update_run method with real database."""

    @pytest.fixture
    def service(self):
        """Create a WorkflowService instance with in-memory database."""
        db_connection = DatabaseConnection(":memory:")
        db_connection.create_tables()
        config_manager = ConfigManager()
        return DataRepository(db_connection, config_manager)

    @pytest.fixture
    def sample_prompt(self, service):
        """Create a sample prompt for testing."""
        return service.create_prompt(
            prompt_text="test prompt",
            inputs={"video": "test.mp4"},
            parameters={"fps": 24},
        )

    @pytest.fixture
    def sample_run(self, service, sample_prompt):
        """Create a sample run for testing."""
        return service.create_run(
            prompt_id=sample_prompt["id"],
            model_type="transfer",
            execution_config={"weights": {"vis": 0.25}},
            metadata={},
        )

    def test_update_run_outputs(self, service, sample_run):
        """Test updating run outputs."""
        # Initially outputs should be empty
        run = service.get_run(sample_run["id"])
        assert run["outputs"] == {}

        # Update outputs
        new_outputs = {"video_path": "/outputs/result.mp4", "duration": 10.5}
        updated = service.update_run(sample_run["id"], outputs=new_outputs)

        assert updated is not None
        assert updated["outputs"] == new_outputs

        # Verify persisted
        run = service.get_run(sample_run["id"])
        assert run["outputs"] == new_outputs

    def test_update_run_metadata(self, service, sample_run):
        """Test updating run metadata."""
        # Update metadata
        new_metadata = {"user": "test_user", "priority": "high", "tags": ["test", "sample"]}
        updated = service.update_run(sample_run["id"], metadata=new_metadata)

        assert updated is not None
        assert updated["metadata"] == new_metadata

        # Verify persisted
        run = service.get_run(sample_run["id"])
        assert run["metadata"] == new_metadata

    def test_update_run_execution_config(self, service, sample_run):
        """Test updating run execution_config."""
        # Update execution config
        new_config = {"weights": {"vis": 0.3, "edge": 0.3}, "num_steps": 50}
        updated = service.update_run(sample_run["id"], execution_config=new_config)

        assert updated is not None
        assert updated["execution_config"] == new_config

        # Verify persisted
        run = service.get_run(sample_run["id"])
        assert run["execution_config"] == new_config

    def test_update_run_multiple_fields(self, service, sample_run):
        """Test updating multiple run fields at once."""
        # Update multiple fields
        result = service.update_run(
            sample_run["id"],
            outputs={"enhanced_prompt_id": "ps_enhanced_789"},
            metadata={"model": "pixtral", "version": "1.0"},
        )

        assert result is not None
        assert result["outputs"] == {"enhanced_prompt_id": "ps_enhanced_789"}
        assert result["metadata"] == {"model": "pixtral", "version": "1.0"}

        # Verify persisted
        run = service.get_run(sample_run["id"])
        assert run["outputs"] == {"enhanced_prompt_id": "ps_enhanced_789"}
        assert run["metadata"] == {"model": "pixtral", "version": "1.0"}

    def test_update_run_invalid_field(self, service, sample_run):
        """Test that invalid field raises ValueError."""
        with pytest.raises(ValueError, match="Invalid fields"):
            service.update_run(sample_run["id"], invalid_field="value")

    def test_update_run_none_run_id(self, service):
        """Test that None run_id raises ValueError."""
        with pytest.raises(ValueError, match="run_id is required"):
            service.update_run(None, outputs={})

    def test_update_run_empty_run_id(self, service):
        """Test that empty run_id raises ValueError."""
        with pytest.raises(ValueError, match="run_id cannot be empty"):
            service.update_run("", outputs={})

    def test_update_run_not_found(self, service):
        """Test that non-existent run returns None."""
        result = service.update_run("rs_nonexistent", outputs={})
        assert result is None


class TestWorkflowServiceEnhancementSupport:
    """Test that enhancement model type is supported."""

    @pytest.fixture
    def service(self):
        """Create a WorkflowService instance with in-memory database."""
        db_connection = DatabaseConnection(":memory:")
        db_connection.create_tables()
        config_manager = ConfigManager()
        return DataRepository(db_connection, config_manager)

    def test_create_prompt_with_enhancement_type(self, service):
        """Test creating a prompt with enhancement model type."""
        # Create an enhancement prompt
        result = service.create_prompt(
            prompt_text="enhance this prompt",
            inputs={"original_prompt_id": "ps_original_123"},
            parameters={"model": "pixtral", "temperature": 0.7},
        )

        # Verify it was created successfully
        assert result is not None
        assert result["prompt_text"] == "enhance this prompt"
        assert result["inputs"]["original_prompt_id"] == "ps_original_123"
        assert result["parameters"]["model"] == "pixtral"
        assert "id" in result
        assert result["id"].startswith("ps_")

        # Verify we can retrieve it
        prompt = service.get_prompt(result["id"])
        assert prompt is not None

    def test_create_run_with_enhancement_type(self, service):
        """Test creating a run with enhancement model type."""
        # First create an enhancement prompt
        prompt = service.create_prompt(
            prompt_text="enhance this",
            inputs={"original_prompt_id": "ps_test"},
            parameters={"model": "pixtral"},
        )

        # Create a run for the enhancement prompt
        result = service.create_run(
            prompt_id=prompt["id"],
            model_type="enhance",
            execution_config={"model": "pixtral", "type": "enhance"},
            metadata={"source": "test"},
        )

        # Verify the run was created with correct model type
        assert result is not None
        assert result["execution_config"]["type"] == "enhance"
        assert "id" in result
        assert result["id"].startswith("rs_")

        # Verify we can retrieve it
        run = service.get_run(result["id"])
        assert run is not None

    def test_enhancement_run_workflow(self, service):
        """Test complete enhancement workflow with status updates."""
        # Create enhancement prompt
        prompt = service.create_prompt(
            prompt_text="enhance",
            inputs={"original_prompt_id": "ps_orig"},
            parameters={"model": "pixtral"},
        )

        # Create enhancement run
        run = service.create_run(
            prompt_id=prompt["id"],
            model_type="enhance",
            execution_config={"model": "pixtral"},
        )

        # Update status to running
        service.update_run_status(run["id"], "running")

        # Update with enhanced prompt output
        service.update_run(
            run["id"],
            outputs={
                "enhanced_prompt_id": "ps_enhanced_new",
                "enhanced_text": "Much better prompt",
            },
        )

        # Complete the run
        service.update_run_status(run["id"], "completed")

        # Verify final state
        final_run = service.get_run(run["id"])
        assert final_run["status"] == "completed"
        assert final_run["outputs"]["enhanced_prompt_id"] == "ps_enhanced_new"
        assert final_run["outputs"]["enhanced_text"] == "Much better prompt"
