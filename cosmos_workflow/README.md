# Cosmos-Transfer1 Python Workflow System

A modern, modular Python workflow system that replaces the bash script approach for Cosmos-Transfer1 inference workflows. This system provides better error handling, cross-platform compatibility, and cleaner architecture while maintaining full compatibility with your existing configuration.

## 🏗️ Architecture Overview

The system is designed with clear separation of concerns and follows Python best practices:

```
cosmos_workflow/
├── config/                 # Configuration management
│   ├── __init__.py
│   └── config_manager.py  # Loads and validates config.sh
├── connection/            # SSH connection management
│   ├── __init__.py
│   └── ssh_manager.py    # Handles remote connections
├── transfer/              # File transfer services
│   ├── __init__.py
│   └── file_transfer.py  # Upload/download files
├── execution/             # Docker execution services
│   ├── __init__.py
│   └── docker_executor.py # Runs Docker commands
├── workflows/             # Workflow orchestration
│   ├── __init__.py
│   └── workflow_orchestrator.py # Coordinates everything
├── main.py               # CLI interface
└── README.md             # This file
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Basic Usage

```bash
# Run complete workflow (equivalent to full_cycle.sh)
python -m cosmos_workflow.main run prompt.json

# Run only inference
python -m cosmos_workflow.main inference prompt.json

# Run only upscaling
python -m cosmos_workflow.main upscale prompt.json

# Check remote status
python -m cosmos_workflow.main status
```

## 📖 Detailed Usage

### Run Complete Workflow

```bash
# Basic workflow
python -m cosmos_workflow.main run prompt.json

# Custom videos subdirectory
python -m cosmos_workflow.main run prompt.json --videos-subdir custom_videos

# Skip upscaling
python -m cosmos_workflow.main run prompt.json --no-upscale

# Custom upscale weight
python -m cosmos_workflow.main run prompt.json --upscale-weight 0.7

# Use multiple GPUs
python -m cosmos_workflow.main run prompt.json --num-gpu 2 --cuda-devices "0,1"

# Verbose logging
python -m cosmos_workflow.main run prompt.json --verbose
```

### Run Individual Steps

```bash
# Inference only
python -m cosmos_workflow.main inference prompt.json --videos-subdir custom_videos

# Upscaling only (requires existing inference output)
python -m cosmos_workflow.main upscale prompt.json --upscale-weight 0.6
```

### Check System Status

```bash
# Basic status
python -m cosmos_workflow.main status

# Detailed status with Docker info
python -m cosmos_workflow.main status --verbose
```

## 🔧 Configuration

The system automatically reads your existing `scripts/config.sh` file. No additional configuration is needed.

### Configuration Structure

```bash
# Remote instance settings
REMOTE_USER=ubuntu
REMOTE_HOST=192.222.53.15
REMOTE_PORT=22
SSH_KEY=$HOME/.ssh/LambdaSSHkey.pem
REMOTE_DIR=/home/ubuntu/NatsFS/cosmos-transfer1

# Docker image
DOCKER_IMAGE=nvcr.io/ubuntu/cosmos-transfer1:latest

# Local paths
LOCAL_PROMPTS_DIR=./inputs/prompts
LOCAL_VIDEOS_DIR=./inputs/videos
LOCAL_OUTPUTS_DIR=./outputs
LOCAL_NOTES_DIR=./notes
```

## 🎯 Key Features

### ✅ **Better Error Handling**
- Python exceptions instead of bash exit codes
- Detailed error messages with context
- Automatic retry and recovery where possible

### ✅ **Cross-Platform Compatibility**
- Works on Windows, macOS, and Linux
- No shell script dependencies
- Consistent behavior across platforms

### ✅ **Real-Time Progress Tracking**
- Live output streaming from remote commands
- Clear step-by-step progress indicators
- Emoji-based status indicators for better UX

### ✅ **Modular Architecture**
- Each component has a single responsibility
- Easy to test individual components
- Simple to extend with new features

### ✅ **Comprehensive Logging**
- Structured logging with configurable levels
- Automatic workflow logging to `notes/run_history.log`
- Detailed error logging for debugging

### ✅ **Backward Compatibility**
- Uses your existing `config.sh`
- Same output structure and file organization
- Compatible with existing workflow patterns

## 🔍 System Components

### **ConfigManager**
- Loads and parses `scripts/config.sh`
- Validates configuration values
- Provides typed configuration objects

### **SSHManager**
- Manages SSH connections with automatic reconnection
- Handles command execution with real-time output
- Provides SFTP access for file operations

### **FileTransferService**
- Uploads prompt files and video directories
- Downloads results and upscaled outputs
- Handles directory creation and file validation

### **DockerExecutor**
- Builds and executes Docker commands
- Manages GPU configuration and torchrun
- Creates upscaler specifications automatically

### **WorkflowOrchestrator**
- Coordinates all workflow steps
- Handles error recovery and logging
- Provides high-level workflow interfaces

## 🆚 Comparison with Bash Scripts

| Feature | Bash Scripts | Python Workflow |
|---------|--------------|-----------------|
| **Error Handling** | Exit codes | Python exceptions |
| **Cross-Platform** | Linux/macOS only | Windows/macOS/Linux |
| **Progress Tracking** | Basic echo statements | Real-time streaming |
| **Logging** | Manual file writing | Structured logging |
| **Testing** | Difficult | Easy with Python tools |
| **Extensibility** | Limited | Highly extensible |
| **Debugging** | Shell debugging | Python debugging |
| **Dependencies** | Shell + SSH + Docker | Python + paramiko |

## 🧪 Testing and Development

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run tests
pytest cosmos_workflow/ -v --cov=cosmos_workflow

# Run specific test file
pytest cosmos_workflow/tests/test_workflow_orchestrator.py -v
```

