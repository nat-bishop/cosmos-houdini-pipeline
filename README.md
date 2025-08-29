# Cosmos + Houdini Experiments

A production-ready workflow for combining **Houdini/Nuke procedural outputs** with **NVIDIA Cosmos‑Transfer1** inference. This system maintains clear separation between procedural generation and AI processing while providing automated upload → run → download capabilities with comprehensive logging and reproducibility.

---

## Quick Start

1. **Clone and configure** the repository with your remote instance details
2. **Install dependencies**: `pip install -r requirements.txt`
3. **Configure remote settings** in `scripts/config.toml`
4. **Build Docker image** on your remote instance: `docker build -f Dockerfile . -t nvcr.io/$USER/cosmos-transfer1:latest`
5. **Convert PNG sequences** to MP4: `./scripts/convert_png_sequences.sh <input_dir> <output_name>`
6. **Run inference**: `python -m cosmos_workflow.main run <prompt.json>`

---

## Repository Layout

```
project-root/
├─ art/                        # Houdini/Nuke sources (hip, caches, exr, nk, renders) – not fed to inference directly
│  ├─ houdini/
│  └─ nuke/
│
├─ inputs/                     # Finalized, ready-to-run AI inputs (small curated set)
│  ├─ videos/                  # Per-shot folders (multi-modal MP4s)
│  │  └─ building_flythrough_v1/
│  │     ├─ color.mp4
│  │     ├─ depth.mp4
│  │     └─ segmentation.mp4
│  └─ prompts/                 # Prompt JSONs (one per run)
│
├─ outputs/                    # Results fetched from remote runs (one folder per prompt)
│  └─ building_flythrough_v1_20250821_143000/
│     ├─ spec_used.json       # snapshot of the JSON actually used
│     └─ *.mp4                # generated results
│
├─ cosmos_workflow/            # Python workflow system
├─ scripts/                    # Helper automation (convert, config)
└─ notes/
   ├─ experiment_log.md        # human notes
   └─ run_history.log          # auto-appended command/metadata log
```

> Large binary assets (EXR caches, high-bitrate videos, .hip) should **not** be committed to Git. Store them in cloud storage and curate only needed MP4s into `inputs/videos/` for inference.

---

## Configuration

The system uses TOML configuration files for easy customization. Edit `cosmos_workflow/config/config.toml` to set your remote instance details:

```toml
[remote]
user = "ubuntu"
host = "192.222.53.15"  # Your remote instance IP
port = 22
ssh_key = "~/.ssh/LambdaSSHkey.pem"

[paths]
remote_dir = "/home/ubuntu/NatsFS/cosmos-transfer1"
local_prompts_dir = "./inputs/prompts"
local_videos_dir = "./inputs/videos"
local_outputs_dir = "./outputs"
local_notes_dir = "./notes"

[docker]
image = "nvcr.io/ubuntu/cosmos-transfer1:latest"
```

Environment variables can override any setting (e.g., `export REMOTE_HOST="192.168.1.100"`).

---

## Multimodal Prompt Spec

Example (`inputs/prompts/building_flythrough_v1.json`):

```json
{
  "prompt": "A futuristic skyscraper interior flythrough with glowing neon signs...",
  "input_video_path": "inputs/videos/building_flythrough_v1/color.mp4",
  "vis":   { "control_weight": 0.25 },
  "edge":  { "control_weight": 0.25 },
  "depth": { "input_control": "inputs/videos/building_flythrough_v1/depth.mp4", "control_weight": 0.25 },
  "seg":   { "input_control": "inputs/prompts/building_flythrough_v1/segmentation.mp4", "control_weight": 0.25 }
}
```

Paths are **relative to the cosmos-transfer1 repository root inside the container** (`/workspace`).

---

## Python Workflow System

The modern Python-based workflow system provides better error handling, cross-platform compatibility, and real-time progress tracking.

### **Quick Start**
```bash
# Run complete workflow (upload → run → upscale → download)
python -m cosmos_workflow.main run prompt.json

# Run only inference
python -m cosmos_workflow.main inference prompt.json

# Run only upscaling
python -m cosmos_workflow.main upscale prompt.json

# Check remote status
python -m cosmos_workflow.main status
```

### **Advanced Usage**
```bash
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

---

## Example: End-to-End Workflow

1. **Prepare inputs** (from Houdini/Nuke) into `inputs/videos/building_flythrough_v1/`:
   ```text
   inputs/videos/building_flythrough_v1/
     ├─ color.mp4
     ├─ depth.mp4
     └─ segmentation.mp4
   ```

2. **Create a prompt JSON**:
   ```bash
   ./scripts/new_prompt.sh building_flythrough_v1 "Cinematic night look with neon accents"
   # -> inputs/prompts/building_flythrough_v1_<timestamp>.json
   ```

3. **Run complete workflow**:
   ```bash
   python -m cosmos_workflow.main run inputs/prompts/building_flythrough_v1_<timestamp>.json
   ```

4. **Output structure**:
   ```text
   outputs/building_flythrough_v1_<timestamp>/
     ├─ spec_used.json          # full inference command + spec
     ├─ prompt_spec.json        # original prompt used
     ├─ run.log                 # environment + command + stdout/stderr
     └─ output.mp4              # generated video
   
   outputs/building_flythrough_v1_<timestamp>_upscaled/
     ├─ spec_used.json          # full upscaling command + spec
     └─ output.mp4              # 4K upscaled video
   ```

---

## PNG Sequence to MP4 Conversion

The `convert_png_sequences.sh` script automates conversion of Houdini/Nuke PNG sequences to MP4 videos:

```bash
./scripts/convert_png_sequences.sh <input_directory> <output_name> [frame_count]
```

**Requirements**: ffmpeg must be installed and available in your PATH.

**PNG naming convention**:
- `color.####.png` (e.g., color.0001.png, color.0002.png, ...)
- `depth.####.png` (e.g., depth.0001.png, depth.0002.png, ...)
- `segmentation.####.png` (e.g., segmentation.0001.png, segmentation.0002.png, ...)

---

## Docker Setup

This workflow uses Docker containers for inference on remote instances. Build the custom Docker image on each new instance:

```bash
cd /path/to/cosmos-transfer1
docker build -f Dockerfile . -t nvcr.io/$USER/cosmos-transfer1:latest
```

**Requirements**:
- Docker with NVIDIA Container Toolkit support
- Sufficient disk space for the image (typically 10-20GB)
- Access to model checkpoints and configuration files

---

## Technical Notes

- Model checkpoints should be located under `${REMOTE_DIR}/../checkpoints` or configured via `CHECKPOINT_DIR_REMOTE` environment variable
- Gated models require `huggingface-cli login` authentication inside the container
- Container user permissions may need adjustment with `-u $(id -u):$(id -g)` for proper file ownership

---

## Documentation

- **Reference Guide**: See [REFERENCE.md](REFERENCE.md) for comprehensive details
- **Python API**: See [cosmos_workflow/README.md](cosmos_workflow/README.md) for Python workflow documentation
