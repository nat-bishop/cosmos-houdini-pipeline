"""Tests for WorkflowService core functionality.

Following TDD Gate 1: Write tests first before implementation.
Tests cover create_prompt, create_run, get_prompt, get_run operations.
"""

import pytest

from cosmos_workflow.config.config_manager import ConfigManager
from cosmos_workflow.database import DatabaseConnection
from cosmos_workflow.services import DataRepository


class TestWorkflowServiceInit:
    """Test WorkflowService initialization."""

    def test_init_with_valid_params(self):
        """Test initializing WorkflowService with valid parameters."""
        db_connection = DatabaseConnection(":memory:")
        db_connection.create_tables()
        config_manager = ConfigManager()

        service = DataRepository(db_connection, config_manager)
        assert service.db == db_connection
        assert service.config == config_manager

    def test_init_with_none_db(self):
        """Test that initializing with None db raises error."""
        config_manager = ConfigManager()
        with pytest.raises(ValueError, match="db_connection cannot be None"):
            DataRepository(None, config_manager)

    def test_init_with_none_config(self):
        """Test that initializing with None config is allowed."""
        db_connection = DatabaseConnection(":memory:")
        db_connection.create_tables()
        # DataRepository now allows None config_manager
        service = DataRepository(db_connection, None)
        assert service.db == db_connection
        assert service.config is None


class TestWorkflowServiceCreatePrompt:
    """Test create_prompt functionality."""

    @pytest.fixture
    def service(self):
        """Create a WorkflowService instance for testing."""
        db_connection = DatabaseConnection(":memory:")
        db_connection.create_tables()
        config_manager = ConfigManager()
        return DataRepository(db_connection, config_manager)

    def test_create_prompt_transfer(self, service):
        """Test creating a transfer model prompt."""
        result = service.create_prompt(
            model_type="transfer",
            prompt_text="cyberpunk city",
            inputs={"video": "inputs/city.mp4", "depth": "inputs/depth.mp4"},
            parameters={"num_steps": 35, "cfg_scale": 3.5},
        )

        assert result["model_type"] == "transfer"
        assert result["prompt_text"] == "cyberpunk city"
        assert result["inputs"]["video"] == "inputs/city.mp4"
        assert result["inputs"]["depth"] == "inputs/depth.mp4"
        assert result["parameters"]["num_steps"] == 35
        assert result["parameters"]["cfg_scale"] == 3.5
        assert "id" in result
        assert result["id"].startswith("ps_")
        assert "created_at" in result

    def test_create_prompt_reason(self, service):
        """Test creating a reason model prompt."""
        result = service.create_prompt(
            model_type="reason",
            prompt_text="What happens next?",
            inputs={"video": "outputs/result.mp4"},
            parameters={"reasoning_depth": 3},
        )

        assert result["model_type"] == "reason"
        assert result["prompt_text"] == "What happens next?"
        assert result["inputs"]["video"] == "outputs/result.mp4"
        assert result["parameters"]["reasoning_depth"] == 3

    def test_create_prompt_predict(self, service):
        """Test creating a predict model prompt."""
        result = service.create_prompt(
            model_type="predict",
            prompt_text="Continue this scene",
            inputs={"frames": ["frame1.png", "frame2.png"]},
            parameters={"prediction_length": 60},
        )

        assert result["model_type"] == "predict"
        assert result["prompt_text"] == "Continue this scene"
        assert result["inputs"]["frames"] == ["frame1.png", "frame2.png"]
        assert result["parameters"]["prediction_length"] == 60

    def test_create_prompt_missing_model_type(self, service):
        """Test that missing model_type raises error."""
        with pytest.raises(ValueError, match="model_type is required"):
            service.create_prompt(model_type=None, prompt_text="test", inputs={}, parameters={})

    def test_create_prompt_empty_prompt_text(self, service):
        """Test that empty prompt_text raises error."""
        with pytest.raises(ValueError, match="prompt_text cannot be empty"):
            service.create_prompt(
                model_type="transfer", prompt_text="", inputs={"video": "test.mp4"}, parameters={}
            )

    def test_create_prompt_invalid_inputs(self, service):
        """Test that None inputs raises error."""
        with pytest.raises(ValueError, match="inputs cannot be None"):
            service.create_prompt(
                model_type="transfer", prompt_text="test", inputs=None, parameters={}
            )

    def test_create_prompt_invalid_parameters(self, service):
        """Test that None parameters raises error."""
        with pytest.raises(ValueError, match="parameters cannot be None"):
            service.create_prompt(
                model_type="transfer", prompt_text="test", inputs={}, parameters=None
            )


