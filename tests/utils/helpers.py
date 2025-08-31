"""
Test helper utilities for common testing operations.
"""
import json
import random
import string
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def create_mock_video_file(path: Path, size_mb: float = 1.0) -> Path:
    """
    Create a mock video file with specified size.

    Args:
        path: Path where to create the file
        size_mb: Size of the file in megabytes

    Returns:
        Path to the created file
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Create a file with approximate size
    content = b"\x00" * int(size_mb * 1024 * 1024)
    path.write_bytes(content)

    return path


def create_mock_png_sequence(
    directory: Path,
    modality: str = "color",
    frame_count: int = 10,
    start_frame: int = 1,
    width: int = 1920,
    height: int = 1080,
) -> List[Path]:
    """
    Create a sequence of mock PNG files.

    Args:
        directory: Directory to create files in
        modality: Type of frames (color, depth, segmentation, etc.)
        frame_count: Number of frames to create
        start_frame: Starting frame number
        width: Image width
        height: Image height

    Returns:
        List of created file paths
    """
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)

    files = []
    for i in range(start_frame, start_frame + frame_count):
        file_path = directory / f"{modality}.{i:04d}.png"
        # Create a minimal valid PNG header
        png_header = b"\x89PNG\r\n\x1a\n"
        # Add some mock image data
        file_path.write_bytes(png_header + b"\x00" * 1000)
        files.append(file_path)

    return files


def create_test_prompt_spec(
    name: str = None,
    prompt: str = None,
    video_path: str = None,
    control_inputs: Dict[str, str] = None,
) -> Dict[str, Any]:
    """
    Create a test PromptSpec dictionary.

    Args:
        name: Name for the spec (auto-generated if None)
        prompt: Prompt text (auto-generated if None)
        video_path: Path to input video
        control_inputs: Dictionary of control input paths

    Returns:
        PromptSpec dictionary
    """
    if name is None:
        name = f"test_scene_{random.randint(1000, 9999)}"

    if prompt is None:
        prompt = f"A test prompt for {name}"

    if video_path is None:
        video_path = f"/path/to/{name}/color.mp4"

    if control_inputs is None:
        control_inputs = {}

    return {
        "id": f"ps_{generate_random_id()}",
        "name": name,
        "prompt": prompt,
        "negative_prompt": "blurry, low quality",
        "input_video_path": video_path,
        "control_inputs": control_inputs,
        "timestamp": datetime.now().isoformat(),
    }


def create_test_run_spec(
    prompt_spec_id: str = None,
    control_weights: Dict[str, float] = None,
    parameters: Dict[str, Any] = None,
    status: str = "pending",
) -> Dict[str, Any]:
    """
    Create a test RunSpec dictionary.

    Args:
        prompt_spec_id: ID of associated PromptSpec
        control_weights: Control weight mapping
        parameters: Execution parameters
        status: Execution status

    Returns:
        RunSpec dictionary
    """
    if prompt_spec_id is None:
        prompt_spec_id = f"ps_{generate_random_id()}"

    if control_weights is None:
        control_weights = {"depth": 0.3, "segmentation": 0.4}

    if parameters is None:
        parameters = {"num_steps": 35, "guidance_scale": 8.0, "seed": 42}

    return {
        "id": f"rs_{generate_random_id()}",
        "prompt_spec_id": prompt_spec_id,
        "control_weights": control_weights,
        "parameters": parameters,
        "execution_status": status,
        "output_path": f"outputs/run_{generate_random_id()}",
        "timestamp": datetime.now().isoformat(),
    }


def generate_random_id(length: int = 8) -> str:
    """Generate a random ID string."""
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


def create_mock_config_toml(path: Path, **overrides) -> Path:
    """
    Create a mock config.toml file.

    Args:
        path: Path to create the config file
        **overrides: Values to override in the config

    Returns:
        Path to created config file
    """
    default_config = {
        "remote": {
            "host": overrides.get("host", "test-host"),
            "port": overrides.get("port", 22),
            "user": overrides.get("user", "test-user"),
            "ssh_key": overrides.get("ssh_key", "~/.ssh/test_key.pem"),
            "remote_dir": overrides.get("remote_dir", "/remote/cosmos"),
        },
        "paths": {
            "local_dir": overrides.get("local_dir", "./"),
            "prompts_dir": overrides.get("prompts_dir", "./inputs/prompts"),
            "runs_dir": overrides.get("runs_dir", "./inputs/runs"),
            "outputs_dir": overrides.get("outputs_dir", "./outputs"),
            "videos_dir": overrides.get("videos_dir", "./outputs/videos"),
        },
        "docker": {
            "image": overrides.get("docker_image", "cosmos-transfer:latest"),
            "gpu_enabled": overrides.get("gpu_enabled", True),
        },
    }

    import toml

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(toml.dumps(default_config))

    return path


def assert_files_equal(file1: Path, file2: Path, binary: bool = False):
    """
    Assert that two files have identical content.

    Args:
        file1: First file path
        file2: Second file path
        binary: Whether to compare as binary files
    """
    if binary:
        content1 = Path(file1).read_bytes()
        content2 = Path(file2).read_bytes()
    else:
        content1 = Path(file1).read_text()
        content2 = Path(file2).read_text()

    assert content1 == content2, f"Files {file1} and {file2} have different content"


def assert_json_files_equal(file1: Path, file2: Path, ignore_keys: List[str] = None):
    """
    Assert that two JSON files have equivalent content.

    Args:
        file1: First JSON file path
        file2: Second JSON file path
        ignore_keys: List of keys to ignore in comparison
    """
    data1 = json.loads(Path(file1).read_text())
    data2 = json.loads(Path(file2).read_text())

    if ignore_keys:
        for key in ignore_keys:
            data1.pop(key, None)
            data2.pop(key, None)

    assert data1 == data2, f"JSON files {file1} and {file2} have different content"


def create_mock_ssh_response(
    return_code: int = 0, stdout: str = "Success", stderr: str = ""
) -> Tuple[int, str, str]:
    """
    Create a mock SSH command response.

    Args:
        return_code: Command return code
        stdout: Standard output
        stderr: Standard error

    Returns:
        Tuple of (return_code, stdout, stderr)
    """
    return (return_code, stdout, stderr)


def simulate_file_transfer_progress(
    total_size: int, chunk_size: int = 1024 * 1024, callback=None
) -> List[int]:
    """
    Simulate file transfer progress.

    Args:
        total_size: Total size in bytes
        chunk_size: Size of each chunk
        callback: Optional progress callback

    Returns:
        List of progress percentages
    """
    progress_points = []
    transferred = 0

    while transferred < total_size:
        transferred += min(chunk_size, total_size - transferred)
        progress = int((transferred / total_size) * 100)
        progress_points.append(progress)

        if callback:
            callback(transferred, total_size)

    return progress_points


def create_mock_docker_output(
    success: bool = True, inference_time: float = 60.0, gpu_memory_used: float = 8.5
) -> str:
    """
    Create mock Docker inference output.

    Args:
        success: Whether inference succeeded
        inference_time: Time taken for inference
        gpu_memory_used: GPU memory used in GB

    Returns:
        Mock Docker output string
    """
    if success:
        output = f"""
