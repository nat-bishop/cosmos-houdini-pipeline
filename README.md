# Cosmos Workflow System

A Python workflow orchestrator for NVIDIA Cosmos Transfer video generation with remote GPU execution.

[![Test Coverage](https://img.shields.io/badge/coverage-80%25-green.svg)](tests/)
[![Tests](https://img.shields.io/badge/tests-453%20passing-brightgreen.svg)](tests/)
[![Architecture](https://img.shields.io/badge/architecture-service%20layer-blue.svg)](docs/API.md)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- SSH access to GPU instance with NVIDIA Cosmos Transfer
- Docker on remote instance

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

### Basic Usage
```bash
# Create a prompt (returns database ID)
cosmos create prompt "A futuristic city at sunset" inputs/videos/scene1
# Returns: Created prompt ps_a1b2c3d4 with name "futuristic_city_sunset"

# Create a run from the prompt
cosmos create run ps_a1b2c3d4
# Returns: Created run rs_x9y8z7w6 for prompt ps_a1b2c3d4

# Execute the run on GPU
cosmos inference rs_x9y8z7w6

# Or use the Gradio UI
cosmos ui

# Check status
cosmos status
```

## 📁 Commands

### Database Operations
- `cosmos create prompt "text" video_dir` - Create prompt in database, returns ps_xxxxx ID
- `cosmos create run ps_xxxxx` - Create run from prompt ID, returns rs_xxxxx ID
- `cosmos list prompts [--model transfer] [--limit 50] [--json]` - List prompts with filtering
- `cosmos list runs [--status completed] [--prompt ps_xxxxx] [--json]` - List runs with filtering
- `cosmos search "query" [--limit 50] [--json]` - Full-text search prompts with highlighting
- `cosmos show ps_xxxxx [--json]` - Detailed prompt view with run history

### GPU Execution
- `cosmos inference rs_xxxxx [--upscale/--no-upscale]` - Execute run on GPU with status tracking
- `cosmos prompt-enhance ps_xxxxx [--resolution 480]` - AI prompt enhancement (creates new prompt + run)
- `cosmos prepare input_dir [--name scene]` - Prepare video sequences for inference
- `cosmos status [--stream]` - Check GPU status or stream container logs

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

### Workflow Example
```bash
# 1. Data Layer: Create prompt in database
cosmos create prompt "cyberpunk city" inputs/videos/scene1
# → WorkflowService.create_prompt() → Database → Returns ps_abc123

# 2. Data Layer: Create run from prompt
cosmos create run ps_abc123
# → WorkflowService.create_run() → Database → Returns rs_xyz789

# 3. Execution Layer: Execute on GPU
cosmos inference rs_xyz789
# → WorkflowOrchestrator.execute_run() → GPU → Results → WorkflowService.update_run()
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

See [docs/DATABASE.md](docs/DATABASE.md) for complete schema documentation.

## 📚 Documentation

- **[Development Guide](docs/DEVELOPMENT.md)** - Setup, testing, TDD workflow
- **[Formatting Guide](docs/FORMATTING.md)** - Code formatting philosophy and workflow
- **[API Reference](docs/API.md)** - Complete API documentation
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
- **Real-Time Progress** - Granular tracking through all execution stages
- **Rich CLI Interface** - Database IDs, colored tables, JSON output support
- **Gradio Web UI** - Interactive web interface for prompt creation and inference
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
- **Live Log Streaming**: Real-time Docker output with efficient seek-based tailing
- **Prompt Management**: View all prompts with video status indicators
- **Run Tracking**: Monitor inference progress and status
- **Gallery View**: Browse completed video generations
- **GPU Status**: Real-time GPU utilization and Docker container monitoring

### Control Weight System
- **Visual Weight**: Controls visual appearance fidelity
- **Edge Weight**: Controls edge detection influence
- **Depth Weight**: Controls depth map influence (auto-generated if not provided)
- **Segmentation Weight**: Controls semantic segmentation influence (auto-generated if not provided)

Videos are optional except for color - the model will auto-generate depth/segmentation if not provided but weights are still applied.

## ⚡ Performance

- Processes 100+ frame sequences efficiently
- Supports 4K video generation
- Multi-GPU scaling for faster inference
- Optimized SFTP transfers

## 📄 License

MIT License - See LICENSE file for details.

---

**Note**: This project requires access to NVIDIA Cosmos Transfer models and a compatible GPU instance.
