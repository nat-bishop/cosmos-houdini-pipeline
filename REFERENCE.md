# API Reference

Complete API documentation for the Cosmos Workflow System.

## Table of Contents
- [CLI Commands](#cli-commands)
- [Core Modules](#core-modules)
- [Schemas](#schemas)
- [Configuration](#configuration)
- [Utilities](#utilities)

## CLI Commands

### create-spec
Create a prompt specification for Cosmos Transfer.

```bash
python -m cosmos_workflow.cli create-spec NAME PROMPT [OPTIONS]
```

**Arguments:**
- `NAME`: Name for the prompt specification
- `PROMPT`: Text prompt for generation

**Options:**
- `--negative-prompt`: Negative prompt text
- `--video-path`: Path to input video
- `--control-inputs`: Control modality inputs (JSON)
- `--verbose`: Enable verbose output

**Example:**
```bash
python -m cosmos_workflow.cli create-spec "city_scene" "A futuristic city" \
    --negative-prompt "blurry, low quality" \
    --video-path ./videos/input.mp4
```

### create-run
Create a run specification from a prompt spec.

```bash
python -m cosmos_workflow.cli create-run PROMPT_FILE [OPTIONS]
```

**Arguments:**
- `PROMPT_FILE`: Path to prompt specification JSON

**Options:**
- `--weights`: Control weights (4 values: vis edge depth segmentation)
- `--num-steps`: Number of inference steps (default: 35)
- `--guidance-scale`: CFG guidance scale (default: 8.0)
- `--output-path`: Custom output path
- `--verbose`: Enable verbose output

**Example:**
```bash
python -m cosmos_workflow.cli create-run prompt_spec.json \
    --weights 0.3 0.4 0.2 0.1 \
    --num-steps 50 \
    --guidance-scale 10.0
```

### run
Execute a complete workflow on remote GPU.

```bash
python -m cosmos_workflow.cli run PROMPT_FILE [OPTIONS]
```

**Arguments:**
- `PROMPT_FILE`: Path to prompt or run specification

**Options:**
- `--videos-subdir`: Override video directory
- `--no-upscale`: Skip upscaling step
- `--upscale-weight`: Control weight for upscaling (default: 0.5)
- `--num-gpu`: Number of GPUs to use (default: 1)
- `--cuda-devices`: CUDA device IDs (default: "0")
- `--verbose`: Enable verbose output

**Example:**
```bash
python -m cosmos_workflow.cli run run_spec.json \
    --num-gpu 2 \
    --cuda-devices "0,1" \
    --upscale-weight 0.7
```

### convert-sequence
Convert PNG sequence to video.

```bash
python -m cosmos_workflow.cli convert-sequence INPUT_DIR [OPTIONS]
```

**Arguments:**
- `INPUT_DIR`: Directory containing PNG sequence

**Options:**
- `--output`: Output video path (optional)
- `--fps`: Frame rate (default: 24)
- `--resolution`: Target resolution (720p/1080p/4k/WxH)
- `--generate-metadata`: Generate metadata JSON
- `--ai-analysis`: Use AI for metadata generation
- `--verbose`: Enable verbose output

**Example:**
```bash
python -m cosmos_workflow.cli convert-sequence ./renders/sequence/ \
    --fps 30 \
    --resolution 1080p \
    --generate-metadata \
    --ai-analysis
```

### prepare-inference
Prepare Cosmos sequences for inference.

```bash
python -m cosmos_workflow.cli prepare-inference INPUT_DIR [OPTIONS]
```

**Arguments:**
- `INPUT_DIR`: Directory with control modality PNGs

**Options:**
- `--name`: Name for output (AI-generated if not provided)
- `--fps`: Frame rate for videos (default: 24)
- `--description`: Optional description
- `--use-ai`: Use AI for descriptions (default: True)
- `--verbose`: Enable verbose output

**Example:**
```bash
python -m cosmos_workflow.cli prepare-inference ./cosmos_sequences/ \
    --name "urban_scene" \
    --fps 24 \
    --use-ai
```

### status
Check remote instance and Docker status.

```bash
python -m cosmos_workflow.cli status [OPTIONS]
```

**Options:**
- `--verbose`: Show detailed information

**Example:**
```bash
python -m cosmos_workflow.cli status --verbose
```

## Core Modules

### WorkflowOrchestrator
Main orchestrator for workflow execution.

```python
from cosmos_workflow.workflows.workflow_orchestrator import WorkflowOrchestrator

orchestrator = WorkflowOrchestrator()

# Run complete workflow
result = orchestrator.run(
    prompt_file=Path("prompt.json"),
    inference=True,
    upscale=True,
    upload=True,
    download=True,
    num_gpu=2
)
```

**Methods:**
- `run()`: Execute configurable workflow steps
- `run_full_cycle()`: Complete pipeline (legacy)
- `run_inference_only()`: Inference without upscaling
- `run_upscaling_only()`: Upscale existing output
- `check_remote_status()`: Check remote system

### SSHManager
Manages SSH connections to remote instances.

```python
from cosmos_workflow.connection.ssh_manager import SSHManager

ssh_manager = SSHManager(ssh_options={
    "hostname": "192.222.52.92",
    "username": "ubuntu",
    "key_filename": "~/.ssh/key.pem",
    "port": 22
})

# Context manager usage
with ssh_manager:
    output = ssh_manager.execute_command_success("ls -la")
```

**Methods:**
- `connect()`: Establish SSH connection
- `disconnect()`: Close connection
- `execute_command()`: Run command, return (exit_code, stdout, stderr)
- `execute_command_success()`: Run command, raise on error
- `get_sftp()`: Get SFTP client

### FileTransferService
Handles file transfers via SFTP.

```python
from cosmos_workflow.transfer.file_transfer import FileTransferService

file_transfer = FileTransferService(ssh_manager, remote_dir)

# Upload files for inference
file_transfer.upload_for_inference(
    prompt_file=Path("prompt.json"),
    video_dirs=[Path("videos/scene1")]
)

# Download results
file_transfer.download_results(Path("prompt.json"))
```

**Methods:**
- `upload_for_inference()`: Upload prompt and videos
- `download_results()`: Download generated outputs
- `file_exists_remote()`: Check if remote file exists
- `list_remote_directory()`: List remote directory

### DockerExecutor
Executes Docker commands on remote instance.

```python
from cosmos_workflow.execution.docker_executor import DockerExecutor

docker_executor = DockerExecutor(
    ssh_manager=ssh_manager,
    remote_executor=remote_executor,
    docker_image="nvcr.io/ubuntu/cosmos-transfer1:latest",
    remote_dir="/workspace"
)

# Run inference
docker_executor.run_inference(
    prompt_file=Path("prompt.json"),
    num_gpu=2,
    cuda_devices="0,1"
)

# Run upscaling
docker_executor.run_upscaling(
    prompt_file=Path("prompt.json"),
    control_weight=0.5
)
```

**Methods:**
- `run_inference()`: Execute inference pipeline
- `run_upscaling()`: Execute upscaling pipeline
- `get_docker_status()`: Check Docker status
- `cleanup_containers()`: Clean up stopped containers

## Schemas

### PromptSpec
Prompt specification schema.

```python
from cosmos_workflow.prompts.schemas import PromptSpec

spec = PromptSpec(
    id="unique_id",
    name="scene_name",
    prompt="Generation prompt",
    negative_prompt="Negative prompt",
    input_video_path="path/to/video.mp4",
    control_inputs={
        "vis": "path/to/vis",
        "edge": "path/to/edge",
        "depth": "path/to/depth",
        "segmentation": "path/to/segmentation"
    },
    timestamp="2024-12-30T10:00:00Z"
)

# Save to JSON
spec.save("prompt_spec.json")

# Load from JSON
loaded_spec = PromptSpec.load("prompt_spec.json")
```

**Fields:**
- `id`: Unique identifier (auto-generated)
- `name`: Human-readable name
- `prompt`: Main generation prompt
- `negative_prompt`: Optional negative prompt
- `input_video_path`: Optional input video
- `control_inputs`: Control modality paths
- `timestamp`: Creation timestamp

### RunSpec
Run configuration schema.

```python
from cosmos_workflow.prompts.schemas import RunSpec, ExecutionStatus

run_spec = RunSpec(
    id="run_id",
    prompt_id="prompt_id",
    name="run_name",
    control_weights={
        "vis": 0.3,
        "edge": 0.4,
        "depth": 0.2,
        "segmentation": 0.1
    },
    parameters={
        "num_steps": 50,
        "guidance_scale": 10.0,
        "seed": 42
    },
    execution_status=ExecutionStatus.PENDING,
    output_path="outputs/run_001"
)

# Update status
run_spec.execution_status = ExecutionStatus.COMPLETED
run_spec.save("run_spec.json")
```

**Fields:**
- `id`: Unique run identifier
- `prompt_id`: Reference to PromptSpec
- `name`: Run name
- `control_weights`: Weight for each modality
- `parameters`: Inference parameters
- `execution_status`: Current status
- `output_path`: Output directory
- `timestamp`: Creation time
- `start_time`: Execution start
- `end_time`: Execution end
- `error_message`: Error details if failed

### ExecutionStatus
Enum for execution states.

```python
from cosmos_workflow.prompts.schemas import ExecutionStatus

status = ExecutionStatus.PENDING    # Not started
status = ExecutionStatus.RUNNING    # In progress
status = ExecutionStatus.COMPLETED  # Successful
status = ExecutionStatus.FAILED     # Error occurred
```

## Configuration

### ConfigManager
Manages configuration loading and validation.

```python
from cosmos_workflow.config.config_manager import ConfigManager

config_manager = ConfigManager(config_file="config.toml")

# Get configurations
local_config = config_manager.get_local_config()
remote_config = config_manager.get_remote_config()
docker_config = config_manager.get_docker_config()

# Access values
print(remote_config.host)      # "192.222.52.92"
print(local_config.prompts_dir) # Path("inputs/prompts")
```

### Configuration File (config.toml)
```toml
[remote]
host = "192.222.52.92"
user = "ubuntu"
ssh_key = "~/.ssh/key.pem"
port = 22

[paths]
remote_dir = "/home/ubuntu/NatsFS/cosmos-transfer1"
local_prompts_dir = "./inputs/prompts"
local_runs_dir = "./inputs/runs"
local_videos_dir = "./inputs/videos"
local_outputs_dir = "./outputs"
local_notes_dir = "./notes"

[docker]
image = "nvcr.io/ubuntu/cosmos-transfer1:latest"
shm_size = "8g"
ipc_mode = "host"

[execution]
default_num_steps = 35
default_guidance_scale = 8.0
default_upscale_weight = 0.5
offload_models = true
offload_vae = true
```

## Utilities

### SmartNaming
Generate intelligent names from descriptions.

```python
from cosmos_workflow.utils.smart_naming import generate_smart_name

name = generate_smart_name(
    "A beautiful sunset over the ocean with waves",
    max_length=20
)
# Returns: "sunset_ocean_waves"
```

### VideoProcessor
Process video files and PNG sequences.

```python
from cosmos_workflow.local_ai.video_metadata import VideoProcessor

processor = VideoProcessor(use_ai=True)

# Extract metadata
metadata = processor.extract_metadata(Path("video.mp4"))

# Standardize video
processor.standardize_video(
    input_path=Path("input.mp4"),
    output_path=Path("output.mp4"),
    target_fps=24,
    target_resolution=(1920, 1080)
)

# Create video from frames
processor.create_video_from_frames(
    frame_paths=[Path("frame1.png"), Path("frame2.png")],
    output_path=Path("output.mp4"),
    fps=24
)
```

### CosmosSequenceValidator
Validate and process Cosmos control sequences.

```python
from cosmos_workflow.local_ai.cosmos_sequence import CosmosSequenceValidator

validator = CosmosSequenceValidator(fps=24, use_ai=True)

# Validate sequence directory
info = validator.validate_directory(Path("cosmos_sequences/"))

# Convert to videos
results = validator.convert_to_videos(
    sequence_info=info,
    output_dir=Path("outputs/"),
    name="scene"
)

# Generate metadata
metadata = validator.generate_metadata(
    sequence_info=info,
    video_path="outputs/scene/color.mp4"
)
```

## Error Handling

All modules use consistent error handling:

```python
try:
    orchestrator.run(prompt_file)
except ConnectionError as e:
    # SSH connection failed
    print(f"Connection error: {e}")
except FileNotFoundError as e:
    # File not found
    print(f"File error: {e}")
except RuntimeError as e:
    # Execution error
    print(f"Runtime error: {e}")
except Exception as e:
    # Unexpected error
    print(f"Unexpected error: {e}")
```

## Logging

Configure logging level via environment or config:

```python
import logging

# Set logging level
logging.basicConfig(level=logging.DEBUG)

# Or use CLI verbose flag
python -m cosmos_workflow.cli run prompt.json --verbose
```

Log levels:
- `DEBUG`: Detailed information
- `INFO`: General information
- `WARNING`: Warning messages
- `ERROR`: Error messages

## Testing

Run tests for any module:

```bash
# Test specific module
pytest tests/unit/prompts/test_schemas.py

# Test with coverage
pytest --cov=cosmos_workflow.prompts

# Run integration tests
pytest tests/integration/
```

## Performance Tips

1. **Use Multiple GPUs**: `--num-gpu 2 --cuda-devices "0,1"`
2. **Enable Model Offloading**: Set `offload_models = true` in config
3. **Batch Processing**: Process multiple prompts in sequence
4. **Optimize Transfers**: Use compression for large files
5. **Cache Models**: Keep models loaded between runs

## Troubleshooting

### SSH Connection Issues
```python
# Test SSH connection
ssh_manager = SSHManager(ssh_options)
try:
    ssh_manager.connect()
    print("Connection successful")
except ConnectionError as e:
    print(f"Failed: {e}")
```

### Docker Issues
```bash
# Check Docker status
python -m cosmos_workflow.cli status

# Clean up containers
docker_executor.cleanup_containers()
```

### File Transfer Issues
```python
# Verify remote directory exists
exists = file_transfer.file_exists_remote("/path/to/dir")

# List remote contents
files = file_transfer.list_remote_directory("/path")
```

---

For more examples and implementation details, see the [docs/implementation/](docs/implementation/) directory.