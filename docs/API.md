# API Reference

Complete API documentation for the Cosmos Workflow System.

## Table of Contents
- [CLI Commands](#cli-commands)
- [Core Modules](#core-modules)
- [Schemas](#schemas)
- [Configuration](#configuration)
- [Utilities](#utilities)

## CLI Commands

**Service Layer Architecture - Production Ready**

The Cosmos Workflow System uses a clean database-first service layer architecture:

- **Database-First Design**: All data stored in SQLAlchemy database with no persistent JSON files
- **Database IDs**: Commands work with database IDs (ps_xxxxx for prompts, rs_xxxxx for runs)
- **Service Layer**: WorkflowService handles all business logic and data operations
- **Execution Layer**: WorkflowOrchestrator handles ONLY GPU execution (inference, upscaling, AI enhancement)
- **Temporary JSON**: NVIDIA-format JSON files created only temporarily for GPU script compatibility
- **Transaction Safety**: Comprehensive error handling with automatic rollback
- **Multi-Model Ready**: Extensible design supports current transfer model and future AI models

This architecture provides excellent data consistency, enables analytics dashboards, and maintains clean separation between data management and GPU execution. The system is production-ready with 453 passing tests.

### create prompt
Create a new prompt in the database.

```bash
cosmos create prompt "PROMPT_TEXT" VIDEO_DIR [OPTIONS]
```

**Arguments:**
- `PROMPT_TEXT`: Text prompt for generation
- `VIDEO_DIR`: Directory containing video files (color.mp4, depth.mp4, segmentation.mp4)

**Options:**
- `-n, --name`: Name for the prompt (auto-generated from content if not provided)
- `--negative`: Negative prompt for quality improvement (has comprehensive default)

**Database-First Architecture:**
- Creates prompt directly in SQLAlchemy database with generated ID (ps_xxxxx)
- All data persisted in database - no JSON file management
- Returns prompt ID for use with other commands and tracking
- Smart name generation using KeyBERT semantic analysis
- Extensible JSON columns support multiple AI model types

**Example:**
```bash
cosmos create prompt "A futuristic city at night" inputs/videos/scene1
# Returns: Created prompt ps_a1b2c3 with name "futuristic_city_night"

cosmos create prompt "Transform to anime style" /path/to/video_dir --name "anime_transform"
# Returns: Created prompt ps_d4e5f6 with name "anime_transform"
```

### create run
Create a run in the database from a prompt ID.

```bash
cosmos create run PROMPT_ID [OPTIONS]
```

**Arguments:**
- `PROMPT_ID`: Database ID of existing prompt (ps_xxxxx format)

**Options:**
- `--weights`: Control weights (4 values: vis edge depth segmentation)
- `--num-steps`: Number of inference steps (default: 35)
- `--guidance-scale`: CFG guidance scale (default: 8.0)
- `--output-path`: Custom output path

**Database-First Architecture:**
- Works with prompt IDs from database, not JSON files
- Creates run directly in database with UUID-based ID (rs_xxxxx)
- Links run to existing prompt via foreign key relationship
- Stores execution configuration in database for analytics and tracking
- Run lifecycle tracked: pending → running → completed/failed

**Example:**
```bash
cosmos create run ps_a1b2c3 --weights 0.3 0.4 0.2 0.1
# Returns: Created run rs_x9y8z7 for prompt ps_a1b2c3

cosmos create run ps_d4e5f6 --num-steps 50 --guidance-scale 10.0
# Returns: Created run rs_m5n4o3 for prompt ps_d4e5f6
```

### inference
Run Cosmos Transfer inference with optional upscaling using database IDs.

```bash
cosmos inference RUN_ID [OPTIONS]
```

**Arguments:**
- `RUN_ID`: Database ID of run to execute (rs_xxxxx format)

**Options:**
- `--upscale/--no-upscale`: Enable/disable 4K upscaling (default: enabled)
- `--upscale-weight`: Control weight for upscaling (0.0-1.0, default: 0.5)
- `--dry-run`: Preview without executing

**Database-First Execution:**
- Works with run IDs from database, not JSON files
- Retrieves run and linked prompt data automatically via WorkflowService
- Updates run status in real-time: pending → running → completed/failed
- Creates temporary NVIDIA-format JSON only for GPU script compatibility
- All execution results stored back in database for persistence and analytics

**Example:**
```bash
cosmos inference rs_x9y8z7                    # Inference + upscaling for run
cosmos inference rs_x9y8z7 --no-upscale       # Inference only
cosmos inference rs_x9y8z7 --upscale-weight 0.7 --dry-run  # Preview execution plan
```

### batch-inference
Run multiple Cosmos Transfer inference jobs as a batch for improved efficiency.

```bash
cosmos batch-inference RUN_ID1 RUN_ID2 RUN_ID3... [OPTIONS]
```

**Arguments:**
- `RUN_ID1 RUN_ID2 ...`: Multiple database IDs of runs to execute (rs_xxxxx format)

**Options:**
- `--batch-name`: Custom name for the batch (auto-generated if not provided)
- `--dry-run`: Preview batch execution without running on GPU

**Batch Processing Features:**
- Converts multiple runs to JSONL format for NVIDIA Cosmos Transfer batch mode
- Reduces GPU initialization overhead by keeping models in memory
- Automatic splitting of batch output folder into individual run directories
- Per-run control weight configuration with auto-generation for missing videos
- Complete batch logging and error handling with reproducibility specs

**JSONL Format:**
Each line represents one inference job with the structure:
```json
{
  "visual_input": "/path/to/video.mp4",
  "prompt": "Text prompt for generation",
  "control_overrides": {
    "vis": {"control_weight": 0.3},
    "depth": {"input_control": null, "control_weight": 0.2},
    "seg": {"input_control": "/path/segmentation.mp4", "control_weight": 0.3}
  }
}
```

**Benefits:**
- **Performance**: 40-60% faster than individual runs due to reduced model loading
- **Memory Efficiency**: Models stay loaded between jobs in the batch
- **Automatic Organization**: Each run gets its own output folder with proper naming
- **Control Flexibility**: Per-video control weights with auto-generation support

**Example:**
```bash
# Create multiple runs first
cosmos create prompt "futuristic city" inputs/videos/scene1  # → ps_abc123
cosmos create run ps_abc123                                  # → rs_xyz789
cosmos create prompt "cyberpunk street" inputs/videos/scene2 # → ps_def456
cosmos create run ps_def456                                  # → rs_uvw012

# Execute as batch
cosmos batch-inference rs_xyz789 rs_uvw012 rs_mno345
# Creates: outputs/run_rs_xyz789/, outputs/run_rs_uvw012/, outputs/run_rs_mno345/

# Custom batch name
cosmos batch-inference rs_xyz789 rs_uvw012 --batch-name "urban_scenes_batch"

# Preview batch execution
cosmos batch-inference rs_xyz789 rs_uvw012 --dry-run
```

### prompt-enhance
Enhance prompts using Pixtral AI model with database tracking.

```bash
cosmos prompt-enhance PROMPT_IDS... [OPTIONS]
```

**Arguments:**
- `PROMPT_IDS`: One or more prompt database IDs (ps_xxxxx format)

**Options:**
- `--resolution`: Max resolution for preprocessing (e.g., 480)
- `--dry-run`: Preview without calling AI API

**Database-First AI Enhancement:**
- Works with prompt IDs from database, not JSON files
- Creates new enhanced prompts in database with KeyBERT-generated smart names
- Creates enhancement runs in database to track Pixtral AI processing
- Links enhanced prompts to original prompts for traceability
- Full lifecycle tracking: pending → running → completed with enhanced results
- All AI operations treated as trackable runs in the system

**Example:**
```bash
cosmos prompt-enhance ps_a1b2c3
# Returns: Created enhanced prompt ps_g7h8i9 and enhancement run rs_j4k5l6

cosmos prompt-enhance ps_a1b2c3 ps_d4e5f6 ps_m7n8o9 --resolution 480
# Enhances multiple prompts, creates multiple enhanced prompts and runs

cosmos prompt-enhance ps_a1b2c3 --dry-run
# Preview enhancement without calling AI API or creating database entries
```

### list prompts
List all prompts in the database with optional filtering.

```bash
cosmos list prompts [OPTIONS]
```

**Options:**
- `--model [transfer|enhancement|reason|predict]` - Filter by model type
- `--limit INTEGER` - Maximum results to show (default: 50)
- `--json` - Output in JSON format instead of rich table

**Features:**
- Rich table display with colored output
- Automatic prompt text truncation for readability
- Timestamp formatting for easy reading
- Support for pagination with limit option

**Examples:**
```bash
cosmos list prompts                    # List all prompts in rich table
cosmos list prompts --model transfer   # Only transfer model prompts
cosmos list prompts --limit 10         # Show first 10 prompts
cosmos list prompts --json             # Output as JSON for scripting
```

### list runs
List all runs in the database with optional filtering.

```bash
cosmos list runs [OPTIONS]
```

**Options:**
- `--status [pending|running|completed|failed]` - Filter by run status
- `--prompt PROMPT_ID` - Filter by prompt ID
- `--limit INTEGER` - Maximum results to show (default: 50)
- `--json` - Output in JSON format

**Features:**
- Color-coded status display (green=completed, yellow=running, red=failed)
- Shows associated prompt IDs for tracking
- Timestamp formatting for easy reading
- Multiple filter combinations supported

**Examples:**
```bash
cosmos list runs                           # List all runs
cosmos list runs --status completed        # Only completed runs
cosmos list runs --prompt ps_abc123        # Runs for specific prompt
cosmos list runs --status failed --json    # Failed runs as JSON
```

### search
Search for prompts by text content.

```bash
cosmos search QUERY [OPTIONS]
```

**Arguments:**
- `QUERY`: Search text to find in prompts (case-insensitive)

**Options:**
- `--limit INTEGER` - Maximum results to show (default: 50)
- `--json` - Output in JSON format

**Features:**
- Case-insensitive full-text search
- Highlighted matches in results (yellow bold)
- Context-aware truncation around matches
- Rich table display with search result count

**Examples:**
```bash
cosmos search cyberpunk              # Find prompts containing "cyberpunk"
cosmos search "futuristic city"      # Multi-word search
cosmos search robot --limit 20       # Limit to 20 results
cosmos search anime --json           # Output as JSON
```

### show
Show detailed information about a prompt and its runs.

```bash
cosmos show PROMPT_ID [OPTIONS]
```

**Arguments:**
- `PROMPT_ID`: Database ID of prompt to show (ps_xxxxx format)

**Options:**
- `--json` - Output in JSON format

**Features:**
- Complete prompt details in formatted panel
- List of all associated runs with status
- Run duration calculation for completed runs
- Output paths for successful runs
- Rich formatting with colors and panels

**Examples:**
```bash
cosmos show ps_abc123               # Show prompt details with runs
cosmos show ps_xyz789 --json        # Output as JSON for processing
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

### WorkflowService

The WorkflowService provides the complete business logic layer for managing prompts and runs in the database. This is the core service class that handles all data operations, validation, and transaction management.

#### Query Methods

```python
from cosmos_workflow.services.workflow_service import WorkflowService

# Initialize service (used by CLI commands)
from cosmos_workflow.services.workflow_service import WorkflowService
from cosmos_workflow.database import DatabaseConnection
from cosmos_workflow.config import ConfigManager

db_connection = DatabaseConnection()
config_manager = ConfigManager()
service = WorkflowService(db_connection, config_manager)

# List prompts with optional filtering
prompts = service.list_prompts(model_type="transfer", limit=50, offset=0)
# Returns: List of prompt dictionaries

# List runs with filtering
runs = service.list_runs(status="completed", prompt_id="ps_abc123", limit=50)
# Returns: List of run dictionaries with status, outputs, timestamps

# Search prompts by text
results = service.search_prompts("cyberpunk", limit=50)
# Returns: List of matching prompts (case-insensitive search)

# Get prompt with all associated runs
details = service.get_prompt_with_runs("ps_abc123")
# Returns: Prompt dictionary with "runs" list containing all runs
```

#### Core Methods

```python
# Create a new prompt
prompt = service.create_prompt(
    model_type="transfer",
    prompt_text="A futuristic city",
    inputs={"video": "path/to/video.mp4"},
    parameters={"num_steps": 35}
)
# Returns: Dictionary with prompt data including generated ID

# Create a run from prompt
run = service.create_run(
    prompt_id="ps_abc123",
    execution_config={"weights": [0.25, 0.25, 0.25, 0.25]},
    metadata={"user": "NAT"}
)
# Returns: Dictionary with run data and generated ID

# Update run status
updated = service.update_run_status("rs_xyz789", "completed")

# Update run with outputs
updated = service.update_run("rs_xyz789",
    outputs={"video_path": "outputs/result.mp4"}
)
```

### Database System

The database system provides flexible data persistence supporting multiple AI models through extensible JSON schemas.

```python
from cosmos_workflow.database import init_database, get_database_url
from cosmos_workflow.database.connection import DatabaseConnection
from cosmos_workflow.database.models import Prompt, Run

# Initialize database with all tables
conn = init_database()

# Create a workflow
with conn.get_session() as session:
    # Create prompt for any AI model type
    prompt = Prompt(
        id="ps_example",
        model_type="transfer",  # or "reason", "predict", future models
        prompt_text="A futuristic cityscape",
        inputs={
            "video": "/inputs/cityscape.mp4",
            "depth": "/inputs/cityscape_depth.mp4"
        },
        parameters={
            "num_steps": 35,
            "cfg_scale": 7.5
        }
    )

    # Create run for execution tracking
    run = Run(
        id="rs_example",
        prompt_id=prompt.id,
        model_type="transfer",
        status="pending",
        execution_config={
            "gpu_node": "gpu-001",
            "docker_image": "cosmos:latest"
        },
        outputs={},
        run_metadata={"user": "NAT", "session": "workflow"}
    )

    session.add_all([prompt, run])
    session.commit()
```

#### DatabaseConnection
Manages secure database connections with automatic session handling.

**Methods:**
- `create_tables()`: Create all database tables
- `get_session()`: Context manager for database sessions with auto-rollback
- `close()`: Close database connection

**Security Features:**
- Path traversal protection for database URLs
- Input validation for all operations
- Automatic transaction rollback on exceptions

#### Database Models

**Prompt Model:**
- Flexible schema supporting multiple AI models (transfer, reason, predict)
- JSON columns for model-specific inputs and parameters
- Built-in validation for required fields and data integrity

**Run Model:**
- Execution lifecycle tracking (pending → uploading → running → downloading → completed/failed)
- JSON storage for execution configuration and outputs
- Automatic timestamp management for audit trail


#### Helper Functions

```python
# Get database URL from environment or default
database_url = get_database_url()

# Initialize with custom URL
conn = init_database("/custom/path/cosmos.db")

# Environment configuration
os.environ["COSMOS_DATABASE_URL"] = ":memory:"  # For testing
```

**Features:**
- Environment-based configuration via `COSMOS_DATABASE_URL`
- Automatic directory creation for file-based databases
- In-memory database support for testing
- Comprehensive error handling and validation

See [docs/DATABASE.md](docs/DATABASE.md) for detailed documentation.

### WorkflowService

The service layer provides business logic for managing prompts and runs with transaction safety and comprehensive validation.

```python
from cosmos_workflow.services import WorkflowService
from cosmos_workflow.database import DatabaseConnection
from cosmos_workflow.config import ConfigManager

# Initialize service
db_connection = DatabaseConnection(":memory:")
db_connection.create_tables()
config_manager = ConfigManager()
service = WorkflowService(db_connection, config_manager)

# Create prompts for any AI model
prompt_data = service.create_prompt(
    model_type="transfer",  # or "reason", "predict", future models
    prompt_text="A futuristic cityscape at night",
    inputs={
        "video_path": "/inputs/scene.mp4",
        "depth_path": "/inputs/scene_depth.mp4"
    },
    parameters={
        "num_steps": 35,
        "guidance_scale": 7.5,
        "cfg_scale": 8.0
    }
)
# Returns: {"id": "ps_abcd1234", "model_type": "transfer", ...}

# Create execution runs
run_data = service.create_run(
    prompt_id=prompt_data["id"],
    execution_config={
        "gpu_node": "gpu-001",
        "docker_image": "cosmos:latest",
        "output_dir": "/outputs/run_001"
    },
    metadata={"user": "NAT", "priority": "high"},
    initial_status="pending"  # or "queued", "running", etc.
)
# Returns: {"id": "rs_wxyz5678", "prompt_id": "ps_abcd1234", ...}

# Retrieve entities
prompt = service.get_prompt("ps_abcd1234")
run = service.get_run("rs_wxyz5678")
```

**Methods:**

- `create_prompt(model_type, prompt_text, inputs, parameters)`: Create AI model prompts
  - Validates model_type against supported types: "transfer", "reason", "predict"
  - Enforces maximum prompt_text length of 10,000 characters
  - Sanitizes input text by removing null bytes and control characters
  - Validates required fields and JSON structure
  - Returns dictionary optimized for CLI display
  - Generates deterministic IDs based on content hash

- `create_run(prompt_id, execution_config, metadata=None, initial_status="pending")`: Create execution runs
  - Links to existing prompts with foreign key validation
  - Raises PromptNotFoundError if prompt doesn't exist
  - Configurable initial status for workflow control (default: "pending")
  - Generates unique IDs using UUID4 to prevent collisions
  - Flexible execution configuration via JSON
  - Optional metadata for user tracking and priority

- `get_prompt(prompt_id)`: Retrieve prompts by ID
  - Returns dictionary representation or None if not found
  - Includes all fields: id, model_type, prompt_text, inputs, parameters, created_at

- `get_run(run_id)`: Retrieve runs by ID
  - Returns dictionary with all run data including optional timestamps
  - Fields: id, prompt_id, model_type, status, execution_config, outputs, metadata
  - Includes created_at, updated_at, started_at, completed_at when available

**Features:**
- Transaction safety with flush/commit pattern for data consistency
- Comprehensive input validation including model type and text length checks
- Input sanitization to prevent security issues
- Dictionary returns optimized for CLI display (not raw ORM objects)
- Support for flexible JSON fields enabling future model extensibility
- Deterministic prompt ID generation, UUID-based run ID generation
- Configurable initial status for runs enabling queue management
- Parameterized logging throughout for debugging and audit trails

**Error Handling:**
- Validates all required parameters with clear error messages
- Enforces supported model types ("transfer", "reason", "predict")
- Raises custom PromptNotFoundError when prompt references don't exist
- Handles database connection failures with automatic rollback
- Returns None for not-found entities in get operations
- Input length validation (max 10,000 chars for prompt_text)
- Null byte and control character sanitization

### WorkflowOperations
Unified interface for all workflow operations, combining service and orchestrator functionality into high-level operations.

```python
from cosmos_workflow.api.workflow_operations import WorkflowOperations

# Initialize operations (auto-creates service and orchestrator)
ops = WorkflowOperations()

# Primary inference method - accepts prompt_id directly
result = ops.quick_inference(
    prompt_id="ps_abc123",
    weights={"vis": 0.3, "edge": 0.4, "depth": 0.2, "seg": 0.1},
    num_steps=35,
    guidance=7.0,
    upscale=True,
    upscale_weight=0.5
)
# Returns: {"run_id": "rs_xyz789", "output_path": "/outputs/result.mp4", "status": "success"}

# Batch inference method - accepts list of prompt_ids
batch_result = ops.batch_inference(
    prompt_ids=["ps_abc123", "ps_def456", "ps_ghi789"],
    shared_weights={"vis": 0.4, "edge": 0.3, "depth": 0.2, "seg": 0.1},
    num_steps=50,
    guidance=8.0
)
# Returns: {"output_mapping": {...}, "successful": 3, "failed": 0}

# Create prompt (same as WorkflowService)
prompt = ops.create_prompt(
    prompt_text="A futuristic city",
    video_dir="inputs/videos/scene1",
    name="futuristic_city"
)
# Returns: {"id": "ps_abc123", ...}
```

**Primary Methods (What Most Users Should Use):**
- `quick_inference(prompt_id, weights=None, **kwargs)`: Main inference method
  - Accepts prompt_id directly, creates run internally
  - Supports all execution parameters (num_steps, guidance, seed, upscale, etc.)
  - Returns execution results with run_id for tracking

- `batch_inference(prompt_ids, shared_weights=None, **kwargs)`: Batch processing
  - Accepts list of prompt_ids, creates runs internally for each
  - Executes all runs as a batch for improved performance
  - Returns batch results with output mapping

**Low-Level Methods (For Advanced Use):**
- `create_run(prompt_id, weights=None, num_steps=35, **kwargs)`: Explicit run creation
  - For workflows that need control over run creation timing
  - Returns run dictionary with generated ID

- `execute_run(run_id, upscale=False, upscale_weight=0.5)`: Explicit run execution
  - For workflows that need control over execution timing
  - Returns execution results

**Convenience Methods:**
- `create_and_run(prompt_text, video_dir, **kwargs)`: Complete workflow in one call
- `enhance_prompt(prompt_id, create_new=True)`: AI-powered prompt enhancement
- `list_prompts(**kwargs)`, `list_runs(**kwargs)`: Query methods
- `get_prompt(prompt_id)`, `get_run(run_id)`: Retrieve methods
- `search_prompts(query, limit=50)`: Full-text search

**Design Principles:**
- **User-Focused**: Primary methods match common workflows (create prompt → run inference)
- **Intelligent Defaults**: Sensible defaults for weights, steps, guidance, etc.
- **Internal Run Management**: Users work with prompt_ids, runs created automatically
- **Backward Compatible**: Low-level methods remain available for advanced workflows
- **Single Interface**: Combines WorkflowService and WorkflowOrchestrator capabilities

### WorkflowOrchestrator
Simplified orchestrator handling ONLY GPU execution (no data persistence).

```python
from cosmos_workflow.workflows.workflow_orchestrator import WorkflowOrchestrator

orchestrator = WorkflowOrchestrator()

# Execute a run from database data
result = orchestrator.execute_run(
    run_dict={"id": "rs_abc123", "execution_config": {"weights": [0.3, 0.4, 0.2, 0.1]}},
    prompt_dict={"id": "ps_def456", "prompt_text": "A futuristic city", "inputs": {"video": "/path/to/video"}},
    upscale=True,
    upscale_weight=0.5
)
# Returns: {"status": "completed", "output_path": "/outputs/result.mp4", "duration": 362.1}

# Execute multiple runs as a batch
batch_result = orchestrator.execute_batch_runs(
    runs_and_prompts=[
        ({"id": "rs_abc123", "execution_config": {"weights": [0.3, 0.4, 0.2, 0.1]}},
         {"id": "ps_def456", "prompt_text": "A futuristic city", "inputs": {"video": "/path/video1.mp4"}}),
        ({"id": "rs_xyz789", "execution_config": {"weights": [0.4, 0.3, 0.2, 0.1]}},
         {"id": "ps_ghi012", "prompt_text": "Cyberpunk street", "inputs": {"video": "/path/video2.mp4"}})
    ],
    batch_name="urban_scenes_batch"
)
# Returns: {"status": "success", "batch_name": "urban_scenes_batch", "output_mapping": {...}, "duration_seconds": 456.7}

# Enhance prompt text with Pixtral AI
enhanced_text = orchestrator.run_prompt_upsampling("A simple city scene")
# Returns: "A breathtaking futuristic metropolis with gleaming skyscrapers and neon lights"
```

**Core Methods:**
- `execute_run(run_dict, prompt_dict, upscale=True, upscale_weight=0.5)`: Execute complete GPU workflow
  - Converts database dictionaries to NVIDIA Cosmos format
  - Creates temporary JSON files for GPU scripts
  - Handles SSH connection, file upload, Docker execution, result download
  - Returns execution results for WorkflowService to persist

- `execute_batch_runs(runs_and_prompts, batch_name=None)`: Execute multiple runs as a batch
  - Converts run/prompt pairs to JSONL format using `nvidia_format.to_cosmos_batch_inference_jsonl()`
  - Uploads JSONL file and all referenced videos to remote GPU server
  - Executes batch inference using `scripts/batch_inference.sh`
  - Automatically splits batch outputs into individual run folders
  - Downloads all outputs and organizes them locally
  - Returns batch execution summary with output mapping

- `run_prompt_upsampling(prompt_text)`: AI-powered prompt enhancement
  - Uses Pixtral vision-language model for prompt improvement
  - Returns enhanced text for WorkflowService to create new prompt

- `check_remote_status()`: Check remote GPU system health and container status

**Architecture Principles:**
- **Pure Execution Layer**: No data persistence or business logic
- **Stateless**: Takes input dictionaries, returns result dictionaries
- **NVIDIA Compatible**: Creates temporary JSON in required format for GPU scripts
- **Clean Separation**: Data operations handled entirely by WorkflowService
- **Error Handling**: Returns error status in result dictionary for service layer processing

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
Handles file transfers via SFTP with automatic format conversion.

```python
from cosmos_workflow.transfer.file_transfer import FileTransferService

file_transfer = FileTransferService(ssh_manager, remote_dir)

# Upload files for inference (automatically converts to NVIDIA Cosmos format)
file_transfer.upload_prompt_and_videos(
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
- `upload_prompt_and_videos()`: Upload prompt and videos with automatic PromptSpec to NVIDIA Cosmos format conversion
- `download_file()`: Download a single file from remote
- `download_results()`: Download generated outputs

**Features:**
- Automatic conversion from PromptSpec to NVIDIA Cosmos Transfer format during upload
- Path separator conversion from Windows to Unix for cross-platform compatibility
- Fallback to original format if conversion fails
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

# Run batch inference
batch_result = docker_executor.run_batch_inference(
    batch_name="urban_scenes_batch_20241206_123456",
    batch_jsonl_file="urban_scenes_batch_20241206_123456.jsonl",
    num_gpu=1,
    cuda_devices="0"
)
# Returns: {"batch_name": "urban_scenes_batch_20241206_123456", "output_dir": "/remote/outputs/batch_name", "output_files": [...]}

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
- `run_batch_inference(batch_name, batch_jsonl_file, num_gpu=1, cuda_devices="0")`: Execute batch inference
  - Executes multiple inference jobs from JSONL file using `scripts/batch_inference.sh`
  - Creates batch output directory on remote server
  - Validates JSONL file exists before execution
  - Returns batch execution results with output file list
  - Handles Docker container orchestration for batch processing
- `run_upscaling()`: Execute upscaling pipeline
- `get_docker_status()`: Check Docker status
- `cleanup_containers()`: Clean up stopped containers
- `stream_container_logs(container_id=None)`: Stream container logs in real-time
  - Auto-detects most recent container if ID not provided
  - Gracefully handles Ctrl+C interruption
  - Uses 24-hour timeout for long-running streams

## Database Schema

The system uses SQLAlchemy database models instead of JSON file schemas. All data is stored in the database with flexible JSON columns for extensibility.

### Prompt Model
Database model for storing AI prompts with flexible JSON columns.

```python
from cosmos_workflow.database.models import Prompt
from datetime import datetime, timezone

# Create prompt via WorkflowService (recommended)
service = WorkflowService(db_connection, config_manager)
prompt_data = service.create_prompt(
    model_type="transfer",
    prompt_text="A futuristic city with neon lights",
    inputs={
        "video": "inputs/videos/city.mp4",
        "depth": "inputs/videos/city_depth.mp4",
        "segmentation": "inputs/videos/city_seg.mp4"
    },
    parameters={
        "negative_prompt": "blurry, low quality, distorted",
        "num_steps": 35,
        "guidance_scale": 8.0
    }
)
# Returns: {"id": "ps_abc123", "model_type": "transfer", "created_at": "...", ...}
```

**Database Fields:**
- `id`: Database primary key (ps_xxxxx format)
- `model_type`: AI model type ("transfer", "enhancement", "reason", "predict")
- `prompt_text`: Main generation prompt text
- `inputs`: JSON column for model-specific inputs (videos, images, etc.)
- `parameters`: JSON column for model-specific parameters
- `created_at`: Timestamp of creation

### Run Model
Database model for tracking execution runs with complete lifecycle management.

```python
from cosmos_workflow.database.models import Run

# Create run via WorkflowService (recommended)
run_data = service.create_run(
    prompt_id="ps_abc123",
    execution_config={
        "weights": [0.3, 0.4, 0.2, 0.1],  # vis, edge, depth, segmentation
        "num_steps": 50,
        "guidance_scale": 10.0,
        "upscale": True,
        "upscale_weight": 0.5
    },
    metadata={"user": "NAT", "priority": "high"}
)
# Returns: {"id": "rs_xyz789", "prompt_id": "ps_abc123", "status": "pending", ...}

# Update run status (done automatically by WorkflowOrchestrator)
service.update_run_status("rs_xyz789", "completed")
service.update_run("rs_xyz789", outputs={"video_path": "/outputs/result.mp4"})
```

**Database Fields:**
- `id`: Database primary key (rs_xxxxx format)
- `prompt_id`: Foreign key reference to Prompt model
- `model_type`: AI model type (inherited from linked prompt)
- `status`: Current execution status ("pending", "running", "completed", "failed")
- `execution_config`: JSON column for run-specific configuration
- `outputs`: JSON column for execution results and output paths
- `run_metadata`: JSON column for additional metadata
- `created_at`, `updated_at`, `started_at`, `completed_at`: Lifecycle timestamps


## Database ID Format

### ID Generation Strategy
The system uses deterministic and UUID-based ID generation for database entities:

**Prompt IDs:** `ps_{hash}` format
- Generated deterministically based on prompt content
- Example: `ps_a1b2c3d4` (content-based hash ensures uniqueness)
- Allows duplicate detection and consistent references

**Run IDs:** `rs_{uuid}` format
- Generated using UUID4 for guaranteed uniqueness
- Example: `rs_x9y8z7w6` (random UUID prevents collisions)
- Each run gets a unique ID regardless of configuration

### Database Relationships
```sql
-- Prompts table
CREATE TABLE prompts (
    id VARCHAR PRIMARY KEY,           -- ps_xxxxx format
    model_type VARCHAR NOT NULL,      -- "transfer", "enhancement", etc.
    prompt_text TEXT NOT NULL,
    inputs JSON,                      -- Model-specific inputs
    parameters JSON,                  -- Model-specific parameters
    created_at TIMESTAMP DEFAULT NOW()
);

-- Runs table with foreign key to prompts
CREATE TABLE runs (
    id VARCHAR PRIMARY KEY,           -- rs_xxxxx format
    prompt_id VARCHAR REFERENCES prompts(id),
    model_type VARCHAR NOT NULL,
    status VARCHAR NOT NULL,          -- "pending", "running", "completed", "failed"
    execution_config JSON,            -- Run-specific configuration
    outputs JSON,                     -- Execution results
    run_metadata JSON,                -- Additional metadata
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);
```

### No File Management
- **No JSON files**: All data stored in database, JSON only created temporarily for GPU scripts
- **No directory structure**: Database provides organization and querying
- **Easy relationships**: Foreign keys link runs to prompts automatically
- **Analytics ready**: SQL queries enable dashboard creation and usage analytics

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

### NVIDIA Format Utilities
Convert database formats to NVIDIA Cosmos Transfer compatible formats.

```python
from cosmos_workflow.utils.nvidia_format import (
    to_cosmos_inference_json,
    to_cosmos_batch_inference_jsonl,
    write_batch_jsonl,
    write_cosmos_json
)

# Convert single run to NVIDIA Cosmos inference format
cosmos_json = to_cosmos_inference_json(
    prompt_dict={"prompt_text": "A futuristic city", "inputs": {"video": "/path/video.mp4"}},
    run_dict={"execution_config": {"weights": {"vis": 0.3, "edge": 0.4, "depth": 0.2, "seg": 0.1}}}
)
# Returns: {"prompt": "A futuristic city", "input_video_path": "/path/video.mp4", "vis": {"control_weight": 0.3}, ...}

# Convert multiple runs to JSONL format for batch processing
runs_and_prompts = [
    ({"execution_config": {"weights": {"vis": 0.3, "depth": 0.2}}}, {"prompt_text": "City scene", "inputs": {"video": "video1.mp4"}}),
    ({"execution_config": {"weights": {"vis": 0.4, "seg": 0.3}}}, {"prompt_text": "Street view", "inputs": {"video": "video2.mp4"}})
]
batch_jsonl = to_cosmos_batch_inference_jsonl(runs_and_prompts)
# Returns: [
#   {"visual_input": "video1.mp4", "prompt": "City scene", "control_overrides": {"vis": {"control_weight": 0.3}, "depth": {"input_control": null, "control_weight": 0.2}}},
#   {"visual_input": "video2.mp4", "prompt": "Street view", "control_overrides": {"vis": {"control_weight": 0.4}, "seg": {"input_control": null, "control_weight": 0.3}}}
# ]

# Write JSONL to file
jsonl_path = write_batch_jsonl(batch_jsonl, "batch_data.jsonl")
# Creates JSONL file with one JSON object per line, removes internal metadata fields

# Write single Cosmos JSON to file
json_path = write_cosmos_json(cosmos_json, "inference_spec.json")
# Creates formatted JSON file for single inference
```

**Functions:**
- `to_cosmos_inference_json(prompt_dict, run_dict)`: Convert database dicts to NVIDIA inference format
  - Maps `prompt_text` → `prompt`, handles control weights, converts Windows paths to Unix
  - Only includes controls with weight > 0 for efficiency
  - Adds default negative prompt if none provided

- `to_cosmos_batch_inference_jsonl(runs_and_prompts)`: Convert multiple runs to JSONL format
  - Each line represents one inference job with visual_input, prompt, and control_overrides
  - Supports per-video control settings with auto-generation (null input_control)
  - Includes metadata fields for tracking (removed when writing to file)

- `write_batch_jsonl(batch_data, output_path)`: Write JSONL data to file
  - One JSON object per line, creates parent directories if needed
  - Removes internal metadata fields starting with underscore

- `write_cosmos_json(cosmos_data, output_path)`: Write single JSON to file
  - Formatted JSON with proper indentation, creates parent directories

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
