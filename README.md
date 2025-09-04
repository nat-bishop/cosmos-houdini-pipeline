# Cosmos Workflow System

A Python workflow orchestrator for NVIDIA Cosmos Transfer video generation with remote GPU execution.

[![Test Coverage](https://img.shields.io/badge/coverage-80%25-green.svg)](tests/)
[![Tests](https://img.shields.io/badge/tests-613%20tests-brightgreen.svg)](tests/)
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
# Create a prompt
cosmos create prompt "A futuristic city at sunset"

# Run inference (with upscaling)
cosmos inference prompt_spec.json

# Check status
cosmos status
```

## 📁 Commands

- `cosmos create prompt` - Create prompt specifications
- `cosmos inference` - Run inference with optional upscaling
- `cosmos prompt-enhance` - Enhance prompts with AI
- `cosmos prepare` - Prepare renders for inference
- `cosmos status` - Check remote GPU status
- `cosmos status --stream` - Stream Docker container logs in real-time

For shell completion setup, see [docs/SHELL_COMPLETION.md](docs/SHELL_COMPLETION.md)

## 🏗️ Project Structure
```
cosmos_workflow/
├── cli/             # CLI commands
├── workflows/       # Orchestration logic
├── connection/      # SSH/SFTP management
├── execution/       # Docker execution
├── database/        # SQLAlchemy models & connection management
├── prompts/         # Schema definitions
├── local_ai/        # AI processing
└── config/          # Configuration
```

## 🗄️ Database System

The Cosmos Workflow System includes a flexible database foundation supporting multiple AI models:

### Key Features
- **Multi-Model Support**: Extensible schema for transfer, reason, predict, and future AI models
- **Flexible JSON Storage**: Model-specific inputs and parameters stored in JSON columns
- **Real-Time Progress**: Granular tracking through uploading, inference, and downloading stages
- **Security First**: Path traversal protection and input validation
- **Transaction Safety**: Automatic rollback on errors with session management

### Database Models
- **`Prompt`**: AI model prompts with flexible inputs and parameters
- **`Run`**: Execution tracking with status lifecycle management
- **`Progress`**: Real-time progress updates for dashboard visualization

See [docs/DATABASE.md](docs/DATABASE.md) for detailed database documentation.

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

- **Remote GPU Execution** - SSH-based orchestration
- **Multi-GPU Support** - Configurable CUDA devices
- **AI Enhancement** - Prompt improvement with Pixtral
- **Video Processing** - Frame extraction and metadata
- **Progress Tracking** - Real-time transfer monitoring

## ⚡ Performance

- Processes 100+ frame sequences efficiently
- Supports 4K video generation
- Multi-GPU scaling for faster inference
- Optimized SFTP transfers

## 📄 License

MIT License - See LICENSE file for details.

---

**Note**: This project requires access to NVIDIA Cosmos Transfer models and a compatible GPU instance.
