"""Fake implementations for testing without infrastructure."""

from pathlib import Path
from unittest.mock import Mock

# Mock implementations for external modules that may not be installed
try:
    import paramiko
except ImportError:
    # Mock paramiko for testing when it's not installed
    class SSHClient:
        """Mock SSHClient."""

        pass

    class SFTPClient:
        """Mock SFTPClient."""

        pass

    class paramiko:
        """Mock paramiko module."""

        SSHClient = SSHClient
        SFTPClient = SFTPClient
        Transport = Mock


# Try importing the real modules, fall back to mocks
try:
    from cosmos_workflow.config import ConfigManager
except ImportError:
    ConfigManager = Mock

try:
    from cosmos_workflow.connection import SSHManager
except ImportError:
    SSHManager = Mock

try:
    from cosmos_workflow.database import DatabaseConnection
except ImportError:
    DatabaseConnection = Mock

try:
    from cosmos_workflow.database.models import Prompt, Run
except ImportError:
    Prompt = Mock
    Run = Mock

try:
    from cosmos_workflow.services import DataRepository
except ImportError:
    DataRepository = Mock


class FakeSSHManager:
    """Fake SSH manager for testing without real SSH connections."""

    def __init__(self, host="fake-host", user="fake-user", ssh_key=None):
        self.host = host
        self.user = user
        self.ssh_key = ssh_key
        self.is_connected = False
        self.commands_executed: list[str] = []
        self.sftp_transfers: list[dict] = []

    def connect(self) -> None:
        """Simulate SSH connection."""
        self.is_connected = True

    def disconnect(self) -> None:
        """Simulate SSH disconnection."""
        self.is_connected = False

    def execute_command(self, command: str, timeout: int | None = None) -> tuple[str, str, int]:
        """Simulate command execution."""
        self.commands_executed.append(command)
        # Return fake output based on command
        if "nvidia-smi" in command:
            return ("GPU 0: NVIDIA A100", "", 0)
        elif "docker ps" in command:
            return ("CONTAINER ID   IMAGE   STATUS", "", 0)
        elif "ls" in command:
            return ("file1.txt\nfile2.txt", "", 0)
        return ("", "", 0)

    def execute_command_success(self, command: str, timeout: int | None = None) -> None:
        """Simulate successful command execution."""
        self.commands_executed.append(command)

    def get_sftp(self):
        """Get fake SFTP client context manager."""

        class FakeSFTPContext:
            def __enter__(self_sftp):
                return FakeSFTPClient(self)

            def __exit__(self_sftp, *args):
                pass

        return FakeSFTPContext()

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, *args):
        """Context manager exit."""
        self.disconnect()


class FakeSFTPClient:
    """Fake SFTP client for testing."""

    def __init__(self, ssh_manager):
        self.ssh_manager = ssh_manager
        self.files: dict[str, bytes] = {}
        self.directories: set[str] = set()

    def put(self, local_path, remote_path):
        """Simulate file upload."""
        self.ssh_manager.sftp_transfers.append(
            {"type": "upload", "local": str(local_path), "remote": remote_path}
        )
        self.files[remote_path] = b"fake content"

    def get(self, remote_path, local_path):
        """Simulate file download."""
        self.ssh_manager.sftp_transfers.append(
            {"type": "download", "remote": remote_path, "local": str(local_path)}
        )
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)
        Path(local_path).write_bytes(self.files.get(remote_path, b"fake content"))

    def mkdir(self, path):
        """Simulate directory creation."""
        self.directories.add(path)

    def stat(self, path):
        """Simulate file stat."""
        if path in self.files or path in self.directories:
            return Mock(st_size=1024)
        raise FileNotFoundError(f"File not found: {path}")


class FakeFileTransferService:
    """Fake file transfer service for testing."""

    def __init__(self, ssh_manager=None, remote_dir="/remote"):
        self.ssh_manager = ssh_manager or FakeSSHManager()
        self.remote_dir = remote_dir
        self.uploaded_files: list[dict] = []
        self.downloaded_files: list[dict] = []
        self.uploaded_directories: list[dict] = []

    def upload_file(self, local_path: Path, remote_dir: str) -> bool:
        """Simulate file upload."""
        if not isinstance(local_path, Path):
            local_path = Path(local_path)

        if not local_path.exists():
            raise FileNotFoundError(f"Local file not found: {local_path}")

        upload_info = {
            "local": str(local_path),
            "remote": f"{remote_dir}/{local_path.name}",
            "type": "file",
        }
        self.uploaded_files.append(upload_info)
        return True

    def upload_directory(self, local_dir: Path, remote_dir: str) -> bool:
        """Simulate directory upload."""
        if not isinstance(local_dir, Path):
            local_dir = Path(local_dir)

        if not local_dir.exists():
            raise FileNotFoundError(f"Local directory not found: {local_dir}")

        self.uploaded_directories.append(
            {"local": str(local_dir), "remote": remote_dir, "type": "directory"}
        )

        # Simulate uploading all files in directory
        for file_path in local_dir.rglob("*"):
            if file_path.is_file():
                relative_path = file_path.relative_to(local_dir)
                upload_info = {
                    "local": str(file_path),
                    "remote": f"{remote_dir}/{relative_path}",
                    "type": "file_in_dir",
                    "filename": file_path.name,
                }
                self.uploaded_files.append(upload_info)

    def download_file(self, remote_path: str, local_path: Path) -> None:
        """Download a file from remote."""
        if not isinstance(local_path, Path):
            local_path = Path(local_path)

        # Create parent directory
        local_path.parent.mkdir(parents=True, exist_ok=True)

        # Simulate download
        local_path.write_text("fake downloaded content")
        self.downloaded_files.append({"remote": remote_path, "local": str(local_path)})

    def download_results(self, prompt_file: Path) -> None:
        """Simulate downloading results."""
        if not isinstance(prompt_file, Path):
            prompt_file = Path(prompt_file)

        output_name = prompt_file.stem
        remote_output_dir = f"{self.remote_dir}/outputs/{output_name}"

        # Create fake local output directory
        local_output_dir = Path("outputs") / output_name
        local_output_dir.mkdir(parents=True, exist_ok=True)

        # Simulate downloading output files
        (local_output_dir / "output.mp4").write_text("fake video content")
        (local_output_dir / "log.txt").write_text("fake log content")

        self.downloaded_files.append(
            {"remote": remote_output_dir, "local": str(local_output_dir), "type": "results"}
        )


