"""Fake implementations for testing that maintain contracts without mocking internals.

These fakes replace mocks to enable behavior testing instead of implementation testing.
Following principles from the TEST_SUITE_INVESTIGATION_REPORT.md.
"""

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class FakeSFTPClient:
    """Fake SFTP client for testing file transfer operations."""

    def __init__(self, ssh_manager):
        self.ssh_manager = ssh_manager
        self.fake_files = {}  # Store fake remote files

    def stat(self, remote_path: str):
        """Fake stat - check if file exists."""
        # Always raise FileNotFoundError for testing download behavior
        # This simulates remote files not existing
        raise FileNotFoundError(f"Remote file not found: {remote_path}")

    def get(self, remote_path: str, local_path: str):
        """Fake download file."""
        self.ssh_manager.files_downloaded.append((remote_path, Path(local_path)))
        # Create a fake file locally for testing
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)
        Path(local_path).write_text("fake downloaded content")

    def put(self, local_path: str, remote_path: str):
        """Fake upload file."""
        self.ssh_manager.files_uploaded.append((Path(local_path), remote_path))
        self.fake_files[remote_path] = (
            Path(local_path).read_bytes() if Path(local_path).exists() else b""
        )

    def listdir(self, remote_path: str):
        """Fake list directory."""
        return [Path(p).name for p in self.fake_files.keys() if p.startswith(remote_path + "/")]

    def listdir_attr(self, remote_path: str):
        """Fake list directory with attributes."""

        @dataclass
        class FakeAttr:
            filename: str
            st_mode: int

        # Return empty list to simulate no files
        return []