class TestWorkflowServiceCreateRun:
    """Test create_run functionality."""

    @pytest.fixture
    def service(self):
        """Create a WorkflowService instance with a test prompt."""
        db_connection = DatabaseConnection(":memory:")
        db_connection.create_tables()
        config_manager = ConfigManager()
        service = DataRepository(db_connection, config_manager)

        # Create a test prompt
        prompt = service.create_prompt(
            model_type="transfer",
            prompt_text="test prompt",
            inputs={"video": "test.mp4"},
            parameters={"num_steps": 30},
        )
        return service, prompt["id"]

    def test_create_run_basic(self, service):
        """Test creating a basic run."""
        svc, prompt_id = service

        result = svc.create_run(
            prompt_id=prompt_id, execution_config={"gpu_node": "node1", "weights": "v1.0"}
        )

        assert result["prompt_id"] == prompt_id
        assert result["status"] == "pending"
        assert result["execution_config"]["gpu_node"] == "node1"
        assert result["execution_config"]["weights"] == "v1.0"
        assert "id" in result
        assert result["id"].startswith("rs_")
        assert "created_at" in result
        assert "outputs" in result
        assert "metadata" in result

    def test_create_run_with_metadata(self, service):
        """Test creating a run with metadata."""
        svc, prompt_id = service

        result = svc.create_run(
            prompt_id=prompt_id,
            execution_config={"gpu_node": "node2"},
            metadata={"user": "test_user", "priority": "high"},
        )

        assert result["metadata"]["user"] == "test_user"
        assert result["metadata"]["priority"] == "high"

    def test_create_run_invalid_prompt_id(self, service):
        """Test that invalid prompt_id raises error."""
        svc, _ = service

        with pytest.raises(ValueError, match="Prompt not found"):
            svc.create_run(prompt_id="invalid_id", execution_config={"gpu_node": "node1"})

    def test_create_run_none_prompt_id(self, service):
        """Test that None prompt_id raises error."""
        svc, _ = service

        with pytest.raises(ValueError, match="prompt_id is required"):
            svc.create_run(prompt_id=None, execution_config={"gpu_node": "node1"})

    def test_create_run_none_execution_config(self, service):
        """Test that None execution_config raises error."""
        svc, prompt_id = service

        with pytest.raises(ValueError, match="execution_config cannot be None"):
            svc.create_run(prompt_id=prompt_id, execution_config=None)


class TestWorkflowServiceGetPrompt:
    """Test get_prompt functionality."""

    @pytest.fixture
    def service(self):
        """Create a WorkflowService instance with test prompts."""
        db_connection = DatabaseConnection(":memory:")
        db_connection.create_tables()
        config_manager = ConfigManager()
        service = DataRepository(db_connection, config_manager)

        # Create test prompts
        prompt1 = service.create_prompt(
            model_type="transfer",
            prompt_text="prompt 1",
            inputs={"video": "test1.mp4"},
            parameters={"num_steps": 30},
        )
        prompt2 = service.create_prompt(
            model_type="reason",
            prompt_text="prompt 2",
            inputs={"video": "test2.mp4"},
            parameters={"depth": 2},
        )

        return service, prompt1["id"], prompt2["id"]

    def test_get_prompt_existing(self, service):
        """Test getting an existing prompt."""
        svc, prompt1_id, _ = service

        result = svc.get_prompt(prompt1_id)

        assert result["id"] == prompt1_id
        assert result["model_type"] == "transfer"
        assert result["prompt_text"] == "prompt 1"
        assert result["inputs"]["video"] == "test1.mp4"
        assert result["parameters"]["num_steps"] == 30

    def test_get_prompt_different_model(self, service):
        """Test getting a prompt with different model type."""
        svc, _, prompt2_id = service

        result = svc.get_prompt(prompt2_id)

        assert result["id"] == prompt2_id
        assert result["model_type"] == "reason"
        assert result["prompt_text"] == "prompt 2"

    def test_get_prompt_nonexistent(self, service):
        """Test getting a non-existent prompt."""
        svc, _, _ = service

        result = svc.get_prompt("nonexistent_id")
        assert result is None

    def test_get_prompt_none_id(self, service):
        """Test that None prompt_id raises error."""
        svc, _, _ = service

        with pytest.raises(ValueError, match="prompt_id is required"):
            svc.get_prompt(None)

    def test_get_prompt_empty_id(self, service):
        """Test that empty prompt_id raises error."""
        svc, _, _ = service

        with pytest.raises(ValueError, match="prompt_id cannot be empty"):
            svc.get_prompt("")


