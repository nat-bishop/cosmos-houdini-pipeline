# API Reference

## Recent Updates (2025-01-19)

### Batch Inference Improvements

The batch inference system has been significantly enhanced with several critical fixes:

#### Fixed Issues
- **Script Compatibility**: Resolved CRLF/LF line ending issues on Windows that caused "No such file or directory" errors
- **Parameter Requirements**: Added required `--controlnet_specs` parameter with base specification for NVIDIA batch inference
- **Output Structure**: Fixed batch output handling to properly process video_X subdirectory structure
- **File Naming**: Updated control file handling to support _0 suffix naming convention from batch operations
- **Logging**: Corrected log path handling to use shared batch logs instead of individual run logs

#### Technical Implementation
```
# Batch inference now properly handles output structure
outputs/batch_xxx/
├── video_0/
│   ├── output.mp4          # Main output video
│   ├── depth_input_control_0.mp4   # Generated depth control
│   ├── edge_input_control_0.mp4    # Generated edge control
│   └── seg_input_control_0.mp4     # Generated segmentation control
├── video_1/
│   └── ...
└── execution.log           # Shared batch log
```

### Enhancement System Fixes

The prompt enhancement system has been stabilized with these critical fixes:

#### Threading and Connection Issues
- **Removed Thread-Local Storage**: Eliminated incorrect thread-local implementation in legacy QueueService that caused SSH connection failures
- **Connection Stability**: Enhanced SSH connection management for long-running enhancement operations
- **Message Filtering**: Fixed legacy queue service spamming "GPU busy" messages during operations

#### Duplicate Creation Prevention
```python
# Fixed duplicate prompt creation in enhancement workflow
def enhance_prompt(self, prompt_id, create_new=True, force_overwrite=False):
    # Now properly handles status validation
    if status not in ["started", "completed"]:
        raise ValueError(f"Unexpected enhancement status: {status}")
    # Prevents duplicate prompt creation
    if create_new and not force_overwrite:
        # Validates before creation
```

#### Error Handling Improvements
- **Status Validation**: Now only accepts "started" or "completed" status from execute_enhancement_run
- **Fast Failure**: Fails immediately on unexpected status instead of attempting recovery
- **Legacy Code Removal**: Cleaned up deprecated code paths that caused inconsistent behavior

### UI Filter Enhancement

Added new "Run Status" filter in Prompts tab for improved workflow management:

#### Filter Options
- **All**: Shows all prompts regardless of run status
- **No Runs**: Shows only prompts that haven't been used for inference yet
- **Has Runs**: Shows only prompts that have associated inference runs

#### Implementation Details
```python
# Filter logic for run status
def filter_prompts_by_run_status(prompts, run_status_filter):
    if run_status_filter == "No Runs":
        return [p for p in prompts if not p.get("run_count", 0)]
    elif run_status_filter == "Has Runs":
        return [p for p in prompts if p.get("run_count", 0) > 0]
    else:  # "All"
        return prompts
```

## Smart Batching System (2025-09-25)

### Overview

The Smart Batching system is an overlay optimization for the existing queue system that provides **2-5x performance improvements** through intelligent job grouping and batching. It operates as a non-invasive enhancement that requires the queue to be paused before analysis and execution.

### Key Features

- **Two Batching Modes**: Strict (identical controls only) and Mixed (master batch approach)
- **Conservative Memory Management**: Batch sizing based on control count to prevent GPU OOM errors
- **Zero Impact When Not Used**: Non-invasive overlay design with no effect on normal queue operations
- **Comprehensive Analysis**: Efficiency calculations with estimated speedup metrics
- **Atomic Execution**: Database-consistent batch execution with proper job lifecycle management

### Smart Batching API Methods

#### SimplifiedQueueService Smart Batching Methods

**`analyze_queue_for_smart_batching(mix_controls: bool = False) -> dict[str, Any] | None`**

Analyzes queued jobs for batching opportunities.

**Parameters:**
- `mix_controls`: If True, use mixed mode (master batch approach). If False, use strict mode (identical controls only).

**Returns:**
- Analysis dictionary with batches and efficiency metrics, or None if no batchable jobs found.

**Example:**
```python
queue_service = SimplifiedQueueService()
analysis = queue_service.analyze_queue_for_smart_batching(mix_controls=False)
if analysis:
    print(f"Estimated speedup: {analysis['efficiency']['estimated_speedup']:.1f}x")
    print(f"Jobs: {analysis['efficiency']['job_count_before']} → {analysis['efficiency']['job_count_after']} batches")
```

**`execute_smart_batches() -> dict[str, Any]`**

Executes the stored smart batch analysis with atomic job management.

**Returns:**
- Results dictionary with execution status, job counts, and speedup metrics.

**Example:**
```python
# Must analyze first, then execute
analysis = queue_service.analyze_queue_for_smart_batching()
if analysis:
    results = queue_service.execute_smart_batches()
    print(f"Executed {results['jobs_executed']} jobs in {results['batches_created']} batches")
    print(f"Achieved {results['speedup']:.1f}x speedup")
```

**`get_smart_batch_preview() -> str`**

Returns human-readable preview of stored analysis.

**Returns:**
- Preview string showing batch breakdown and efficiency metrics, or empty string if no analysis.

**Example:**
```python
preview = queue_service.get_smart_batch_preview()
print(preview)  # Shows batch breakdown and estimated performance gains
```

### Core Smart Batching Algorithms

Located in `cosmos_workflow/utils/smart_batching.py`, these functions provide the core batching logic:

#### Control Signature Functions

**`get_control_signature(job_config: dict) -> tuple[str, ...]`**

Extracts sorted tuple of active controls from job configuration.

**`filter_batchable_jobs(jobs: list) -> list`**

Filters jobs to only include batchable types (inference and batch_inference).

#### Batching Algorithms

**`group_jobs_strict(jobs: list, max_batch_size: int) -> list[dict]`**

Groups jobs with identical control signatures only for maximum efficiency.

**`group_jobs_mixed(jobs: list, max_batch_size: int) -> list[dict]`**

Groups jobs allowing mixed controls using master batch approach.

#### Memory Management

**`get_safe_batch_size(num_controls: int, user_max: int = 16) -> int`**

Conservative batch sizing based on control count:
- 1 control: max 8 jobs per batch
- 2 controls: max 4 jobs per batch
- 3+ controls: max 2 jobs per batch

#### Analysis Functions

**`calculate_batch_efficiency(batches: list[dict], original_jobs: list) -> dict`**

Calculates comprehensive efficiency metrics including estimated speedup and control reduction.

### Usage Workflow

1. **Pause Queue**: Queue must be paused before analysis to ensure consistent state
2. **Analyze**: Call `analyze_queue_for_smart_batching()` to examine current jobs
3. **Preview**: Use `get_smart_batch_preview()` to review the proposed batching
4. **Execute**: Call `execute_smart_batches()` to run the optimized batches
5. **Resume**: Unpause queue to continue normal processing

### Performance Characteristics

- **Strict Mode**: Best for queues with many identical jobs (same control weights)
- **Mixed Mode**: Optimal for diverse jobs with different control combinations
- **Memory Safety**: Conservative batch sizes prevent GPU OOM based on control complexity
- **Efficiency Gains**: Typical 2-5x speedup through reduced model loading and GPU initialization overhead

### Test Coverage

The smart batching system includes comprehensive test coverage:
- **48 total tests** across unit and integration test suites
- **Core algorithm tests**: Control signature extraction, job grouping, efficiency calculations
- **Service integration tests**: Queue analysis, batch execution, error handling
- **Performance benchmarks**: Validates speedup claims in controlled scenarios
- **Memory safety tests**: Ensures conservative batch sizing prevents OOM errors

Complete API documentation for the Cosmos Workflow System.

