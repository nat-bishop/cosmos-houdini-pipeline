"""Fake implementations for testing that maintain contracts without mocking internals.

These fakes replace mocks to enable behavior testing instead of implementation testing.
Following principles from the TEST_SUITE_INVESTIGATION_REPORT.md.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class FakeSSHManager:
    """Fake SSH manager that maintains behavior without real connections.

    This fake tracks commands and provides predictable responses,
    allowing tests to verify behavior rather than method calls.
    """

    def __init__(self, connected: bool = True):
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

    def is_connected(self) -> bool:
        """Check connection status."""
        return self.connected

    def execute_command(self, command: str, timeout: int = 30, **kwargs) -> tuple[int, str, str]:
        """Execute command and return predictable output based on command type."""
        self.commands_executed.append((command, kwargs))

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
        self.uploaded_files: dict[str, Path] = {}  # remote_path -> local_path
        self.uploaded_dirs: dict[str, Path] = {}
        self.downloaded_files: dict[Path, str] = {}  # local_path -> remote_path

    def upload_file(self, local_path: Path, remote_dir: str) -> None:
        """Track file upload."""
        if not isinstance(local_path, Path):
            local_path = Path(local_path)

        if not local_path.exists():
            raise FileNotFoundError(f"Local file not found: {local_path}")

        remote_path = f"{remote_dir}/{local_path.name}"
        self.uploaded_files[remote_path] = local_path
        self.ssh_manager.files_uploaded.append((local_path, remote_path))

    def upload_prompt_and_videos(self, prompt_file: Path, video_dirs: list[Path]) -> None:
        """Upload prompt and video directories."""
        # Upload prompt
        self.upload_file(prompt_file, f"{self.remote_dir}/inputs/prompts")

        # Upload video directories
        for video_dir in video_dirs:
            if video_dir.exists():
                self.uploaded_dirs[f"{self.remote_dir}/inputs/videos/{video_dir.name}"] = video_dir

    def download_results(self, prompt_file: Path) -> None:
        """Download results for a prompt."""
        prompt_name = prompt_file.stem
        remote_results = f"{self.remote_dir}/outputs/{prompt_name}"
        local_results = Path("outputs") / prompt_name
        self.downloaded_files[local_results] = remote_results

    def file_exists_remote(self, remote_path: str) -> bool:
        """Check if file exists on remote."""
        return remote_path in self.uploaded_files

    def create_remote_directory(self, remote_path: str) -> None:
        """Track remote directory creation."""
        self.ssh_manager.execute_command(f"mkdir -p {remote_path}")

    def list_remote_directory(self, remote_dir: str) -> list[str]:
        """List files in remote directory."""
        # Return files we've uploaded to this directory
        files = []
        for remote_path in self.uploaded_files:
            if remote_path.startswith(remote_dir + "/"):
                files.append(Path(remote_path).name)
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

    def run_inference(self, prompt_file: Path, num_gpu: int = 1, cuda_devices: str = "0") -> None:
        """Simulate running inference."""
        prompt_name = prompt_file.stem

        # Track execution
        self.containers_run.append(
            ("inference", {"prompt": prompt_name, "num_gpu": num_gpu, "cuda_devices": cuda_devices})
        )

        # Create output directory
        output_dir = f"{self.remote_dir}/outputs/{prompt_name}"
        self.ssh_manager.execute_command(f"mkdir -p {output_dir}")

        # Store result
        self.inference_results[prompt_name] = {
            "status": "success",
            "output_path": f"{output_dir}/output.mp4",
            "duration": 10.5,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def run_upscaling(
        self,
        prompt_file: Path,
        control_weight: float = 0.5,
        num_gpu: int = 1,
        cuda_devices: str = "0",
    ) -> None:
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

            # Simulate Docker execution
            self.docker_executor.run_inference(run_spec_path, num_gpu=num_gpus)

            # Simulate results download
            self.file_transfer.download_results(run_spec_path)

            return True
        return False

    def check_status(self, verbose: bool = False) -> bool:
        """Check system status."""
        return self.ssh_manager.is_connected()

    def _get_video_directories(self, name: str, run_spec_file: str) -> list[Path]:
        """Get video directories for a given name."""
        # Return fake directories for testing
        return [Path(f"outputs/videos/{name}_20250830_120000")]


@dataclass
class FakePromptSpec:
    """Fake PromptSpec for testing."""

    id: str = "test_ps_001"
    name: str = "test_prompt"
    prompt: str = "A beautiful test scene"
    negative_prompt: str = ""
    input_video_path: str = "inputs/test.mp4"
    control_inputs: dict[str, str] = field(
        default_factory=lambda: {
            "depth": "inputs/depth.mp4",
            "segmentation": "inputs/segmentation.mp4",
        }
    )
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "prompt": self.prompt,
            "negative_prompt": self.negative_prompt,
            "input_video_path": self.input_video_path,
            "control_inputs": self.control_inputs,
            "timestamp": self.timestamp,
        }

    def validate(self) -> bool:
        """Validate the spec."""
        return bool(self.prompt and self.input_video_path)


@dataclass
class FakeRunSpec:
    """Fake RunSpec for testing."""

    id: str = "test_rs_001"
    prompt_spec_id: str = "test_ps_001"
    control_weights: dict[str, float] = field(
        default_factory=lambda: {"depth": 0.3, "segmentation": 0.2}
    )
    parameters: dict[str, Any] = field(default_factory=lambda: {"num_steps": 35, "seed": 42})
    execution_status: str = "pending"
    output_path: str = "outputs/test_run"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "prompt_spec_id": self.prompt_spec_id,
            "control_weights": self.control_weights,
            "parameters": self.parameters,
            "execution_status": self.execution_status,
            "output_path": self.output_path,
            "timestamp": self.timestamp,
        }