### Development Setup

```bash
# Install in development mode
pip install -e .

# Run linting
pip install flake8 black
flake8 cosmos_workflow/
black cosmos_workflow/
```

## 🔧 Troubleshooting

### Common Issues

#### **SSH Connection Failed**
```bash
# Check SSH key permissions
chmod 600 ~/.ssh/LambdaSSHkey.pem

# Verify connection manually
ssh -i ~/.ssh/LambdaSSHkey.pem ubuntu@192.222.53.15
```

#### **Docker Image Not Found**
```bash
# Check remote Docker images
python -m cosmos_workflow.main status --verbose

# Build image on remote if needed
ssh -i ~/.ssh/LambdaSSHkey.pem ubuntu@192.222.53.15
cd /path/to/cosmos-transfer1
docker build -f Dockerfile . -t nvcr.io/ubuntu/cosmos-transfer1:latest
```

#### **Permission Denied**
```bash
# Check file permissions
ls -la scripts/config.sh
ls -la ~/.ssh/LambdaSSHkey.pem

# Fix permissions if needed
chmod 644 scripts/config.sh
chmod 600 ~/.ssh/LambdaSSHkey.pem
```

### Debug Mode

```bash
# Enable verbose logging
python -m cosmos_workflow.main run prompt.json --verbose

# Check system status
python -m cosmos_workflow.main status --verbose
```

## 📚 API Reference

### **WorkflowOrchestrator**

```python
from cosmos_workflow.workflows.workflow_orchestrator import WorkflowOrchestrator

# Initialize orchestrator
orchestrator = WorkflowOrchestrator()

# Run complete workflow
result = orchestrator.run_full_cycle(
    prompt_file=Path("prompt.json"),
    videos_subdir="custom_videos",
    no_upscale=False,
    upscale_weight=0.5,
    num_gpu=1,
    cuda_devices="0"
)

# Run individual steps
orchestrator.run_inference_only(prompt_file)
orchestrator.run_upscaling_only(prompt_file)

# Check system status
status = orchestrator.check_remote_status()
```

### **Individual Services**

```python
from cosmos_workflow.config.config_manager import ConfigManager
from cosmos_workflow.connection.ssh_manager import SSHManager
from cosmos_workflow.transfer.file_transfer import FileTransferService
from cosmos_workflow.execution.docker_executor import DockerExecutor

# Use services directly if needed
config = ConfigManager()
ssh = SSHManager(config.get_ssh_options())
file_transfer = FileTransferService(ssh, config.get_remote_config().remote_dir)
docker_exec = DockerExecutor(ssh, config.get_remote_config().remote_dir, config.get_remote_config().docker_image)
```

## 🚀 Migration Guide

### **From Bash Scripts**

1. **Keep existing scripts** for now (they still work)
2. **Start using Python** for new workflows
3. **Gradually migrate** complex workflows
4. **Use both approaches** during transition

### **Equivalent Commands**

| Bash Script | Python Command |
|-------------|----------------|
| `./scripts/full_cycle.sh prompt.json` | `python -m cosmos_workflow.main run prompt.json` |
| `./scripts/run_inference_remote.sh prompt.json` | `python -m cosmos_workflow.main inference prompt.json` |
| `./scripts/run_upscale_remote.sh prompt.json` | `python -m cosmos_workflow.main upscale prompt.json` |
| `./scripts/ssh_lambda.sh` | `python -m cosmos_workflow.main status` |

## 🤝 Contributing

### **Code Style**
- Follow PEP 8 guidelines
- Use type hints for all functions
- Write comprehensive docstrings
- Keep functions small and focused

### **Testing**
- Write tests for new features
- Maintain >90% code coverage
- Test error conditions and edge cases

### **Documentation**
- Update this README for new features
- Add docstrings to all public methods
- Include usage examples

## 📄 License

This Python workflow system is part of your Cosmos-Transfer1 experiments repository and follows the same licensing terms.

## 🆘 Support

For issues or questions:
1. Check the troubleshooting section above
2. Enable verbose logging with `--verbose` flag
3. Check the system status with `python python/main.py status`
4. Review the logs in `notes/run_history.log`

---

**Happy Workflowing! 🎬✨**
