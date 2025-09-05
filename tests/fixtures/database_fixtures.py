"""Database-based test fixtures that test behavior, not implementation.

These fixtures create real database objects using the service layer,
ensuring tests remain valid even when internal implementation changes.
"""

import pytest

from cosmos_workflow.config.config_manager import ConfigManager
from cosmos_workflow.database import DatabaseConnection
from cosmos_workflow.services import WorkflowService


@pytest.fixture
def test_db():
    """Create an in-memory test database."""
    db = DatabaseConnection(":memory:")
    db.create_tables()
    return db


@pytest.fixture
def test_service(test_db):
    """Create a test WorkflowService with in-memory database."""
    config = ConfigManager()
    return WorkflowService(test_db, config)


@pytest.fixture
def sample_prompt_data():
    """Sample prompt data for testing."""
    return {
        "model_type": "transfer",
        "prompt_text": "A futuristic city",
        "inputs": {"video": "/test/video.mp4", "depth": "/test/depth.mp4", "seg": "/test/seg.mp4"},
        "parameters": {"negative_prompt": "blurry, dark", "fps": 24},
    }


@pytest.fixture
def sample_run_data():
    """Sample run data for testing."""
    return {
        "execution_config": {
            "weights": {"vis": 0.25, "edge": 0.25, "depth": 0.25, "seg": 0.25},
            "num_steps": 35,
            "guidance": 8.0,
            "seed": 42,
        },
        "metadata": {"purpose": "test_run"},
    }


@pytest.fixture
def created_prompt(test_service, sample_prompt_data):
    """Create a prompt in the test database and return it."""
    return test_service.create_prompt(**sample_prompt_data)


@pytest.fixture
def created_run(test_service, created_prompt, sample_run_data):
    """Create a run in the test database and return it."""
    return test_service.create_run(prompt_id=created_prompt["id"], **sample_run_data)


@pytest.fixture
def created_prompt_with_runs(test_service, created_prompt, sample_run_data):
    """Create a prompt with multiple runs for testing queries."""
    # Create 3 runs with different statuses
    run1 = test_service.create_run(prompt_id=created_prompt["id"], **sample_run_data)
    test_service.update_run_status(run1["id"], "completed")

    run2 = test_service.create_run(prompt_id=created_prompt["id"], **sample_run_data)
    test_service.update_run_status(run2["id"], "running")

    run3 = test_service.create_run(prompt_id=created_prompt["id"], **sample_run_data)
    test_service.update_run_status(run3["id"], "failed")

    return created_prompt


# Legacy compatibility fixtures - these help transition old tests
# They return database objects that have similar structure to old stubs


@pytest.fixture
def sample_prompt_spec(created_prompt):
    """Compatibility fixture that returns a database prompt.

    Old tests expected:
    - .id, .name, .prompt, .negative_prompt, etc.

    New system returns dict from database.
    """
    # Return the database object which is a dict
    # Old tests will need updating to use dict access
    return created_prompt


@pytest.fixture
def sample_run_spec(created_run):
    """Compatibility fixture that returns a database run.

    Old tests expected:
    - .id, .prompt_id, .execution_status, etc.

    New system returns dict from database.
    """
    # Return the database object which is a dict
    return created_run


# NO COMPATIBILITY CLASSES!
# Tests should use the database directly, not fake objects.
# If a test needs PromptSpec or RunSpec, it's testing the OLD system
# and should be updated or deleted.
