# Cosmos Workflow System

A professional Python workflow orchestrator for NVIDIA Cosmos Transfer video generation with remote GPU execution.

[![Test Coverage](https://img.shields.io/badge/coverage-75%25-green.svg)](tests/)
[![Tests](https://img.shields.io/badge/tests-614%20passing-brightgreen.svg)](tests/)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)

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

# Install Python dependencies
pip install click rich paramiko toml pyyaml

# The 'cosmos' command is now available via:
# 1. Direct Python script (Windows/Unix/Mac):
python cosmos --help

# 2. Or via Python module:
python -m cosmos_workflow --help
```

#### Optional: Add to PATH for direct `cosmos` command

**Windows (Command Prompt/PowerShell):**
```bash
# Add current directory to PATH for this session
set PATH=%PATH%;%cd%

# Or use cosmos.bat directly
cosmos.bat --help
```

**Unix/Linux/Mac:**
```bash
# Make script executable
chmod +x cosmos

# Add to PATH for this session
export PATH="$PATH:$(pwd)"

# Or add permanently to ~/.bashrc or ~/.zshrc
echo 'export PATH="$PATH:/path/to/cosmos-houdini-experiments"' >> ~/.bashrc
```

**Git Bash (Windows):**
```bash
# Use the Python script directly
python cosmos --help

# Or create an alias in ~/.bashrc
echo "alias cosmos='python /path/to/cosmos-houdini-experiments/cosmos'" >> ~/.bashrc
source ~/.bashrc
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
# After setup, you can use the 'cosmos' command directly:

# 1. Create a prompt specification
cosmos create prompt "A futuristic city at sunset" --name my_scene

# 2. Execute on remote GPU
cosmos run prompt_spec.json --num-gpu 2

# 3. Check remote status
cosmos status

# Or use Python module directly (always works):
python -m cosmos_workflow create prompt "A futuristic city"
```

## 📁 Key Commands

### Command Structure
```bash
cosmos <command> [options]

Commands:
  create prompt     Create a new prompt specification
  create run        Create a run specification
  run              Execute full workflow (inference + upscaling)
  inference        Run inference only
  upscale          Run upscaling only
  prompt-enhance   Enhance prompts with AI (formerly 'upsample')
  prepare          Prepare Houdini/Blender renders for inference
  status           Check remote GPU status
  completion       Setup shell completion
  version          Show version info
```

### Examples
```bash
# Create and run a prompt
cosmos create prompt "Transform to cyberpunk style" --video input.mp4
cosmos run prompt_spec.json --num-gpu 2

# Prepare renders from Houdini/Blender
cosmos prepare ./renders/ --name city_scene --fps 24

# Enhance prompts with AI
cosmos prompt-enhance prompts/ --save-dir enhanced/

# Check system status
cosmos status --verbose
```

## 🔧 Shell Completion

Enable tab completion for better CLI experience:

### Windows PowerShell
```powershell
# Show setup instructions
cosmos completion powershell

# Or add to $PROFILE manually:
notepad $PROFILE
# Add the completion script shown by the command above
```

### Git Bash (Windows)
```bash
# Show setup instructions
cosmos completion gitbash

# Or add to ~/.bashrc:
eval "$(_COSMOS_COMPLETE=bash_source python /path/to/cosmos)"
```

### Linux/Mac Bash
```bash
# Add to ~/.bashrc
eval "$(_COSMOS_COMPLETE=bash_source cosmos)"
source ~/.bashrc
```

### Zsh
```bash
# Add to ~/.zshrc
eval "$(_COSMOS_COMPLETE=zsh_source cosmos)"
source ~/.zshrc
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
