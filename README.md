# Cosmos + Houdini Experiments

This repository documents experiments combining **Houdini/Nuke procedural outputs** with **NVIDIA Cosmos‑Transfer1** inference. The workflow keeps **Art** (procedural generation) clearly separated from **AI inputs/outputs**, and automates upload → run → download with reproducible logging.

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
├─ scripts/                    # Helper automation (sync, run, full-cycle)
└─ notes/
   ├─ experiment_log.md        # human notes
   └─ run_history.log          # auto-appended command/metadata log
```

> Large binary assets (EXR caches, high-bitrate videos, .hip) should **not** be committed to Git. Store them in cloud storage and curate only needed MP4s into `inputs/videos/` for inference.

---

## Docker Setup

This workflow uses Docker containers for inference on remote instances. **Important**: You must build the custom Docker image on each new instance before running inference.

### **Building the Docker Image**

On your remote instance, navigate to the cosmos-transfer1 directory and run:

```bash
cd /path/to/cosmos-transfer1
docker build -f Dockerfile . -t nvcr.io/$USER/cosmos-transfer1:latest
```

This command:
- Builds a custom image with all required packages pre-installed
- Includes your specific model checkpoints and configuration
- Creates the image tag that your scripts expect (`nvcr.io/$USER/cosmos-transfer1:latest`)

### **Why This is Required**

- **New instances start with no Docker images** - you lose all previously built images
- **Custom configuration** - your image includes specific checkpoints and settings
- **Dependency management** - ensures all required packages are available
- **Reproducibility** - guarantees consistent environment across runs

### **Requirements**

- Docker must be installed on your remote instance
- NVIDIA Container Toolkit must be available for GPU access
- Sufficient disk space for the image (typically 10-20GB)

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

Paths are **relative to the cosmos-transfer1 repository root inside the container** (`/workspace`), because we mount the remote cosmos-transfer1 directory as `/workspace` and set `-w /workspace`.

---

## Scripts Overview

All scripts read shared settings from `scripts/config.sh`:

```bash
# Remote
REMOTE_USER=ubuntu
REMOTE_HOST=<your lambda ip>
REMOTE_PORT=22
SSH_KEY=$HOME/.ssh/LambdaSSHkey.pem
REMOTE_DIR=$HOME/NatsFS/cosmos-transfer1

# Local
LOCAL_PROMPTS_DIR=./inputs/prompts
LOCAL_VIDEOS_DIR=./inputs/videos
LOCAL_OUTPUTS_DIR=./outputs

# Docker image used on remote
DOCKER_IMAGE=nvcr.io/$USER/cosmos-transfer1:latest
```

**Core scripts:**

- `convert_png_sequences.sh <input_directory> <output_name> [frame_count]`  
  Converts PNG sequences (color.####.png, depth.####.png, segmentation.####.png) to MP4 videos and places them in `inputs/videos/<output_name>/` directory. Optional `frame_count` parameter limits conversion to first N frames. Requires ffmpeg to be installed.

- `new_prompt.sh <base_name> "<prompt text>"`  
  Creates `inputs/prompts/<base_name>_<timestamp>.json` and prepares a matching outputs folder.

- `new_prompt.sh --duplicate <existing_prompt.json>`  
  Duplicates an existing prompt with a new timestamp, useful for making variations or running the same prompt multiple times.

- `upload_prompt.sh <prompt.json> [videos_subdir_override]`  
  Uploads the prompt JSON and the matching `inputs/videos/<base_name>/` directory to the remote instance.

- `run_inference_remote.sh <prompt.json>`  
  SSH into the remote and run inference **inside Docker** with live logs. Captures the exact JSON (`spec_used.json`) and a `run.log` in the remote outputs folder.

- `run_upscale_remote.sh <prompt.json> [control_weight]`  
  Runs 4K upscaling on the generated video using the same model. Default control weight is 0.5.

- `download_results.sh <prompt.json>`  
  Fetch results from remote `outputs/<prompt_name>/` into local `./outputs/<prompt_name>/`, including both original and upscaled outputs.

- `full_cycle.sh <prompt.json> [videos_subdir_override] [--no-upscale] [--upscale-weight <weight>]`  
  One command: **upload → run (attached logs) → 4K upscaling → download**, then appends a concise **run record** into `notes/run_history.log` locally.

- `ssh_lambda.sh`  
  Quick SSH to the remote instance using the same config.

---

## Example: End-to-End Run

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
   
   # Or duplicate an existing prompt:
   ./scripts/new_prompt.sh --duplicate inputs/prompts/building_flythrough_v1_20250821_143000.json
   # -> inputs/prompts/building_flythrough_v1_<new_timestamp>.json
   ```

3. **Full-cycle run (upload → run with live logs → 4K upscaling → download)**:
   ```bash
   ./scripts/full_cycle.sh inputs/prompts/building_flythrough_v1_<timestamp>.json
   ```

4. **Inspect results**:
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

5. **Review history** (auto-appended each run):
   ```bash
   cat notes/run_history.log
   ```

---

## PNG Sequence to MP4 Conversion

Before running inference, you'll need to convert your Houdini/Nuke PNG sequences to MP4 videos. The `convert_png_sequences.sh` script automates this process:

### **Requirements**
- **ffmpeg** must be installed and available in your PATH
- PNG sequences must follow the naming convention:
  - `color.####.png` (e.g., color.0001.png, color.0002.png, ...)
  - `depth.####.png` (e.g., depth.0001.png, depth.0002.png, ...)
  - `segmentation.####.png` (e.g., segmentation.0001.png, segmentation.0002.png, ...)

