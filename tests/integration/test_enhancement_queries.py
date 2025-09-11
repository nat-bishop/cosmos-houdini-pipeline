"""Integration tests for enhancement query helper functions."""

import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from cosmos_workflow.api import CosmosAPI
from cosmos_workflow.config.config_manager import ConfigManager
from cosmos_workflow.database import DatabaseConnection
from cosmos_workflow.services import DataRepository


class TestEnhancementQueries:
    """Test the new enhancement query helper functions."""

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

    def test_get_enhancement_details(self, api, repository):
        """Test getting enhancement details for a prompt."""
        # Create and enhance a prompt
        prompt = repository.create_prompt(
            prompt_text="Original text",
            inputs={"video": "/test.mp4"},
            parameters={"name": "test"},
        )

        api.enhance_prompt(
            prompt_id=prompt["id"],
            create_new=False,
            enhancement_model="pixtral",
        )

        # Get enhancement details
        details = repository.get_enhancement_details(prompt["id"])

        assert details is not None
        assert details["enhanced_text"] == f"Enhanced: {prompt['prompt_text']}"
        assert details["enhancement_model"] == "pixtral"
        assert details["original_prompt_id"] == prompt["id"]
        assert details["enhanced_prompt_id"] == prompt["id"]  # Same since overwrite
        assert "enhanced_at" in details
        assert details["duration_seconds"] == 15.5

    def test_get_enhancement_details_returns_none_for_unenhanced(self, repository):
        """Test that get_enhancement_details returns None for unenhanced prompts."""
        prompt = repository.create_prompt(
            prompt_text="Unenhanced text",
            inputs={},
            parameters={},
        )

        details = repository.get_enhancement_details(prompt["id"])
        assert details is None

    def test_get_original_prompt(self, api, repository):
        """Test getting the original prompt from an enhanced one."""
        # Create original
        original = repository.create_prompt(
            prompt_text="Original",
            inputs={"video": "/test.mp4"},
            parameters={"name": "original"},
        )

        # Enhance with create_new
        result = api.enhance_prompt(
            prompt_id=original["id"],
            create_new=True,
            enhancement_model="pixtral",
        )

        # Get original from enhanced
        found_original = repository.get_original_prompt(result["enhanced_prompt_id"])

        assert found_original is not None
        assert found_original["id"] == original["id"]
        assert found_original["prompt_text"] == "Original"

    def test_get_original_prompt_returns_none_for_overwritten(self, api, repository):
        """Test that overwritten enhancements return None for original."""
        prompt = repository.create_prompt(
            prompt_text="Text",
            inputs={},
            parameters={},
        )

        # Enhance with overwrite
        api.enhance_prompt(
            prompt_id=prompt["id"],
            create_new=False,
            enhancement_model="pixtral",
        )

        # Should return None since it was overwritten (same ID)
        original = repository.get_original_prompt(prompt["id"])
        assert original is None

    def test_list_enhanced_prompts(self, api, repository):
        """Test listing all enhanced prompts."""
        # Create mix of enhanced and regular prompts
        regular1 = repository.create_prompt(
            prompt_text="Regular 1",
            inputs={},
            parameters={},
        )

        regular2 = repository.create_prompt(
            prompt_text="Regular 2",
            inputs={},
            parameters={},
        )

        # Enhance one prompt
        api.enhance_prompt(
            prompt_id=regular1["id"],
            create_new=False,
            enhancement_model="pixtral",
        )

        # Create new enhanced prompt
        api.enhance_prompt(
            prompt_id=regular2["id"],
            create_new=True,
            enhancement_model="gpt-4",
        )

        # List enhanced prompts
        enhanced_list = repository.list_enhanced_prompts()

        # Should have 2 enhanced prompts (overwritten + new)
        assert len(enhanced_list) == 2

        # All should have enhanced=True
        for prompt in enhanced_list:
            assert prompt["parameters"]["enhanced"] is True

        # Check IDs are present
        enhanced_ids = [p["id"] for p in enhanced_list]
        assert regular1["id"] in enhanced_ids  # Overwritten
        # regular2 should NOT be in list (it's the original, not enhanced)
        assert regular2["id"] not in enhanced_ids

    def test_get_enhancement_history(self, api, repository):
        """Test getting all enhancement runs for a prompt."""
        # Create prompt
        prompt = repository.create_prompt(
            prompt_text="Text to enhance",
            inputs={},
            parameters={},
        )

        # Multiple enhancements
        api.enhance_prompt(
            prompt_id=prompt["id"],
            create_new=True,
            enhancement_model="pixtral",
        )

        api.enhance_prompt(
            prompt_id=prompt["id"],
            create_new=True,
            enhancement_model="gpt-4",
        )

        # Get history for original prompt
        history = repository.get_enhancement_history(prompt["id"])

        # Should have 2 enhancement runs
        assert len(history) == 2

        # All should be enhancement runs
        for run in history:
            assert run["model_type"] == "enhance"
            assert run["status"] == "completed"

        # Check both models are present
        models = [r["execution_config"]["model"] for r in history]
        assert "pixtral" in models
        assert "gpt-4" in models

    def test_backward_compatibility_with_old_structure(self, repository):
        """Test that helper functions work with old metadata structure."""
        # Manually create a prompt with old-style enhancement metadata
        prompt = repository.create_prompt(
            prompt_text="Enhanced text from old system",
            inputs={},
            parameters={
                "enhanced": True,
                "enhancement_model": "legacy-model",
                "enhanced_at": "2024-01-01T12:00:00Z",
                "parent_prompt_id": "ps_old_parent",
            },
        )

        # get_enhancement_details should still work
        details = repository.get_enhancement_details(prompt["id"])
        assert details is not None
        assert details["enhancement_model"] == "legacy-model"
        assert details["enhanced_at"] == "2024-01-01T12:00:00Z"
        assert details["original_prompt_id"] == "ps_old_parent"

        # get_original_prompt should work with parent_prompt_id
        # (Would need actual parent prompt in DB for full test)

        # list_enhanced_prompts should include it
        enhanced_list = repository.list_enhanced_prompts()
        enhanced_ids = [p["id"] for p in enhanced_list]
        assert prompt["id"] in enhanced_ids

    def test_enhancement_lineage_tracking(self, api, repository):
        """Test tracking enhancement lineage through multiple generations."""
        # Create original
        original = repository.create_prompt(
            prompt_text="Generation 0",
            inputs={},
            parameters={"name": "gen0"},
        )

        # First enhancement (gen 1)
        result1 = api.enhance_prompt(
            prompt_id=original["id"],
            create_new=True,
            enhancement_model="pixtral",
        )
        gen1_id = result1["enhanced_prompt_id"]

        # Second enhancement from gen1 (gen 2)
        result2 = api.enhance_prompt(
            prompt_id=gen1_id,
            create_new=True,
            enhancement_model="gpt-4",
        )
        gen2_id = result2["enhanced_prompt_id"]

        # Trace lineage back
        # Gen2 should trace back to Gen1
        gen1_from_gen2 = repository.get_original_prompt(gen2_id)
        assert gen1_from_gen2["id"] == gen1_id

        # Gen1 should trace back to original
        gen0_from_gen1 = repository.get_original_prompt(gen1_id)
        assert gen0_from_gen1["id"] == original["id"]

        # Original has no parent
        no_parent = repository.get_original_prompt(original["id"])
        assert no_parent is None

    def test_queries_work_with_no_runs(self, repository):
        """Test that queries handle prompts with no runs gracefully."""
        prompt = repository.create_prompt(
            prompt_text="No runs",
            inputs={},
            parameters={},
        )

        # These should all return empty/None
        details = repository.get_enhancement_details(prompt["id"])
        assert details is None

        history = repository.get_enhancement_history(prompt["id"])
        assert history == []

        original = repository.get_original_prompt(prompt["id"])
        assert original is None

    def test_list_enhanced_prompts_respects_limit(self, api, repository):
        """Test that list_enhanced_prompts respects the limit parameter."""
        # Create multiple enhanced prompts
        for i in range(5):
            prompt = repository.create_prompt(
                    prompt_text=f"Prompt {i}",
                inputs={},
                parameters={},
            )
            api.enhance_prompt(
                prompt_id=prompt["id"],
                create_new=False,
                enhancement_model="pixtral",
            )

        # Test with limit
        limited_list = repository.list_enhanced_prompts(limit=3)
        assert len(limited_list) == 3

        # Test without limit (default 100)
        full_list = repository.list_enhanced_prompts()
        assert len(full_list) == 5
