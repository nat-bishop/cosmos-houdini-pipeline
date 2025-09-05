"""
Shared pytest fixtures and configuration for all tests.
"""

import tempfile
from pathlib import Path

import pytest

# Import only database fixtures - NO compatibility classes
from tests.fixtures.database_fixtures import test_service  # noqa: F401
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
