"""
Shared pytest fixtures and configuration for all tests.
"""
import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest

from cosmos_workflow.config.config_manager import ConfigManager, LocalConfig, RemoteConfig
from cosmos_workflow.prompts.schemas import PromptSpec, RunSpec

# --- Configuration Fixtures ---


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_config_manager(temp_dir):
    """Create a mock ConfigManager with test configuration."""
    config_manager = Mock(spec=ConfigManager)

    # Mock remote config
    remote_config = RemoteConfig(
        host="test-host",
        port=22,
        user="test-user",
        ssh_key=str(temp_dir / "test_key.pem"),
        remote_dir="/remote/test",
        docker_image="nvcr.io/ubuntu/cosmos-transfer1:latest",
    )

    # Mock local config
    local_config = LocalConfig(
        prompts_dir=temp_dir / "prompts",
        runs_dir=temp_dir / "runs",
        outputs_dir=temp_dir / "outputs",
        videos_dir=temp_dir / "videos",
        notes_dir=temp_dir / "notes",
    )

    config_manager.get_remote_config.return_value = remote_config
    config_manager.get_local_config.return_value = local_config
    config_manager.config_path = temp_dir / "config.toml"

    return config_manager


@pytest.fixture
def mock_ssh_manager():
    """Create a mock SSHManager."""
    ssh_manager = MagicMock()
    ssh_manager.execute_command.return_value = (0, "Success", "")
    ssh_manager.is_connected.return_value = True
    return ssh_manager


@pytest.fixture
def mock_file_transfer():
    """Create a mock FileTransferManager."""
    file_transfer = MagicMock()
    file_transfer.upload_file.return_value = True
    file_transfer.upload_directory.return_value = True
    file_transfer.download_directory.return_value = True
    return file_transfer


# --- Schema Fixtures ---


@pytest.fixture
def sample_prompt_spec(temp_dir):
    """Create a sample PromptSpec for testing."""
    return PromptSpec(
        id="test_ps_123",
        name="test_scene",
        prompt="A futuristic city",
        negative_prompt="blurry, dark",
        input_video_path=str(temp_dir / "test_video.mp4"),
        control_inputs={
            "depth": str(temp_dir / "depth.mp4"),
            "segmentation": str(temp_dir / "segmentation.mp4"),
        },
        timestamp=datetime.now().isoformat(),
    )


@pytest.fixture
def sample_run_spec(sample_prompt_spec):
    """Create a sample RunSpec for testing."""
    return RunSpec(
        id="test_rs_456",
        prompt_spec_id=sample_prompt_spec.id,
        control_weights={"depth": 0.3, "segmentation": 0.4},
        parameters={"num_steps": 35, "guidance_scale": 8.0, "seed": 42},
        execution_status="pending",
        output_path="outputs/test_run",
        timestamp=datetime.now().isoformat(),
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
    executor = MagicMock()
    executor.run_inference.return_value = (0, "Inference complete", "")
    executor.run_upsampling.return_value = (0, "Upsampling complete", "")
    return executor


@pytest.fixture
def mock_ai_generator():
    """Create a mock AI description generator."""
    generator = MagicMock()
    generator.generate_description.return_value = "A modern architectural scene"
    generator.generate_name.return_value = "modern_architecture"
    return generator


# --- Test Data Factories ---


@pytest.fixture
def create_test_spec(temp_dir):
    """Factory for creating test spec files."""

    def _create_spec(spec_type="prompt", **kwargs):
        spec_dir = temp_dir / f"{spec_type}s"
        spec_dir.mkdir(exist_ok=True)

        if spec_type == "prompt":
            spec = PromptSpec(
                id=kwargs.get("id", "test_ps_001"),
                name=kwargs.get("name", "test"),
                prompt=kwargs.get("prompt", "Test prompt"),
                negative_prompt=kwargs.get("negative_prompt", ""),
                input_video_path=kwargs.get("input_video_path", "test.mp4"),
                control_inputs=kwargs.get("control_inputs", {}),
                timestamp=kwargs.get("timestamp", datetime.now().isoformat()),
            )
        else:  # run spec
            spec = RunSpec(
                id=kwargs.get("id", "test_rs_001"),
                prompt_spec_id=kwargs.get("prompt_spec_id", "test_ps_001"),
                control_weights=kwargs.get("control_weights", {}),
                parameters=kwargs.get("parameters", {}),
                execution_status=kwargs.get("execution_status", "pending"),
                output_path=kwargs.get("output_path", "outputs/test"),
                timestamp=kwargs.get("timestamp", datetime.now().isoformat()),
            )

        spec_file = spec_dir / f"{spec.id}.json"
        spec_file.write_text(json.dumps(spec.to_dict(), indent=2))
        return spec_file, spec

    return _create_spec


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