Starting inference...
Loading model...
GPU Memory: {gpu_memory_used:.1f}GB
Processing frames...
Frame 1/48 processed
Frame 24/48 processed
Frame 48/48 processed
Inference completed in {inference_time:.1f} seconds
Output saved to: output.mp4
"""
    else:
        output = """
Starting inference...
Loading model...
Error: CUDA out of memory
Inference failed
"""

    return output


def wait_for_condition(
    condition_func,
    timeout: float = 10.0,
    interval: float = 0.1,
    error_msg: str = "Condition not met within timeout",
) -> bool:
    """
    Wait for a condition to become true.

    Args:
        condition_func: Function that returns True when condition is met
        timeout: Maximum time to wait in seconds
        interval: Check interval in seconds
        error_msg: Error message if timeout occurs

    Returns:
        True if condition met, raises TimeoutError otherwise
    """
    import time

    start_time = time.time()

    while time.time() - start_time < timeout:
        if condition_func():
            return True
        time.sleep(interval)

    raise TimeoutError(error_msg)


def compare_specs(spec1: Dict, spec2: Dict, ignore_fields: List[str] = None) -> bool:
    """
    Compare two spec dictionaries.

    Args:
        spec1: First spec dictionary
        spec2: Second spec dictionary
        ignore_fields: Fields to ignore in comparison

    Returns:
        True if specs are equivalent
    """
    if ignore_fields is None:
        ignore_fields = ["timestamp", "id"]

    # Create copies to avoid modifying originals
    s1 = spec1.copy()
    s2 = spec2.copy()

    for field in ignore_fields:
        s1.pop(field, None)
        s2.pop(field, None)

    return s1 == s2
