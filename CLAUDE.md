# CLAUDE.md

This file provides comprehensive guidance to Claude Code (claude.ai/code) when working with code in this repository. 

## Project Overview

This is a **Python-based workflow orchestration system** for running Nvidia Cosmos Transfer video generation experiments with Houdini integration. The system manages remote GPU execution via SSH and Docker containers, orchestrating the entire pipeline from prompt creation to video generation and upscaling.

## Tech Stack

### Core Technologies
- **Python 3.x** - Main programming language
- **Paramiko** (≥3.0.0) - SSH connection management
- **TOML** (≥0.10.0) - Configuration file format
- **Docker** - Container execution environment on remote GPU instances
- **Nvidia Cosmos Transfer** - Video generation AI model (located at F:/Art/cosmos-transfer1)
- **PyTorch** - Deep learning framework (via torchrun)
- **pytest** - Testing framework with coverage support

### Nvidia Cosmos Transfer Dependencies
The Cosmos Transfer model requires:
- CUDA 12.4+ with compatible GPU drivers
- PyTorch with CUDA support
- Specialized dependencies: apex, megatron_core, einops, transformers
- Video processing: decord, imageio, opencv, mediapy
- Model checkpoints (~300GB storage)

## Architecture Overview

### This Repository Structure
```
cosmos-houdini-experiments/           # Orchestration layer
├── cosmos_workflow/                  # Main Python package
│   ├── config/                      # TOML-based configuration management
│   │   └── config.toml             # Central config (SSH, paths, Docker)
│   ├── connection/                  # SSH connectivity via paramiko
│   │   └── ssh_manager.py          # SSH connection handling
│   ├── execution/                   # Docker container orchestration
│   │   └── docker_executor.py      # Container management
│   ├── prompts/                     # Schema-based prompt management
│   │   ├── schemas.py              # PromptSpec/RunSpec dataclasses
│   │   ├── prompt_spec_manager.py  # PromptSpec operations
│   │   ├── run_spec_manager.py     # RunSpec operations
│   │   └── prompt_manager.py       # High-level orchestration
│   ├── transfer/                    # File transfer operations
│   │   └── file_transfer.py        # rsync-based synchronization
│   ├── workflows/                   # High-level workflow orchestration
│   │   └── workflow_orchestrator.py # Main workflow coordinator
│   └── cli.py                      # Command-line interface
│
├── inputs/                          # Organized input data
│   ├── prompts/                    # PromptSpec JSON files (date-organized)
│   ├── runs/                       # RunSpec JSON files (date-organized)
│   └── videos/                     # Input video files by experiment
│
├── outputs/                         # Generated results
├── tests/                          # Comprehensive test suite
└── scripts/                        # Bash scripts for remote execution
    ├── inference.sh                # Run Cosmos Transfer inference
    └── upscale.sh                  # Run 4K upscaling
```

### Nvidia Cosmos Transfer Structure (F:/Art/cosmos-transfer1/)
```
cosmos-transfer1/
├── cosmos_transfer1/               # Main Python module
│   ├── diffusion/                 # Diffusion model implementation
│   │   └── inference/             # Inference scripts
│   │       ├── transfer.py       # Main inference entry point
│   │       ├── transfer_pipeline.py
│   │       └── world_generation_pipeline.py
│   ├── auxiliary/                 # Helper modules
│   ├── checkpointer/              # Model checkpoint handling
│   ├── distillation/              # Model distillation
│   └── utils/                     # Utility functions
│
├── checkpoints/                    # Model weights (download required)
│   ├── nvidia/
│   │   ├── Cosmos-Transfer1-7B/  # Main model weights
│   │   ├── Cosmos-Transfer1-7B-Sample-AV/  # AV-specific models
│   │   ├── Cosmos-Tokenize1-CV8x8x8-720p/  # Video tokenizer
│   │   └── Cosmos-UpsamplePrompt1-12B-Transfer/  # Prompt upsampler
│   └── [other model dependencies]
│
├── examples/                       # Usage examples and documentation
├── scripts/                       # Utility scripts
│   └── download_checkpoints.py   # Download model weights
└── requirements.txt               # Python dependencies
```

## Commands and Development

### Testing Commands
```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_schemas.py

# Run with coverage
pytest --cov=cosmos_workflow tests/

# Run with verbose output
pytest -v tests/
```

### Python Workflow Execution
```bash
# Create a PromptSpec (prompt definition)
python -m cosmos_workflow.main create-spec "name" "prompt text" --negative-prompt "negative text"

# Create a RunSpec (execution configuration) 
python -m cosmos_workflow.main create-run prompt_spec.json --weights 0.3 0.4 0.2 0.1

# Execute workflow (runs on remote GPU via SSH/Docker)
python -m cosmos_workflow.main run run_spec.json --num-gpu 2 --cuda-devices "0,1"

# Check remote status
python -m cosmos_workflow.main status --verbose
```

