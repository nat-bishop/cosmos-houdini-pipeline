"""Integration tests for prompt enhancement database runs."""

import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

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
        import gc
        import time

        # Create temporary directory
        tmpdir = tempfile.mkdtemp()
        db_path = Path(tmpdir) / "test.db"

        try:
            db = DatabaseConnection(str(db_path))
            db.create_tables()
            yield db
        finally:
            # Aggressive cleanup for Windows file locking
            try:
                # Close all sessions
                db.close_all_sessions()
                # Dispose of the engine to release all connections
                if hasattr(db, "engine"):
                    db.engine.dispose()
                # Force delete the db object
                del db
                # Force garbage collection
                gc.collect()
                # Wait for file handles to release
                time.sleep(0.2)
            except Exception:
                pass

            # Remove the temp directory
            import shutil

            for attempt in range(3):
                try:
                    shutil.rmtree(tmpdir, ignore_errors=False)
                    break
                except (PermissionError, OSError):
                    if attempt < 2:
                        time.sleep(0.5)
                    else:
                        # Last attempt - ignore errors
                        shutil.rmtree(tmpdir, ignore_errors=True)

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
        # Create a mock API instance without calling __init__

        # Use object.__new__ to create instance without calling __init__
        api = object.__new__(CosmosAPI)
        # Manually set the attributes that __init__ would set
        api.config = MagicMock()
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
        # With new structure, only enhanced flag is in prompt
        assert enhanced["parameters"]["enhanced"] is True
        # Details are in run outputs
        assert "parent_prompt_id" not in enhanced["parameters"]
        assert "enhancement_model" not in enhanced["parameters"]

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
        # Use create_new=True to create separate enhancement runs
        result1 = api.enhance_prompt(
            prompt_id=prompt["id"],
            create_new=True,  # Creates new prompt, not overwriting
            enhancement_model="pixtral",
        )

        result2 = api.enhance_prompt(
            prompt_id=prompt["id"],
            create_new=True,  # Creates another new prompt
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

    def test_overwrite_safety_check(self, api, repository):
        """Test that overwriting with existing runs requires force_overwrite."""
        # Create prompt
        prompt = repository.create_prompt(
            model_type="transfer",
            prompt_text="Original text",
            inputs={},
            parameters={},
        )

        # Create a run for this prompt
        run = repository.create_run(
            prompt_id=prompt["id"],
            model_type="transfer",
            execution_config={},
        )

        # Try to overwrite without force - should fail
        with pytest.raises(ValueError) as exc:
            api.enhance_prompt(
                prompt_id=prompt["id"],
                create_new=False,
                enhancement_model="pixtral",
                force_overwrite=False,  # Should fail
            )

        assert "Cannot overwrite prompt" in str(exc.value)
        assert "force_overwrite=True" in str(exc.value)
        assert "1 run(s)" in str(exc.value)

        # Now try with force_overwrite=True - should succeed
        result = api.enhance_prompt(
            prompt_id=prompt["id"],
            create_new=False,
            enhancement_model="pixtral",
            force_overwrite=True,  # Should work
        )

        assert result["status"] == "success"

        # Original run should be deleted
        deleted_run = repository.get_run(run["id"])
        assert deleted_run is None

    def test_create_new_preserves_original_prompt(self, api, repository):
        """Test that create_new=True leaves original prompt completely unchanged."""
        # Create original prompt with specific data
        original = repository.create_prompt(
            model_type="transfer",
            prompt_text="Original creative prompt",
            inputs={"video_path": "/path/to/video.mp4"},
            parameters={"name": "test_scene", "cfg_scale": 7.5},
        )
        original_id = original["id"]

        # Store original state for comparison
        original_text = original["prompt_text"]
        original_inputs = original["inputs"].copy()
        original_params = original["parameters"].copy()

        # Enhance with create_new=True
        result = api.enhance_prompt(
            prompt_id=original_id,
            create_new=True,  # Should create new prompt
            enhancement_model="pixtral",
        )

        assert result["status"] == "success"
        new_prompt_id = result["enhanced_prompt_id"]

        # Verify new prompt was created
        assert new_prompt_id != original_id

        # Verify original prompt is COMPLETELY unchanged
        original_check = repository.get_prompt(original_id)
        assert original_check["prompt_text"] == original_text
        assert original_check["inputs"] == original_inputs
        assert original_check["parameters"] == original_params
        assert "enhanced" not in original_check["parameters"]
        # With new structure, these should never be in original prompt
        assert "enhancement_model" not in original_check["parameters"]
        assert "parent_prompt_id" not in original_check["parameters"]
        assert "enhanced_at" not in original_check["parameters"]

        # Verify new prompt has minimal metadata (just enhanced flag)
        new_prompt = repository.get_prompt(new_prompt_id)
        assert new_prompt["prompt_text"] != original_text  # Enhanced text
        assert new_prompt["parameters"]["enhanced"] is True
        # With new structure, these details are in run outputs, not prompt
        assert "parent_prompt_id" not in new_prompt["parameters"]
        assert "enhancement_model" not in new_prompt["parameters"]
        assert "enhanced_at" not in new_prompt["parameters"]

        # Verify enhancement details are in run outputs
        run = repository.get_run(result["run_id"])
        assert run["outputs"]["original_prompt_id"] == original_id
        assert run["outputs"]["enhanced_prompt_id"] == new_prompt_id
        assert run["outputs"]["enhancement_model"] == "pixtral"
        assert "enhanced_at" in run["outputs"]

    def test_overwrite_updates_enhancement_metadata(self, api, repository):
        """Test that overwrite properly updates enhancement metadata."""
        # Create original prompt
        original = repository.create_prompt(
            model_type="transfer",
            prompt_text="Original text",
            inputs={"video_path": "/path/to/video.mp4"},
            parameters={"name": "test_scene"},
        )
        prompt_id = original["id"]

        # First enhancement
        result1 = api.enhance_prompt(
            prompt_id=prompt_id,
            create_new=False,
            enhancement_model="pixtral",
            force_overwrite=False,  # No runs yet
        )

        # Check first enhancement metadata (now in run outputs)
        updated1 = repository.get_prompt(prompt_id)
        assert updated1["parameters"]["enhanced"] is True
        # Enhancement details should be in run, not prompt
        run1 = repository.get_run(result1["run_id"])
        assert run1["outputs"]["enhancement_model"] == "pixtral"
        first_enhanced_at = run1["outputs"]["enhanced_at"]

        # Second enhancement (different model)
        result2 = api.enhance_prompt(
            prompt_id=prompt_id,
            create_new=False,
            enhancement_model="gpt-4",
            force_overwrite=True,  # Required now due to enhancement run
        )

        # Check second enhancement metadata (should be in new run)
        updated2 = repository.get_prompt(prompt_id)
        assert updated2["parameters"]["enhanced"] is True
        # Enhancement details should be in new run
        run2 = repository.get_run(result2["run_id"])
        assert run2["outputs"]["enhancement_model"] == "gpt-4"
        second_enhanced_at = run2["outputs"]["enhanced_at"]
        assert second_enhanced_at != first_enhanced_at  # Different timestamp
