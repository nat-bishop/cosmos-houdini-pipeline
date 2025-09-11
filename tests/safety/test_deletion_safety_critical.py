"""Critical safety tests for deletion operations.

WARNING: These tests protect against data loss.
Do not modify without careful consideration.
All tests here MUST pass before any deployment.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cosmos_workflow.api import CosmosAPI
from cosmos_workflow.database import DatabaseConnection
from cosmos_workflow.services.data_repository import DataRepository


@pytest.fixture
def temp_db():
    """Create an in-memory test database."""
    db = DatabaseConnection(":memory:")
    db.create_tables()
    return db


@pytest.fixture
def repository(temp_db):
    """Create a data repository with test database."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        mock_config = MagicMock()
        mock_config.get_local_config.return_value = MagicMock(outputs_dir=temp_path)
        repo = DataRepository(temp_db, mock_config)
        yield repo


@pytest.fixture
def api(repository):
    """Create API instance with mocked orchestrator."""
    with patch("cosmos_workflow.api.cosmos_api.DataRepository"):
        with patch("cosmos_workflow.api.cosmos_api.GPUExecutor"):
            api = CosmosAPI()
            api.service = repository

            # Mock successful enhancement
            api.orchestrator.execute_enhancement_run = lambda r, p: {
                "enhanced_text": "Enhanced: " + p.get("prompt_text", ""),
                "status": "completed",
            }
            yield api


class TestCriticalDeletionSafety:
    """CRITICAL: Core safety invariants that must never be violated."""

    def test_active_runs_warning_is_accurate(self, api, repository):
        """SAFETY: Verify active run detection is accurate.

        If this test fails, users might delete running GPU jobs.
        """
        prompt = repository.create_prompt(
            prompt_text="Test",
            inputs={},
            parameters={},
        )

        # Create runs with various states
        states = {
            "running": True,  # Active
            "pending": False,  # Not active
            "completed": False,  # Not active
            "failed": False,  # Not active
        }

        for status, _is_active in states.items():
            run = repository.create_run(
                prompt_id=prompt["id"],
                model_type="transfer",
                execution_config={"status": status},
            )
            repository.update_run_status(run["id"], status)

        # Try to overwrite
        with pytest.raises(ValueError) as exc:
            api.enhance_prompt(
                prompt_id=prompt["id"],
                create_new=False,
                force_overwrite=False,
            )

        # Must correctly identify 1 active run (only "running" is active)
        assert "1 ACTIVE" in str(exc.value)

    def test_preview_matches_actual_deletion(self, api, repository):
        """SAFETY: Preview must exactly match what gets deleted.

        If preview is wrong, users make incorrect decisions about data loss.
        """
        prompt = repository.create_prompt(
            prompt_text="Test",
            inputs={},
            parameters={},
        )

        # Create multiple runs
        run_ids = []
        for i in range(3):
            run = repository.create_run(
                prompt_id=prompt["id"],
                model_type="transfer",
                execution_config={"index": i},
            )
            run_ids.append(run["id"])

        # Get preview
        preview = api.preview_prompt_deletion(prompt["id"])
        preview_run_ids = {r["id"] for r in preview["runs"]}

        # Must match exactly
        assert preview_run_ids == set(run_ids)

        # Force delete
        api.enhance_prompt(
            prompt_id=prompt["id"],
            create_new=False,
            force_overwrite=True,
        )

        # Verify preview was accurate
        for run_id in run_ids:
            assert repository.get_run(run_id) is None

        # No other runs should be affected
        other_prompt = repository.create_prompt(
            prompt_text="Other",
            inputs={},
            parameters={},
        )
        other_run = repository.create_run(
            prompt_id=other_prompt["id"],
            model_type="transfer",
            execution_config={},
        )
        assert repository.get_run(other_run["id"]) is not None

    def test_enhancement_runs_dont_trigger_safety(self, api, repository):
        """SAFETY: Enhancement runs alone shouldn't block overwrite.

        Enhancement runs are metadata operations, not real GPU work.
        """
        prompt = repository.create_prompt(
            prompt_text="Test",
            inputs={},
            parameters={},
        )

        # Create only enhancement runs
        for _i in range(5):
            repository.create_run(
                prompt_id=prompt["id"],
                model_type="enhance",
                execution_config={},
            )

        # Should NOT require force_overwrite
        result = api.enhance_prompt(
            prompt_id=prompt["id"],
            create_new=False,
            force_overwrite=False,  # Should work without force
        )

        assert result["status"] == "success"

    def test_error_message_actionable(self, api, repository):
        """SAFETY: Error messages must tell user exactly what to do.

        Unclear errors lead to data loss from confused users.
        """
        prompt = repository.create_prompt(
            prompt_text="Test",
            inputs={},
            parameters={},
        )

        repository.create_run(
            prompt_id=prompt["id"],
            model_type="transfer",
            execution_config={},
        )

        with pytest.raises(ValueError) as exc:
            api.enhance_prompt(
                prompt_id=prompt["id"],
                create_new=False,
                force_overwrite=False,
            )

        error = str(exc.value)
        # Must include:
        assert prompt["id"] in error  # Which prompt
        assert "preview_prompt_deletion" in error  # How to check
        assert "force_overwrite=True" in error  # How to proceed
        assert "1 run(s)" in error  # What will be deleted

    def test_partial_failure_doesnt_corrupt_data(self, api, repository):
        """SAFETY: If deletion fails midway, data must remain consistent.

        Partial deletion could leave orphaned data.
        """
        prompt = repository.create_prompt(
            prompt_text="Test",
            inputs={},
            parameters={},
        )

        run1 = repository.create_run(
            prompt_id=prompt["id"],
            model_type="transfer",
            execution_config={},
        )

        run2 = repository.create_run(
            prompt_id=prompt["id"],
            model_type="transfer",
            execution_config={},
        )

        # Make second deletion fail
        original_delete = repository.delete_run
        calls = []

        def tracked_delete(run_id, keep_outputs=True):
            calls.append(run_id)
            if len(calls) == 2:
                raise RuntimeError("Database locked")
            return original_delete(run_id, keep_outputs)

        repository.delete_run = tracked_delete

        # Attempt force overwrite
        with pytest.raises(RuntimeError):
            api.enhance_prompt(
                prompt_id=prompt["id"],
                create_new=False,
                force_overwrite=True,
            )

        # Check state after failure
        # First run deleted (before error)
        assert repository.get_run(run1["id"]) is None
        # Second run NOT deleted (error occurred)
        assert repository.get_run(run2["id"]) is not None
        # Prompt NOT modified (transaction should rollback)
        assert repository.get_prompt(prompt["id"])["prompt_text"] == "Test"


