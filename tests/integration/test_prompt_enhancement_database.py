"""Integration tests for prompt enhancement database runs."""

import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cosmos_workflow.api import CosmosAPI
from cosmos_workflow.config.config_manager import ConfigManager
from cosmos_workflow.database import DatabaseConnection
from cosmos_workflow.services import DataRepository


class TestPromptEnhancementDatabaseIntegration:
    """Integration tests for prompt enhancement with real database."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        db = DatabaseConnection(db_path)
        db.create_tables()
        yield db

        # Cleanup
        Path(db_path).unlink(missing_ok=True)

    @pytest.fixture
    def repository(self, temp_db):
        """Create repository with temp database."""
        config = ConfigManager()
        return DataRepository(temp_db, config)

    @pytest.fixture
    def mock_orchestrator(self):
        """Create mock orchestrator that simulates enhancement."""
        orchestrator = MagicMock()

        def mock_execute_enhancement(run, prompt, **kwargs):
            """Simulate enhancement execution."""
            return {
                "enhanced_text": f"Enhanced: {prompt['prompt_text']}",
                "original_prompt_id": prompt["id"],
                "duration_seconds": 15.5,
                "log_path": f"outputs/run_{run['id']}/logs/enhancement.log",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        orchestrator.execute_enhancement_run = MagicMock(side_effect=mock_execute_enhancement)
        return orchestrator

    @pytest.fixture
    def api(self, repository, mock_orchestrator):
        """Create API with real repository and mock orchestrator."""

        with patch("cosmos_workflow.api.cosmos_api.init_database"):
            with patch("cosmos_workflow.api.cosmos_api.DataRepository"):
                with patch("cosmos_workflow.api.cosmos_api.GPUExecutor"):
                    api = CosmosAPI()
                    api.service = repository
                    api.orchestrator = mock_orchestrator
                    return api

    def test_full_enhancement_workflow_with_database(self, api, repository):
        """Test complete enhancement workflow with database persistence."""
        # Create a prompt first
        prompt = repository.create_prompt(
            model_type="transfer",
            prompt_text="A beautiful sunset over mountains",
            inputs={"video": "/test/video.mp4"},
            parameters={"name": "sunset_scene"},
        )

        # Enhance the prompt
        result = api.enhance_prompt(
            prompt_id=prompt["id"],
            create_new=True,
            enhancement_model="pixtral",
        )

        # Verify run was created in database
        assert "run_id" in result
        run = repository.get_run(result["run_id"])
        assert run is not None
        assert run["model_type"] == "enhance"
        assert run["prompt_id"] == prompt["id"]
        assert run["status"] == "completed"

        # Verify execution config
        assert run["execution_config"]["model"] == "pixtral"
        assert run["execution_config"]["offload"] is True
        assert run["execution_config"]["batch_size"] == 1

        # Verify outputs stored
        assert "enhanced_text" in run["outputs"]
        assert run["outputs"]["original_prompt_id"] == prompt["id"]
        assert run["outputs"]["duration_seconds"] == 15.5

    def test_enhancement_run_appears_in_listings(self, api, repository):
        """Test that enhancement runs appear in run listings."""
        # Create prompt
        prompt = repository.create_prompt(
            model_type="transfer",
            prompt_text="Original text",
            inputs={},
            parameters={},
        )

        # Create enhancement run
        result = api.enhance_prompt(
            prompt_id=prompt["id"],
            create_new=False,
            enhancement_model="pixtral",
        )

        # List all runs
        all_runs = repository.list_runs()
        assert len(all_runs) == 1
        assert all_runs[0]["id"] == result["run_id"]
        assert all_runs[0]["model_type"] == "enhance"

        # List runs for prompt
        prompt_runs = repository.list_runs(prompt_id=prompt["id"])
        assert len(prompt_runs) == 1
        assert prompt_runs[0]["model_type"] == "enhance"

    def test_enhancement_creates_new_prompt_with_linkage(self, api, repository):
        """Test that create_new=True creates linked prompts."""
        # Create original prompt
        original = repository.create_prompt(
            model_type="transfer",
            prompt_text="Short description",
            inputs={"video": "/test.mp4"},
            parameters={"name": "original"},
        )

        # Enhance with new prompt creation
        result = api.enhance_prompt(
            prompt_id=original["id"],
            create_new=True,
            enhancement_model="pixtral",
        )

        # Verify new prompt was created
        assert "enhanced_prompt_id" in result
        enhanced = repository.get_prompt(result["enhanced_prompt_id"])
        assert enhanced is not None
        assert enhanced["prompt_text"] == result["enhanced_text"]
        assert enhanced["parameters"]["parent_prompt_id"] == original["id"]
        assert enhanced["parameters"]["enhanced"] is True
        assert enhanced["parameters"]["enhancement_model"] == "pixtral"

        # Verify run was created for enhancement
        assert "run_id" in result
        run = repository.get_run(result["run_id"])
        assert run["model_type"] == "enhance"

    def test_enhancement_run_with_video_context(self, api, repository):
        """Test that video context is properly stored."""
        # Create prompt with video
        prompt = repository.create_prompt(
            model_type="transfer",
            prompt_text="Scene description",
            inputs={"video": "/path/to/context/video.mp4"},
            parameters={},
        )

        # Enhance
        result = api.enhance_prompt(
            prompt_id=prompt["id"],
            create_new=False,
            enhancement_model="pixtral",
        )

        # Check run has video context in execution config
        run = repository.get_run(result["run_id"])
        assert run["execution_config"]["video_context"] == "/path/to/context/video.mp4"

    def test_failed_enhancement_updates_status(self, api, repository, mock_orchestrator):
        """Test that failed enhancement properly updates run status."""
        # Setup failure
        mock_orchestrator.execute_enhancement_run.side_effect = RuntimeError("GPU OOM")

        # Create prompt
        prompt = repository.create_prompt(
            model_type="transfer",
            prompt_text="Test prompt",
            inputs={},
            parameters={},
        )

        # Try enhancement
        result = api.enhance_prompt(
            prompt_id=prompt["id"],
            create_new=False,
            enhancement_model="pixtral",
        )

        # Verify failure recorded
        assert result["status"] == "failed"
        run = repository.get_run(result["run_id"])
        assert run["status"] == "failed"
        assert run["model_type"] == "enhance"

    def test_multiple_enhancement_runs_for_same_prompt(self, api, repository):
        """Test that multiple enhancement runs can exist for one prompt."""
        # Create prompt
        prompt = repository.create_prompt(
            model_type="transfer",
            prompt_text="Base text",
            inputs={},
            parameters={},
        )

        # Run enhancement multiple times with different models
        result1 = api.enhance_prompt(
            prompt_id=prompt["id"],
            create_new=False,
            enhancement_model="pixtral",
        )

        result2 = api.enhance_prompt(
            prompt_id=prompt["id"],
            create_new=False,
            enhancement_model="gpt-4",  # Different model
        )

        # Both runs should exist
        runs = repository.list_runs(prompt_id=prompt["id"])
        assert len(runs) == 2
        assert all(r["model_type"] == "enhance" for r in runs)

        # Different execution configs
        run1 = repository.get_run(result1["run_id"])
        run2 = repository.get_run(result2["run_id"])
        assert run1["execution_config"]["model"] == "pixtral"
        assert run2["execution_config"]["model"] == "gpt-4"

    def test_enhancement_run_id_format(self, api, repository):
        """Test that enhancement runs use standard run_id format."""
        # Create prompt
        prompt = repository.create_prompt(
            model_type="transfer",
            prompt_text="Text",
            inputs={},
            parameters={},
        )

        # Enhance
        result = api.enhance_prompt(
            prompt_id=prompt["id"],
            create_new=False,
            enhancement_model="pixtral",
        )

        # Verify run_id format (should start with rs_)
        assert result["run_id"].startswith("rs_")
        assert len(result["run_id"]) > 3  # Has actual ID after prefix