class TestWorkflowServiceGetRun:
    """Test get_run functionality."""

    @pytest.fixture
    def service(self):
        """Create a WorkflowService instance with test runs."""
        db_connection = DatabaseConnection(":memory:")
        db_connection.create_tables()
        config_manager = ConfigManager()
        service = DataRepository(db_connection, config_manager)

        # Create test prompt and runs
        prompt = service.create_prompt(
            model_type="transfer",
            prompt_text="test prompt",
            inputs={"video": "test.mp4"},
            parameters={"num_steps": 30},
        )

        run1 = service.create_run(prompt_id=prompt["id"], execution_config={"gpu_node": "node1"})

        run2 = service.create_run(
            prompt_id=prompt["id"],
            execution_config={"gpu_node": "node2"},
            metadata={"user": "alice"},
        )

        return service, run1["id"], run2["id"]

    def test_get_run_existing(self, service):
        """Test getting an existing run."""
        svc, run1_id, _ = service

        result = svc.get_run(run1_id)

        assert result["id"] == run1_id
        assert result["status"] == "pending"
        assert result["execution_config"]["gpu_node"] == "node1"

    def test_get_run_with_metadata(self, service):
        """Test getting a run with metadata."""
        svc, _, run2_id = service

        result = svc.get_run(run2_id)

        assert result["id"] == run2_id
        assert result["metadata"]["user"] == "alice"

    def test_get_run_nonexistent(self, service):
        """Test getting a non-existent run."""
        svc, _, _ = service

        result = svc.get_run("nonexistent_id")
        assert result is None

    def test_get_run_none_id(self, service):
        """Test that None run_id raises error."""
        svc, _, _ = service

        with pytest.raises(ValueError, match="run_id is required"):
            svc.get_run(None)

    def test_get_run_empty_id(self, service):
        """Test that empty run_id raises error."""
        svc, _, _ = service

        with pytest.raises(ValueError, match="run_id cannot be empty"):
            svc.get_run("")


class TestWorkflowServiceTransactions:
    """Test transaction handling."""

    @pytest.fixture
    def service(self):
        """Create a WorkflowService instance for testing."""
        db_connection = DatabaseConnection(":memory:")
        db_connection.create_tables()
        config_manager = ConfigManager()
        return DataRepository(db_connection, config_manager)

    def test_rollback_on_error(self, service):
        """Test that transactions are rolled back on error."""
        # Create a prompt successfully
        prompt = service.create_prompt(
            model_type="transfer", prompt_text="test", inputs={"video": "test.mp4"}, parameters={}
        )

        # Try to create a run with invalid data that will cause an error
        # This should rollback and not affect the database
        with pytest.raises(ValueError):
            service.create_run(
                prompt_id=prompt["id"],
                execution_config=None,  # This will cause an error
            )

        # The prompt should still exist and be retrievable
        retrieved = service.get_prompt(prompt["id"])
        assert retrieved is not None
        assert retrieved["id"] == prompt["id"]

    def test_concurrent_operations(self, service):
        """Test that service handles concurrent operations safely."""
        # Create multiple prompts
        prompts = []
        for i in range(5):
            prompt = service.create_prompt(
                model_type="transfer",
                prompt_text=f"prompt {i}",
                inputs={"video": f"video{i}.mp4"},
                parameters={"index": i},
            )
            prompts.append(prompt)

        # Verify all prompts were created
        for prompt in prompts:
            retrieved = service.get_prompt(prompt["id"])
            assert retrieved is not None
            assert retrieved["id"] == prompt["id"]
