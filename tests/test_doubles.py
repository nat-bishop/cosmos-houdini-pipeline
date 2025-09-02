"""
Test doubles (fakes, stubs) for testing without excessive mocking.
These provide realistic behavior without external dependencies.
"""

from datetime import datetime
from pathlib import Path
from typing import Any

from cosmos_workflow.prompts.schemas import PromptSpec, RunSpec


class FakeSSHManager:
    """Fake SSH manager that simulates SSH operations without network."""

    def __init__(self):
        self.connected = False
        self.commands_executed = []
        self.files_uploaded = []
        self.files_downloaded = []
        self.command_responses = {}

    def connect(self) -> None:
        """Simulate connection."""
        self.connected = True

    def disconnect(self) -> None:
        """Simulate disconnection."""
        self.connected = False

    def is_connected(self) -> bool:
        """Check connection status."""
        return self.connected

    def execute_command(self, cmd: str, timeout: int | None = None) -> tuple[int, str, str]:
        """Simulate command execution."""
        self.commands_executed.append(cmd)

        # Return predefined responses or defaults
        if cmd in self.command_responses:
            return self.command_responses[cmd]

        # Default responses for common commands
        if "docker run" in cmd:
            return (0, "Container started successfully", "")
        elif "docker ps" in cmd:
            return (0, "CONTAINER ID   IMAGE   STATUS", "")
        elif "ls" in cmd:
            return (0, "file1.txt\nfile2.txt", "")
        elif "echo" in cmd:
            return (0, cmd.replace("echo ", ""), "")

        return (0, "", "")

    def set_command_response(self, cmd: str, response: tuple[int, str, str]) -> None:
        """Set a specific response for a command."""
        self.command_responses[cmd] = response

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()


class FakeFileTransferService:
    """Fake file transfer service that simulates SFTP operations."""

    def __init__(self, temp_dir: Path | None = None):
        self.temp_dir = temp_dir or Path("/tmp/fake_transfer")
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.uploaded_files = []
        self.uploaded_dirs = []
        self.downloaded_dirs = []

    def upload_file(self, local_path: Path, remote_path: str) -> bool:
        """Simulate file upload."""
        self.uploaded_files.append((str(local_path), remote_path))

        # Create a marker file in temp dir
        marker = self.temp_dir / f"uploaded_{Path(remote_path).name}"
        marker.touch()

        return True

    def upload_directory(self, local_dir: Path, remote_dir: str) -> bool:
        """Simulate directory upload."""
        self.uploaded_dirs.append((str(local_dir), remote_dir))

        # Create marker directory
        marker_dir = self.temp_dir / f"uploaded_{Path(remote_dir).name}"
        marker_dir.mkdir(parents=True, exist_ok=True)

        return True

    def download_directory(self, remote_dir: str, local_dir: Path) -> bool:
        """Simulate directory download."""
        self.downloaded_dirs.append((remote_dir, str(local_dir)))

        # Create some fake output files
        local_dir.mkdir(parents=True, exist_ok=True)
        (local_dir / "output.mp4").touch()
        (local_dir / "metadata.json").write_text('{"status": "complete"}')

        return True

    def upload_prompt_and_videos(self, prompt_spec: PromptSpec, run_spec: RunSpec) -> dict:
        """Simulate uploading prompt and associated videos."""
        result = {"prompt_uploaded": True, "videos_uploaded": [], "remote_paths": {}}

        # Simulate uploading prompt
        self.uploaded_files.append(
            (f"prompt_{prompt_spec.id}.json", f"/remote/prompts/{prompt_spec.id}.json")
        )

        # Simulate uploading videos
        if prompt_spec.input_video_path:
            video_name = Path(prompt_spec.input_video_path).name
            self.uploaded_files.append(
                (prompt_spec.input_video_path, f"/remote/videos/{video_name}")
            )
            result["videos_uploaded"].append(video_name)
            result["remote_paths"]["input_video"] = f"/remote/videos/{video_name}"

        # Upload control inputs
        for control_type, control_path in prompt_spec.control_inputs.items():
            control_name = Path(control_path).name
            self.uploaded_files.append((control_path, f"/remote/controls/{control_name}"))
            result["videos_uploaded"].append(control_name)
            result["remote_paths"][control_type] = f"/remote/controls/{control_name}"

        return result


