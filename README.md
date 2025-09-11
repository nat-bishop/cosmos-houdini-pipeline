# Cosmos Workflow System

**Production-style Python orchestration system for NVIDIA Cosmos AI video generation across remote GPU instances. I created Synthetic, multimodal data with my fully procedural destoryed city generator (created with Houdini) then augment the data with Cosmos Transfer for use in Physical AI. This tool manages the full end-to-end workflow through synthetic randomized data creation from Houdini, to prompt creation, to Cosmos Augmentation, to artifact retreival. Launches remote jobs into docker containers with fily sync and container lifecycle control. Fully featured Gradio UI and command line interface that supports batch inference, 4K upscaling, prompt enhancing, realtime log viewing, experiment data management and more.**

## 🎯 The Problem & Solution

**Problem:** Orchestrating AI video generation across remote GPU clusters requires complex coordination of SSH connections, Docker containers, file transfers, and job scheduling. Using multimodal synthetic inputs (Omniverse, Houdini, ect.), adds more complexity.

**Solution:** A full-stack Python system that abstracts this complexity behind a clean API, providing database persistence, real-time monitoring, and batch processing capabilities for production AI workflows.

<div align="center">

### Example multimodal Result using tool
https://github.com/user-attachments/assets/d9670944-7518-4f0b-a58d-75ce4e901672

## Gradio UI
### Advanced Operations Interface with Two-Column Layout

![Operations Interface](docs/images/inference.png)
*New Operations tab with prompt selection and inference controls including adjustable weights*

### Multimodal Input Support

![Multimodal Inputs](docs/images/multimodal-inputs.png)
*Support for color, depth, edge, and segmentation control inputs with flexible weight system*

### Prompt Creation & Enhancement

![Prompt Creation](docs/images/prompt-creation.png)
*Create prompts with AI enhancement using Pixtral model for improved descriptions*


### Results & Log Streaming

<table>
<tr>
<td width="50%">

![Results Gallery](docs/images/results.png)
*Visual gallery for generated videos with metadata*

</td>
<td width="50%">

![Real-time Logs](docs/images/log-streaming.png)
*Real-time log streaming with theme-aware CSS variables*

</td>
</tr>
</table>

</div>

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

## Houdini Procedural Generation
- I authored a production ready procedural Houdini tool to randomly generate destroyed cities
- Using synthetic data as input for Cosmos Transfer helps support synthetic data for rare situations
- Can export variety of different pixel perfect control inputs (segemnetaion, spatiotemporal control, depth, edge, lidar, ect.)
  - Avoids innacurate depth map/segmentation mask generation using AI
- Features automated rigid body dynamics for the destruction simulation to create the damage to the buildings.
**Example New York City building with fire escape generated with tool""
https://github.com/user-attachments/assets/a78f251d-52b1-4764-b65c-19555e1f1a84

## 💪 Technical Achievements

- **🧪 Testing:** 450+ passing tests with 80%+ code coverage
- **🎨 Advanced UI:** Two-column Operations interface with intelligent prompt selection and fine-grained inference controls
- **🤖 AI Integration:** Pixtral model integration for prompt enhancement and semantic improvement
- **🎥 Video Pipeline Innovation:** Seamless integration with NVIDIA Cosmos Transfer models for AI video generation
- **🔄 Video-Agnostic Upscaling:** Universal 4K upscaling system that works with any video source (inference outputs or arbitrary files)
- **🌐 Remote GPU Orchestration:** SSH-based Docker container management across distributed GPU infrastructure
- **📊 Monitoring:** Real-time GPU status with lazy evaluation pattern and theme-aware log visualization
- **🏗️ Architecture:** Clean facade pattern with separation of concerns and proper dependency injection
- **🔧 Robust File Transfer:** SFTP-based file synchronization with integrity verification and retry mechanisms

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
│           Web UI (Gradio) / CLI             │
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
- Streamlined batch execution with shared GPU resources
- Automatic retry and error recovery

### **Lazy Status Monitoring**
- Checks container status only when queried
- Automatic output downloading on completion
- No background threads - reliable CLI operation
- Exit code parsing from container logs

### **Advanced Web Interface (Gradio)**
- **Operations Tab**: New two-column layout with prompt selection and inference controls
- **Inference Controls**: Adjustable weights for visual, edge, depth, and segmentation controls (0.0-1.0)
- **AI Enhancement**: Prompt enhancement using Pixtral model for improved descriptions
- **Theme System**: Proper dark/light mode support respecting system preferences
- **Real-time Monitoring**: Log streaming with CSS variables instead of hardcoded colors
- **Visual Gallery**: Browse and manage generated videos with comprehensive metadata
- **Batch Management**: Progress tracking for multiple inference operations

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

---

**Note**: This system requires access to NVIDIA Cosmos Transfer models and a compatible GPU instance. See [Development Guide](docs/DEVELOPMENT.md) for detailed setup instructions.
