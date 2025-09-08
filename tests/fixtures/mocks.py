"""Single source of truth for all test mocks.
No duplication, easy to maintain.
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock


def create_mock_ssh_manager():
    """Standard SSH mock for all tests.

    Returns a mock SSH manager with context manager support and
    common SSH operations stubbed out.
    """
    ssh = MagicMock()
    ssh.__enter__ = MagicMock(return_value=ssh)
    ssh.__exit__ = MagicMock(return_value=None)
    ssh.execute_command.return_value = (0, "Success", "")
    ssh.execute_command_success.return_value = (0, "Success", "")
    ssh.is_connected.return_value = True

    # Add SFTP client mock
    mock_sftp = MagicMock()
    mock_sftp.put = MagicMock()
    mock_sftp.get = MagicMock()
    mock_sftp.mkdir = MagicMock()
    mock_sftp.listdir = MagicMock(return_value=[])
    mock_sftp.listdir_attr = MagicMock(return_value=[])
    mock_sftp.stat = MagicMock(side_effect=FileNotFoundError())

    ssh.get_sftp.return_value.__enter__ = lambda self: mock_sftp
    ssh.get_sftp.return_value.__exit__ = lambda self, *args: None
    ssh._sftp_client = mock_sftp  # Store reference for tests

    return ssh


def create_mock_docker_executor():
    """Standard Docker mock for all tests.

    Returns a mock Docker executor with inference and upscaling
    operations stubbed out.
    """
    docker = MagicMock()
    # Updated to match new return format from DockerExecutor
    docker.run_inference.return_value = {
        "status": "started",
        "log_path": "/tmp/outputs/test/logs/run_test.log",
        "prompt_name": "test",
    }
    docker.run_upscaling.return_value = {
        "status": "started",
        "log_path": "/tmp/outputs/test_upscaled/logs/run_test.log",
        "prompt_name": "test",
    }
    docker.get_docker_status.return_value = {"status": "ready"}
    docker.check_gpu_availability.return_value = True
    docker.stream_logs = MagicMock()
    return docker


def create_mock_file_transfer():
    """Standard file transfer mock for all tests.

    Returns a mock file transfer service with upload/download
    operations stubbed out.
    """
    transfer = MagicMock()
    transfer.upload_file.return_value = True
    transfer.upload_directory.return_value = True
    transfer.download_file.return_value = True
    transfer.download_directory.return_value = True
    transfer.download_results.return_value = {"success": True, "output_path": "/outputs/result.mp4"}
    transfer.file_exists_remote.return_value = True
    return transfer


def create_mock_config_manager(temp_dir):
    """Standard config manager mock for all tests.

    Args:
        temp_dir: Temporary directory for test files

    Returns a mock config manager with standard test configuration.
    """
    from cosmos_workflow.config.config_manager import LocalConfig, RemoteConfig

    config_manager = Mock()

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


def create_mock_data_repository():
    """Standard data repository mock for tests.

    Returns a mock data repository with database operations
    stubbed out.
    """
    service = MagicMock()

    # Mock prompt operations
    service.create_prompt.return_value = {
        "id": "ps_test_123",
        "model_type": "transfer",
        "prompt_text": "Test prompt",
        "created_at": datetime.now().isoformat(),
    }
    service.get_prompt.return_value = service.create_prompt.return_value

    # Mock run operations
    service.create_run.return_value = {
        "id": "rs_test_456",
        "prompt_id": "ps_test_123",
        "status": "pending",
        "created_at": datetime.now().isoformat(),
    }
    service.get_run.return_value = service.create_run.return_value
    service.update_run_status.return_value = True
    service.update_run.return_value = True

    # Mock query operations
    service.list_prompts.return_value = [service.create_prompt.return_value]
    service.list_runs.return_value = [service.create_run.return_value]
    service.search_prompts.return_value = []
    service.get_prompt_with_runs.return_value = None

    return service


def create_mock_ai_generator():
    """Standard AI generator mock for tests.

    Returns a mock AI generator with description and name
    generation stubbed out.
    """
    generator = MagicMock()
    generator.generate_description.return_value = "A modern architectural scene"
    generator.generate_name.return_value = "modern_architecture"
    generator.enhance_prompt.return_value = (
        "An elaborate and detailed modern architectural scene with stunning visuals"
    )
    return generator


# Keep the old mock classes for backward compatibility during transition
# TODO: Remove these once all tests are migrated


class MockSSHManager:
    """DEPRECATED: Use create_mock_ssh_manager() instead."""

    def __init__(self, connected: bool = True):
        import warnings

        warnings.warn(
            "MockSSHManager is deprecated, use create_mock_ssh_manager() instead",
            DeprecationWarning,
            stacklevel=2,
        )
        self.connected = connected
        self.ssh_client = MagicMock()
        self.commands_executed = []
        self.files_transferred = []

    def is_connected(self) -> bool:
        return self.connected

    def connect(self) -> bool:
        self.connected = True
        return True

    def disconnect(self):
        self.connected = False

    def execute_command(self, command: str) -> tuple[int, str, str]:
        """Mock command execution."""
        self.commands_executed.append(command)

        # Simulate different command responses
        if "ls" in command:
            return (0, "file1.txt\nfile2.txt\ndir1/", "")
        elif "docker" in command:
            return (0, "Container started", "")
        elif "nvidia-smi" in command:
            return (0, "GPU 0: Tesla V100", "")
        elif "error" in command.lower():
            return (1, "", "Command failed")
        else:
            return (0, "Success", "")


class MockFileTransferManager:
    """DEPRECATED: Use create_mock_file_transfer() instead."""

    def __init__(self, success: bool = True):
        import warnings

        warnings.warn(
            "MockFileTransferManager is deprecated, use create_mock_file_transfer() instead",
            DeprecationWarning,
            stacklevel=2,
        )
        self.success = success
        self.files_uploaded = []
        self.files_downloaded = []

    def upload_file(self, local_path: str, remote_path: str) -> bool:
        """Mock file upload."""
        self.files_uploaded.append((local_path, remote_path))
        return self.success

    def download_file(self, remote_path: str, local_path: str) -> bool:
        """Mock file download."""
        self.files_downloaded.append((remote_path, local_path))
        return self.success

    def upload_directory(self, local_dir: Path, remote_dir: str) -> bool:
        """Mock directory upload."""
        self.files_uploaded.append((str(local_dir), remote_dir))
        return self.success

    def download_directory(self, remote_dir: str, local_dir: Path) -> bool:
        """Mock directory download."""
        self.files_downloaded.append((remote_dir, str(local_dir)))
        return self.success
