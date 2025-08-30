# Cosmos-Houdini Experiments

An advanced Python workflow orchestration system for NVIDIA Cosmos Transfer video generation, featuring AI-powered metadata extraction, modular architecture, and seamless remote GPU execution.

## 🌟 Key Features

### Core Capabilities
- **Automated Video Generation Pipeline**: End-to-end workflow from text prompts to high-quality video output
- **Remote GPU Orchestration**: Execute computationally intensive tasks on remote GPU instances via SSH
- **Docker-Based Execution**: Containerized environment for consistent, reproducible results
- **AI-Enhanced Metadata**: Automatic frame tagging and captioning using transformer models
- **Intelligent Prompt Management**: Schema-based system with validation and reusability
- **4K Video Upscaling**: Built-in support for high-resolution video enhancement

### Technical Highlights
- **Modular Architecture**: Clean separation of concerns with specialized service modules
- **Comprehensive Testing**: 100+ unit and integration tests with high coverage
- **Flexible Configuration**: TOML-based configuration with environment variable overrides
- **Batch Processing**: Support for overnight batch jobs with parameter randomization
- **Error Recovery**: Robust error handling with retry mechanisms and detailed logging

## 🏗️ Architecture

```
cosmos-houdini-experiments/
├── cosmos_workflow/                 # Main Python package
│   ├── config/                     # Configuration management (TOML-based)
│   ├── connection/                 # SSH connectivity via Paramiko
│   ├── execution/                  # Docker orchestration & command building
│   ├── prompts/                    # Schema-based prompt management
│   ├── transfer/                   # File synchronization (rsync)
│   ├── workflows/                  # High-level workflow orchestration
│   ├── local_ai/                   # AI-powered analysis tools
│   └── utils/                      # Reusable utilities & abstractions
├── tests/                          # Comprehensive test suite
├── scripts/                        # Bash scripts for remote execution
└── inputs/outputs/                 # Organized I/O directories
```

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/cosmos-houdini-experiments.git
cd cosmos-houdini-experiments

# Install dependencies
pip install -r requirements.txt

# Configure the system
cp cosmos_workflow/config/config.toml.example cosmos_workflow/config/config.toml
# Edit config.toml with your remote GPU instance details
```

### Basic Usage

```python
# Create a prompt specification
from cosmos_workflow.prompts import PromptSpec

prompt = PromptSpec.create(
    name="cyberpunk_city",
    prompt="Futuristic cyberpunk cityscape at night with neon lights",
    negative_prompt="blurry, low quality, distorted"
)

# Run the workflow
from cosmos_workflow.workflows import WorkflowOrchestrator

orchestrator = WorkflowOrchestrator()
result = orchestrator.run(
    prompt_file=prompt.save(),
    num_gpu=2,
    cuda_devices="0,1"
)
```

## 🎯 Advanced Features

### PNG Sequence to Video Conversion

Convert PNG sequences (from Houdini renders, Nuke compositions, etc.) to videos with AI-generated metadata:

```python
from cosmos_workflow.local_ai import VideoProcessor, VideoMetadataExtractor

# Initialize processor
processor = VideoProcessor()

# Validate PNG sequence
validation = processor.validate_sequence("art/houdini/renders/comp/sequence_001")
if validation["valid"]:
    print(f"Found {validation['frame_count']} frames")
else:
    print(f"Issues: {validation['issues']}")

# Convert to video
frame_paths = sorted(Path("sequence_001").glob("*.png"))
success = processor.create_video_from_frames(
    frame_paths=frame_paths,
    output_path="output.mp4",
    fps=24
)

# Generate AI metadata
extractor = VideoMetadataExtractor(use_ai=True)
metadata = extractor.extract_metadata("output.mp4")
```

**Features:**
- Automatic gap detection in frame sequences
- Support for multiple naming patterns (frame_000.png, image_0.png, etc.)
- Mixed resolution handling
- Video standardization (FPS, resolution adjustment)
- Frame extraction from existing videos

### AI-Powered Video Analysis

The system includes sophisticated AI capabilities for video analysis:

```python
from cosmos_workflow.local_ai import VideoMetadataExtractor

extractor = VideoMetadataExtractor(use_ai=True)
metadata = extractor.extract_metadata("video.mp4")

# Access AI-generated insights
print(f"Caption: {metadata.ai_caption}")
print(f"Tags: {metadata.ai_tags}")
print(f"Detected Objects: {metadata.detected_objects}")
```

**Models Used:**
- **BLIP** (Salesforce): Image captioning
- **ViT** (Google): Image classification for tagging
- **DETR** (Facebook): Object detection

### Schema-Based Prompt Management

The system uses a two-tier schema system for maximum flexibility:

#### PromptSpec
- Defines the creative intent (prompts, video paths, control inputs)
- Reusable across multiple runs with different parameters
- Hash-based unique IDs for version tracking

#### RunSpec
- Execution configuration (weights, inference parameters)
- Tracks execution status (PENDING → RUNNING → SUCCESS/FAILED)
- Links to parent PromptSpec for traceability

### Command Builder Pattern

Clean, maintainable command construction:

```python
from cosmos_workflow.execution import DockerCommandBuilder

builder = DockerCommandBuilder("nvidia/cosmos:latest")
builder.with_gpu()
builder.add_volume("/data", "/workspace/data")
builder.add_environment("CUDA_VISIBLE_DEVICES", "0,1")
builder.set_command("python inference.py")

command = builder.build()  # Returns properly formatted Docker command
```

## 🔧 Configuration

### config.toml Structure

```toml
[remote]
host = "192.168.1.100"
user = "ubuntu"
ssh_key = "~/.ssh/gpu_key.pem"
port = 22

[paths]
remote_dir = "/home/ubuntu/cosmos-transfer1"
local_prompts_dir = "./inputs/prompts"
local_outputs_dir = "./outputs"

[docker]
image = "nvcr.io/nvidia/cosmos-transfer1:latest"
gpu_enabled = true
shm_size = "8g"
```

## 📊 Testing

The project includes comprehensive testing:

```bash
# Run all tests
pytest tests/

# Run with coverage report
pytest --cov=cosmos_workflow tests/

# Run specific test modules
pytest tests/test_workflow_orchestrator.py -v
```

## 🤝 Contributing

Contributions are welcome! The codebase follows:
- **PEP 8** style guidelines
- **Type hints** throughout
- **Comprehensive docstrings**
- **Test-driven development**

## 📝 Documentation

- **README.md**: This file - project overview and usage
- **REFERENCE.md**: Detailed technical documentation
- **DEVELOPMENT_PLAN.md**: Roadmap and development guidelines
- **CLAUDE.md**: AI assistant context and guidelines

## 🚦 Project Status

### Completed Features ✅
- Core workflow orchestration
- SSH/Docker integration
- Schema-based prompt management
- AI-powered metadata extraction
- Comprehensive test suite
- Refactored architecture with clean abstractions

### In Development 🚧
- Batch inference support
- Prompt upsampling feature
- Parameter randomization for testing
- Web UI for monitoring

## 📄 License

This project is proprietary software. All rights reserved.

## 🙏 Acknowledgments

- NVIDIA for the Cosmos Transfer model
- The open-source community for the excellent libraries used
- Contributors and testers who helped improve the system

---

**Author**: [Your Name]  
**Contact**: [Your Email]  
**Last Updated**: August 2024