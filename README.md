# Cosmos Workflow System

A professional Python workflow orchestrator for NVIDIA Cosmos Transfer video generation with remote GPU execution.

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- SSH access to GPU instance with NVIDIA Cosmos Transfer
- Docker on remote instance

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/cosmos-houdini-experiments.git
cd cosmos-houdini-experiments

# Install dependencies
pip install -r requirements.txt

# Install development dependencies (optional)
pip install -r requirements-dev.txt
pre-commit install
```

### Configuration

Create `cosmos_workflow/config/config.toml`:

```toml
[remote]
host = "192.222.52.92"
user = "ubuntu"
ssh_key = "~/.ssh/your-key.pem"
port = 22

[paths]
remote_dir = "/home/ubuntu/NatsFS/cosmos-transfer1"

[docker]
image = "nvcr.io/ubuntu/cosmos-transfer1:latest"
```

### Basic Usage

```bash
# 1. Create a prompt specification
python -m cosmos_workflow.cli create-spec "my_scene" "A futuristic city at sunset"

# 2. Create a run configuration with control weights
python -m cosmos_workflow.cli create-run prompt_spec.json --weights 0.3 0.4 0.2 0.1

# 3. Execute on remote GPU
python -m cosmos_workflow.cli run run_spec.json --num-gpu 2

# 4. Check remote status
python -m cosmos_workflow.cli status
```

## 📁 Key Commands

### Video Processing
```bash
# Convert PNG sequence to video
python -m cosmos_workflow.cli convert-sequence ./renders/sequence/ --fps 30 --resolution 1080p

# Prepare Cosmos sequences for inference
python -m cosmos_workflow.cli prepare-inference ./cosmos_sequences/ --name "my_scene" --fps 24
```

### Workflow Management
```bash
# Run full pipeline (upload → inference → upscale → download)
python -m cosmos_workflow.cli run prompt.json --upscale

# Run inference only
python -m cosmos_workflow.cli run-inference prompt.json

# Run upscaling only
python -m cosmos_workflow.cli run-upscale prompt.json --weight 0.5
```

## 🎯 Features

### Core Capabilities
- **Remote GPU Execution** - SSH-based orchestration with Docker
- **Cross-Platform** - Windows/Linux/macOS compatible SFTP transfers
- **Multi-GPU Support** - Configurable CUDA device allocation
- **Schema Management** - Structured prompt and run specifications

### AI Integration
- **Smart Naming** - AI-powered descriptive names from prompts
- **Video Analysis** - Automatic metadata extraction and description
- **Content Understanding** - BLIP model for scene analysis

### Developer Tools
- **Modern Linting** - Ruff, MyPy, Bandit for code quality
- **Comprehensive Testing** - Unit, integration, and system tests
- **Pre-commit Hooks** - Automated quality checks
- **Type Hints** - Full type annotation coverage

## 🏗️ Architecture

```
cosmos_workflow/
├── config/          # Configuration management
├── connection/      # SSH/SFTP connections
├── execution/       # Docker orchestration
├── prompts/         # Schema definitions
├── transfer/        # File transfers
├── local_ai/        # AI features
└── workflows/       # Pipeline orchestration
```

## 🧪 Development

### Running Tests
```bash
# All tests with coverage
pytest --cov=cosmos_workflow

# Specific test categories
pytest -m unit           # Fast unit tests
pytest -m integration    # Integration tests
pytest -m system        # End-to-end tests
```

### Code Quality
```bash
# Run linting
make lint

# Format code
make format

# Security scan
make security

# All checks
make check-all
```

### Using Make Commands
```bash
make help        # Show all available commands
make dev         # Install dev dependencies
make test        # Run tests with coverage
make clean       # Clean cache files
```

## 📊 Project Status

- **Version**: 0.3.0
- **Test Coverage**: 80%+
- **Python**: 3.10+
- **License**: MIT

## 🔧 Configuration Options

See `config.toml.example` for all available options:
- SSH connection settings
- Docker runtime configuration
- Path mappings
- GPU allocation
- Logging levels

## 📚 Documentation

- **[Documentation Index](docs/README.md)** - Complete documentation guide
- [Quick Start](#-quick-start) - Get started immediately
- [Testing Results](docs/TESTING_RESULTS.md) - Performance benchmarks & testing
- [API Reference](REFERENCE.md) - Detailed API documentation
- [Changelog](CHANGELOG.md) - Version history
- [AI Context](docs/ai-context/PROJECT_STATE.md) - Current project state

## 🤝 Contributing

This is currently a private project for internal development. For questions or issues, please contact the maintainer.

## ⚡ Performance

- Processes 100+ frame sequences in seconds
- Supports 4K video generation
- Multi-GPU scaling for faster inference
- Optimized SFTP transfers with progress tracking

## 🔒 Security

- SSH key authentication only
- Secure configuration management
- No hardcoded credentials
- Regular dependency scanning

---

**Note**: This project requires access to NVIDIA Cosmos Transfer models and a compatible GPU instance.
