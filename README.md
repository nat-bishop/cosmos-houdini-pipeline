# Cosmos Workflow System

A Python workflow orchestrator for NVIDIA Cosmos Transfer video generation with remote GPU execution.


## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- SSH access to GPU instance with NVIDIA Cosmos Transfer
- Docker on remote instance with NVIDIA Container Toolkit

### Remote Instance Setup
The remote GPU instance needs NVIDIA Cosmos Transfer set up according to NVIDIA's instructions:

```bash
# Clone the cosmos-transfer1 source code
git clone git@github.com:nvidia-cosmos/cosmos-transfer1.git
cd cosmos-transfer1
git submodule update --init --recursive
```

Cosmos runs only on Linux systems (tested with Ubuntu 24.04, 22.04, and 20.04) and requires Python 3.12.x. Docker and the NVIDIA Container Toolkit must be installed.

```bash
# Build the Docker image
docker build -f Dockerfile . -t nvcr.io/$USER/cosmos-transfer1:latest

# Generate a Hugging Face access token (set to 'Read' permission)
# Log in to Hugging Face with the access token:
huggingface-cli login

# Accept the Llama-Guard-3-8B terms on Hugging Face website

# Download the Cosmos model weights from Hugging Face:
PYTHONPATH=$(pwd) python scripts/download_checkpoints.py --output_dir checkpoints/
```

### Installation
```bash
# Clone and install
git clone https://github.com/yourusername/cosmos-houdini-experiments.git
cd cosmos-houdini-experiments
pip install -r requirements.txt

# Run the CLI
python cosmos --help
```

### Configuration
Edit `cosmos_workflow/config/config.toml`:
```toml
[remote]
host = "192.222.52.92"
user = "ubuntu"
ssh_key = "~/.ssh/your-key.pem"

[paths]
remote_dir = "/home/ubuntu/NatsFS/cosmos-transfer1"
```

### Basic Usage (2-Step Workflow)
```bash
# Step 1: Create a prompt (returns database ID)
cosmos create prompt "A futuristic city at sunset" inputs/videos/scene1
# Returns: Created prompt ps_a1b2c3d4 with name "futuristic_city_sunset"

# Step 2: Run inference (creates run internally and executes on GPU)
cosmos inference ps_a1b2c3d4
# Output saved to: outputs/run_rs_x9y8z7w6/result.mp4

# Or process multiple prompts together for better performance
cosmos inference ps_001 ps_002 ps_003 --batch-name "my_batch"

# Or use the Gradio UI for interactive workflow
cosmos ui

# Check GPU status
cosmos status
```

## 📁 Commands

### Database Operations
- `cosmos create prompt "text" video_dir` - Create prompt in database, returns ps_xxxxx ID
- `cosmos list prompts [--model transfer] [--limit 50] [--json]` - List prompts with filtering
- `cosmos list runs [--status completed] [--prompt ps_xxxxx] [--json]` - List runs with filtering
- `cosmos search "query" [--limit 50] [--json]` - Full-text search prompts with highlighting
- `cosmos show ps_xxxxx [--json]` - Detailed prompt view with run history

### GPU Execution
- `cosmos inference ps_xxxxx [ps_xxx2 ...] [--upscale/--no-upscale]` - Execute inference on prompts (creates runs internally)
- `cosmos prompt-enhance ps_xxxxx [--resolution 480]` - AI prompt enhancement (creates new prompt)
- `cosmos prepare input_dir [--name scene]` - Prepare video sequences for inference
- `cosmos status [--stream]` - Check GPU status or stream container logs
- `cosmos verify [--fix]` - Verify database-filesystem integrity

For shell completion setup, see [docs/SHELL_COMPLETION.md](docs/SHELL_COMPLETION.md)

## 🏗️ Architecture Overview

The Cosmos Workflow System follows a clean service layer architecture with database-first design:

