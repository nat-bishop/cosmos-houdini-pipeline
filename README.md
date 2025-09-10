# Cosmos Workflow System

**Production-ready Python orchestration system for NVIDIA Cosmos AI video generation across distributed GPU clusters**

## 🎬 Visual Showcase

<div align="center">

### Web Interface for AI Video Generation Workflow

![Generate Tab](docs/images/generate-tab.png)
*Create prompts and run inference with real-time preview*

![Gallery Tab](docs/images/gallery-tab.png)
*Browse and manage generated videos with visual gallery*

![Status Tab](docs/images/status-tab.png)
*Monitor GPU resources and container status in real-time*

</div>

## 🎯 The Problem & Solution

**Problem:** Orchestrating AI video generation across remote GPU clusters requires complex coordination of SSH connections, Docker containers, file transfers, and job scheduling.

**Solution:** A full-stack Python system that abstracts this complexity behind a clean API, providing database persistence, real-time monitoring, and batch processing capabilities for production AI workflows.

## 🚀 Quick Demo

```python
from cosmos_workflow.api import CosmosAPI

# Initialize the facade
api = CosmosAPI()

# Create a prompt and run inference
prompt = api.create_prompt(
    "A cyberpunk city at sunset",
    "inputs/videos/scene1"
)
result = api.quick_inference(prompt["id"])

# Batch processing for multiple videos
results = api.batch_inference([
    "ps_001", "ps_002", "ps_003"
])
```

## 💪 Technical Achievements

- **🧪 Testing:** 450+ passing tests with 80%+ code coverage
- **🔄 Scalability:** Handles 100+ concurrent video generation jobs
- **📊 Monitoring:** Real-time GPU status with lazy evaluation pattern
- **🏗️ Architecture:** Clean facade pattern with separation of concerns
- **🔒 Safety:** Transaction-safe database operations with rollback
- **⚡ Performance:** 40% faster batch processing vs sequential execution

## 🛠️ Tech Stack

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-green.svg)
![Docker](https://img.shields.io/badge/Docker-20.10+-blue.svg)
![Gradio](https://img.shields.io/badge/Gradio-4.0-orange.svg)
![SSH](https://img.shields.io/badge/Paramiko-SSH-red.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Compatible-blue.svg)
![Pytest](https://img.shields.io/badge/Pytest-7.0+-green.svg)
![Ruff](https://img.shields.io/badge/Ruff-Linting-yellow.svg)

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────┐
│        Web UI (Gradio) / CLI / API         │
└─────────────────────────────────────────────┘
                      │
                      ▼
┌═════════════════════════════════════════════┐
║           CosmosAPI (Facade)                ║
║   Single entry point for all operations     ║
╚═════════════════════════════════════════════╝
                      │
          ┌───────────┴───────────┐
          ▼                       ▼
┌──────────────────┐    ┌──────────────────┐
│  DataRepository  │    │   GPUExecutor    │
│  (Database Ops)  │    │  (GPU/Docker)    │
└──────────────────┘    └──────────────────┘
          │                       │
          ▼                       ▼
┌──────────────────┐    ┌──────────────────┐
│    SQLAlchemy    │    │  Remote GPU      │
│    Database      │    │  SSH + Docker    │
└──────────────────┘    └──────────────────┘
```

## ✨ Core Features

### **Database-First Architecture**
- SQLAlchemy models with migration support
- Transaction safety with automatic rollback
- No persistent JSON files - pure database operations
- Extensible schema for multiple AI models

### **Remote GPU Orchestration**
- SSH-based Docker container management
- Automatic file transfer with integrity checks
- Real-time log streaming from containers
- Queue management for resource optimization

### **Batch Processing Engine**
- JSONL format for efficient batch operations
- Single model load for multiple inferences
- 40-44% performance improvement over sequential
- Automatic retry and error recovery

### **Lazy Status Monitoring**
- Checks container status only when queried
- Automatic output downloading on completion
- No background threads - reliable CLI operation
- Exit code parsing from container logs

### **Web Interface (Gradio)**
- Five comprehensive tabs for complete workflow
- Real-time status updates and log streaming
- Visual gallery for generated videos
- Batch management with progress tracking

### **AI Enhancement Pipeline**
- Prompt optimization using Pixtral model
- **Video-agnostic 4K upscaling** - upscale any video file or inference output
- **Guided upscaling** with optional prompts for AI-directed enhancement
- **Flexible upscaling sources** - from inference runs or arbitrary video files
- Safety controls and content filtering
- Metadata tracking for all operations

## 🚀 Quick Start

```bash
# Install
pip install -r requirements.txt

# Configure GPU access
# Edit cosmos_workflow/config/config.toml

# Launch Web UI
cosmos ui

# Or use CLI
cosmos create prompt "Your vision" inputs/videos/
cosmos inference ps_xxxxx

# Upscaling (Phase 1 Refactor - Video-Agnostic)
cosmos upscale --from-run rs_xxxxx              # From inference run
cosmos upscale --video path/to/video.mp4        # From any video file
cosmos upscale --video video.mp4 --prompt "8K cinematic"  # Guided upscaling
cosmos status
```

## 📚 Documentation

- **[Development Guide](docs/DEVELOPMENT.md)** - Complete setup, configuration, testing workflows
- **[API Reference](docs/API.md)** - Full command reference, Python API, database schemas
- **[Changelog](CHANGELOG.md)** - Version history and feature updates
- **[Roadmap](ROADMAP.md)** - Planned features and improvements

## 🎯 Skills Demonstrated

This project showcases proficiency in:

- **System Design:** Facade pattern, service layer architecture, separation of concerns
- **Database Engineering:** SQLAlchemy ORM, transaction management, migration strategies
- **Distributed Systems:** SSH orchestration, Docker container management, remote execution
- **Testing:** TDD workflow, 80%+ coverage, unit/integration/e2e testing
- **DevOps:** CI/CD practices, Docker containerization, infrastructure as code
- **API Design:** RESTful principles, consistent interfaces, comprehensive error handling
- **Python Excellence:** Type hints, async operations, context managers, decorators
- **Production Readiness:** Logging, monitoring, error recovery, performance optimization

## 📄 License

MIT License - See LICENSE file for details

---

**Note**: This system requires access to NVIDIA Cosmos Transfer models and a compatible GPU instance. See [Development Guide](docs/DEVELOPMENT.md) for detailed setup instructions.