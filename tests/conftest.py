"""
Shared pytest fixtures and configuration for all tests.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Import only database fixtures - NO compatibility classes
from tests.fixtures.database_fixtures import (  # noqa: F401
    created_prompt,
    created_run,
    sample_prompt_data,
    sample_run_data,
    test_db,
    test_service,
)
from tests.fixtures.mocks import (
    create_mock_ai_generator,
    create_mock_config_manager,
    create_mock_docker_executor,
    create_mock_file_transfer,
    create_mock_ssh_manager,
)

# --- Configuration Fixtures ---


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_config_manager(temp_dir):
    """Create a mock ConfigManager with test configuration."""
    return create_mock_config_manager(temp_dir)


@pytest.fixture
def mock_ssh_manager():
    """Create a mock SSHManager."""
    return create_mock_ssh_manager()


@pytest.fixture
def mock_file_transfer():
    """Create a mock FileTransferManager."""
    return create_mock_file_transfer()


# --- Schema Fixtures ---


@pytest.fixture
def sample_prompt(test_service, temp_dir):  # noqa: F811
    """Create a sample prompt in the database.

    Returns a dict with database fields.
    No compatibility hacks - tests should use the actual fields.
    """
    return test_service.create_prompt(
        model_type="transfer",
        prompt_text="A futuristic city",
        inputs={
            "video": str(temp_dir / "test_video.mp4"),
            "depth": str(temp_dir / "depth.mp4"),
            "seg": str(temp_dir / "segmentation.mp4"),
        },
        parameters={"negative_prompt": "blurry, dark", "fps": 24},
    )


@pytest.fixture
def sample_run(test_service, sample_prompt):  # noqa: F811
    """Create a sample run in the database.

    Returns a dict with database fields.
    No compatibility hacks - tests should use the actual fields.
    """
    return test_service.create_run(
        prompt_id=sample_prompt["id"],
        execution_config={
            "weights": {"vis": 0.25, "edge": 0.25, "depth": 0.3, "seg": 0.4},
            "num_steps": 35,
            "guidance": 8.0,
            "seed": 42,
        },
        metadata={"purpose": "test_run"},
    )


# --- File System Fixtures ---


@pytest.fixture
def sample_png_sequence(temp_dir):
    """Create a sample PNG sequence directory."""
    sequence_dir = temp_dir / "sequence"
    sequence_dir.mkdir()

    # Create color frames
    for i in range(1, 11):
        (sequence_dir / f"color.{i:04d}.png").touch()

    # Create depth frames
    for i in range(1, 11):
        (sequence_dir / f"depth.{i:04d}.png").touch()

    return sequence_dir


@pytest.fixture
def sample_video_files(temp_dir):
    """Create sample video files."""
    video_dir = temp_dir / "videos"
    video_dir.mkdir()

    (video_dir / "color.mp4").touch()
    (video_dir / "depth.mp4").touch()
    (video_dir / "segmentation.mp4").touch()

    return video_dir


# --- Mock External Services ---


@pytest.fixture
def mock_docker_executor():
    """Create a mock DockerExecutor."""
    return create_mock_docker_executor()


@pytest.fixture
def mock_ai_generator():
    """Create a mock AI description generator."""
    return create_mock_ai_generator()


# --- CLI Testing Fixtures ---


@pytest.fixture
def mock_cosmos_api_for_cli():
    """Create a mock CosmosAPI for CLI tests that doesn't touch the real database.

    This fixture ensures CLI tests don't create real database entries or output directories.
    """
    mock_api = Mock()

    # Mock the create_prompt method
    def mock_create_prompt(**kwargs):
        prompt_text = kwargs.get("prompt_text", "test")
        name = kwargs.get("name", None)
        if not name:
            # Auto-generate name from prompt text (mimic real behavior)
            name = prompt_text[:20].replace(" ", "_").lower()

        return {
            "id": f"ps_test_{hash(prompt_text) % 10000:04d}",
            "prompt_text": prompt_text,
            "parameters": {"name": name, "negative_prompt": kwargs.get("negative_prompt", "")},
            "inputs": {"video": str(kwargs.get("video_dir", ""))},
        }

    # Mock other common methods
    mock_api.create_prompt = Mock(side_effect=mock_create_prompt)
    mock_api.get_prompt = Mock(return_value={"id": "ps_test_0001", "prompt_text": "test"})
    mock_api.list_prompts = Mock(return_value=[])
    mock_api.list_runs = Mock(return_value=[])
    mock_api.create_run = Mock(return_value={"id": "rs_test_0001", "status": "pending"})
    mock_api.get_run = Mock(return_value={"id": "rs_test_0001", "status": "completed"})

    return mock_api


@pytest.fixture
def mock_cli_context(mock_cosmos_api_for_cli):
    """Automatically patch CosmosAPI for CLI tests.

    Use this fixture in CLI test files to ensure they use the mocked API.
    """
    with patch("cosmos_workflow.api.CosmosAPI") as mock_class:
        mock_class.return_value = mock_cosmos_api_for_cli
        yield mock_cosmos_api_for_cli


# --- Test Data Factories ---


# Removed create_test_spec factory - it was maintaining old compatibility
# Tests should create database objects directly using test_service


# --- Pytest Markers ---


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "system: mark test as a system test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "gpu: mark test as requiring GPU")
    config.addinivalue_line("markers", "ssh: mark test as requiring SSH")
    config.addinivalue_line("markers", "docker: mark test as requiring Docker")


# --- Test Session Configuration ---


def pytest_collection_modifyitems(config, items):
    """Automatically add markers based on test location."""
    for item in items:
        # Add markers based on test file location
        if "tests/unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "tests/integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "tests/system" in str(item.fspath):
            item.add_marker(pytest.mark.system)
