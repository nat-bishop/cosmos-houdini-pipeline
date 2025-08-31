"""
Reusable mock objects for testing.
"""
import json
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, Mock


class MockSSHManager:
    """Mock SSH manager for testing."""

    def __init__(self, connected: bool = True):
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
    """Mock file transfer manager for testing."""

    def __init__(self, success: bool = True):
        self.success = success
        self.uploaded_files = []
        self.downloaded_files = []
        self.transfer_speed = 10  # MB/s

    def upload_file(self, local_path: str, remote_path: str) -> bool:
        """Mock file upload."""
        if self.success:
            self.uploaded_files.append((local_path, remote_path))
            # Simulate transfer time
            file_size = 1024 * 1024  # 1MB default
            time.sleep(file_size / (self.transfer_speed * 1024 * 1024))
        return self.success

    def upload_directory(self, local_dir: str, remote_dir: str) -> bool:
        """Mock directory upload."""
        if self.success:
            self.uploaded_files.append((local_dir, remote_dir))
        return self.success

    def download_file(self, remote_path: str, local_path: str) -> bool:
        """Mock file download."""
        if self.success:
            self.downloaded_files.append((remote_path, local_path))
        return self.success

    def download_directory(self, remote_dir: str, local_dir: str) -> bool:
        """Mock directory download."""
        if self.success:
            self.downloaded_files.append((remote_dir, local_dir))
        return self.success


class MockDockerExecutor:
    """Mock Docker executor for testing."""

    def __init__(self, success: bool = True):
        self.success = success
        self.containers_run = []
        self.inference_time = 60  # seconds

    def run_inference(
        self, spec_path: str, num_gpus: int = 1, verbose: bool = False
    ) -> tuple[int, str, str]:
        """Mock inference execution."""
        self.containers_run.append(
            {"spec_path": spec_path, "num_gpus": num_gpus, "verbose": verbose}
        )

        if self.success:
            output = f"""
Loading model...
Processing with {num_gpus} GPU(s)...
Inference completed in {self.inference_time} seconds
Output saved to: output.mp4
"""
            return (0, output, "")
        else:
            return (1, "", "CUDA out of memory")

    def run_upsampling(self, prompts: list[str], video_path: str | None = None) -> tuple[int, str, str]:
        """Mock prompt upsampling."""
        if self.success:
            upsampled = [f"Detailed and enhanced: {p}" for p in prompts]
            return (0, json.dumps({"upsampled_prompts": upsampled}), "")
        else:
            return (1, "", "Upsampling failed")


class MockVideoProcessor:
    """Mock video processor for testing."""

    def __init__(self, valid: bool = True):
        self.valid = valid
        self.videos_created = []

    def validate_sequence(self, input_dir: str) -> tuple[bool, list[str]]:
        """Mock sequence validation."""
        if self.valid:
            return (True, [])
        else:
            return (False, ["Missing frames: 4, 5", "Corrupted frame: 10"])

    def create_video_from_frames(self, input_pattern: str, output_path: str, fps: int = 24) -> bool:
        """Mock video creation."""
        if self.valid:
            self.videos_created.append({"input": input_pattern, "output": output_path, "fps": fps})
            # Create mock file
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).touch()
        return self.valid

    def standardize_video(
        self,
        input_path: str,
        output_path: str,
        target_fps: int | None = None,
        target_resolution: str | None = None,
    ) -> bool:
        """Mock video standardization."""
        return self.valid

    def extract_frame(
        self, video_path: str, frame_number: int, output_path: str | None = None
    ) -> Any | None:
        """Mock frame extraction."""
        if self.valid:
            # Return mock frame data
            return b"\x89PNG\r\n\x1a\n" + b"\x00" * 1000
        return None