## Table of Contents
- [System Architecture](#system-architecture)
- [CLI Commands](#cli-commands)
- [Core Modules](#core-modules)
- [Log Visualization](#log-visualization)
- [Schemas](#schemas)
- [Execution Configuration Schema](#execution-configuration-schema)
- [Configuration](#configuration)
- [Utilities](#utilities)

## System Architecture

### Overview

The Cosmos Workflow System follows a **facade pattern** with a clean, layered architecture. **CosmosAPI is the PRIMARY INTERFACE** - all external code, CLI commands, and UI interactions must go through this facade.

### Architecture Layers

```
┌─────────────────────────────────────────────────────────┐
│             External Code / CLI / UI                    │
│         ALL interactions go through the facade          │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌═════════════════════════════════════════════════════════┐
║             CosmosAPI (MAIN FACADE)                    ║
║       (cosmos_workflow/api/cosmos_api.py)               ║
║                                                          ║
║  THE PRIMARY INTERFACE - Use this for everything!       ║
║  • High-level operations matching user intentions       ║
║  • Combines database + GPU functionality                ║
║  • Single point of entry for all operations             ║
╚═════════════════════════════════════════════════════════╝
                            │
           ┌────────────────┴────────────────┐
           ▼                                 ▼
┌──────────────────────────┐    ┌────────────────────────┐
│   DataRepository         │    │     GPUExecutor        │
│   (INTERNAL - Data)      │    │  (INTERNAL - GPU Exec) │
│ (services/data_          │    │ (execution/gpu_        │
│    repository.py)        │    │    executor.py)        │
│                          │    │                        │
│ • Database CRUD          │    │ • GPU execution        │
│ • Data validation        │    │ • SSH/Docker ops       │
│ • Query operations       │    │ • File transfers       │
└──────────────────────────┘    └────────────────────────┘
            │                            │
            ▼                            ▼
┌──────────────────────────┐    ┌────────────────────────┐
│      Database            │    │    Remote GPU          │
│   (SQLAlchemy)           │    │  (SSH, Docker)         │
└──────────────────────────┘    └────────────────────────┘

* Note: Architecture has been updated with clearer names - GPUExecutor
  handles GPU operations, DataRepository handles data persistence.
```

### Layer Responsibilities

#### 1. CLI Layer (`cosmos_workflow/cli/`)
- **Purpose**: User interaction and display
- **Responsibilities**:
  - Parse command-line arguments
  - Display results to users
  - Handle user input validation
  - Format output (tables, progress bars, etc.)
- **Rules**:
  - ✅ ONLY uses `CosmosAPI` facade
  - ❌ NEVER directly imports service, database, or orchestrator modules
  - ❌ NEVER contains business logic

#### 2. CosmosAPI (`cosmos_workflow/api/cosmos_api.py`) - **MAIN FACADE**
- **Purpose**: THE PRIMARY INTERFACE for the entire system
- **Responsibilities**:
  - Provide the single point of entry for all operations
  - Combine service (database) and orchestrator (GPU) functionality
  - Provide high-level operations that match user intentions
  - Handle complex workflows (e.g., create prompt + run inference)
  - Maintain consistent API for CLI, UI, and external code
- **Rules**:
  - ✅ **THIS IS THE ONLY INTERFACE external code should use**
  - ✅ The ONLY layer that imports both Service and Orchestrator
  - ✅ All high-level business logic lives here
  - ✅ Returns simple dictionaries (no ORM objects)
  - ❌ NEVER bypass this to use DataRepository or GPUExecutor directly

#### 3. DataRepository (`cosmos_workflow/services/data_repository.py`) - **INTERNAL COMPONENT**
- **Purpose**: Internal data layer for database operations
- **Responsibilities**:
  - CRUD operations for prompts and runs
  - Data validation and integrity
  - Database queries and updates
  - Transaction management
- **Rules**:
  - ⚠️ **INTERNAL ONLY - Do not use directly, use CosmosAPI instead**
  - ✅ ONLY handles database operations
  - ❌ NO remote execution logic
  - ❌ NO file system operations (except validation)

#### 4. GPUExecutor (`cosmos_workflow/workflows/workflow_orchestrator.py`) - **INTERNAL COMPONENT**
- **Purpose**: Internal GPU execution layer (confusing name - will be renamed to GPUExecutor in v2.0)
- **Responsibilities**:
  - Execute inference on remote GPU
  - Manage SSH connections
  - Handle Docker containers
  - Transfer files to/from remote systems
  - Stream logs and monitor execution
- **Rules**:
  - ⚠️ **INTERNAL ONLY - Do not use directly, use CosmosAPI instead**
  - ⚠️ **NOT the main orchestrator despite its name - just GPU execution**
  - ✅ ONLY handles execution logic
  - ❌ NO database operations
  - ❌ Receives data from Service layer via Operations

### Usage Examples

#### Correct Usage - Through CosmosAPI

```python
from cosmos_workflow.api import CosmosAPI

# Initialize the API (this is the ONLY import you need)
ops = CosmosAPI()

# Create a prompt
prompt = ops.create_prompt(
  prompt_text="A cyberpunk city at night",
  video_dir="/path/to/videos",
  name="cyberpunk_test"
)
print(f"Created prompt: {prompt['id']}")

# Run inference (no manual run creation needed!)
result = ops.quick_inference(
  prompt_id=prompt["id"],
  weights={"vis": 0.3, "edge": 0.3, "depth": 0.2, "seg": 0.2},
  num_steps=50,
  upscale=True
)
print(f"Output: {result['output_path']}")

# Batch inference for multiple prompts
results = ops.batch_inference(
  prompt_ids=["ps_001", "ps_002", "ps_003"],
  shared_weights={"vis": 0.25, "edge": 0.25, "depth": 0.25, "seg": 0.25}
)

# List and search operations
all_prompts = ops.list_prompts(limit=10)
matching = ops.search_prompts("cyberpunk")
prompt_details = ops.get_prompt("ps_001")

# System operations
status = ops.check_status()  # Check GPU status
integrity = ops.verify_integrity()  # Verify data integrity
ops.stream_container_logs(container_id)  # Stream logs from specific container

# Cleanup
ops.delete_prompt(prompt["id"])
```

#### Incorrect Usage - Bypassing Layers

```python
# ❌ WRONG - CLI directly using Service
from cosmos_workflow.services import DataRepository

service = DataRepository()
prompt = service.create_prompt(...)  # Don't do this in CLI!

# ❌ WRONG - CLI directly using Orchestrator
from cosmos_workflow.workflows import GPUExecutor

orchestrator = GPUExecutor()
orchestrator.execute_run(...)  # Don't do this in CLI!

# ❌ WRONG - Direct database access
from cosmos_workflow.database import DatabaseConnection

db = DatabaseConnection()
db.session.query(...)  # Never do this outside Service layer!
```

### DockerCommandBuilder
Centralized Docker command construction following wrapper pattern for security and consistency.

```python
from cosmos_workflow.execution.command_builder import DockerCommandBuilder

# Build various Docker commands using static methods
logs_cmd = DockerCommandBuilder.build_logs_command("container_id", follow=True)
# Returns: "sudo docker logs -f container_id"

info_cmd = DockerCommandBuilder.build_info_command()
# Returns: "sudo docker info"

images_cmd = DockerCommandBuilder.build_images_command()
# Returns: "sudo docker images"

kill_cmd = DockerCommandBuilder.build_kill_command(["container1", "container2"])
# Returns: "sudo docker kill container1 container2"
```

**Methods:**
- `build_logs_command(container_id, follow=False)`: Construct Docker logs command with optional follow flag
- `build_info_command()`: Construct Docker system info command
- `build_images_command()`: Construct Docker images listing command
- `build_kill_command(container_ids)`: Construct Docker kill command for multiple containers

**Design Principles:**
- All Docker commands must use wrapper methods instead of raw strings
- Prevents command injection and ensures consistent error handling
- Centralizes Docker command construction for maintainability
- Required by project architecture as documented in CLAUDE.md

### CosmosAPI API Methods

#### Core Operations
- `create_prompt()` - Create a new prompt
- `enhance_prompt()` - Enhance prompt with AI (creates database run with model_type="enhance")
- `quick_inference()` - Run inference on a prompt (creates run internally)
- `batch_inference()` - Run inference on multiple prompts
- `create_and_run()` - Create prompt and run inference in one call

#### Data Operations
- `list_prompts()` - List all prompts
- `list_runs()` - List all runs
- `get_prompt()` - Get prompt details
- `get_run()` - Get run details
- `search_prompts()` - Search prompts by text
- `delete_prompt(prompt_id, keep_outputs=True)` - Delete a prompt and its runs
- `delete_run(run_id, keep_outputs=True)` - Delete a specific run
- `preview_prompt_deletion(prompt_id, keep_outputs=True)` - Preview prompt deletion
- `preview_run_deletion(run_id, keep_outputs=True)` - Preview run deletion
- `delete_all_prompts(keep_outputs=True)` - Delete all prompts and runs
- `delete_all_runs(keep_outputs=True)` - Delete all runs
- `preview_all_prompts_deletion()` - Preview bulk prompt deletion
- `preview_all_runs_deletion()` - Preview bulk run deletion

#### System Operations
- `check_status()` - Check remote GPU status with active operation details (type, run ID, prompt)
- `get_active_operations()` - Get detailed information about currently running operations
- `stream_container_logs(container_id, callback=None)` - Stream logs from Docker container (stdout for CLI, callback for Gradio)
- `verify_integrity()` - Verify database-filesystem integrity
- `kill_containers()` - Kill all running Cosmos containers on GPU instance

## CLI Commands

### Complete Command Reference

#### Database Operations
- `cosmos create prompt "text" video_dir` - Create prompt in database, returns ps_xxxxx ID
- `cosmos list prompts [--model transfer] [--limit 50] [--json]` - List prompts with filtering
- `cosmos list runs [--status completed] [--prompt ps_xxxxx] [--json]` - List runs with filtering
- `cosmos search "query" [--limit 50] [--json]` - Full-text search prompts with highlighting
- `cosmos show ps_xxxxx [--json]` - Detailed prompt view with run history

#### GPU Execution
- `cosmos inference ps_xxxxx [ps_xxx2 ...]` - Execute inference on prompts (creates runs internally, blocks until complete)
- `cosmos upscale rs_xxxxx [--weight 0.5]` - Upscale completed inference run to 4K (creates separate run, blocks until complete)
- `cosmos prompt-enhance ps_xxxxx [--resolution 480]` - AI prompt enhancement (creates new prompt, blocks until complete)
- `cosmos prepare input_dir [--name scene]` - Prepare video sequences for inference
- `cosmos status [--stream]` - Check GPU status or stream container logs
- `cosmos kill [--force]` - Kill all running Cosmos containers on GPU instance

#### System Management
- `cosmos verify [--fix]` - Verify database-filesystem integrity
- `cosmos delete prompt ps_xxxxx [--delete-outputs] [--force]` - Delete a prompt and its runs
- `cosmos delete run rs_xxxxx [--delete-outputs] [--force]` - Delete a specific run
- `cosmos delete prompt --all [--delete-outputs] [--force]` - Delete all prompts and runs
- `cosmos delete run --all [--delete-outputs] [--force]` - Delete all runs
- `cosmos ui` - Launch Gradio web interface

For shell completion setup, see [docs/SHELL_COMPLETION.md](SHELL_COMPLETION.md)

### Command Details

**Service Layer Architecture - Production Ready**

The Cosmos Workflow System uses a clean database-first service layer architecture:

- **Database-First Design**: All data stored in SQLAlchemy database with no persistent JSON files
- **Database IDs**: Commands work with database IDs (ps_xxxxx for prompts, rs_xxxxx for runs)
- **Service Layer**: DataRepository handles all business logic and data operations
- **Execution Layer**: GPUExecutor handles ONLY GPU execution (inference, upscaling, AI enhancement)
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

### inference
Run Cosmos Transfer inference with optional upscaling using prompt IDs.

```bash
cosmos inference PROMPT_ID [PROMPT_ID2 ...] [OPTIONS]
```

**Arguments:**
- `PROMPT_ID`: One or more database IDs of prompts (ps_xxxxx format)

**Options:**
- `--weights`: Control weights (4 values: vis edge depth segmentation)
- `--num-steps`: Number of inference steps (default: 35)
- `--guidance-scale`: CFG guidance scale (default: 8.0)
- `--batch-name`: Name for batch when running multiple prompts
- `--prompts-file`: File containing prompt IDs (one per line)
- `--dry-run`: Preview without executing

**Note:** Upscaling is now a separate operation. Use `cosmos upscale <run_id>` after inference completes.

**2-Step Workflow:**
- Works directly with prompt IDs - creates runs internally
- Single prompt: Uses `quick_inference()` for immediate execution
- Multiple prompts: Uses `batch_inference()` for efficient GPU utilization
- Updates run status in real-time: pending → running → completed/failed
- All execution results stored back in database for persistence and analytics

**Example:**
```bash
# Single prompt inference (upscaling now separate)
cosmos inference ps_a1b2c3                    # Inference only
cosmos inference ps_a1b2c3 --weights 0.3 0.3 0.2 0.2

# Batch inference for multiple prompts
cosmos inference ps_001 ps_002 ps_003 --batch-name "my_batch"
cosmos inference --prompts-file prompt_list.txt

# Two-step workflow: inference + upscaling
cosmos inference ps_a1b2c3                    # First: inference
cosmos upscale rs_xyz789                       # Then: upscale the result
```

**Note:** Batch inference is now integrated into the main `inference` command. Simply provide multiple prompt IDs to run them as a batch.
- **Reduced Overhead**: Single model load/unload cycle for entire batch

**JSONL Format:**
Batch inference uses JSONL (JSON Lines) format where each line represents one inference job:
```json
{"visual_input": "/path/to/video.mp4", "prompt": "Text description", "control_overrides": {"vis": {"control_weight": 0.3}}}
{"visual_input": "/path/to/video2.mp4", "prompt": "Another description", "control_overrides": {"depth": {"input_control": null, "control_weight": 0.2}}}
```

**Control Weight System:**
- `vis`: Visual control (always auto-generated), typical range: 0.2-0.4
- `edge`: Edge control (always auto-generated), typical range: 0.3-0.5
- `depth`: Depth control (provided or auto-generated), typical range: 0.1-0.3
- `seg`: Segmentation control (provided or auto-generated), typical range: 0.1-0.3

**Output Organization:**
```
outputs/
├── run_rs_xyz789/
│   ├── output.mp4           # Generated video
│   ├── execution.log        # Individual execution log
│   └── manifest.txt         # File manifest
├── run_rs_uvw012/
│   └── output.mp4
└── batch_urban_scenes_20241206_123456/
    ├── batch_spec.json      # Batch configuration
    ├── batch_run.log        # Complete batch log
    └── batch.jsonl          # Original JSONL
```

**Example Workflow:**
```bash
# Create multiple prompts
cosmos create prompt "futuristic city" inputs/videos/scene1  # → ps_abc123
cosmos create prompt "cyberpunk street" inputs/videos/scene2 # → ps_def456
cosmos create prompt "neon alley" inputs/videos/scene3       # → ps_ghi789

# Execute as batch (40% faster than individual runs)
cosmos inference ps_abc123 ps_def456 ps_ghi789 --batch-name "urban_scenes"

# Custom control weights for all prompts
cosmos inference ps_abc123 ps_def456 --weights 0.3 0.3 0.2 0.2

# Preview without execution
cosmos inference ps_abc123 ps_def456 ps_ghi789 --dry-run
```

**Performance Scaling:**
| Batch Size | Individual Time | Batch Time | Time Savings |
|------------|-----------------|------------|--------------|
| 3 runs     | 15 minutes     | 9 minutes  | 40%          |
| 5 runs     | 25 minutes     | 14 minutes | 44%          |
| 10 runs    | 50 minutes     | 28 minutes | 44%          |

### prompt-enhance
Enhance prompts using Pixtral AI model with complete database run tracking.

```bash
cosmos prompt-enhance PROMPT_IDS... [OPTIONS]
```

**Arguments:**
- `PROMPT_IDS`: One or more prompt database IDs (ps_xxxxx format)

**Options:**
- `--resolution`: Max resolution for preprocessing (e.g., 480)
- `--dry-run`: Preview without calling AI API

**Phase 2 Enhancement Run System:**
- Creates proper database runs with model_type="enhance" for full tracking
- Run directories created as `outputs/run_{run_id}/` with logs and results
- Complete status lifecycle: pending → running → completed/failed
- Enhancement results stored in database outputs field with metadata
- Support for both create_new and overwrite modes with validation
- Links enhanced prompts to original prompts for complete traceability
- All enhancement operations treated as trackable database runs

**Examples:**
```bash
cosmos prompt-enhance ps_a1b2c3
# Returns: {
#   "run_id": "rs_enhance123",
#   "enhanced_prompt_id": "ps_g7h8i9",
#   "enhanced_text": "Enhanced prompt text with better details",
#   "status": "success"
# }

cosmos prompt-enhance ps_a1b2c3 ps_d4e5f6 ps_m7n8o9 --resolution 480
# Enhances multiple prompts, creates enhancement runs for each

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

### kill
Kill all running Cosmos containers on the GPU instance.

```bash
cosmos kill [OPTIONS]
```

**Options:**
- `--force, -f`: Skip confirmation prompt

**Examples:**
```bash
cosmos kill            # Prompts for confirmation before killing
cosmos kill --force    # Kills immediately without confirmation
```

**Warning:** This command will immediately terminate all running inference and upscaling jobs. Logs may be incomplete for terminated jobs.

### delete
Delete prompts or runs from the database with enhanced safety and bulk operations.

```bash
cosmos delete prompt PS_ID [OPTIONS]
cosmos delete prompt --all [OPTIONS]
cosmos delete run RS_ID [OPTIONS]
cosmos delete run --all [OPTIONS]
```

**Arguments:**
- `PS_ID`: Prompt ID to delete (e.g., ps_abc123)
- `RS_ID`: Run ID to delete (e.g., rs_xyz789)

**Options:**
- `--force`: Skip confirmation prompt
- `--all`: Delete all prompts or all runs (cannot be combined with ID)
- `--delete-outputs`: Delete output files (default: keep outputs for safety)

**Default Behavior - Output File Safety:**
- Output files are **kept by default** to protect valuable generated content
- Use `--delete-outputs` flag explicitly to remove output files
- Preview shows file counts, types, and sizes before deletion

**Bulk Operations:**
- `--all` flag enables bulk deletion of all prompts or all runs
- Special confirmation required: type "DELETE ALL" to proceed
- Preview shows total counts and sample items before bulk deletion
- Cannot combine `--all` with specific prompt/run IDs

**Enhanced File Preview:**
- Shows detailed file information including types and sizes
- File type breakdown: "3 mp4 files (45.2 MB), 2 json files (1.3 KB)"
- Sample file listings with individual sizes
- Clear indication of what will be kept vs deleted

**Examples:**
```bash
# Safe deletion (keeps output files by default)
cosmos delete prompt ps_abc123
cosmos delete run rs_xyz789

# Explicit output file deletion
cosmos delete prompt ps_abc123 --delete-outputs
cosmos delete run rs_xyz789 --delete-outputs --force

# Bulk operations with special confirmation
cosmos delete prompt --all                    # Keeps outputs, requires confirmation
cosmos delete run --all --delete-outputs      # Deletes outputs, requires "DELETE ALL"
cosmos delete prompt --all --force            # Skips confirmation but still keeps outputs

# View detailed preview before deciding
cosmos delete prompt ps_abc123                # Shows file details before confirmation
```

**Safety Features:**
- Default behavior preserves generated outputs (videos, images, etc.)
- Rich preview showing file counts, types, and total sizes
- Special confirmation for bulk operations prevents accidental deletion
- Clear distinction between database records and output files in preview

### verify
Verify database-filesystem integrity.

```bash
cosmos verify [OPTIONS]
```

**Options:**
- `--fix`: Attempt to fix integrity issues (clean orphaned files/records)

**Examples:**
```bash
cosmos verify         # Check integrity and report issues
cosmos verify --fix   # Fix integrity issues automatically
```

### ui
Launch the advanced Gradio web interface with comprehensive run management and enhanced controls.

```bash
cosmos ui [OPTIONS]
```

**Features:**
- **Operations Tab**: Two-column layout with prompt selection and inference controls
- **Run History Tab**: Comprehensive run management with advanced filtering, search, and batch operations
- **Enhanced Status Indicators**: Visual indicators for AI-enhanced prompts with enhanced status checkbox
- **Multi-tab Run Details**: General, Parameters, Logs, and Output tabs for comprehensive run information
- **Advanced Filtering**: Multi-criteria filtering by status, date range, and text search capabilities
- **Batch Operations**: Select multiple runs with batch delete functionality and selection controls
- **Professional Design System**: Gradient animations, glassmorphism effects, and loading skeleton animations
- **Inference Controls**: Adjustable weights for visual, edge, depth, segmentation (0.0-1.0)
- **AI Enhancement**: Pixtral model integration for prompt enhancement
- **Theme System**: Automatic dark/light mode with system preference detection
- **Real-time Logs**: Theme-aware log streaming with CSS variables

**Options:**
- `--port`: Port to run the server on (default: 7860)
- `--share`: Create a public share link

**Examples:**
```bash
cosmos ui                    # Launch on localhost:7860
cosmos ui --port 8080        # Launch on custom port
cosmos ui --share            # Create public share link
```

**Interface Tabs:**
- **Inputs**: Input video browser with create prompt functionality and multimodal preview
- **Prompts**: Unified prompt management and operations with enhanced status indicators
- **Outputs**: Generated video gallery with comprehensive metadata and download capabilities
- **Run History**: Advanced run filtering, search, statistics, and batch management system
- **Active Jobs**: Real-time container monitoring with auto-refresh and log streaming interface

**Run History Features:**
- **Filtering System**: Filter by status (all/completed/running/pending/failed/cancelled), date range (all/today/yesterday/last 7 days/last 30 days)
- **Text Search**: Real-time search across prompt text and run IDs with instant results
- **Statistics Panel**: Total runs, status breakdown, and success rate calculations
- **Batch Operations**: Select All/Clear Selection with batch delete functionality
- **Run Details Tabs**:
  - **General**: Run ID, status, duration, prompt information, created/completed timestamps
  - **Parameters**: Control weights (JSON), inference parameters (JSON)
  - **Logs**: Log file path, full log content viewer with copy button
  - **Output**: Generated video preview, output path, download/delete buttons
- **Professional UI**: Card layouts with glassmorphism effects, hover animations, and loading states

### upscale
Upscale video to 4K resolution using AI enhancement (Phase 1 Refactor - Video-Agnostic).

```bash
# From inference run
cosmos upscale --from-run RUN_ID [--weight 0.5] [--prompt TEXT] [--dry-run]

# From video file
cosmos upscale --video VIDEO_PATH [--weight 0.5] [--prompt TEXT] [--dry-run]
```

**Source Options (Mutually Exclusive):**
- `--from-run, -r RUN_ID`: Run ID of completed inference run to upscale (rs_xxxxx format)
- `--video, -v VIDEO_PATH`: Path to video file to upscale (supports .mp4, .mov, .avi, .mkv)

**Enhancement Options:**
- `--prompt, -p TEXT`: Optional prompt to guide the AI upscaling process
- `--weight, -w`: Control weight for upscaling strength (0.0-1.0, default: 0.5)
- `--dry-run`: Preview the upscaling operation without executing

**Phase 1 Upscaling Refactor - Video-Agnostic System:**
- **Video-agnostic upscaling** - works with any video file, not just inference runs
- **Mutually exclusive sources** - either `--from-run` OR `--video` (never both)
- **Guided upscaling** - optional `--prompt` parameter for AI-directed enhancement
- **Comprehensive validation** - file existence, format support, run completion status
- Creates separate database run with model_type="upscale" for complete tracking independence
- Links to parent inference run via execution_config["source_run_id"] for traceability (when from run)
- Independent status lifecycle: pending → running → completed/failed
- Creates dedicated run directory as `outputs/run_{upscale_run_id}/` with separate logs
- Follows "One GPU Operation = One Database Run" architecture principle
- Completely separate from inference operations - no shared parameters or execution context

**Examples:**
```bash
# From inference run
cosmos upscale --from-run rs_abc123
# Returns: Created upscaling run rs_upscale_xyz789

# From video file with custom weight
cosmos upscale --video my_video.mp4 --weight 0.7

# Guided upscaling with prompt
cosmos upscale --video video.mp4 --prompt "cinematic 8K quality"
cosmos upscale --from-run rs_abc123 --prompt "enhance details"

# Preview mode (no execution)
cosmos upscale --from-run rs_abc123 --dry-run
cosmos upscale --video video.mp4 --dry-run

# Monitor progress
cosmos status --stream

# Check upscaling run details
cosmos show run rs_upscale_xyz789
```

**Complete Upscaling Workflow:**
1. **Source Validation**: Verifies run exists/completed OR video file exists/supported format
2. **Run Creation**: Creates new database run with model_type="upscale" and unique run_id
3. **GPU Execution**: Uploads upscaling spec, executes 4K upscaling on GPU cluster
4. **Output Download**: Downloads upscaled video to dedicated run directory
5. **Status Update**: Updates database with completion status and output paths
6. **Independent Tracking**: Complete separation from parent inference run

**Technical Requirements:**
- Parent inference run must have status "completed" with valid output video
- Control weight range: 0.0-1.0 (validates before execution)
- GPU cluster must have sufficient memory for 4K upscaling operations
- Separate Docker container execution independent of inference processes

### SimplifiedQueueService - Streamlined Job Queue System

The SimplifiedQueueService provides comprehensive job queue management for the Gradio UI, implementing a simplified, reliable queuing system that wraps CosmosAPI using database-level concurrency control instead of application locks.

**Architecture:** The queue system is EXCLUSIVELY for the Gradio UI. The CLI continues to use direct CosmosAPI calls without queuing, maintaining separate execution paths for different interfaces.

**Key Improvements Over Legacy QueueService:**
- **No Threading Complexity**: Eliminates background threads and application-level locks
- **Database-First Concurrency**: Uses `SELECT ... FOR UPDATE SKIP LOCKED` for atomic job claiming
- **Single Warm Container**: Maintains one container preventing accumulation issues
- **Timer-Based Processing**: Uses Gradio Timer component for 2-second intervals
- **Linear Execution**: Simple, predictable execution flow
- **Fresh Database Sessions**: Prevents stale data through session management

**Key Features:**
- **Thread-Safe Design**: Uses `_job_processing_lock` to prevent race conditions when claiming jobs
- **GPU Conflict Prevention**: Checks actual running Docker containers before processing new jobs
- **SQLite Persistence**: Queue state survives UI restarts and maintains complete job history
- **FIFO Processing**: First-in, first-out job processing with position tracking
- **Background Processing**: Automatic job execution without blocking UI interaction
- **Single Container Paradigm**: Only one job runs at a time due to GPU limitations
- **Intelligent Cleanup**: Automatic deletion of successful jobs and trimming of failed/cancelled jobs (keeps last 50)
- **Enhanced Job Control**: Cancel selected jobs from queue table and kill active jobs with database updates
- **Auto-Refresh**: 5-second timer for real-time queue status updates
- **Graceful Shutdown**: Marks running jobs as cancelled when app closes to maintain state consistency

#### Core Features

```python
from cosmos_workflow.services.simple_queue_service import SimplifiedQueueService
from cosmos_workflow.api import CosmosAPI
from cosmos_workflow.database import DatabaseConnection

# Initialize simplified queue service
cosmos_api = CosmosAPI()
db_connection = DatabaseConnection()
queue_service = SimplifiedQueueService(cosmos_api=cosmos_api, db_connection=db_connection)

# Add job to queue
job_id = queue_service.add_job(
    prompt_ids=["ps_abc123"],
    job_type="inference",
    config={
        "weights": {"vis": 0.3, "edge": 0.4, "depth": 0.2, "seg": 0.1},
        "num_steps": 25,
        "guidance_scale": 4.0
    },
    priority=50
)

# Check queue status
status = queue_service.get_queue_status()
print(f"Total queued: {status['total_queued']}")

# Get job position
position = queue_service.get_position(job_id)
print(f"Position in queue: {position}")

# Process next job (timer-based processing handles this automatically)
result = queue_service.process_next_job()
```

#### Supported Job Types

**1. Single Inference (`job_type="inference"`):**
- Executes single prompt inference with configurable parameters
- Supports all control weights (visual, edge, depth, segmentation)
- Configuration includes num_steps, guidance_scale, seed, fps, etc.

**2. Batch Inference (`job_type="batch_inference"`):**
- Processes multiple prompts together for efficiency (40% faster)
- Shared weights configuration applied to all prompts in batch
- Automatic output splitting into individual run directories

**3. AI Enhancement (`job_type="enhancement"`):**
- Uses Pixtral model for intelligent prompt enhancement
- Supports create_new and force_overwrite modes
- Configuration includes enhancement model selection

**4. Video Upscaling (`job_type="upscale"`):**
- 4K upscaling of any video source (not just inference outputs)
- Supports optional prompt guidance for AI-directed enhancement
- Configuration includes video_source, control_weight, and optional prompt

#### Queue Management

```python
# Processing is handled automatically by Gradio Timer component
# No need to start/stop background processors

# Cancel a queued job (only works for "queued" status)
cancelled = queue_service.cancel_job(job_id)

# Completed jobs are automatically cleaned up
# No manual cleanup needed

# Get estimated wait time
wait_time = queue_service.get_estimated_wait_time(job_id)

# Set batch size for GPU processing
queue_service.set_batch_size(4)

# Ensure container is ready for processing
container_id = queue_service.ensure_container()
```

#### Database Integration

The SimplifiedQueueService uses the JobQueue model for persistence with enhanced concurrency control:

```python
# JobQueue model fields:
# - id: Unique job identifier (job_xxxxx format)
# - prompt_ids: JSON list of prompt IDs to process
# - job_type: Type of operation (inference, batch_inference, enhancement)
# - status: Current status (queued, running, completed, failed, cancelled)
# - config: JSON configuration parameters
# - created_at, started_at, completed_at: Timestamps
# - result: JSON results after completion
# - priority: Integer priority (higher = more important)
```

#### Key Design Principles

- **UI-Only**: Queue system designed specifically for Gradio UI experience
- **FIFO Processing**: Jobs processed in creation order (first in, first out)
- **Synchronous Execution**: Maintains existing synchronous execution model
- **Wrapper Pattern**: Wraps existing CosmosAPI methods without changing their behavior
- **Background Processing**: Automatic job execution via background thread
- **Status Persistence**: Queue state persisted in SQLite database

## Log Visualization

The Cosmos Workflow System includes a comprehensive log visualization interface that provides real-time log streaming, advanced filtering, and interactive web-based viewing capabilities.

### LogViewer

Core log viewer component for managing and displaying logs with real-time streaming capabilities.

```python
from cosmos_workflow.ui.log_viewer import LogViewer, LogFilter, LogEntry
from datetime import datetime

# Initialize log viewer with buffer management
log_viewer = LogViewer(max_entries=1000, buffer_size=50)

# Add log entries from various sources
log_viewer.add_log_line("2024-01-01 12:00:00 [INFO] Starting inference process")

# Create custom log entry
entry = LogEntry(
    timestamp=datetime.now(),
    level="INFO",
    message="Custom log message",
    source="inference.py",
    line_number=42
)
log_viewer.add_entry(entry)

# Set up real-time streaming from remote source
callback = log_viewer.get_stream_callback(stream_id="gpu_logs")
# callback can be used with RemoteLogStreamer for real-time updates

# Apply filters
filter_obj = LogFilter(
    levels=["ERROR", "WARNING"],
    search_text="inference",
    start_time=datetime(2024, 1, 1),
    end_time=datetime(2024, 1, 2)
)
log_viewer.set_filter(filter_obj)
filtered_entries = log_viewer.get_filtered_entries()

# Export logs in various formats
json_export = log_viewer.export_json(filtered=True)
text_export = log_viewer.export_text()
html_output = log_viewer.get_formatted_html()

# Search functionality
results = log_viewer.search("error")

# Pagination for large log sets
page_entries = log_viewer.get_page(page=0, page_size=50)
```

**Key Features:**
- **Real-time streaming** with configurable buffer sizes and update callbacks
- **Advanced filtering** by log level, search text, regex patterns, and time ranges
- **Multiple export formats** including JSON, plain text, and HTML with syntax highlighting
- **Performance optimization** with virtual scrolling and caching for large log sets
- **Stream integration** with callback system for RemoteLogStreamer integration
- **Memory management** with configurable maximum entries and automatic cleanup

### LogFilter

Flexible filtering system for log entries based on multiple criteria.

```python
from cosmos_workflow.ui.log_viewer import LogFilter
from datetime import datetime

# Create comprehensive filter
log_filter = LogFilter(
    levels=["ERROR", "WARNING", "INFO"],  # Include specific log levels
    search_text="docker",                   # Search for specific text
    regex_pattern=r"\berror\d+\b",          # Regex pattern matching
    start_time=datetime(2024, 1, 1, 8, 0),  # Time range filtering
    end_time=datetime(2024, 1, 1, 18, 0)
)

# Apply filter to log entries
filtered_logs = log_filter.apply(all_log_entries)
```

### LogViewerWeb

Web-based log viewer component designed for Gradio integration with advanced UI features.

```python
from cosmos_workflow.ui.log_viewer_web import LogViewerWeb, create_log_viewer_interface
import gradio as gr

# Initialize web log viewer
web_viewer = LogViewerWeb()

# Add log streams for real-time monitoring
stream_id = web_viewer.add_stream(run_id="rs_abc123", log_path="/remote/logs/inference.log")

# Configure UI settings
web_viewer.set_theme("dark")
web_viewer.enable_auto_refresh(interval=2.0)
web_viewer.set_viewport_size("desktop")

# Render logs with syntax highlighting
html_output = web_viewer.render_html()

# Performance optimizations
page_html = web_viewer.render_page(page=0, page_size=50)
viewport_config = web_viewer.get_viewport_config()

# Search and filtering
results = web_viewer.incremental_search("error", previous_query="err")
web_viewer.apply_filter(levels=["ERROR", "WARNING"])
filtered_html = web_viewer.get_filtered_html()

# Accessibility features
announcement = web_viewer.get_screen_reader_announcement()
keyboard_shortcuts = web_viewer.get_keyboard_shortcuts()

# Create complete Gradio interface
interface = create_log_viewer_interface()
interface.launch()
```

**Web Interface Features:**
- **Gradio integration** with interactive filtering controls and real-time updates
- **Responsive design** with mobile, tablet, and desktop layouts
- **Theme support** with dark and light modes
- **Accessibility features** including screen reader support and keyboard navigation
- **Performance optimization** with virtual scrolling, caching, and incremental search
- **Export capabilities** supporting JSON, text, and CSV formats
- **Auto-refresh** with configurable intervals for real-time monitoring

### Integration with RemoteLogStreamer

The log visualization system integrates seamlessly with the existing RemoteLogStreamer infrastructure:

```python
from cosmos_workflow.monitoring.log_streamer import RemoteLogStreamer
from cosmos_workflow.ui.log_viewer import LogViewer

# Create log viewer and streamer
log_viewer = LogViewer()
streamer = RemoteLogStreamer(
    ssh_manager=ssh_manager,
    remote_log_path="/remote/logs/inference.log",
    local_log_path="local/logs/inference.log"
)

# Connect log viewer to streamer
callback = log_viewer.get_stream_callback(stream_id="inference")
streamer.start_streaming(callback=callback)

# Logs will now appear in real-time in the log viewer
# with automatic parsing, filtering, and display capabilities
```

### Usage in Gradio UI

The log visualization interface is designed to integrate into the existing Gradio UI:

```python
# Add to existing UI tabs
with gr.Tab("Logs"):
    log_interface = create_log_viewer_interface()

# Or embed in existing inference tab
with gr.Tab("Generate"):
    # ... existing UI components ...

    log_display = gr.HTML(
        label="Execution Logs",
        value="",
        elem_classes=["log-display"]
    )

    # Update logs during inference
    def update_logs():
        return web_viewer.render_html()

    gr.Timer(fn=update_logs, outputs=[log_display], active=True)
```

## Synchronous Execution Model

The Cosmos Workflow System now uses a fully synchronous execution model that eliminates the complexity of background monitoring and provides immediate, reliable operation completion.

### Overview

The synchronous execution model provides:

- **Blocking Operations**: All GPU operations block until completion, returning final status
- **Direct Exit Code Handling**: Container exit codes processed immediately
- **Immediate Output Downloads**: Outputs downloaded synchronously after container completion
- **Real-time Status Updates**: Database status updated during execution, not after

### Key Features

**Synchronous API Usage**
```python
from cosmos_workflow.api import CosmosAPI

# All operations block until complete
ops = CosmosAPI()

# This blocks until inference is finished
result = ops.quick_inference("ps_abc123")
if result["status"] == "completed":
    print(f"Output ready: {result['output_path']}")
else:
    print(f"Failed: {result.get('error', 'Unknown error')}")
```

**Direct Container Execution**
```python
# Docker containers run without -d flag, naturally blocking
# Exit codes handled immediately:
# 0 = success → status="completed", outputs downloaded
# non-zero = failure → status="failed", error logged
```

**Configuration-driven Timeouts**
```toml
# config.toml
[execution]
docker_execution = 3600  # 1 hour timeout for inference/upscaling
enhancement_timeout = 1800  # 30 minutes for AI enhancement
```

### Architecture Benefits

**Eliminates Background Complexity**
- No background threads that die with CLI exit
- No container status polling or monitoring
- No lazy evaluation or completion detection
- No race conditions between monitoring and database updates

**Immediate Feedback**
```python
# Before (async): Operations returned "started" status
result = ops.quick_inference("ps_abc123")
# Returns: {"status": "started", "run_id": "rs_xyz"}

# Now (sync): Operations return final completion status
result = ops.quick_inference("ps_abc123")
# Returns: {"status": "completed", "output_path": "/outputs/...", "duration": 245.6}
```

**Single Container Paradigm**
```python
# System enforces single container operations for reliable resource management
# Active Jobs tab provides real-time monitoring of single running container
# Auto-refresh and status monitoring ensure reliable operation tracking
ops = CosmosAPI()
status = ops.check_status()  # Comprehensive system status
containers = ops.get_active_containers()  # Running container info
```

### Usage Examples

**CLI Operations**
```bash
# All CLI commands now block until completion
cosmos inference ps_abc123  # Waits for inference to finish
# Output: "✅ Inference completed for ps_abc123"
#         "📁 Output: outputs/run_rs_xyz789/output.mp4"

cosmos prompt-enhance ps_abc123  # Waits for enhancement
# Output: "✅ Enhanced prompt created: ps_def456"
```

**API Integration**
```python
ops = CosmosAPI()

# Single inference - blocks until done
result = ops.quick_inference(
    prompt_id="ps_abc123",
    weights={"vis": 0.3, "edge": 0.3, "depth": 0.2, "seg": 0.2},
    stream_output=True  # Show real-time progress in CLI
)

# Batch inference - processes sequentially
results = ops.batch_inference(
    prompt_ids=["ps_001", "ps_002", "ps_003"],
    shared_weights={"vis": 0.25, "edge": 0.25, "depth": 0.25, "seg": 0.25}
)
```

**Gradio UI Integration**
```python
# UI operations use gr.Progress() for real-time feedback
def run_inference_on_selected(dataframe_data, weights, progress=None):
    if progress is None:
        progress = gr.Progress()

    progress(0.1, desc="Initializing inference...")

    result = ops.quick_inference(
        prompt_id=selected_ids[0],
        weights=weights,
        stream_output=False,  # Clean UI without console output
        # ... other parameters
    )

    progress(1.0, desc="Inference complete!")

    if result.get("status") == "completed":
        return f"✅ Inference completed", "Idle"
    else:
        return f"❌ Failed: {result.get('error')}", "Idle"
```

### Error Handling

**Immediate Error Detection**
- Container failures detected through exit codes
- Network issues cause immediate operation failure
- No timeout-based error detection needed
- Cleaner error propagation through execution stack

**Timeout Management**
```python
# Timeouts configured per operation type
TIMEOUTS = {
    "inference": config.get("execution", {}).get("docker_execution", 3600),
    "upscaling": config.get("execution", {}).get("docker_execution", 3600),
    "enhancement": config.get("execution", {}).get("enhancement_timeout", 1800)
}
```

### Migration Benefits

**Simplified Codebase**
- Removed StatusChecker class and all monitoring infrastructure
- Eliminated background thread management
- No more container lifecycle complexity
- Direct execution flow from start to completion

**Improved Reliability**
- No more orphaned "running" runs
- Database always reflects actual operation state
- No CLI exit dependencies
- Predictable execution behavior

**Better User Experience**
- Immediate completion feedback
- Real-time progress in UI with container status monitoring
- Clear success/failure indication
- No more "check status later" workflows

## Core Modules

### DataRepository

The DataRepository provides the complete business logic layer for managing prompts and runs in the database. This is the core service class that handles all data operations, validation, and transaction management.

#### Query Methods

```python
from cosmos_workflow.services.data_repository import DataRepository

# Initialize service (used by CLI commands)
from cosmos_workflow.services.data_repository import DataRepository
from cosmos_workflow.database import DatabaseConnection
from cosmos_workflow.config import ConfigManager

db_connection = DatabaseConnection()
config_manager = ConfigManager()
service = DataRepository(db_connection, config_manager)

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

#### Enhancement Query Methods

These methods provide specialized queries for enhancement metadata and lineage tracking:

```python
# Get enhancement details for a prompt
details = service.get_enhancement_details("ps_abc123")
# Returns: Dictionary with enhancement metadata or None if not enhanced
# {
#     "enhanced_text": str,
#     "enhancement_model": str,
#     "enhanced_at": str,
#     "original_prompt_id": str,
#     "enhanced_prompt_id": str,
#     "duration_seconds": float
# }

# Get the original prompt that was enhanced
original = service.get_original_prompt("ps_enhanced_xyz")
# Returns: Original prompt dictionary or None if not found/not enhanced

# List all enhanced prompts
enhanced_prompts = service.list_enhanced_prompts(limit=100)
# Returns: List of prompts where parameters->enhanced is true

# Get enhancement history for a prompt
history = service.get_enhancement_history("ps_abc123")
# Returns: List of all enhancement runs (as original or result)
```

**Key Features:**
- **Backward Compatible**: Works with both old (metadata in prompt) and new (metadata in run) structures
- **Efficient Queries**: Uses indexed boolean flag for fast filtering
- **Lineage Tracking**: Can trace enhancement relationships across generations
- **No Duplication**: Enhancement details stored once in run outputs

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

**JobQueue Model:**
- Queue management for Gradio UI job processing (CLI uses direct CosmosAPI calls)
- Supports four job types: inference, batch_inference, enhancement, upscale
- FIFO processing order with priority support for future enhancement
- Complete status tracking: queued → running → completed/failed/cancelled
- SQLite persistence ensures queue survives UI restarts and maintains job history
- Thread-safe design with atomic job claiming to prevent race conditions


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

### Performance Considerations

**Indexing Strategy:**
```sql
CREATE INDEX idx_prompts_model_type ON prompts(model_type);
CREATE INDEX idx_runs_status ON runs(status);
CREATE INDEX idx_runs_prompt_id ON runs(prompt_id);
```

**JSON Column Performance:**
- SQLite JSON functions enable efficient querying
- Consider extracting frequently queried fields to dedicated columns
- Use JSON_EXTRACT for complex queries

### DataRepository

The service layer provides business logic for managing prompts and runs with transaction safety and comprehensive validation.

```python
from cosmos_workflow.services import DataRepository
from cosmos_workflow.database import DatabaseConnection
from cosmos_workflow.config import ConfigManager

# Initialize service
db_connection = DatabaseConnection(":memory:")
db_connection.create_tables()
config_manager = ConfigManager()
service = DataRepository(db_connection, config_manager)

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
  initial_status="pending"  # or "running", "completed", "failed", etc.
)
# Returns: {"id": "rs_wxyz5678", "prompt_id": "ps_abcd1234", ...}

# Retrieve entities
prompt = service.get_prompt("ps_abcd1234")
run = service.get_run("rs_wxyz5678")
```

**Methods:**

- `create_prompt(model_type, prompt_text, inputs, parameters)`: Create AI model prompts
  - Validates model_type against supported types: "transfer", "reason", "predict", "enhance", "upscale"
  - Enforces maximum prompt_text length of 10,000 characters
  - Sanitizes input text by removing null bytes and control characters
  - Validates required fields and JSON structure
  - Returns dictionary optimized for CLI display
  - Generates deterministic IDs based on content hash

- `create_run(prompt_id, execution_config, metadata=None, initial_status="pending", model_type=None)`: Create execution runs
  - Links to existing prompts with foreign key validation
  - Raises PromptNotFoundError if prompt doesn't exist
  - Configurable initial status for workflow control (default: "pending")
  - Optional model_type override for specialized runs (e.g., "enhance", "upscale")
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
- Configurable initial status for runs enabling lifecycle management
- Parameterized logging throughout for debugging and audit trails

**Error Handling:**
- Validates all required parameters with clear error messages
- Enforces supported model types ("transfer", "reason", "predict")
- Raises custom PromptNotFoundError when prompt references don't exist
- Handles database connection failures with automatic rollback
- Returns None for not-found entities in get operations
- Input length validation (max 10,000 chars for prompt_text)
- Null byte and control character sanitization

### CosmosAPI
Unified interface for all workflow operations, combining service and orchestrator functionality into high-level operations.

```python
from cosmos_workflow.api.cosmos_api import CosmosAPI

# Initialize operations (auto-creates service and orchestrator)
ops = CosmosAPI()

# Primary inference method - accepts prompt_id directly
result = ops.quick_inference(
  prompt_id="ps_abc123",
  weights={"vis": 0.3, "edge": 0.4, "depth": 0.2, "seg": 0.1},
  num_steps=35,
  guidance=5.0
)
# Returns: {"run_id": "rs_xyz789", "output_path": "/outputs/result.mp4", "status": "success"}

# Separate upscaling operation
# Phase 1 Refactor - Video-agnostic upscaling
upscale_result = ops.upscale(
  video_source="rs_xyz789",  # From run
  control_weight=0.5
)
# OR from video file
upscale_result = ops.upscale(
  video_source="/path/to/video.mp4",  # From file
  control_weight=0.5,
  prompt="cinematic quality"  # Optional guided upscaling
)
# Returns: {"upscale_run_id": "rs_upscale_abc", "status": "success", "output_path": "/outputs/run_rs_upscale_abc/"}

# Batch inference method - accepts list of prompt_ids
batch_result = ops.batch_inference(
  prompt_ids=["ps_abc123", "ps_def456", "ps_ghi789"],
  shared_weights={"vis": 0.4, "edge": 0.3, "depth": 0.2, "seg": 0.1},
  num_steps=50,
  guidance=8.0
)
# Returns: {"output_mapping": {...}, "successful": 3, "failed": 0}

# Create prompt (same as DataRepository)
prompt = ops.create_prompt(
  prompt_text="A futuristic city",
  video_dir="inputs/videos/scene1",
  name="futuristic_city"
)
# Returns: {"id": "ps_abc123", ...}

# Enhanced deletion operations with output file safety
# Safe deletion (keeps output files by default)
deletion_preview = ops.preview_prompt_deletion("ps_abc123", keep_outputs=True)
print(f"Will delete {len(deletion_preview['runs'])} runs")
print(f"Output files: {deletion_preview['files_summary']['total_files']} files ({deletion_preview['files_summary']['total_size']})")

result = ops.delete_prompt("ps_abc123", keep_outputs=True)
# Returns: {"success": True, "deleted": {"prompt_id": "ps_abc123", "run_ids": [...], "directories": []}}

# Delete with output files removed
result = ops.delete_prompt("ps_abc123", keep_outputs=False)
# Returns: {"success": True, "deleted": {"prompt_id": "ps_abc123", "run_ids": [...], "directories": ["outputs/run_rs_xyz789"]}}

# Bulk deletion operations
bulk_preview = ops.preview_all_prompts_deletion()
print(f"Total prompts: {bulk_preview['total_prompt_count']}, Total runs: {bulk_preview['total_run_count']}")

result = ops.delete_all_prompts(keep_outputs=True)
# Returns: {"success": True, "deleted": {"prompt_ids": [...], "run_ids": [...], "directories": []}}

# Run-specific operations
run_preview = ops.preview_run_deletion("rs_xyz789", keep_outputs=False)
result = ops.delete_run("rs_xyz789", keep_outputs=False)

# Bulk run deletion
all_runs_preview = ops.preview_all_runs_deletion()
result = ops.delete_all_runs(keep_outputs=True)
```

**Primary Methods (What Most Users Should Use):**
- `quick_inference(prompt_id, weights=None, **kwargs)`: Main inference method
  - Accepts prompt_id directly, creates run internally
  - Supports all execution parameters (num_steps, guidance, seed, etc.)
  - Returns execution results with run_id for tracking
  - Note: Upscaling parameters removed - use separate `upscale()` method (Phase 1 refactor)

- `batch_inference(prompt_ids, shared_weights=None, **kwargs)`: Batch processing
  - Accepts list of prompt_ids, creates runs internally for each
  - Executes all runs as a batch for improved performance
  - Returns batch results with output mapping

**Low-Level Methods (For Advanced Use):**
- `create_run(prompt_id, weights=None, num_steps=35, **kwargs)`: Explicit run creation
  - For workflows that need control over run creation timing
  - Returns run dictionary with generated ID

- `execute_run(run_id)`: Explicit run execution
  - For workflows that need control over execution timing
  - Returns execution results
  - Note: Upscaling parameters removed - use separate `upscale()` method (Phase 1 refactor)

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
- **Single Interface**: Combines DataRepository and GPUExecutor capabilities

### GPUExecutor
Simplified orchestrator handling ONLY GPU execution (no data persistence). Now includes prompt enhancement runs.

```python
from cosmos_workflow.execution.gpu_executor import GPUExecutor

orchestrator = GPUExecutor()

# Execute a run from database data
result = orchestrator.execute_run(
  run_dict={"id": "rs_abc123", "execution_config": {"weights": [0.3, 0.4, 0.2, 0.1]}},
  prompt_dict={"id": "ps_def456", "prompt_text": "A futuristic city", "inputs": {"video": "/path/to/video"}}
)
# Returns: {"status": "completed", "output_path": "/outputs/result.mp4", "duration": 362.1}

# Separate upscaling execution
upscale_result = orchestrator.execute_upscaling_run(
  upscale_run={"id": "rs_upscale_123", "execution_config": {"parent_run_id": "rs_abc123", "control_weight": 0.5}},
  prompt_dict={"id": "ps_def456", "prompt_text": "A futuristic city", "inputs": {"video": "/path/to/video"}}
)
# Returns: {"status": "completed", "output_path": "/outputs/run_rs_upscale_123/output.mp4", "duration": 180.5}

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
- `execute_run(run_dict, prompt_dict)`: Execute inference GPU workflow
  - Converts database dictionaries to NVIDIA Cosmos format
  - Creates temporary JSON files for GPU scripts
  - Handles SSH connection, file upload, Docker execution, result download
  - Returns execution results for DataRepository to persist
  - Note: Upscaling removed - now handled by separate `execute_upscaling_run()` method

- `execute_upscaling_run(upscale_run, prompt_dict)`: Execute upscaling GPU workflow (Phase 3)
  - Takes upscale run with parent_run_id and control_weight in execution_config
  - Creates minimal upscaling specification for GPU execution
  - Independent execution with separate run directory and logs
  - Downloads upscaled output to dedicated run directory
  - Returns upscaling results for database persistence

- `execute_batch_runs(runs_and_prompts, batch_name=None)`: Execute multiple runs as a batch
  - Converts run/prompt pairs to JSONL format using `nvidia_format.to_cosmos_batch_inference_jsonl()`
  - Uploads JSONL file and all referenced videos to remote GPU server
  - Executes batch inference using `scripts/batch_inference.sh`
  - Automatically splits batch outputs into individual run folders
  - Downloads all outputs and organizes them locally
  - Returns batch execution summary with output mapping

- `execute_enhancement_run(run, prompt)`: Execute prompt enhancement as database run (Phase 2)
  - Creates proper run directories with logs and results storage
  - Handles run_id parameter for consistent directory structure
  - Returns enhancement results in database format with metadata
  - Full integration with database run tracking system

- `run_prompt_upsampling(prompt_text)`: Legacy AI-powered prompt enhancement
  - Uses Pixtral vision-language model for prompt improvement
  - Maintained for backward compatibility
  - Internally creates temporary run_id for new implementation

- `check_remote_status()`: Check remote GPU system health and container status

**Architecture Principles:**
- **Pure Execution Layer**: No data persistence or business logic
- **Stateless**: Takes input dictionaries, returns result dictionaries
- **NVIDIA Compatible**: Creates temporary JSON in required format for GPU scripts
- **Clean Separation**: Data operations handled entirely by DataRepository
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
Executes Docker commands on remote instance with centralized container management and GPU detection. All Docker operations use the wrapper pattern through DockerCommandBuilder for consistent security and error handling.

```python
from cosmos_workflow.execution.docker_executor import DockerExecutor

docker_executor = DockerExecutor(
    ssh_manager=ssh_manager,
    remote_dir="/workspace",
    docker_image="nvcr.io/ubuntu/cosmos-transfer1:latest"
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

# Get active container (centralized container detection)
container = docker_executor.get_active_container()
# Returns: {
#   "id": "abc123456789...",
#   "id_short": "abc123456789",
#   "name": "cosmos_inference",
#   "status": "Up 5 minutes",
#   "image": "nvcr.io/ubuntu/cosmos-transfer1:latest",
#   "created": "2025-09-07 12:00:00",
#   "warning": "Multiple containers detected (2), using most recent: cosmos_inference"  # Optional
# }
# Returns None if no containers running

# Get GPU information via nvidia-smi
gpu_info = docker_executor.get_gpu_info()
# Returns: {
#   "name": "NVIDIA H100 PCIe",
#   "memory_total": "81559 MB",
#   "driver_version": "525.60.13",
#   "cuda_version": "12.2"  # Optional if detection fails
# }
# Returns None if GPU not available or nvidia-smi fails

# Stream container logs
docker_executor.stream_container_logs()  # Auto-detect using get_active_container()
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
- `get_active_container()`: Get the active cosmos container (single container paradigm)
  - Returns structured container info: id, id_short, name, status, image, created timestamp
  - Expects exactly one running container, warns if multiple detected
  - Central source for container detection, eliminates duplicate docker ps calls across codebase
  - Returns None if no containers running
  - Includes optional "warning" field when multiple containers found
- `get_gpu_info()`: Detect GPU information via nvidia-smi query
  - Returns GPU model name, total memory in MB, driver version
  - Attempts to detect CUDA version from nvidia-smi output
  - Returns None if GPU drivers not available or nvidia-smi command fails
  - Gracefully handles systems without GPU hardware
  - Used by `cosmos status` command for GPU information display
- `run_upscaling()`: Execute upscaling pipeline
- `get_docker_status()`: Check Docker status
- `kill_containers()`: Kill all running containers using DockerCommandBuilder.build_kill_command()
  - Follows wrapper pattern for consistent security and error handling
  - Works with multiple containers simultaneously
- `stream_container_logs(container_id=None)`: Stream container logs using DockerCommandBuilder.build_logs_command()
  - Auto-detects most recent container if ID not provided
  - Uses wrapper pattern for proper command construction
  - Gracefully handles Ctrl+C interruption
  - Uses 24-hour timeout for long-running streams

## Database Schema

The system uses a database-first architecture built on SQLAlchemy with no persistent JSON files. All data is stored in the database with flexible JSON columns supporting multiple AI models.

### Architecture Overview

**Core Principles:**
- **Multi-Model Support**: Single schema supports different AI models (transfer, reason, predict, enhance, upscale)
- **Flexible JSON Storage**: Model-specific data stored in JSON columns for easy extensibility
- **Security First**: Path traversal protection, input validation, and transaction safety
- **Lazy Status Monitoring**: StatusChecker provides on-demand container status updates through lazy evaluation

**Supported Model Types (Phase 2 Update):**
- `transfer`: NVIDIA Cosmos Transfer video generation model (core functionality)
- `enhance`: Prompt enhancement using vision-language models (Phase 2 implementation)
- `upscale`: Video upscaling operations (planned Phase 3)
- `reason`: Future reasoning model support
- `predict`: Future prediction model support

The "enhance" and "upscale" types enable specialized AI operations with full database run tracking while maintaining compatibility with existing prompt models.

### Prompt Model
Stores AI prompts with flexible schema supporting any model type.

```python
class Prompt(Base):
    id = Column(String, primary_key=True)           # ps_xxxxx format
    model_type = Column(String, nullable=False)     # transfer, enhancement, reason, predict
    prompt_text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True))
    inputs = Column(JSON, nullable=False)          # Flexible input data
    parameters = Column(JSON, nullable=False)      # Flexible parameters
```

**Example Usage:**
```python
# Transfer model (video generation)
prompt_data = service.create_prompt(
    model_type="transfer",
    prompt_text="A futuristic city with neon lights",
    inputs={
        "video": "inputs/videos/city.mp4",
        "depth": "inputs/videos/city_depth.mp4",
        "segmentation": "inputs/videos/city_seg.mp4"
    },
    parameters={
        "negative_prompt": "blurry, low quality",
        "num_steps": 35,
        "guidance_scale": 8.0
    }
)

# Enhancement model (prompt improvement)
enhancement_prompt = service.create_prompt(
    model_type="enhancement",
    prompt_text="A simple city scene",
    inputs={"original_prompt_id": "ps_abc123", "resolution": 480},
    parameters={"ai_model": "pixtral", "enhancement_type": "detailed_description"}
)

# Future models supported through flexible JSON
future_prompt = service.create_prompt(
    model_type="reason",
    prompt_text="What happens next?",
    inputs={"video": "/outputs/result.mp4", "context": "urban"},
    parameters={"reasoning_depth": 3, "temperature": 0.7}
)
```

### Run Model
Tracks execution attempts of prompts with complete lifecycle management.

```python
class Run(Base):
    id = Column(String, primary_key=True)                      # rs_xxxxx format
    prompt_id = Column(String, ForeignKey("prompts.id"))
    model_type = Column(String, nullable=False)
    status = Column(String, nullable=False)                    # pending→running→completed/failed
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    execution_config = Column(JSON, nullable=False)           # Runtime configuration
    outputs = Column(JSON, nullable=False)                    # Execution results
    run_metadata = Column(JSON, nullable=False)               # Additional metadata
    rating = Column(Integer, nullable=True)                   # User rating (1-5 stars)
```

**Status Lifecycle:**
- `pending`: Run created, awaiting execution
- `uploading`: Files being transferred to GPU
- `running`: Executing on GPU
- `downloading`: Retrieving results
- `completed`: Successfully finished
- `failed`: Error occurred

**Rating System:**
- `rating`: Optional integer field (1-5 stars) for user quality assessment
- Only available for completed runs to ensure meaningful feedback
- Ratings persist in database and are included in run exports for analytics
- Displayed in UI tables and run details for quick visual assessment
- Supports quality tracking and improvement of inference parameters

### JobQueue Model
Queue management for Gradio UI job processing (UI-only, CLI uses direct CosmosAPI calls).

```python
class JobQueue(Base):
    id = Column(String, primary_key=True)                    # job_xxxxx format
    prompt_ids = Column(JSON, nullable=False)                # List of prompt IDs to process
    job_type = Column(String, nullable=False)                # inference, batch_inference, enhancement
    status = Column(String, nullable=False)                  # queued→running→completed/failed/cancelled
    config = Column(JSON, nullable=False)                    # Job-specific configuration
    created_at = Column(DateTime(timezone=True))
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    result = Column(JSON, nullable=True)                     # Results/outputs after completion
    priority = Column(Integer, default=50, nullable=True)    # Priority for future use
```

**Queue Status Lifecycle:**
- `queued`: Job added to queue, awaiting processing
- `running`: Job currently being executed
- `completed`: Job finished successfully
- `failed`: Job execution failed
- `cancelled`: Job cancelled by user

**Supported Job Types:**
- `inference`: Single prompt inference using CosmosAPI.quick_inference()
- `batch_inference`: Multiple prompt batch processing using CosmosAPI.batch_inference()
- `enhancement`: Prompt enhancement using CosmosAPI.enhance_prompt()

**Usage Pattern:**
```python
# Example job configuration for inference
config = {
    "weights": [0.3, 0.4, 0.2, 0.1],
    "num_steps": 25,
    "guidance_scale": 4.0,
    "seed": 42
}

# Queue processing uses FIFO order
# Background processor executes jobs automatically
# Results stored in result field as JSON
```

### Database Connection

**DatabaseConnection Class:**
```python
from cosmos_workflow.database.connection import DatabaseConnection

# Create connection with automatic session management
conn = DatabaseConnection("outputs/cosmos_workflow.db")
conn.create_tables()

with conn.get_session() as session:
    # Automatic commit/rollback on context exit
    prompt = Prompt(id="ps_example", model_type="transfer", ...)
    session.add(prompt)
    # Auto-commits on successful exit, rollbacks on exception
```

**Security Features:**
- Path traversal protection (rejects `../`, absolute paths validated)
- Input validation (required fields, JSON integrity)
- Transaction safety (automatic rollback on exceptions)
- Parameterized queries (SQL injection prevention)

### Query Capabilities

**List Operations:**
```python
# Filter by model type with pagination
prompts = service.list_prompts(model_type="transfer", limit=50, offset=0)

# Filter runs by status and/or prompt
runs = service.list_runs(status="completed", prompt_id="ps_abc123")

# Search prompts (case-insensitive)
results = service.search_prompts("cyberpunk", limit=50)

# Get prompt with all runs (eager loading)
details = service.get_prompt_with_runs("ps_abc123")
```

### ID Generation Strategy

**Prompt IDs:** `ps_{hash}` - Deterministic based on content
- Allows duplicate detection
- Consistent references
- Example: `ps_a1b2c3d4`

**Run IDs:** `rs_{uuid}` - UUID4 for guaranteed uniqueness
- Prevents collisions
- Each run unique regardless of configuration
- Example: `rs_x9y8z7w6`


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

## Execution Configuration Schema

The `execution_config` field is a JSON column in the Run table that contains all configuration parameters needed for GPU execution. Its structure varies by model type and contains the specific settings required for each operation.

### Schema Overview

`execution_config` is a flexible JSON field that stores:
- **Model parameters**: weights, steps, guidance, model type
- **Runtime settings**: batch size, memory management, GPU configuration
- **Workflow context**: parent run links, input files, control weights
- **Infrastructure**: Docker images, GPU nodes, file paths

### Model Type Structures

#### Inference Runs (`model_type="transfer"`)

Standard AI inference with control weight configuration:

```json
{
    "weights": {
        "vis": 0.25,      // Visual control weight (0.0-1.0)
        "edge": 0.25,     // Edge detection weight (0.0-1.0)
        "depth": 0.25,    // Depth estimation weight (0.0-1.0)
        "seg": 0.25       // Segmentation weight (0.0-1.0)
    },
    "num_steps": 35,      // Inference steps (1-100)
    "guidance": 7.0,      // Guidance scale (1.0-20.0)
    "gpu_node": "gpu-001", // Optional: specific GPU node
    "docker_image": "cosmos:latest" // Optional: Docker image override
}
```

#### Enhancement Runs (`model_type="enhance"`)

Prompt enhancement using AI models like Pixtral:

```json
{
    "model": "pixtral",           // AI model: "pixtral", "claude", etc.
    "offload": true,              // Memory efficient mode
    "batch_size": 1,              // Batch size for processing
    "video_context": "/path/to/video.mp4" // Optional: video context file
}
```

#### Upscaling Runs (`model_type="upscale"`)

Video upscaling with parent run context:

```json
{
    "parent_run_id": "rs_abc123",    // Source run for upscaling
    "control_weight": 0.8,           // Upscaling control strength (0.0-1.0)
    "input_video": "/path/to/input.mp4" // Source video file path
}
```

### Field Reference

| Field | Type | Description | Model Types | Required |
|-------|------|-------------|-------------|----------|
| `weights` | Object | Control weight configuration for inference | inference | Yes |
| `weights.vis` | Float | Visual control weight (0.0-1.0) | inference | Yes |
| `weights.edge` | Float | Edge detection weight (0.0-1.0) | inference | Yes |
| `weights.depth` | Float | Depth estimation weight (0.0-1.0) | inference | Yes |
| `weights.seg` | Float | Segmentation weight (0.0-1.0) | inference | Yes |
| `num_steps` | Integer | Number of inference steps (1-100) | inference | No (default: 35) |
| `guidance` | Float | Guidance scale (1.0-20.0) | inference | No (default: 5.0) |
| `model` | String | AI model name ("pixtral", "claude") | enhancement | Yes |
| `offload` | Boolean | Enable memory efficient mode | enhancement | No (default: false) |
| `batch_size` | Integer | Processing batch size | enhancement | No (default: 1) |
| `video_context` | String | Video context file path | enhancement | No |
| `parent_run_id` | String | Parent run ID for linked operations | upscaling | Yes |
| `control_weight` | Float | Control strength (0.0-1.0) | upscaling | Yes |
| `input_video` | String | Input video file path | upscaling | Yes |
| `gpu_node` | String | Specific GPU node identifier | all | No |
| `docker_image` | String | Docker image override | all | No |

### Integration Flow

The `execution_config` flows through the system as follows:

1. **CosmosAPI** (`cosmos_workflow/api/cosmos_api.py:452`):
   - `_build_execution_config()` creates the configuration
   - Validates parameters and sets defaults
   - Passes to DataRepository for storage

2. **DataRepository** (`cosmos_workflow/services/data_repository.py:140`):
   - `create_run()` validates and stores execution_config
   - Ensures required fields are present
   - Stores as JSON in database

3. **GPUExecutor** (`cosmos_workflow/execution/gpu_executor.py:706`):
   - Reads execution_config from run data
   - Extracts model-specific parameters
   - Configures GPU execution environment

### Usage Examples

**Creating inference run:**
```python
execution_config = {
    "weights": {"vis": 0.3, "edge": 0.4, "depth": 0.2, "seg": 0.1},
    "num_steps": 50,
    "guidance": 8.0
}
run = api.create_inference(prompt_id="ps_abc123", weights=execution_config["weights"])
```

**Creating enhancement run:**
```python
run = api.enhance_prompt(prompt_id="ps_abc123", enhancement_model="pixtral")
# Creates execution_config: {"model": "pixtral", "offload": true, "batch_size": 1}
```

**Creating upscaling run:**
```python
# Phase 1 Refactor - Video-agnostic upscaling
run = api.upscale(video_source="rs_abc123", control_weight=0.8)  # From run
run = api.upscale(video_source="/path/to/video.mp4", control_weight=0.8)  # From file
run = api.upscale(video_source="video.mp4", prompt="cinematic quality")  # Guided

# Creates execution_config: {"source_run_id": "rs_abc123", "control_weight": 0.8, "input_video_source": "..."}
```

### Validation Rules

- **Weights must sum to ≤ 1.0**: Total control weights cannot exceed 1.0
- **Required fields**: Each model type requires specific fields as marked in reference table
- **Valid ranges**: Numeric fields must be within specified ranges
- **File paths**: Input files must exist and be accessible
- **Parent relationships**: `parent_run_id` must reference existing completed run

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
host = "209.20.156.243"  # Remote GPU instance IP
user = "ubuntu"
ssh_key = "~/.ssh/LambdaSSHkey.pem"
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

[generation]
# Default negative prompt for video generation quality control
negative_prompt = """
The video captures a game playing, with bad crappy graphics and \
cartoonish frames. It represents a recording of old outdated games. \
The lighting looks very fake. The textures are very raw and basic. \
The geometries are very primitive. The images are very pixelated and \
of poor CG quality. There are many subtitles in the footage. \
Overall, the video is unrealistic at all.\
"""

[timeouts]
docker_execution = 3600  # 1 hour timeout for inference/upscaling operations
stream_logs = 86400      # 24 hours for log streaming operations

[ui]
port = 7860             # Default Gradio port
host = "0.0.0.0"        # Bind to all interfaces for SSH tunnel access
share = false           # Don't create public Gradio share links
```

## Utilities

### Workflow Utilities
Common utility functions for workflow orchestration and code deduplication.

```python
from cosmos_workflow.utils.workflow_utils import (
    ensure_directory,
    get_log_path,
    sanitize_remote_path,
    format_duration,
    log_workflow_event,
    validate_gpu_configuration
)

# Directory management
output_dir = ensure_directory("outputs/run_123")
# Creates directory if it doesn't exist, returns Path object

# Standardized log path generation
log_path = get_log_path("inference", "my_prompt", "run_abc123")
# Returns: outputs/my_prompt/inference_logs/inference_run_abc123.log
# Creates parent directories automatically

# Without run_id, uses timestamp
log_path = get_log_path("upscaling", "my_prompt")
# Returns: outputs/my_prompt/upscaling_logs/upscaling_20250907_143022.log

# Cross-platform path handling
remote_path = sanitize_remote_path(r"C:\Users\files\video.mp4")
# Returns: "C:/Users/files/video.mp4" (forward slashes for remote systems)

# Duration formatting
duration_str = format_duration(3665.5)  # seconds
# Returns: "1h 1m 5s"

# Workflow event logging
log_workflow_event(
    event_type="SUCCESS",
    workflow_name="inference_run_123",
    metadata={"duration": 180.5, "gpu_used": "H100"},
    log_dir=Path("notes")
)
# Writes to notes/run_history.log with timestamp

# GPU configuration validation
is_valid = validate_gpu_configuration(num_gpu=2, cuda_devices="0,1")
# Returns: True if configuration is valid
```

**Key Functions:**
- `ensure_directory(path)`: Ensures directory exists, creating if needed. Replaces 14+ duplicate `mkdir` calls
- `get_log_path(operation, identifier, run_id=None)`: Standardizes log path generation across 8 locations
- `sanitize_remote_path(path)`: Converts Windows paths to POSIX format, replaces 11+ manual conversions
- `format_duration(seconds)`: Human-readable duration formatting (e.g., "2h 15m 30s")
- `log_workflow_event()`: Centralized workflow event logging to run history
- `validate_gpu_configuration()`: Validates GPU count matches CUDA device specification

**Code Reduction Impact:**
- Eliminated ~100 lines of duplicate code across the codebase
- Centralized common operations for consistency and maintainability
- Standardized directory creation, log paths, and remote path handling
- Single source of truth for workflow utility operations

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
