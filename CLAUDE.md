# CLAUDE.md

## Project Overview
Python-based workflow orchestration for Nvidia Cosmos Transfer video generation with remote GPU execution via SSH/Docker.

## Tech Stack
- **Python 3.x** with Paramiko (SSH), TOML (config), pytest (testing)
- **Nvidia Cosmos Transfer** model at F:/Art/cosmos-transfer1
- **Docker**: `nvcr.io/ubuntu/cosmos-transfer1:latest`
- **Remote GPU**: CUDA 12.4+, PyTorch, 24GB+ VRAM

## Repository Structure
```
cosmos-houdini-experiments/
├── cosmos_workflow/                  # Main Python package
│   ├── config/config.toml           # SSH, paths, Docker config
│   ├── connection/ssh_manager.py    # SSH management
│   ├── execution/docker_executor.py # Docker orchestration
│   ├── prompts/                     # Schema management
│   │   ├── schemas.py               # PromptSpec/RunSpec dataclasses
│   │   ├── prompt_spec_manager.py
│   │   └── run_spec_manager.py
│   ├── transfer/file_transfer.py    # rsync file sync
│   └── cli.py                       # CLI interface
├── inputs/                           # prompts/, runs/, videos/
├── outputs/                          # Generated videos
├── scripts/                          # inference.sh, upscale.sh
└── tests/                           # pytest test suite
```

## Cosmos Transfer Key Files (F:/Art/cosmos-transfer1/)
- `cosmos_transfer1/diffusion/inference/transfer.py` - Main inference
- `cosmos_transfer1/diffusion/inference/transfer_pipeline.py` - Pipeline
- `checkpoints/nvidia/Cosmos-Transfer1-7B/` - Model weights
- `checkpoints/nvidia/Cosmos-UpsamplePrompt1-12B-Transfer/` - Upsampler

## Schema System
**PromptSpec**: Prompt definition without execution params
- Fields: id, name, prompt, negative_prompt, input_video_path, control_inputs
- Location: `inputs/prompts/{date}/{name}_{timestamp}_ps_{hash}.json`

**RunSpec**: Execution configuration with all parameters
- Fields: id, prompt_spec_id, control_weights, parameters, execution_status
- Location: `inputs/runs/{date}/{name}_{timestamp}_rs_{hash}.json`

## Common Commands
```bash
# Create prompt
python -m cosmos_workflow.main create-spec "name" "prompt text"

# Create run with control weights
python -m cosmos_workflow.main create-run prompt_spec.json --weights 0.3 0.4 0.2 0.1

# Execute on remote GPU
python -m cosmos_workflow.main run run_spec.json --num-gpu 2

# Run tests
pytest tests/ --cov=cosmos_workflow
```

## Direct Cosmos Inference (on GPU)
```bash
torchrun --nproc_per_node=$NUM_GPU cosmos_transfer1/diffusion/inference/transfer.py \
    --checkpoint_dir checkpoints \
    --input_video_path video.mp4 \
    --controlnet_specs spec.json \
    --num_gpus $NUM_GPU
```

## Control Modalities
- **vis/blur**: Visual blur control
- **edge**: Canny edge detection
- **depth**: Depth estimation
- **segmentation**: Semantic segmentation
- **lidar/hdmap**: AV-specific controls

## Configuration (config.toml)
```toml
[remote]
host = "192.222.52.92"
user = "ubuntu"
ssh_key = "~/.ssh/LambdaSSHkey.pem"

[paths]
remote_dir = "/home/ubuntu/NatsFS/cosmos-transfer1"
local_prompts_dir = "./inputs/prompts"
local_outputs_dir = "./outputs"

[docker]
image = "nvcr.io/ubuntu/cosmos-transfer1:latest"
```

## Remote Execution Flow
1. Create PromptSpec locally
2. Upload to remote via rsync/SSH
3. Execute inference.sh in Docker container
4. Optional: Run upscale.sh for 4K
5. Download results via rsync

## Important Parameters
- **num_steps**: 35 (default) or 1 (distilled)
- **guidance_scale**: CFG scale (default 8.0)
- **control_weight**: 0.0-1.0 per modality
- **offload_***: Memory optimization flags

## Code Standards
- Type hints throughout
- Dataclasses with validation
- Pathlib for paths
- Comprehensive docstrings
- Test coverage >80%

## Documentation Updates (REQUIRED)
When making changes, update:
- **CHANGELOG.md**: Primary log of ALL changes (development history, completed phases, planned work)
- **README.md**: User-facing features and usage
- **REFERENCE.md**: Technical API documentation
- **CLAUDE.md**: Only major workflow/structure changes
- **docs/implementation/**: Detailed technical implementation docs for completed features

## Known Issues & Solutions
- **Vocab out of range error**: Occurs with high-res videos + prompt upsampling
  - Solution: Manually call upsampling functions instead of --upsample-prompt
- **SSH failures**: Check key permissions (chmod 600)
- **GPU memory**: Use offload flags for optimization

## Phase 2 Focus: Prompt Upsampling
- Implement batch prompt upsampling without inference
- Keep model loaded between runs
- Handle video preprocessing (resolution/frame reduction)
- Work around vocab range bug with high-res inputs

## Testing
```bash
pytest tests/                        # All tests
pytest tests/test_schemas.py -v      # Specific file
pytest --cov=cosmos_workflow tests/  # With coverage
```

## External Resources
- [Cosmos Transfer GitHub](https://github.com/nvidia-cosmos/cosmos-transfer1)
- [Hugging Face Models](https://huggingface.co/collections/nvidia/cosmos-transfer1-67c9d328196453be6e568d3e)