class FakeDockerExecutor:
    """Fake Docker executor for testing.

    Simulates Docker execution without requiring Docker to be installed.
    """

    def __init__(
        self,
        ssh_manager: FakeSSHManager = None,
        remote_dir: str = "/remote",
        docker_image: str = "test:latest",
    ):
        self.ssh_manager = ssh_manager or FakeSSHManager()
        self.remote_dir = remote_dir
        self.docker_image = docker_image
        self.containers_run: list[tuple[str, dict]] = []
        self.inference_results: dict[str, dict] = {}

        # Fake remote executor
        self.remote_executor = FakeRemoteExecutor(ssh_manager)

    def run_inference(
        self, prompt_file: Path, run_id: str, num_gpu: int = 1, cuda_devices: str = "0"
    ) -> dict:
        """Simulate running inference."""
        prompt_name = prompt_file.stem

        # Track execution
        self.containers_run.append(
            ("inference", {"prompt": prompt_name, "num_gpu": num_gpu, "cuda_devices": cuda_devices})
        )

        # Create output directory
        output_dir = f"{self.remote_dir}/outputs/{prompt_name}"
        self.ssh_manager.execute_command(f"mkdir -p {output_dir}")
        self.remote_executor.created_directories.append(output_dir)

        # Create log path
        log_path = f"outputs/{prompt_name}/logs/run_{run_id if run_id else 'test'}.log"

        # Store result
        self.inference_results[prompt_name] = {
            "status": "success",
            "output_path": f"{output_dir}/output.mp4",
            "log_path": log_path,
        }

        return self.inference_results[prompt_name]

    def run_checkpoint(self, run_spec_file: Path) -> dict:
        """Simulate running checkpoint."""
        spec_name = run_spec_file.stem

        # Track execution
        self.containers_run.append(("checkpoint", {"spec": spec_name}))

        # Create output directory
        output_dir = f"{self.remote_dir}/outputs/{spec_name}"
        self.ssh_manager.execute_command(f"mkdir -p {output_dir}")

        return {"status": "success", "output_path": f"{output_dir}/checkpoint.ckpt"}

    def run_enhancement(
        self, prompt_id: str, run_spec: dict, num_gpus: int = 1, cuda_devices: str = "0"
    ) -> dict:
        """Simulate running enhancement."""
        # Track execution
        self.containers_run.append(
            (
                "enhancement",
                {"prompt_id": prompt_id, "num_gpus": num_gpus, "cuda_devices": cuda_devices},
            )
        )

        # Create output directory
        output_dir = f"{self.remote_dir}/outputs/{prompt_id}_enhanced"
        self.ssh_manager.execute_command(f"mkdir -p {output_dir}")

        return {
            "status": "success",
            "output_path": f"{output_dir}/enhanced.mp4",
            "log_path": f"{output_dir}/log.txt",
        }

    def get_containers(self, all_containers: bool = False) -> list[dict]:
        """Get list of containers."""
        if all_containers:
            # Return some fake stopped containers too
            return [
                {"id": "abc123", "image": self.docker_image, "status": "running"},
                {"id": "def456", "image": self.docker_image, "status": "exited"},
            ]
        return [{"id": "abc123", "image": self.docker_image, "status": "running"}]

    def stop_container(self, container_id: str) -> bool:
        """Stop a container."""
        self.ssh_manager.execute_command(f"docker stop {container_id}")
        return True

    def stream_logs(self, container_id: str):
        """Stream container logs."""
        # Yield some fake log lines
        yield "Starting inference..."
        yield "Loading model..."
        yield "Processing..."
        yield "Complete!"


class FakeRemoteExecutor:
    """Fake remote command executor."""

    def __init__(self, ssh_manager):
        self.ssh_manager = ssh_manager
        self.created_directories: list[str] = []

    def create_remote_directory(self, directory: str) -> None:
        """Create remote directory."""
        self.ssh_manager.execute_command(f"mkdir -p {directory}")
        self.created_directories.append(directory)

    def check_file_exists(self, file_path: str) -> bool:
        """Check if remote file exists."""
        self.ssh_manager.execute_command(f"test -f {file_path}")
        # For testing, assume files in /remote exist
        return file_path.startswith("/remote")

    def get_file_size(self, file_path: str) -> int:
        """Get remote file size."""
        self.ssh_manager.execute_command(f"stat -c %s {file_path}")
        # Return fake size
        return 1024

    def remove_file(self, file_path: str) -> None:
        """Remove remote file."""
        self.ssh_manager.execute_command(f"rm -f {file_path}")

    def set_file_exists(self, remote_path: str) -> None:
        """Mark a file as existing (for testing)."""
        self.existing_files = getattr(self, "existing_files", set())
        self.existing_files.add(remote_path)
