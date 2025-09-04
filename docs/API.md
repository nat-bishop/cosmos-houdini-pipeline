# API Reference

Complete API documentation for the Cosmos Workflow System.

## Table of Contents
- [CLI Commands](#cli-commands)
- [Core Modules](#core-modules)
- [Schemas](#schemas)
- [Configuration](#configuration)
- [Utilities](#utilities)

## CLI Commands

### create prompt
Create a new prompt specification.

```bash
cosmos create prompt "PROMPT_TEXT" [OPTIONS]
```

**Arguments:**
- `PROMPT_TEXT`: Text prompt for generation

**Options:**
- `-n, --name`: Name for the prompt (auto-generated if not provided)
- `--negative`: Negative prompt for quality improvement
- `--video`: Path to input video file
- `--enhanced`: Mark as enhanced (upsampled) prompt
- `--parent-prompt`: Original prompt text (if enhanced)

**Example:**
```bash
cosmos create prompt "A futuristic city at night" inputs/videos/scene1
cosmos create prompt "Transform to anime style" /path/to/video_dir
```

### create run
Create a run specification from a prompt spec.

```bash
cosmos create run PROMPT_FILE [OPTIONS]
```

**Arguments:**
- `PROMPT_FILE`: Path to prompt specification JSON

**Options:**
- `--weights`: Control weights (4 values: vis edge depth segmentation)
- `--num-steps`: Number of inference steps (default: 35)
- `--guidance-scale`: CFG guidance scale (default: 8.0)
- `--output-path`: Custom output path

**Example:**
```bash
cosmos create run prompt_spec.json --weights 0.3 0.4 0.2 0.1
```

### inference
Run Cosmos Transfer inference with optional upscaling.

```bash
cosmos inference SPEC_FILE [OPTIONS]
```

**Arguments:**
- `SPEC_FILE`: Path to prompt or run specification JSON

**Options:**
- `--videos-dir`: Custom videos directory
- `--upscale/--no-upscale`: Enable/disable 4K upscaling (default: enabled)
- `--upscale-weight`: Control weight for upscaling (0.0-1.0)
- `--dry-run`: Preview without executing

**Example:**
```bash
cosmos inference prompt_spec.json              # Inference + upscaling
cosmos inference prompt_spec.json --no-upscale # Inference only
cosmos inference prompt_spec.json --upscale-weight 0.7
```

### prompt-enhance
Enhance prompts using Pixtral AI model.

```bash
cosmos prompt-enhance PROMPT_SPECS... [OPTIONS]
```

**Arguments:**
- `PROMPT_SPECS`: One or more prompt specification JSON files

**Options:**
- `--resolution`: Max resolution for preprocessing (e.g., 480)
- `--dry-run`: Preview without calling AI API

**Example:**
```bash
cosmos prompt-enhance prompt_spec.json
cosmos prompt-enhance spec1.json spec2.json spec3.json
cosmos prompt-enhance inputs/prompts/*.json --resolution 480
```

### prepare
Prepare renders for Cosmos inference.

```bash
cosmos prepare INPUT_DIR [OPTIONS]
```

**Arguments:**
- `INPUT_DIR`: Directory with control modality PNGs

**Options:**
- `--name`: Name for output (AI-generated if not provided)
- `--fps`: Frame rate for videos (default: 24)
- `--description`: Optional description
- `--use-ai`: Use AI for descriptions (default: True)

**Example:**
```bash
cosmos prepare ./cosmos_sequences/ --name "urban_scene" --fps 24
```

### status
Check remote GPU instance status or stream container logs.

```bash
cosmos status [OPTIONS]
```

**Options:**
- `--stream`: Stream container logs in real-time instead of showing status

**Examples:**
```bash
cosmos status                  # Show GPU instance status
cosmos status --stream          # Stream logs from most recent container
```

When using `--stream`:
- Auto-detects the most recent Docker container
- Streams logs in real-time until interrupted with Ctrl+C
- Shows helpful error messages if no containers are running

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

# Download a single file
file_transfer.download_file(
    remote_file="/remote/path/to/file.mp4",
    local_file="local/path/to/file.mp4"
)

# Download results
file_transfer.download_results(Path("prompt.json"))
```

**Methods:**
- `upload_for_inference()`: Upload prompt and videos
- `download_file()`: Download a single file from remote
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

# Stream container logs
docker_executor.stream_container_logs()  # Auto-detect latest container
docker_executor.stream_container_logs(container_id="abc123")  # Specific container
```

**Methods:**
- `run_inference()`: Execute inference pipeline
- `run_upscaling()`: Execute upscaling pipeline
- `get_docker_status()`: Check Docker status
- `cleanup_containers()`: Clean up stopped containers
- `stream_container_logs(container_id=None)`: Stream container logs in real-time
  - Auto-detects most recent container if ID not provided
  - Gracefully handles Ctrl+C interruption
  - Uses 24-hour timeout for long-running streams

## Schemas

### PromptSpecManager
Manages creation, validation, and file operations for PromptSpec objects.

```python
from cosmos_workflow.prompts.prompt_spec_manager import PromptSpecManager
from cosmos_workflow.prompts.schemas import DirectoryManager

# Initialize with directory manager
dir_manager = DirectoryManager(prompts_dir, runs_dir)
spec_manager = PromptSpecManager(dir_manager)

# Create a prompt spec with automatic smart naming
spec = spec_manager.create_prompt_spec(
    prompt_text="A futuristic city with neon lights",
    input_video_path="inputs/videos/city.mp4",
    control_inputs={
        "vis": "path/to/vis",
        "edge": "path/to/edge",
        "depth": "path/to/depth",
        "seg": "path/to/seg"
    }
)
# Automatically saved with smart name: "futuristic_city_neon"

# Create enhanced prompt (from upsampling)
enhanced_spec = spec_manager.create_prompt_spec(
    prompt_text="A breathtaking futuristic metropolis bathed in vibrant neon",
    input_video_path="inputs/videos/city.mp4",
    control_inputs=control_inputs,
    is_upsampled=True,
    parent_prompt_text="A futuristic city with neon lights"
)
# Smart name generated from content: "breathtaking_metropolis"
```

**Key Features:**
- Automatic smart name generation from prompt content
- Consistent ID generation using SchemaUtils
- Automatic file saving to proper directory structure
- Support for upsampled/enhanced prompts with parent tracking
- Centralized API for all prompt spec creation

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

## File Naming Conventions

### PromptSpec Files
PromptSpec files are saved with a standardized naming format for easy identification and sorting.

**Format:** `{name}_{date}_{time}-{milliseconds}.json`
- `name`: Sanitized prompt name (alphanumeric and underscores only)
- `date`: Date in `YYYY-MM-DD` format
- `time`: Time in `HH-MM-SS` format
- `milliseconds`: 3-digit milliseconds for uniqueness

**Example:** `golden_hour_warmth_2025-09-03_07-55-25-548.json`

**Directory Structure:** `inputs/prompts/YYYY-MM-DD/`

### RunSpec Files
RunSpec files follow the same naming convention as PromptSpec files.

**Format:** `{name}_{date}_{time}-{milliseconds}.json`

**Example:** `test_run_2025-09-03_10-30-45-567.json`

**Directory Structure:** `inputs/runs/YYYY-MM-DD/`

### Internal ID Format
While filenames use the above format, internally the specs maintain unique IDs:
- **PromptSpec ID:** `ps_{hash}` - 12-character hash based on content
- **RunSpec ID:** `rs_{hash}` - 12-character hash based on content
- **RunSpec.prompt_id:** References the PromptSpec ID (e.g., `ps_c2e9e46032bf`)

These IDs are stored in the JSON file's `id` field and used for cross-referencing between specs.

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

### Configuration File (cosmos_workflow/config/config.toml)
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

### GPU Utilities
Manage and validate GPU resources.

```python
from cosmos_workflow.utils.example_feature import format_gpu_info, validate_gpu_request

# Format GPU information for display
info = format_gpu_info(gpu_count=4, gpu_memory=16)
# Returns: "4 GPU(s) with 64GB total memory"

info = format_gpu_info(gpu_count=0, gpu_memory=0)
# Returns: "No GPUs available"

# Validate GPU request against available resources
is_valid = validate_gpu_request(requested=2, available=4)
# Returns: True (request can be fulfilled)

is_valid = validate_gpu_request(requested=8, available=4)
# Returns: False (not enough GPUs)
```

### SmartNaming
Generate intelligent names from descriptions using semantic keyword extraction.

**Features:**
- Uses KeyBERT with SBERT embeddings for semantic understanding
- Extracts up to 3 most relevant keywords/phrases
- Filters common English and VFX-specific stopwords
- Falls back to simple extraction when KeyBERT unavailable

```python
from cosmos_workflow.utils.smart_naming import generate_smart_name

name = generate_smart_name(
    "A beautiful sunset over the ocean with waves",
    max_length=50
)
# Returns: "sunset_ocean_waves"

# More examples:
generate_smart_name("Low-lying mist with gradual falloff")
# Returns: "low_lying_mist"

generate_smart_name("Golden hour light creating long shadows")
# Returns: "golden_hour_shadows"
```

**Dependencies:**
- keybert>=0.8.0
- sentence-transformers>=2.2.0 (for SBERT model)


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
cosmos status --verbose
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

1. **Use Multiple GPUs**: Currently limited to single GPU
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
cosmos status

# Clean up containers manually via SSH
ssh user@host "docker container prune -f"
```

### File Transfer Issues
```python
# Verify remote directory exists
exists = file_transfer.file_exists_remote("/path/to/dir")

# List remote contents
files = file_transfer.list_remote_directory("/path")
```