```
cosmos_workflow/
├── cli/             # CLI commands using database IDs (ps_xxx, rs_xxx)
├── services/        # Business logic layer (WorkflowService)
├── workflows/       # GPU execution only (WorkflowOrchestrator)
├── database/        # SQLAlchemy models: Prompt, Run, Progress
├── connection/      # SSH/SFTP management
├── execution/       # Docker execution
├── transfer/        # File transfer services
├── utils/           # NVIDIA format conversion utilities
├── local_ai/        # AI processing (prompt enhancement)
└── config/          # Configuration management
```

### Clean Separation of Concerns

**1. Data Layer (WorkflowService)**
- All database operations: create, read, update, delete
- Query methods: list, search, filter prompts and runs
- Input validation, sanitization, and security
- Transaction safety with automatic rollback
- Returns dictionaries optimized for CLI display

**2. Execution Layer (WorkflowOrchestrator)**
- GPU execution ONLY: inference, upscaling, AI enhancement
- Takes database dictionaries as input
- Creates temporary NVIDIA-format JSON for GPU scripts
- No data persistence - returns results to service layer
- Handles remote SSH, Docker containers, file transfers

**3. Interface Layer (CLI)**
- User-friendly commands working with database IDs
- Rich terminal output with tables and colors
- JSON output support for scripting (--json flag)
- Error handling with clear, actionable messages

**4. Unified API Layer (WorkflowOperations)**
- High-level API combining service and orchestrator functionality
- Simplified methods: `quick_inference(prompt_id)` and `batch_inference(prompt_ids)` create runs internally
- Low-level methods: `create_run()` and `execute_run()` for advanced workflows
- Single interface for all workflow operations with intelligent defaults

### Workflow Example

**CLI Workflow:**
```bash
# 1. Data Layer: Create prompt in database
cosmos create prompt "cyberpunk city" inputs/videos/scene1
# → WorkflowService.create_prompt() → Database → Returns ps_abc123

# 2. Execution Layer: Run inference (creates run internally)
cosmos inference ps_abc123
# → WorkflowOperations.quick_inference() → Creates run → GPU → Results
```

**Simplified API Workflow:**
```python
from cosmos_workflow.api.workflow_operations import WorkflowOperations

ops = WorkflowOperations()

# Create prompt (same as CLI)
prompt = ops.create_prompt("cyberpunk city", "inputs/videos/scene1")
# → Returns: {"id": "ps_abc123", ...}

# Run inference directly with prompt_id (creates run internally)
result = ops.quick_inference("ps_abc123", weights={"vis": 0.3, "depth": 0.2})
# → Creates run, executes, returns: {"run_id": "rs_xyz789", "output_path": "...", "status": "success"}

# Or batch multiple prompts (creates runs internally)
results = ops.batch_inference(["ps_abc123", "ps_def456", "ps_ghi789"])
# → Creates runs for all prompts, executes as batch, returns batch results
```

### Batch Inference Processing

The system supports efficient batch processing of multiple inference jobs using NVIDIA Cosmos Transfer's batch mode:

```bash
# Create multiple prompts
cosmos create prompt "futuristic city" inputs/videos/scene1  # → ps_abc123
cosmos create prompt "cyberpunk street" inputs/videos/scene2 # → ps_def456
cosmos create prompt "neon alley" inputs/videos/scene3       # → ps_ghi789

# Execute all prompts as a batch for maximum efficiency
cosmos inference ps_abc123 ps_def456 ps_ghi789 --batch-name "city_scenes"
# → Creates runs internally → JSONL batch → Single GPU execution → Individual outputs
```

**Batch Processing Benefits:**
- **Reduced GPU Initialization** - Models stay loaded in memory between jobs
- **JSONL Format Support** - Native compatibility with NVIDIA Cosmos Transfer batch processing
- **Automatic Output Splitting** - Each run gets its own organized output folder
- **Control Weight Flexibility** - Per-run control weights with auto-generation for missing videos
- **Progress Tracking** - Individual run status updates within batch execution