class FakeSSHManager:
    """Fake SSH manager that maintains behavior without real connections.

    This fake tracks commands and provides predictable responses,
    allowing tests to verify behavior rather than method calls.
    """

    def __init__(self, connected: bool = False):
        self.connected = connected
        self.commands_executed: list[tuple[str, dict]] = []
        self.files_uploaded: list[tuple[Path, str]] = []
        self.files_downloaded: list[tuple[str, Path]] = []
        self.command_responses: dict[str, tuple[int, str, str]] = {}

    def connect(self) -> bool:
        """Simulate connection."""
        self.connected = True
        return True

    def disconnect(self) -> None:
        """Simulate disconnection."""
        self.connected = False

    def __enter__(self):
        """Enter context manager."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        self.disconnect()
        return False

    def is_connected(self) -> bool:
        """Check connection status."""
        return self.connected

    def ensure_connected(self) -> None:
        """Ensure SSH connection is active."""
        if not self.connected:
            self.connect()

    def get_sftp(self):
        """Get SFTP client (fake)."""
        from contextlib import contextmanager

        @contextmanager
        def fake_sftp_context():
            self.ensure_connected()
            yield FakeSFTPClient(self)

        return fake_sftp_context()

    def execute_command(self, command: str, timeout: int = 30) -> tuple[int, str, str]:
        """Execute command and return predictable output based on command type."""
        self.commands_executed.append((command, {"timeout": timeout}))

        # Return predictable responses based on command patterns
        if "docker run" in command:
            return (0, "Container started successfully", "")
        elif "mkdir" in command:
            return (0, "", "")
        elif "test -f" in command:
            # File exists if it's in our upload list
            path = command.split()[-1]
            exists = any(str(f[1]) == path for f in self.files_uploaded)
            return (0, "", "") if exists else (1, "", "File not found")
        elif "echo" in command:
            return (0, command.split("echo")[1].strip(), "")

        # Check for custom responses
        for pattern, response in self.command_responses.items():
            if pattern in command:
                return response

        # Default success
        return (0, "Success", "")

    def execute_command_success(self, command: str, **kwargs) -> str:
        """Execute command expecting success."""
        code, stdout, stderr = self.execute_command(command, **kwargs)
        if code != 0:
            raise RuntimeError(f"Command failed: {stderr}")
        return stdout


class FakeFileTransferService:
    """Fake file transfer service that tracks transfers without real SFTP.

    Maintains the contract of FileTransferService while allowing
    behavior verification instead of mock call checking.
    """

    def __init__(self, ssh_manager: FakeSSHManager = None, remote_dir: str = "/remote"):
        self.ssh_manager = ssh_manager or FakeSSHManager()
        self.remote_dir = remote_dir
        # Changed structure to track more details
        self.uploaded_files: list[dict] = []  # List of upload details
        self.downloaded_files: list[dict] = []  # List of download details
        self.failed_uploads: list[dict] = []  # Track failed uploads
        self.remote_files: dict[str, bytes] = {}  # Simulated remote files
        self.fail_next_upload = False  # For testing failure scenarios

    def upload_file(self, local_path: Path, remote_dir: str) -> None:
        """Track file upload."""
        if not isinstance(local_path, Path):
            local_path = Path(local_path)

        if self.fail_next_upload:
            self.fail_next_upload = False
            self.failed_uploads.append(
                {"local_path": local_path, "remote_path": remote_dir, "reason": "Simulated failure"}
            )
            raise ConnectionError("Simulated upload failure")

        # For testing, don't check if file exists - just track the upload
        # This allows tests to work with mocked paths
        upload_info = {
            "local_path": local_path,
            "remote_path": remote_dir,
            "filename": local_path.name,
        }
        self.uploaded_files.append(upload_info)

        # Also track in SSH manager for compatibility
        remote_full_path = f"{remote_dir}/{local_path.name}"
        self.ssh_manager.files_uploaded.append((local_path, remote_full_path))

    def upload_directory(self, local_dir: Path, remote_dir: str) -> None:
        """Upload directory recursively."""
        if not isinstance(local_dir, Path):
            local_dir = Path(local_dir)

        if not local_dir.exists():
            raise FileNotFoundError(f"Local directory not found: {local_dir}")

        # Upload all files in directory recursively
        for file_path in local_dir.rglob("*"):
            if file_path.is_file():
                # Preserve directory structure
                relative_path = file_path.relative_to(local_dir.parent)
                remote_subdir = f"{remote_dir}/{relative_path.parent}".replace("\\", "/")

                upload_info = {
                    "local_path": file_path,
                    "remote_path": remote_subdir,
                    "filename": file_path.name,
                }
                self.uploaded_files.append(upload_info)

    def upload_prompt_and_videos(self, prompt_file: Path, video_dirs: list[Path]) -> None:
        """Upload prompt and video directories."""
        # Upload prompt
        self.upload_file(prompt_file, f"{self.remote_dir}/inputs/prompts")

        # Upload video directories
        for video_dir in video_dirs:
            if video_dir.exists():
                self.upload_directory(video_dir, f"{self.remote_dir}/inputs/videos")

    def download_file(self, remote_path: str, local_path: Path) -> None:
        """Download a file from remote."""
        if not isinstance(local_path, Path):
            local_path = Path(local_path)

        # Create parent directory
        local_path.parent.mkdir(parents=True, exist_ok=True)

        # Simulate download
        download_info = {
            "remote_path": remote_path,
            "local_path": local_path,
            "filename": Path(remote_path).name,
        }
        self.downloaded_files.append(download_info)

        # If we have simulated content, write it
        if remote_path in self.remote_files:
            local_path.write_bytes(self.remote_files[remote_path])

    def download_directory(self, remote_dir: str, local_dir: Path) -> None:
        """Download directory from remote."""
        if not isinstance(local_dir, Path):
            local_dir = Path(local_dir)

        local_dir.mkdir(parents=True, exist_ok=True)

        # Download all files that match the remote directory
        for remote_path in self.remote_files:
            if remote_path.startswith(remote_dir):
                # Calculate local path
                relative_path = Path(remote_path).relative_to(remote_dir)
                local_path = local_dir / relative_path

                self.download_file(remote_path, local_path)

    def download_results(self, prompt_file: Path) -> None:
        """Download results for a prompt."""
        prompt_name = prompt_file.stem
        remote_results = f"{self.remote_dir}/outputs/{prompt_name}"
        local_results = Path("outputs") / prompt_name

        # Download as directory
        self.download_directory(remote_results, local_results)

    def file_exists_remote(self, remote_path: str) -> bool:
        """Check if file exists on remote."""
        # Check if path was uploaded
        for upload in self.uploaded_files:
            full_path = f"{upload['remote_path']}/{upload['filename']}"
            if full_path == remote_path:
                return True
        return remote_path in self.remote_files

    def create_remote_directory(self, remote_path: str) -> None:
        """Track remote directory creation."""
        self.ssh_manager.execute_command(f"mkdir -p {remote_path}")

    def list_remote_directory(self, remote_dir: str) -> list[str]:
        """List files in remote directory."""
        # Return files we've uploaded to this directory
        files = []
        for upload in self.uploaded_files:
            full_path = f"{upload['remote_path']}/{upload['filename']}"
            if full_path.startswith(remote_dir + "/"):
                files.append(upload["filename"])
        return files


class FakeDockerExecutor:
    """Fake Docker executor that simulates container operations.

    Provides predictable behavior for testing without real Docker commands.
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
            "duration": 10.5,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Return result dict like real implementation
        return {"status": "success", "log_path": log_path, "prompt_name": prompt_name}

    def run_upscaling(
        self,
        prompt_file: Path,
        run_id: str,
        control_weight: float = 0.5,
        num_gpu: int = 1,
        cuda_devices: str = "0",
    ) -> dict:
        """Simulate running upscaling."""
        prompt_name = prompt_file.stem

        # Check if input video exists (from previous inference)
        input_video = f"{self.remote_dir}/outputs/{prompt_name}/output.mp4"
        if prompt_name not in self.inference_results:
            raise FileNotFoundError(f"Input video not found: {input_video}")

        # Track execution
        self.containers_run.append(
            (
                "upscaling",
                {
                    "prompt": prompt_name,
                    "control_weight": control_weight,
                    "num_gpu": num_gpu,
                    "cuda_devices": cuda_devices,
                },
            )
        )

        # Create upscaled output directory
        output_dir = f"{self.remote_dir}/outputs/{prompt_name}_upscaled"
        self.ssh_manager.execute_command(f"mkdir -p {output_dir}")
        self.remote_executor.created_directories.append(output_dir)

        # Store result
        self.upscaling_results[prompt_name] = {
            "status": "success",
            "output_path": f"{output_dir}/output_upscaled.mp4",
            "control_weight": control_weight,
            "duration": 15.2,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Return result dict like real implementation
        log_path = f"outputs/{prompt_name}_upscaled/logs/run_{run_id}.log"
        return {"status": "success", "log_path": log_path, "prompt_name": prompt_name}

    def get_container_logs(self, container_id: str) -> str:
        """Get logs for a container (stub)."""
        return f"Logs for container {container_id}"

    def cleanup_containers(self) -> None:
        """Clean up containers (stub)."""
        self.containers_run.clear()
        self.inference_results.clear()

    def get_docker_status(self) -> dict[str, Any]:
        """Get Docker status."""
        if self.ssh_manager.connected:
            return {
                "docker_running": True,
                "containers_run": len(self.containers_run),
                "docker_info": "Docker version 24.0.0",
                "available_images": [self.docker_image],
                "running_containers": [],
            }
        return {"docker_running": False, "error": "Not connected"}

    def stream_container_logs(self, container_id: str | None = None) -> None:
        """Stream container logs (stub)."""
        if not container_id:
            container_id = "auto-detected-container"
        # Simulate streaming logs
        print(f"[INFO] Streaming logs from container {container_id[:12]}...")
        print("[INFO] Container started successfully")
        print("[INFO] Processing...")
        print("[INFO] Container completed")


class FakeRemoteExecutor:
    """Fake remote command executor."""

    def __init__(self, ssh_manager: FakeSSHManager = None):
        self.ssh_manager = ssh_manager or FakeSSHManager()
        self.created_directories: list[str] = []
        self.existing_files: set = set()

    def file_exists(self, remote_path: str) -> bool:
        """Check if file exists."""
        return remote_path in self.existing_files

    def create_directory(self, remote_path: str) -> None:
        """Create directory."""
        self.created_directories.append(remote_path)
        self.ssh_manager.execute_command(f"mkdir -p {remote_path}")

    def add_file(self, remote_path: str) -> None:
        """Add a file to the fake filesystem."""
        self.existing_files.add(remote_path)


class FakeWorkflowOrchestrator:
    """Fake workflow orchestrator for integration testing.

    Simulates the complete workflow without real infrastructure.
    """

    def __init__(self, config=None):
        self.config = config
        self.ssh_manager = FakeSSHManager()
        self.ssh_manager.connect()  # Connect by default for orchestrator
        self.file_transfer = FakeFileTransferService(self.ssh_manager)
        self.docker_executor = FakeDockerExecutor(self.ssh_manager)
        self.workflows_run: list[dict] = []

    def run_inference(self, run_spec_file: str, num_gpus: int = 1, verbose: bool = False) -> bool:
        """Run inference workflow."""
        # Track workflow execution
        self.workflows_run.append(
            {
                "type": "inference",
                "run_spec": run_spec_file,
                "num_gpus": num_gpus,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        # Simulate successful workflow
        run_spec_path = Path(run_spec_file)
        if run_spec_path.exists():
            # Read the spec
            with open(run_spec_path) as f:
                json.load(f)

            # Simulate file uploads
            self.file_transfer.upload_file(run_spec_path, "/remote/inputs")

            # Simulate Docker execution with fake run_id
            self.docker_executor.run_inference(
                run_spec_path, run_id="fake_run_001", num_gpu=num_gpus
            )

            # Simulate results download
            self.file_transfer.download_results(run_spec_path)

            return True
        return False

    def check_status(self, verbose: bool = False) -> bool:
        """Check system status."""
        return self.ssh_manager.is_connected()

    def check_remote_status(self) -> dict:
        """Check remote system status."""
        return {
            "ssh_connected": self.ssh_manager.is_connected(),
            "docker_running": True,
            "disk_space": "100GB available",
        }

    def run(self, spec_file: str, **kwargs) -> bool:
        """Main entry point - delegates to run_inference."""
        return self.run_inference(spec_file, **kwargs)

    def run_inference_only(self, spec_file: str, **kwargs) -> bool:
        """Run inference only (no upsampling/upscaling)."""
        return self.run_inference(spec_file, **kwargs)

    def run_upscaling_only(self, spec_file: str, **kwargs) -> bool:
        """Run upscaling only."""
        # Simulate upscaling
        self.workflows_run.append(
            {
                "type": "upscaling",
                "run_spec": spec_file,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        return True

    def run_prompt_upsampling(self, spec_file: str, **kwargs) -> bool:
        """Run prompt upsampling (stub for future merge)."""
        self.workflows_run.append(
            {
                "type": "prompt_upsampling",
                "spec": spec_file,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        return True

    def run_single_prompt_upsampling(self, prompt: str, **kwargs) -> str:
        """Upsample a single prompt (stub)."""
        return f"[UPSAMPLED] {prompt}"

    def run_prompt_upsampling_from_directory(self, directory: str, **kwargs) -> bool:
        """Run upsampling on directory of prompts (stub)."""
        self.workflows_run.append(
            {
                "type": "batch_upsampling",
                "directory": directory,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        return True

    def _get_video_directories(self, name: str, run_spec_file: str) -> list[Path]:
        """Get video directories for a given name."""
        # Return fake directories for testing
        return [Path(f"outputs/videos/{name}_20250830_120000")]
