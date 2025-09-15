# Cosmos Workflow System

**A production Python system that orchestrates NVIDIA Cosmos AI video generation on remote GPU clusters, featuring a custom Houdini procedural city generator for synthetic training data.**

## 📑 Table of Contents
- [Overview](#-what-this-system-does)
- [Web Interface](#️-gradio-web-interface)
- [Technical Implementation](#-technical-achievements)
- [Quick Start](#-quick-start)
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

### Run History Management
![Run History Interface](docs/images/run-history.png)
*Comprehensive run filtering, search, and batch operations*

</td>
</tr>
<tr>
<td width="50%">

### Enhanced Status Indicators
![Enhanced Prompts](docs/images/enhanced-status.png)
*AI enhancement status with visual indicators*

</td>
<td width="50%">

### Multi-tab Run Details
![Run Details](docs/images/run-details.png)
*Professional tabs for General, Parameters, Logs, and Output*

</td>
</tr>
<tr>
<td width="50%">

### Advanced Filtering
![Advanced Filters](docs/images/advanced-filtering.png)
*Multi-criteria filtering with date ranges and text search*

</td>
<td width="50%">

### Professional Design System
![Design System](docs/images/design-system.png)
*Glassmorphism effects, gradients, and loading animations*

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
- SSH-based Docker container management with synchronous execution
- Automatic file transfer with integrity checks
- Real-time log streaming from containers
- Queue management for sequential resource utilization
- Graceful shutdown handling with container cleanup

### **Batch Processing Engine**
- JSONL format for efficient batch operations
- Single model load for multiple inferences
- Streamlined batch execution with shared GPU resources
- Automatic retry and error recovery

### **Synchronous Execution Model**
- Blocking operations that complete before returning control
- Immediate status updates and output downloading
- No background threads or async complexity
- Direct exit code handling from Docker containers

### **Advanced Web Interface (Gradio)**
- **Operations Tab**: Two-column layout with prompt selection and inference controls
- **Run History Tab**: Comprehensive run management with advanced filtering, search, and batch operations
- **Inference Controls**: Adjustable weights for visual, edge, depth, and segmentation controls (0.0-1.0)
- **AI Enhancement**: Prompt enhancement using Pixtral model for improved descriptions with enhanced status indicators
- **Advanced Filtering**: Multi-criteria filtering by status, date range, and text search across all runs
- **Batch Operations**: Select multiple runs with batch delete functionality and selection controls
- **Professional Design**: Gradient animations, glassmorphism effects, and loading skeleton animations
- **Multi-tab Details**: Comprehensive run details with General, Parameters, Logs, and Output tabs
- **Real-time Progress**: Progress tracking with gr.Progress() and completion feedback
- **Theme System**: Professional design with gradient animations and glassmorphism effects
- **Visual Gallery**: Browse and manage generated videos with comprehensive metadata
- **Graceful Shutdown**: Container cleanup on server termination

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
cosmos inference ps_xxxxx --weights 0.3 0.4 0.2 0.1  # Blocks until complete
cosmos status --stream  # Watch live execution logs

# Advanced features
cosmos batch-inference ps_001 ps_002 ps_003  # 40% faster
cosmos upscale --from-run rs_xxxxx --prompt "8K cinematic"
cosmos prompt-enhance ps_xxxxx  # AI prompt improvement
```

## 📚 Documentation

- **[UI Guide](UI_GUIDE.md)** - Comprehensive guide to the Gradio web interface with tab-by-tab walkthrough
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

### Intelligent Data Curation with Cosmos Reason

Leveraging **NVIDIA Cosmos Reason** — a 7B-parameter reasoning vision-language model — to automatically analyze and validate augmented synthetic data from Cosmos Transfer. This ensures only physically accurate and high-quality training data enters the pipeline.

#### Quality Assurance Pipeline:

**1. Automated Physics Validation**
- Deploy Cosmos Reason to analyze Cosmos Transfer augmentation outputs
- Automatically identify and prune physically inaccurate results (e.g., floating debris, impossible structural deformations)
- Validate temporal consistency across video sequences
- Score outputs based on physical plausibility and visual coherence

**2. Intelligent Data Filtering**
- Use Cosmos Reason's understanding of physics and common sense to detect anomalies
- Filter out augmentations with rendering artifacts or domain gaps
- Ensure structural integrity is maintained in disaster scenarios
- Create confidence scores for each augmented sample

### Post-Training NVIDIA Cosmos with Synthetic Disaster Data

This project explores a **self-improving feedback loop** for physical AI models through synthetic data generation and augmentation. The approach focuses on creating specialized training data for rare scenarios that are difficult or dangerous to capture in real life.

#### Planned Enhancement Pipeline:

**1. Synthetic Data Generation & Augmentation Loop**
- Generate initial disaster scenarios using my Houdini procedural system (earthquakes, building collapses, floods)
- Augment this data using NVIDIA Cosmos Transfer/Predict to create diverse variations
- **NEW**: Apply Cosmos Reason to validate physical accuracy before training
- Use the augmented and validated Cosmos-generated data to post-train Cosmos models themselves
- Create a feedback loop where each iteration improves the model's understanding of:
  - Structural damage patterns and physics
  - Environmental variations (weather, lighting, debris patterns)
  - Emergency response scenarios

**2. Applications**
- Specialized models for disaster assessment and emergency response
- Training data for autonomous systems in hazardous environments
- Synthetic scenarios for urban planning and resilience testing

### LeRobot Integration for Physical AI Training

Leveraging Hugging Face's **LeRobot framework** (12,000+ GitHub stars) to create a robust sim-to-real pipeline for robotic training.

#### Planned Approach:

**1. Synthetic Data Pipeline**
- Generate teleoperation data in NVIDIA Omniverse with LeRobot integration
- Augment this data using my Cosmos workflow (Transfer/Predict models)
- Train robots to generalize across diverse environments using augmented datasets

**2. Key Benefits**
- **Cost-effective**: LeRobot's $100 hardware democratizes robotic experimentation
- **Generalization**: Cosmos augmentation helps robots adapt to unseen environments
- **Safety**: Test dangerous scenarios in simulation before real-world deployment

### Integration with NVIDIA Omniverse and Isaac Sim

Future exploration of NVIDIA's physical AI ecosystem for enhanced simulation capabilities, including USD pipeline integration and physics-based validation of synthetic data.

This positions the project at the intersection of **procedural generation**, **world models**, and **embodied AI** — three of the most critical areas in physical AI development for 2025 and beyond.