class TestDeletionBoundaryConditions:
    """Test edge cases that might not be obvious but could cause issues."""

    def test_empty_prompt_doesnt_require_force(self, api, repository):
        """Empty prompts (no runs) shouldn't trigger safety checks."""
        prompt = repository.create_prompt(
            prompt_text="Test",
            inputs={},
            parameters={},
        )

        # No runs - should work without force
        result = api.enhance_prompt(
            prompt_id=prompt["id"],
            create_new=False,
            force_overwrite=False,
        )

        assert result["status"] == "success"

    def test_self_referential_enhancement(self, api, repository):
        """Test enhancing an already-enhanced prompt."""
        # Create and enhance a prompt
        prompt = repository.create_prompt(
            prompt_text="Original",
            inputs={},
            parameters={},
        )

        # First enhancement
        api.enhance_prompt(
            prompt_id=prompt["id"],
            create_new=False,
            force_overwrite=False,
        )

        # Try to enhance again - should work
        result2 = api.enhance_prompt(
            prompt_id=prompt["id"],
            create_new=False,
            force_overwrite=False,
        )

        assert result2["status"] == "success"

    def test_concurrent_force_overwrites(self, api, repository):
        """Test that concurrent force_overwrites don't corrupt data.

        This simulates race conditions in a multi-user environment.
        """
        prompt = repository.create_prompt(
            prompt_text="Test",
            inputs={},
            parameters={},
        )

        # Create initial runs
        runs = []
        for _i in range(3):
            run = repository.create_run(
                prompt_id=prompt["id"],
                model_type="transfer",
                execution_config={},
            )
            runs.append(run)

        # Simulate concurrent access by checking state mid-operation
        deletion_calls = []
        original_delete = repository.delete_run

        def intercept_delete(run_id, keep_outputs=True):
            deletion_calls.append(run_id)

            # After first deletion, another process creates a new run
            if len(deletion_calls) == 1:
                repository.create_run(
                    prompt_id=prompt["id"],
                    model_type="transfer",
                    execution_config={"concurrent": True},
                )

            return original_delete(run_id, keep_outputs)

        repository.delete_run = intercept_delete

        # Force overwrite
        api.enhance_prompt(
            prompt_id=prompt["id"],
            create_new=False,
            force_overwrite=True,
        )

        # Should have deleted original 3 runs (not the concurrent one)
        assert len(deletion_calls) == 3

        # The concurrent run should still exist
        remaining_runs = repository.list_runs(prompt_id=prompt["id"])
        assert len(remaining_runs) == 2  # Enhancement run + concurrent run