class FakeDockerExecutor:
    """Fake Docker executor that simulates container operations."""

    def __init__(self):
        self.containers_run = []
        self.execution_results = {}

    def run_inference(
        self, run_spec: RunSpec, num_gpus: int = 1, verbose: bool = False
    ) -> tuple[int, str, str]:
        """Simulate inference execution."""
        self.containers_run.append(
            {"run_spec_id": run_spec.id, "num_gpus": num_gpus, "verbose": verbose}
        )

        # Return predefined result or default success
        if run_spec.id in self.execution_results:
            return self.execution_results[run_spec.id]

        output = f"Inference completed for {run_spec.id}"
        if verbose:
            output += "\nDetailed output..."

        return (0, output, "")

    def run_upsampling(self, prompt_spec: PromptSpec) -> tuple[int, str, str]:
        """Simulate upsampling execution."""
        output = f"Upsampled prompt: {prompt_spec.prompt[:50]}..."
        return (0, output, "")

    def set_execution_result(self, run_spec_id: str, result: tuple[int, str, str]) -> None:
        """Set a specific result for a run spec."""
        self.execution_results[run_spec_id] = result

    def cleanup_containers(self) -> None:
        """Simulate container cleanup."""
        self.containers_run.clear()


class FakePromptSpecManager:
    """Fake PromptSpecManager that works with in-memory data."""

    def __init__(self, temp_dir: Path | None = None):
        self.temp_dir = temp_dir or Path("/tmp/fake_prompts")
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.prompt_specs = {}

    def create_prompt_spec(self, **kwargs) -> PromptSpec:
        """Create a prompt spec."""
        spec = PromptSpec(**kwargs)
        self.prompt_specs[spec.id] = spec

        # Also save to file for compatibility
        spec_file = self.temp_dir / f"{spec.id}.json"
        spec.save(spec_file)

        return spec

    def get_by_id(self, spec_id: str) -> PromptSpec | None:
        """Get prompt spec by ID."""
        return self.prompt_specs.get(spec_id)

    def list_prompts(
        self, prompts_dir: Path | None = None, pattern: str | None = None
    ) -> list[Path]:
        """List available prompts."""
        search_dir = prompts_dir or self.temp_dir
        if not search_dir.exists():
            return []

        files = search_dir.glob(pattern or "*.json")
        return list(files)

    def get_prompt_info(self, prompt_path: Path) -> dict[str, Any]:
        """Get prompt information."""
        if prompt_path.exists():
            spec = PromptSpec.load(prompt_path)
            return spec.to_dict()
        return {}


class FakeWorkflowOrchestrator:
    """Fake orchestrator for testing workflow logic without external deps."""

    def __init__(self, config_manager=None):
        self.config_manager = config_manager
        self.ssh_manager = FakeSSHManager()
        self.file_transfer = FakeFileTransferService()
        self.docker_executor = FakeDockerExecutor()
        self.prompt_manager = FakePromptSpecManager()

        self.workflows_executed = []

    def run_inference(self, run_spec_path: str, num_gpus: int = 1, verbose: bool = False) -> bool:
        """Simulate inference workflow."""
        self.workflows_executed.append(
            {
                "run_spec_path": run_spec_path,
                "num_gpus": num_gpus,
                "verbose": verbose,
                "timestamp": datetime.now().isoformat(),
            }
        )

        # Load run spec
        run_spec = RunSpec.load(Path(run_spec_path))

        # Simulate workflow steps
        # 1. Get prompt spec
        prompt_spec = self.prompt_manager.get_by_id(run_spec.prompt_id)
        if not prompt_spec:
            return False

        # 2. Upload files
        self.file_transfer.upload_prompt_and_videos(prompt_spec, run_spec)

        # 3. Run inference
        exit_code, output, error = self.docker_executor.run_inference(run_spec, num_gpus, verbose)

        # 4. Download results
        if exit_code == 0:
            self.file_transfer.download_directory(
                f"/remote/outputs/{run_spec.id}",
                Path(run_spec.output_path) if run_spec.output_path else Path("outputs"),
            )

        return exit_code == 0

    def check_remote_status(self) -> dict[str, Any]:
        """Check remote system status."""
        return {
            "ssh_connected": self.ssh_manager.is_connected(),
            "containers_running": len(self.docker_executor.containers_run),
            "last_workflow": self.workflows_executed[-1] if self.workflows_executed else None,
        }

    def get_video_directories(self, run_spec_path: Path) -> list[Path]:
        """Get video directories for a run spec."""
        # Simple implementation for testing
        run_spec = RunSpec.load(run_spec_path)

        if run_spec.output_path:
            output_dir = Path(run_spec.output_path)
            if output_dir.exists():
                return [output_dir]

        # Return default
        return [Path("inputs/videos") / run_spec_path.stem]