### Direct Cosmos Transfer Inference (on GPU machine)
```bash
# Basic inference
torchrun --nproc_per_node=$NUM_GPU cosmos_transfer1/diffusion/inference/transfer.py \
    --checkpoint_dir checkpoints \
    --input_video_path path/to/video.mp4 \
    --video_save_name output \
    --controlnet_specs spec.json \
    --num_gpus $NUM_GPU

# With upscaling
torchrun --nproc_per_node=$NUM_GPU cosmos_transfer1/diffusion/inference/transfer.py \
    --checkpoint_dir checkpoints \
    --controlnet_specs upscaler_spec.json \
    --num_steps 10 \
    --num_gpus $NUM_GPU
```

## Schema System

### PromptSpec - Prompt Definition
- **Purpose**: Defines prompts without execution parameters
- **Fields**: id, name, prompt, negative_prompt, input_video_path, control_inputs, metadata
- **File naming**: `{name}_{timestamp}_ps_{hash}.json`
- **Location**: `inputs/prompts/{date}/`

### RunSpec - Execution Configuration
- **Purpose**: Defines actual inference runs with all parameters
- **Fields**: id, prompt_spec_id, control_weights, parameters, execution_status
- **File naming**: `{name}_{timestamp}_rs_{hash}.json`
- **Location**: `inputs/runs/{date}/`
- **Status tracking**: PENDING → RUNNING → SUCCESS/FAILED

### Control Modalities (from Cosmos Transfer)
The system supports multiple control modalities:
- **segmentation**: Semantic segmentation video
- **depth**: Depth estimation video
- **edge**: Canny edge detection video
- **vis/blur**: Visual blur control (BlurStrength enum)
- **lidar**: LiDAR point cloud (AV-specific)
- **hdmap**: HD map data (AV-specific)

## Integration Points

### Key Integration Areas

1. **Prompt Specification Format**
   - Our PromptSpec maps to Cosmos Transfer's controlnet_specs JSON
   - Control inputs (depth, edge, seg, vis) correspond to Cosmos control modalities
   - Text prompts are processed through T5 encoder and optional prompt upsampler

2. **Docker Execution**
   - Scripts (inference.sh, upscale.sh) run inside Docker container
   - Container image: `nvcr.io/ubuntu/cosmos-transfer1:latest`
   - Mounts local directories for input/output data transfer

3. **Remote Execution Flow**
   ```
   Local: Create PromptSpec → Upload to remote → 
   Remote: Run inference.sh in Docker → Generate video →
   Remote: Run upscale.sh in Docker (optional) →
   Local: Download results
   ```

4. **File Transfer Protocol**
   - Uses rsync over SSH for efficient file synchronization
   - Transfers: prompts, input videos, control videos, output videos
   - Preserves directory structure between local and remote

## Cosmos Transfer Reference Points

### Critical Files to Reference
When working with Cosmos Transfer integration:

1. **Inference Entry Points**
   - `cosmos_transfer1/diffusion/inference/transfer.py` - Main inference script
   - `cosmos_transfer1/diffusion/inference/transfer_pipeline.py` - Pipeline logic
   - `cosmos_transfer1/diffusion/inference/inference_utils.py` - Helper functions

2. **Configuration Examples**
   - `examples/inference_cosmos_transfer1_7b.md` - Multi-control inference guide
   - `examples/inference_cosmos_transfer1_7b_4kupscaler.md` - Upscaling guide
   - Control spec JSON format examples in examples/

3. **Model Checkpoints**
   - Base model: `checkpoints/nvidia/Cosmos-Transfer1-7B/base_model.pt`
   - Control models: `{modality}_control.pt` (depth, edge, seg, vis)
   - Upscaler: `4kupscaler_control.pt`

### Important Parameters
- **num_steps**: Diffusion steps (default 35, distilled models use 1)
- **guidance_scale**: CFG scale (default 8.0)
- **control_weight**: Strength of control signal (0.0-1.0)
- **seed**: Random seed for reproducibility
- **offload_***: Memory optimization flags

## Configuration Management

### config.toml Structure
```toml
[remote]
user = "ubuntu"
host = "192.222.52.92"  # GPU instance IP
port = 22
ssh_key = "~/.ssh/LambdaSSHkey.pem"

[paths]
remote_dir = "/home/ubuntu/NatsFS/cosmos-transfer1"
local_prompts_dir = "./inputs/prompts"
local_runs_dir = "./inputs/runs"
local_videos_dir = "./inputs/videos"
local_outputs_dir = "./outputs"

[docker]
image = "nvcr.io/ubuntu/cosmos-transfer1:latest"
```

## Code Standards and Patterns

### Architecture Patterns
- **Service-Oriented Architecture**: Separate managers for each domain
- **Schema-Based Design**: Dataclasses with validation and serialization
- **Manager Pattern**: Specialized managers (PromptSpecManager, RunSpecManager)
- **Configuration Management**: Centralized TOML config with environment overrides

### Python Conventions
- Type hints throughout (Dict, Any, List, Optional, Union)
- Dataclasses with frozen=True for immutability
- Comprehensive docstrings for all classes and methods
- Path objects from pathlib instead of strings
- Context managers for resource handling
- Enum classes for valid values (ExecutionStatus, BlurStrength, CannyThreshold)