class MockAIGenerator:
    """Mock AI description and name generator."""

    def __init__(self):
        self.descriptions = [
            "A modern architectural masterpiece with glass facades",
            "Futuristic cyberpunk cityscape with neon lights",
            "Serene natural landscape with mountains and lake",
            "Abstract geometric patterns in vibrant colors",
            "Industrial complex with pipes and machinery",
        ]
        self.name_counter = 0

    def generate_description(self, image_or_video_path: str) -> str:
        """Generate mock description."""
        import random

        return random.choice(self.descriptions)

    def generate_name(self, text: str) -> str:
        """Generate mock smart name."""
        # Extract key words from text
        words = text.lower().split()
        keywords = [w for w in words if len(w) > 4 and w.isalpha()][:2]

        if keywords:
            return "_".join(keywords)
        else:
            self.name_counter += 1
            return f"scene_{self.name_counter:03d}"


class MockConfigManager:
    """Mock configuration manager."""

    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir or Path("/tmp/test")

    def get_remote_config(self) -> Mock:
        """Get mock remote configuration."""
        config = Mock()
        config.host = "test-server"
        config.port = 22
        config.user = "test-user"
        config.ssh_key = str(self.base_dir / "test_key.pem")
        config.remote_dir = "/remote/cosmos"
        return config

    def get_local_config(self) -> Mock:
        """Get mock local configuration."""
        config = Mock()
        config.local_dir = str(self.base_dir)
        config.prompts_dir = str(self.base_dir / "prompts")
        config.runs_dir = str(self.base_dir / "runs")
        config.outputs_dir = str(self.base_dir / "outputs")
        config.videos_dir = str(self.base_dir / "videos")
        return config

    def get_docker_config(self) -> Mock:
        """Get mock Docker configuration."""
        config = Mock()
        config.image = "cosmos-transfer:latest"
        config.gpu_enabled = True
        config.mount_points = {
            str(self.base_dir / "inputs"): "/inputs",
            str(self.base_dir / "outputs"): "/outputs",
        }
        return config


class MockPromptSpecManager:
    """Mock PromptSpec manager."""

    def __init__(self):
        self.specs = {}
        self.next_id = 1

    def create_prompt_spec(self, name: str, prompt: str, **kwargs) -> tuple[str, Mock]:
        """Create mock PromptSpec."""
        spec = Mock()
        spec.id = f"ps_mock_{self.next_id:04d}"
        spec.name = name
        spec.prompt = prompt
        spec.negative_prompt = kwargs.get("negative_prompt", "")
        spec.input_video_path = kwargs.get("video_path", f"/videos/{name}/color.mp4")
        spec.control_inputs = kwargs.get("control_inputs", {})
        spec.timestamp = time.time()

        self.specs[spec.id] = spec
        self.next_id += 1

        spec_file = f"/prompts/{spec.id}.json"
        return (spec_file, spec)

    def load_by_id(self, spec_id: str) -> Mock | None:
        """Load mock PromptSpec by ID."""
        return self.specs.get(spec_id)


class MockRunSpecManager:
    """Mock RunSpec manager."""

    def __init__(self):
        self.specs = {}
        self.next_id = 1

    def create_run_spec(self, prompt_spec_id: str, **kwargs) -> tuple[str, Mock]:
        """Create mock RunSpec."""
        spec = Mock()
        spec.id = f"rs_mock_{self.next_id:04d}"
        spec.prompt_spec_id = prompt_spec_id
        spec.control_weights = kwargs.get("control_weights", {})
        spec.parameters = kwargs.get(
            "parameters", {"num_steps": 35, "guidance_scale": 8.0, "seed": 42}
        )
        spec.execution_status = "pending"
        spec.output_path = f"/outputs/run_{self.next_id:04d}"
        spec.timestamp = time.time()

        self.specs[spec.id] = spec
        self.next_id += 1

        spec_file = f"/runs/{spec.id}.json"
        return (spec_file, spec)

    def load(self, spec_path: str) -> Mock | None:
        """Load mock RunSpec."""
        # Extract ID from path
        spec_id = Path(spec_path).stem
        return self.specs.get(spec_id)