**JSONL Format Structure:**
```json
{"visual_input": "/path/to/video.mp4", "prompt": "A futuristic city", "control_overrides": {"vis": {"control_weight": 0.3}, "depth": {"input_control": null, "control_weight": 0.2}}}
{"visual_input": "/path/to/video2.mp4", "prompt": "Cyberpunk street", "control_overrides": {"vis": {"control_weight": 0.4}, "seg": {"input_control": "/path/seg.mp4", "control_weight": 0.3}}}
```

## 🗄️ Database-First Architecture

All data is stored in a SQLAlchemy database with no persistent JSON files:

### Core Models
- **Prompt Model**: AI prompts with flexible JSON for inputs/parameters
  - ID format: ps_xxxxx (e.g., ps_a1b2c3d4)
  - Supports multiple AI models: transfer, enhancement, reason, predict
  - Extensible JSON columns allow future model types without schema changes

- **Run Model**: Execution tracking with complete lifecycle management
  - ID format: rs_xxxxx (e.g., rs_x9y8z7w6)
  - Status progression: pending → running → completed/failed
  - Links to prompts via foreign key relationships
  - Flexible execution configuration and output storage

- **Progress Model**: Real-time progress tracking for dashboard
  - Granular updates during uploading, inference, downloading stages
  - Percentage-based progress with human-readable messages

### Key Benefits
- **No JSON File Management**: Data lives in database, JSON only created temporarily for GPU scripts
- **Easy Analytics**: SQL queries enable dashboard creation and usage analytics
- **Multi-Model Ready**: Same schema supports current transfer model and future AI models
- **Transaction Safety**: Automatic rollback on errors, consistent data state
- **Security Built-in**: Input validation, path traversal protection, sanitization

