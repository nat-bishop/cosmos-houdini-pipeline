# Cosmos Workflow System

**A production Python system that orchestrates NVIDIA Cosmos AI video generation on remote GPU clusters, featuring a custom Houdini procedural city generator for synthetic training data.**

## 📑 Table of Contents
- [What This System Does](#-what-this-system-does)
- [Why This Matters](#-why-this-matters)
- [Gradio Web Interface](#️-gradio-web-interface)
- [Code Example](#-code-example)
- [Houdini Procedural City Generator](#️-houdini-procedural-city-generator-input-creation)
- [Technical Achievements](#-technical-achievements)
- [Tech Stack](#️-tech-stack)
- [System Architecture](#️-system-architecture)
- [Core Features](#-core-features)
- [Quick Start](#-quick-start)
- [Documentation](#-documentation)
- [Skills Demonstrated](#-skills-demonstrated)
- [Requirements](#-requirements)
- [Future Work](#-future-work)

## 🎯 What This System Does

• **Generates synthetic training data** using my custom Houdini tool that creates destroyed cities with perfect multimodal outputs (depth, segmentation, etc.)

• **Orchestrates AI video generation** on remote H100 GPU instances via SSH and Docker

• **Manages complex workflows** from data creation → AI processing → output retrieval with database tracking

• **Provides enterprise features** like batch processing (40% faster), real-time monitoring, and 4K upscaling

• **Abstracts infrastructure complexity** behind a clean Python API and Gradio UI

## 📋 Why This Matters

Physical AI models need diverse synthetic data for rare scenarios (destroyed buildings, disasters). My system combines procedural 3D generation with state-of-the-art AI video models to create this data at scale, managing the entire pipeline from creation to augmentation.

<div align="center">

### 🎥 AI-Generated Result: Destroyed City Scene


https://github.com/user-attachments/assets/ca96da3a-ef7a-4625-beda-ebeae7dcfb94


*Cosmos AI output using my Houdini-generated synthetic inputs (color + depth + segmentation)*

</div>

## 🖥️ Gradio Web Interface

<table>
<tr>
<td width="50%">

### Operations & Control
![Operations Interface](docs/images/inference.png)
*Two-column layout with prompt selection and inference controls*

</td>
<td width="50%">

### Multimodal Inputs
![Multimodal Inputs](docs/images/multimodal-inputs.png)
*Weight control for depth, edge, segmentation (0.0-1.0)*

</td>
</tr>
<tr>
<td width="50%">

### AI Enhancement
![Prompt Creation](docs/images/prompt-creation.png)
*Pixtral model integration for prompt improvement*

</td>
<td width="50%">

### Real-time Monitoring
![Real-time Logs](docs/images/log-streaming.png)
*Live log streaming with theme-aware display*

</td>
</tr>
</table>

![Results Gallery](docs/images/results.png)
*Gallery view showing generated videos with metadata and batch processing status*

</div>

## 🚀 Code Example

```python
from cosmos_workflow.api import CosmosAPI

# Single interface for entire system
api = CosmosAPI()

# Create prompt from Houdini-generated videos
prompt = api.create_prompt(
    "Transform this destroyed city into cyberpunk style",
    "outputs/houdini_export/scene_042/"  # Contains color.mp4, depth.mp4, segmentation.mp4
)

# Run on remote H100 GPU with multimodal control
result = api.quick_inference(
    prompt["id"],
    weights={"vis": 0.3, "edge": 0.4, "depth": 0.2, "seg": 0.1}
)
print(f"Generated: {result['output_path']}")  # outputs/run_rs_abc123/output.mp4

# Batch process multiple scenes (40% faster)
results = api.batch_inference(
    ["ps_001", "ps_002", "ps_003"],
    shared_weights={"vis": 0.25, "edge": 0.25, "depth": 0.25, "seg": 0.25}
)
```

## 🏗️ Houdini Procedural City Generator (Input Creation)

I built a production-ready Houdini tool that generates the synthetic input data for Cosmos AI:

• **Procedural city generation** - Randomized buildings with architectural details (fire escapes, facades)

• **Destruction simulation** - Automated rigid body dynamics create realistic damage patterns

• **Perfect multimodal outputs** - Pixel-perfect depth, segmentation, edge maps (no AI estimation errors)

• **Rare scenario data** - Generates training data for edge cases like disasters and destroyed infrastructure

<table>
<tr>
<td width="50%">

### Rendered Building Output

https://github.com/user-attachments/assets/43565e9a-f675-4ec1-b454-e8318f611194

*NYC-style building with fire escape (Houdini render)*

</td>
<td width="50%">

### Houdini Node Network

![Houdini UI](docs/images/houdini-ui.jpg)

*Procedural generation network in Houdini*

</td>
</tr>
</table>

**Note:** These are the INPUT renders from Houdini that get processed by Cosmos AI, not the final AI output.


## 💪 Technical Achievements

### Infrastructure & Scale
• **Remote GPU orchestration** - Manages GPUs (H100, H200, ect.) via SSH/Docker with zero downtime

• **40-60% performance gains** - Batch inference reduces model loading overhead, processing 10 videos in 50min vs 90min sequential

• **Lazy evaluation monitoring** - Novel pattern solving CLI lifecycle issues (runs don't get stuck as "running")

• **Production reliability** - Automatic retry, graceful degradation, comprehensive error recovery

### Architecture & Code Quality
• **Database-first design** - SQLAlchemy database systen, no JSON file management

• **Comprehensive testing** - 600+ tests with 80%+ coverage on critical paths

• **Enterprise patterns** - Dependency injection, parameterized logging

### AI & Video Processing
• **Multimodal pipeline** - Handles color, depth, segmentation, edge maps with weight control (0.0-1.0)

• **Video-agnostic 4K upscaling** - Works with any video source, not just inference outputs

• **Pixtral AI enhancement** - Automatic prompt improvement using vision-language models

• **Real-time streaming** - Live log streaming from containers with gradio GUI + CLI

## 🛠️ Tech Stack

**Core:** Python 3.10+ • SQLAlchemy 2.0 • Gradio 4.0
**Infrastructure:** Docker • SSH (Paramiko) • SFTP
**AI/ML:** NVIDIA Cosmos • KEYbert • Houdini (procedural generation)
**Testing:** Pytest • Ruff • MyPy • 80%+ coverage
**Scale:** H100 GPUs • Batch processing • Real-time streaming

## 🏗️ System Architecture

```
Local Machine                                    Remote GPU Server (H100)
┌─────────────────────────────────────────┐     ┌────────────────────────────┐
│       Gradio UI / CLI / Python API      │     │   Docker Container         │
│                  ↓                      │     │   ┌──────────────────┐     │
│  ┌═══════════════════════════════════┐  │     │   │ Cosmos AI Model  │     │
│  ║       CosmosAPI (Facade)          ║  │     │   │ GPU Execution    │     │
│  ║                                   ║  │ SSH │   │ Real-time Logs   │     │
│  ╚═══════════════════════════════════╝  │ ───>│   └──────────────────┘     │
│           ↓              ↓              │     │                            │
│  ┌──────────────┐    ┌───────────────┐  │ SFTP│   Generated Videos:        │
│  │DataRepository│    │ GPUExecutor   │  │ <───│   • output.mp4             │
│  │(Database Ops)│    │(Orchestration)│  │     │   • upscaled_4K.mp4        │
│  └──────────────┘    └───────────────┘  │     │                            │
│           ↓              ↓              │     └────────────────────────────┘
│  ┌───────────────────────────────────┐  │
│  │     SQLAlchemy + SQLite DB        │  │
│  │     (Prompts, Runs, Metadata)     │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
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
# Install and configure
pip install -r requirements.txt
edit cosmos_workflow/config/config.toml  # Add GPU server details

# Launch web interface
cosmos ui  # Opens at http://localhost:7860

# Or use CLI
cosmos create prompt "Cyberpunk transformation" outputs/houdini/scene_001/
cosmos inference ps_xxxxx --weights 0.3 0.4 0.2 0.1
cosmos status --stream  # Watch live execution

# Advanced features
cosmos batch-inference ps_001 ps_002 ps_003  # 40% faster
cosmos upscale --from-run rs_xxxxx --prompt "8K cinematic"
cosmos prompt-enhance ps_xxxxx  # AI prompt improvement
```

## 📚 Documentation

- **[Development Guide](docs/DEVELOPMENT.md)** - Complete setup, configuration, testing workflows
- **[API Reference](docs/API.md)** - Full command reference, Python API, database schemas
- **[Changelog](CHANGELOG.md)** - Version history and feature updates
- **[Roadmap](ROADMAP.md)** - Planned features and improvements

## 🎯 Skills Demonstrated

### System Architecture
• Designed facade pattern abstracting 40+ modules behind single API

• Implemented database-first architecture with SQLAlchemy ORM

• Created lazy evaluation pattern solving distributed system lifecycle issues

### Infrastructure & DevOps
• Orchestrated remote GPU clusters via SSH/Docker automation

• Built SFTP file transfer with integrity verification and retry logic

• Implemented real-time log streaming from remote containers

### Performance & Scale
• Achieved 40-60% speedup through batch processing optimization

• Managed concurrent operations on H100 GPUs

• Built transaction-safe database operations with automatic rollback

### Python & Software Engineering
• Comprehensive type hints and Google-style docstrings

• Context managers for resource management

• Parameterized logging for production debugging

• Clean separation of concerns across service layers

---

## 📦 Requirements

- **GPU Server**: NVIDIA H100 or similar with Docker and NVIDIA Container Toolkit
- **Cosmos Models**: Access to NVIDIA Cosmos Transfer checkpoints (Hugging Face)
- **Python 3.10+**: With SQLAlchemy, Paramiko, Gradio dependencies
- **Houdini**: For procedural city generation (optional, pre-generated data included)

See [Development Guide](docs/DEVELOPMENT.md) for detailed setup.

---

## 🚀 Future Work

### Post-Training NVIDIA Cosmos with Synthetic Disaster Data

This project positions itself at the forefront of **physical AI model improvement** through specialized synthetic data generation. The unique contribution lies in creating high-quality training data for rare but critical scenarios that are difficult or dangerous to capture in real life.

#### Planned Enhancements:

**1. Domain-Specific Post-Training Pipeline**
- Generate 100,000+ hours of synthetic earthquake/disaster scenarios using my Houdini procedural system
- Create perfect multimodal ground truth (depth, segmentation, damage maps) impossible to obtain from real footage
- Post-train Cosmos WFMs on this specialized dataset to improve physical understanding of:
  - Structural damage patterns and building collapse dynamics
  - Emergency response vehicle navigation through debris
  - Flood and fire propagation in urban environments
  - Search and rescue robot path planning

**2. Disaster Response Applications**
- Train specialized Cosmos models for disaster assessment and emergency response
- Generate training data for autonomous drones surveying damaged infrastructure
- Create synthetic scenarios for testing resilient city planning and building codes
- Enable "what-if" simulations for urban planners and emergency management

### LeRobot Integration for Physical AI Training

Leveraging Hugging Face's **LeRobot framework** (12,000+ GitHub stars) to create an end-to-end physical AI training pipeline that bridges simulation and real-world robotics.

#### Proposed Architecture:

**1. Sim-to-Real Transfer Pipeline**
```
Houdini → Cosmos → LeRobot → Physical Robot
   ↓          ↓          ↓           ↓
3D Scenes  Synthetic  Training   Real-world
           Videos     Dataset    Deployment
```

**2. Implementation Roadmap**
- **Phase 1**: Export Houdini scenes to LeRobot-compatible dataset format
  - Convert multimodal outputs (RGB, depth, segmentation) to LeRobotDataset structure
  - Generate action trajectories for manipulation tasks in destroyed environments
  - Create paired observation-action sequences for imitation learning

- **Phase 2**: Train disaster response behaviors
  - Use LeRobot's PyTorch models with Cosmos-generated synthetic data
  - Implement reinforcement learning for debris clearing tasks
  - Train vision-based navigation through unstable structures
  - Leverage LeRobot's SO-100 ($100 arm) for affordable testing

- **Phase 3**: Scale to multi-robot coordination
  - Generate multi-agent scenarios in Cosmos
  - Train collaborative behaviors for search and rescue
  - Deploy to NVIDIA Jetson edge devices for real-time inference
  - Integrate with ROS2 for production deployment

**3. Technical Advantages**
- **Cost Reduction**: $100 LeRobot hardware vs. $50,000+ industrial robots
- **Safety**: Train dangerous scenarios entirely in simulation first
- **Scale**: Generate millions of training scenarios procedurally
- **Verification**: Perfect ground truth from Houdini eliminates annotation errors
- **Community**: Contribute datasets to Hugging Face hub for research advancement

### Integration with NVIDIA Omniverse and Isaac Sim

Future development will leverage NVIDIA's complete physical AI stack:

- **Omniverse Integration**: Export Houdini scenes to USD format for physics-accurate simulation
- **Isaac Sim**: Validate robot behaviors in high-fidelity physics before real deployment
- **Cosmos Blueprints**: Use NVIDIA's synthetic data generation blueprints for scalable training
- **RTX Acceleration**: Leverage local RTX GPUs for real-time synthetic data generation

This positions the project at the intersection of **procedural generation**, **world models**, and **embodied AI** — three of the most critical areas in physical AI development for 2025 and beyond.