### **Usage**
```bash
./scripts/convert_png_sequences.sh <input_directory> <output_name> [frame_count]
```

**Arguments:**
- `input_directory`: Path to directory containing PNG sequences
- `output_name`: Name of folder to create in `inputs/videos/`
- `frame_count`: Optional - Number of frames to convert (e.g., 50 for frames 1-50)

### **Example Workflow**
1. **Prepare PNG sequences** from Houdini/Nuke:
   ```text
   art/houdini/renders/building_shot1/
     ├─ color.0001.png
     ├─ color.0002.png
     ├─ color.0003.png
     ├─ depth.0001.png
     ├─ depth.0002.png
     ├─ depth.0003.png
     ├─ segmentation.0001.png
     ├─ segmentation.0002.png
     └─ segmentation.0003.png
   ```

2. **Convert to MP4 videos**:
   ```bash
   # Convert all frames
   ./scripts/convert_png_sequences.sh ./art/houdini/renders/building_shot1 building_shot1
   
   # Or convert only first 50 frames
   ./scripts/convert_png_sequences.sh ./art/houdini/renders/building_shot1 building_shot1 50
   ```

3. **Verify output**:
   ```text
   inputs/videos/building_shot1/
     ├─ color.mp4
     ├─ depth.mp4
     └─ segmentation.mp4
   ```

4. **Continue with normal workflow**:
   ```bash
   ./scripts/new_prompt.sh building_shot1 "Cinematic futuristic building interior"
   ./scripts/full_cycle.sh inputs/prompts/building_shot1_<timestamp>.json
   ```

### **Conversion Settings**
- **Frame rate**: 24 fps (assumed, can be modified in the script)
- **Codec**: H.264 with high quality (CRF 18)
- **Pixel format**: yuv420p for maximum compatibility
- **Output**: Overwrites existing files if present

---

## 4K Upscaling

The system automatically runs 4K upscaling after successful video generation, with intelligent error handling:

### **Default Behavior**
- **4K upscaling is enabled by default** after video generation
- Uses control weight of 0.5 by default
- Only runs if video generation succeeds

### **Upscaling Options**

**Disable upscaling:**
```bash
./scripts/full_cycle.sh inputs/prompts/your_prompt.json --no-upscale
```

**Custom control weight:**
```bash
./scripts/full_cycle.sh inputs/prompts/your_prompt.json --upscale-weight 0.8
```

**Combined options:**
```bash
./scripts/full_cycle.sh inputs/prompts/your_prompt.json videos_subdir --upscale-weight 0.7
```

### **Upscaling Process**
1. **Input validation** - Checks if generated video exists before upscaling
2. **Automatic spec generation** - Creates upscaler transfer spec dynamically
3. **Same model architecture** - Uses the same Cosmos-Transfer1 model for upscaling
4. **Comprehensive logging** - Saves full command and spec for reproducibility

### **Output Structure**
```
outputs/
├─ prompt_name_20250822_123456/           # Original generation
│  ├─ output.mp4                          # Generated video
│  ├─ spec_used.json                      # Full inference command + spec
│  ├─ prompt_spec.json                    # Original prompt used
│  └─ run.log                             # Generation logs
└─ prompt_name_20250822_123456_upscaled/ # 4K upscaled
   ├─ output.mp4                          # 4K upscaled video
   ├─ spec_used.json                      # Full upscaling command + spec
   └─ upscale_run.log                     # Upscaling logs
```

---

## Multi‑GPU and TorchRun

Set `NUM_GPU` when you call `run_inference_remote.sh` or `full_cycle.sh` to use torchrun automatically:

```bash
NUM_GPU=2 ./scripts/full_cycle.sh inputs/prompts/building_flythrough_v1_<timestamp>.json
```

The remote command expands to:
```
torchrun --nproc_per_node=$NUM_GPU --nnodes=1 --node_rank=0 cosmos_transfer1/diffusion/inference/transfer.py   --checkpoint_dir ./checkpoints   --video_save_folder outputs/<prompt_name>   --controlnet_specs inputs/prompts/<prompt_name>.json   --offload_text_encoder_model --offload_guardrail_models   --num_gpus $NUM_GPU
```

If `NUM_GPU=1`, it uses plain `python3`.

---

## Enhanced Logging and Error Handling

### **Comprehensive Spec Tracking**
- **`spec_used.json`** - Contains full command, environment variables, and input specs for both generation and upscaling
- **`prompt_spec.json`** - Snapshot of the exact prompt JSON used
- **`run.log`** - Complete stdout/stderr from both generation and upscaling processes

### **Intelligent Error Handling**
- **Dependency checking** - Upscaling only runs if video generation succeeds
- **Graceful failures** - Clear error messages when dependencies are missing
- **Automatic fallbacks** - System continues with available outputs even if some steps fail

### **Reproducibility Features**
- **Exact command capture** - Every run logs the precise command executed
- **Environment snapshots** - GPU settings, checkpoint paths, and other variables are recorded
- **Input validation** - Checks for required files before processing

---

## Notes

- Ensure your remote has the model checkpoints under `${REMOTE_DIR}/../checkpoints` (or set `CHECKPOINT_DIR_REMOTE` in your environment on the call), since REMOTE_DIR now points to the cosmos-transfer1 subdirectory.  
- For gated models, run `huggingface-cli login` inside the container once.  
- If outputs appear owned by root after runs, consider running the container with `-u $(id -u):$(id -g)` or use the `share` alias from the original docs.