See [docs/API.md](docs/API.md#database-schema) for complete database schema documentation.

## 📁 Output Structure

Each run creates a self-contained directory with all artifacts:

```
outputs/
└── run_rs_xxxxx/           # One directory per run
    ├── output.mp4           # Primary generated video
    ├── edge_input_control.mp4  # Generated control video
    ├── spec_used.json       # Actual spec sent to model
    ├── run.log             # Docker execution logs
    ├── execution.log       # UI execution logs (if run via UI)
    ├── output.txt          # Text output from process
    └── manifest.txt        # File manifest with sizes/timestamps
```

### Data Integrity

Use the `cosmos verify` command to check database-filesystem consistency:

```bash
# Check for missing files, orphaned directories, data mismatches
cosmos verify

# Future: auto-fix common issues
cosmos verify --fix
```

## 📚 Documentation

- **[Development Guide](docs/DEVELOPMENT.md)** - Setup, testing, TDD workflow
- **[API Reference](docs/API.md)** - Complete API documentation including batch processing and database schema
- **[Changelog](CHANGELOG.md)** - Version history
- **[Roadmap](ROADMAP.md)** - Planned features and improvements

## 🧪 Development

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest --cov=cosmos_workflow

# Format & lint (manual - pre-commit hooks are read-only)
ruff format .
ruff check . --fix
```

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for detailed development instructions.

## 🎯 Features

- **Database-First Architecture** - No JSON file management, all data in SQLAlchemy database
- **Service Layer Design** - Clean separation between data operations and GPU execution
- **Multi-AI Model Support** - Extensible schema supports transfer, enhancement, reason, predict models
- **Remote GPU Execution** - SSH-based orchestration with Docker containers
- **Batch Inference Processing** - Run multiple inference jobs together for improved efficiency
- **Real-Time Progress** - Granular tracking through all execution stages
- **Rich CLI Interface** - Database IDs, colored tables, JSON output support
- **Real-Time Log Streaming** - Live Docker execution logs with efficient seek-based tailing
- **Log Visualization Interface** - Advanced web-based log viewer with filtering, search, export, and real-time updates
- **Gradio Web UI** - Interactive web interface with live log streaming and integrated log viewer
- **AI Enhancement** - Prompt improvement using Pixtral with full tracking
- **Query & Search** - List, filter, and search prompts with highlighting
- **Production Ready** - 453 passing tests, comprehensive error handling

## 🌐 Gradio UI

Launch the interactive web interface:
```bash
cosmos ui
# Opens browser at http://localhost:7860
```

### Features
- **Two-Step Workflow**: Create prompts → Run inference with custom weights
- **Flexible Video Inputs**: Color video required, depth/segmentation optional
- **All Control Weights**: Configure visual, edge, depth, and segmentation weights (0.0-1.0)
- **Real-Time Log Streaming**: Live Docker execution logs streamed from remote GPU with efficient seek-based position tracking
- **Background Log Monitoring**: Non-blocking log streaming during inference execution
- **Advanced Log Visualization**: Interactive web-based log viewer with filtering, search, export, and syntax highlighting
- **Prompt Management**: View all prompts with video status indicators
- **Run Tracking**: Monitor inference progress and status with live logs
- **Gallery View**: Browse completed video generations
- **GPU Status**: Real-time GPU utilization and Docker container monitoring

### Control Weight System
- **Visual Weight**: Controls visual appearance fidelity
- **Edge Weight**: Controls edge detection influence
- **Depth Weight**: Controls depth map influence (auto-generated if not provided)
- **Segmentation Weight**: Controls semantic segmentation influence (auto-generated if not provided)

Videos are optional except for color - the model will auto-generate depth/segmentation if not provided but weights are still applied.

## 📸 UI Screenshots

### Generate Tab - Create & Run Inference
![Generate Tab](docs/images/generate-tab.png)

The main workflow tab with a two-step process:
- **Step 1**: Upload video files (color required, depth/segmentation optional) and enter your prompt text
- **Step 2**: Select a prompt from the database, configure control weights, and run inference with live Docker logs

### Prompts Tab - Manage Your Prompts
![Prompts Tab](docs/images/prompts-tab.png)

Browse and manage all created prompts with:
- Complete prompt history with text descriptions
- Video availability indicators (✓ for available videos)
- Creation timestamps and unique IDs
- Quick refresh to see new prompts

### Runs Tab - Track Inference Jobs
![Runs Tab](docs/images/runs-tab.png)

Monitor all inference runs with:
- Real-time status tracking (pending, running, completed, failed)
- Associated prompt information
- Creation timestamps and run IDs
- Automatic status updates during execution

### Gallery Tab - View Completed Videos
![Gallery Tab](docs/images/gallery-tab.png)

Browse your generated videos:
- Full video player with playback controls
- Auto-refreshing gallery of completed runs
- High-quality generated content display
- Download option for completed videos
- Shows generated architectural visualization with "Warm low-angle sunlight grazing facades" prompt

### Status Tab - System Monitoring
![Status Tab](docs/images/status-tab.png)

Real-time system information:
- GPU utilization and memory usage
- Docker container status
- Active process monitoring
- Auto-refreshing every 5 seconds

## ⚡ Performance

- Processes 100+ frame sequences efficiently
- Supports 4K video generation
- Multi-GPU scaling for faster inference
- Optimized SFTP transfers

## 📚 Documentation

- **[API Reference](docs/API.md)** - Complete API documentation, CLI commands, database schema
- **[Development Guide](docs/DEVELOPMENT.md)** - TDD workflow, testing guide, code conventions
- **[Shell Completion](docs/SHELL_COMPLETION.md)** - Setup shell completion for CLI commands
- **[Bash Shortcuts](docs/BASH_SHORTCUTS.md)** - Development productivity shortcuts
- **[Changelog](CHANGELOG.md)** - Version history and release notes
- **[Roadmap](ROADMAP.md)** - Future features and development plans
- **[CLAUDE.md](CLAUDE.md)** - Instructions for Claude AI assistant (TDD workflow)

## 📄 License

MIT License - See LICENSE file for details.

---

**Note**: This project requires access to NVIDIA Cosmos Transfer models and a compatible GPU instance.