### Code Quality Guidelines
- Replace magic numbers with named constants
- Use meaningful, self-documenting names
- Comment on why, not what
- Keep functions small with single responsibility
- Extract repeated code into reusable functions
- Maintain clean structure and encapsulation
- Comprehensive test coverage (unit + integration)

## Recent Development History

### Major Milestones
1. **Complete System Modernization** (commit b281e94)
   - Migrated from bash scripts to Python orchestration
   - Converted config from shell to TOML format
   - Added comprehensive pytest test suite (3,264+ lines)
   - Implemented modern schema-based prompt system

2. **Prompt System Refactor**
   - Separated PromptSpec from RunSpec for reusability
   - Added hash-based unique IDs for traceability
   - Implemented date-organized directory structure
   - Added schema validation and type safety

3. **Testing Infrastructure**
   - Unit tests for all components
   - Integration tests with mocked SSH/Docker
   - High code coverage targets
   - Pre-push testing hooks

## Common Tasks and Workflows

### 1. Running a Simple Generation
```bash
# Create prompt
python -m cosmos_workflow.main create-spec "cityscape" "Futuristic city at night"

# Create run configuration
python -m cosmos_workflow.main create-run inputs/prompts/*/cityscape*.json

# Execute on remote GPU
python -m cosmos_workflow.main run inputs/runs/*/cityscape*.json
```

### 2. Multi-Modal Control Generation
```bash
# Prepare control videos
# Place depth.mp4, edge.mp4, segmentation.mp4 in inputs/videos/experiment_name/

# Create prompt with controls
python -m cosmos_workflow.main create-spec "multimodal" "Aerial view" \
    --input-video inputs/videos/experiment_name/rgb.mp4 \
    --control-inputs depth:inputs/videos/experiment_name/depth.mp4 \
                     edge:inputs/videos/experiment_name/edge.mp4

# Run with custom weights
python -m cosmos_workflow.main create-run prompt.json \
    --weights 0.3 0.3 0.2 0.2
```

### 3. Upscaling Workflow
```bash
# After generation completes, upscale to 4K
python -m cosmos_workflow.main upscale run_spec.json \
    --upscale-weight 0.7
```

## Troubleshooting Guide

### Common Issues

1. **SSH Connection Failures**
   - Verify SSH key permissions: `chmod 600 ~/.ssh/LambdaSSHkey.pem`
   - Check remote host IP in config.toml
   - Ensure remote instance is running

2. **Docker Container Issues**
   - Verify Docker image exists on remote: `docker images`
   - Check CUDA availability: `nvidia-smi`
   - Ensure sufficient GPU memory (>24GB recommended)

3. **File Transfer Problems**
   - Verify rsync is installed on both systems
   - Check directory permissions on remote
   - Ensure sufficient disk space

4. **Model Checkpoint Errors**
   - Download all required checkpoints (~300GB)
   - Verify checkpoint directory structure
   - Check model file integrity

## Performance Optimization

### Memory Management
- Use `--offload_guardrail_models` to reduce GPU memory
- Use `--offload_text_encoder_model` for T5 encoder
- Use `--offload_prompt_upsampler` when using prompt upsampling
- Adjust batch size based on available GPU memory

### Multi-GPU Execution
- Set `NUM_GPU` and `CUDA_VISIBLE_DEVICES` appropriately
- Use torchrun with `--nproc_per_node=$NUM_GPU`
- Ensure model supports distributed inference

### Inference Speed
- Use distilled models (1 step vs 35 steps)
- Reduce num_steps for faster (lower quality) results
- Cache tokenizer outputs when processing multiple videos

## Security Considerations

- Store SSH keys securely with proper permissions
- Use environment variables for sensitive configuration
- Sanitize user inputs in prompts
- Implement rate limiting for API endpoints
- Regular security updates for dependencies

## Future Development Areas

1. **Web Interface**: Flask/FastAPI backend with React frontend
2. **Queue System**: Celery/RabbitMQ for job management
3. **Monitoring**: Prometheus/Grafana for system metrics
4. **Auto-scaling**: Kubernetes deployment for GPU clusters
5. **Model Fine-tuning**: Custom training on domain-specific data
6. **Houdini Integration**: Direct plugin for Houdini workflows

## Important Notes

- Always ensure GPU drivers and CUDA versions are compatible
- Monitor GPU memory usage during inference
- Keep backups of successful prompt configurations
- Document custom modifications for reproducibility
- Test changes locally before deploying to production

## External Resources

- [Nvidia Cosmos Transfer GitHub](https://github.com/nvidia-cosmos/cosmos-transfer1)
- [Hugging Face Models](https://huggingface.co/collections/nvidia/cosmos-transfer1-67c9d328196453be6e568d3e)
- [Cosmos Paper](https://arxiv.org/abs/2503.14492)
- [Product Website](https://www.nvidia.com/en-us/ai/cosmos/)